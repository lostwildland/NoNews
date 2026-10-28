//
//  WidgetDataEncoder.swift
//  NetNewsWire
//
//  Created by Stuart Breckenridge on 18/11/20.
//  Copyright © 2020 Ranchero Software. All rights reserved.
//

import Foundation
import WidgetKit
import os
import UIKit
import RSCore
import Articles
import Account

@MainActor final class WidgetDataEncoder {
	static let shared = WidgetDataEncoder()

	var isRunning = false

	private let fetchLimit = 7
	private let imageContainer: URL
	private let dataURL: URL

	private static let logger = Logger(subsystem: Logger.nnwSubsystem, category: "WidgetDataEncoder")

	#if DEBUG
	var fetchWidgetDataForTesting: (() async throws -> WidgetData)?
	#endif

	convenience init?() {
		guard let appGroup = Bundle.main.object(forInfoDictionaryKey: "AppGroup") as? String else {
			Self.logger.error("WidgetDataEncoder: unable to create appGroup")
			return nil
		}
		guard let containerURL = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: appGroup) else {
			Self.logger.error("WidgetDataEncoder: unable to create containerURL")
			return nil
		}

		self.init(containerURL: containerURL)
	}

	init?(containerURL: URL) {
		self.imageContainer = containerURL.appendingPathComponent("widgetImages", isDirectory: true)
		self.dataURL = containerURL.appendingPathComponent("widget-data.json")

		do {
			try FileManager.default.createDirectory(at: imageContainer, withIntermediateDirectories: true, attributes: nil)
		} catch {
			Self.logger.error("WidgetDataEncoder: unable to create folder for images")
			return nil
		}

		NotificationCenter.default.addObserver(self, selector: #selector(handleUnreadCountDisplaySettingDidChange(_:)), name: .unreadCountDisplaySettingDidChange, object: nil)
	}

	@objc func handleUnreadCountDisplaySettingDidChange(_ notification: Notification) {
		encode()
	}

	/// Fire-and-forget. Sets `isRunning` synchronously so the background-task wait loop
	/// (see AppDelegate.waitToComplete) holds the app awake until encoding finishes.
	func encode() {
		guard !isRunning else {
			Self.logger.debug("WidgetDataEncoder: skipping encode because already in encode")
			return
		}
		isRunning = true
		Task { @MainActor in
			await performEncode()
		}
	}

	/// Awaitable variant for callers that must finish encoding before suspending the app.
	func encodeAndWait() async {
		guard !isRunning else {
			Self.logger.debug("WidgetDataEncoder: skipping encode because already in encode")
			return
		}
		isRunning = true
		await performEncode()
	}

	private func performEncode() async {
		defer { isRunning = false }
		do {
			let (latestData, existingData) = try await WidgetSnapshotStore.publish(dataURL: dataURL, imageDirectory: imageContainer) {
				#if DEBUG
				if let fetchWidgetDataForTesting { return try await fetchWidgetDataForTesting() }
				#endif
				return try await fetchWidgetData()
			}
			reloadTimelines(newData: latestData, existingData: existingData)
		} catch {
			Self.logger.error("WidgetDataEncoder: could not publish widget data: \(error.localizedDescription)")
		}
	}

	func reloadTimelines(newData: WidgetData, existingData: WidgetData?) {
		if let existingData = existingData {
			if existingData.effectiveUnreadCountDisplay != newData.effectiveUnreadCountDisplay {
				WidgetCenter.shared.reloadAllTimelines()
				Self.logger.debug("WidgetDataEncoder: Reloading all widgets because unread count display changed")
				return
			}

			var shouldRefreshSummary = false

			if existingData.unreadArticles != newData.unreadArticles {
				WidgetCenter.shared.reloadTimelines(ofKind: "com.ranchero.NetNewsWire.UnreadWidget")
				shouldRefreshSummary = true
				Self.logger.debug("WidgetDataEncoder: Reloading Unread widget")
			}

			if existingData.todayArticles != newData.todayArticles || existingData.totalTodayUnreadCount != newData.totalTodayUnreadCount {
				WidgetCenter.shared.reloadTimelines(ofKind: "com.ranchero.NetNewsWire.TodayWidget")
				shouldRefreshSummary = true
				Self.logger.debug("WidgetDataEncoder: Reloading Today widget")
			}

			if existingData.starredArticles != newData.starredArticles {
				WidgetCenter.shared.reloadTimelines(ofKind: "com.ranchero.NetNewsWire.StarredWidget")
				shouldRefreshSummary = true
				Self.logger.debug("WidgetDataEncoder: Reloading Starred widget")
			}

			if shouldRefreshSummary {
				WidgetCenter.shared.reloadTimelines(ofKind: "com.ranchero.NetNewsWire.LockScreenSummaryWidget")
				Self.logger.debug("WidgetDataEncoder: Reloading Summary widget")
			}
		}
	}

}

@MainActor private extension WidgetDataEncoder {

	func fetchWidgetData() async throws -> WidgetData {
		let fetchedUnreadArticles = try await AccountManager.shared.fetchArticlesAsync(.unread(fetchLimit))
		let unreadArticles = sortedLatestArticles(fetchedUnreadArticles)

		let fetchedStarredArticles = try await AccountManager.shared.fetchArticlesAsync(.starred(fetchLimit))
		let starredArticles = sortedLatestArticles(fetchedStarredArticles)

		let fetchedTodayArticles = try await AccountManager.shared.fetchArticlesAsync(.today(fetchLimit))
		let todayArticles = sortedLatestArticles(fetchedTodayArticles)

		let totalTodayCount = try await AccountManager.shared.fetchCountForTodayArticlesAsync()
		let totalTodayUnreadCount = try await AccountManager.shared.fetchUnreadCountForTodayAsync()
		let totalStarredCount = try await AccountManager.shared.fetchCountForStarredArticlesAsync()

		let latestData = WidgetData(totalUnreadCount: SmartFeedsController.shared.unreadFeed.unreadCount,
									totalTodayCount: totalTodayCount,
									totalTodayUnreadCount: totalTodayUnreadCount,
									totalStarredCount: totalStarredCount,
									unreadArticles: unreadArticles,
									starredArticles: starredArticles,
									todayArticles: todayArticles,
									lastUpdateTime: Date.now,
									unreadCountDisplay: AppDefaults.unreadCountDisplay)

		return latestData
	}

	func fileExists() -> Bool {
		FileManager.default.fileExists(atPath: dataURL.path)
	}

	func writeImageDataToSharedContainer(_ imageData: Data?) -> String? {
		guard let imageData, let md5 = imageData.md5String else {
			return nil
		}

		let imagePath = imageContainer.appendingPathComponent(md5, isDirectory: false)
		let fm = FileManager.default
		if fm.fileExists(atPath: imagePath.path) {
			Self.logger.debug("WidgetDataEncoder: favicon already exists. Will not write again.")
			return imagePath.path
		}
		do {
			try imageData.write(to: imagePath)
			return imagePath.path
		} catch {
			return nil
		}
	}


	func createLatestArticle(_ article: Article) -> LatestArticle {
		let truncatedTitle = ArticleStringFormatter.shared.truncatedTitle(article)
		let articleTitle = truncatedTitle.isEmpty ? ArticleStringFormatter.shared.truncatedSummary(article) : truncatedTitle

		let feedIconPath = writeImageDataToSharedContainer(article.iconImage()?.image.dataRepresentation())

		let pubDate = article.datePublished?.description ?? ""

		let latestArticle = LatestArticle(id: article.articleID,
										  feedTitle: article.feed?.nameForDisplay ?? "",
										  articleTitle: articleTitle,
										  articleSummary: article.summary,
										  feedIconPath: feedIconPath,
										  pubDate: pubDate)
		return latestArticle
	}

	func sortedLatestArticles(_ fetchedArticles: Set<Article>) -> [LatestArticle] {
		let latestArticles = fetchedArticles.map(createLatestArticle)
		return latestArticles.sorted(by: { $0.pubDate > $1.pubDate })
	}
}
