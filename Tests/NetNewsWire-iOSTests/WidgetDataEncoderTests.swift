import Darwin
import Foundation
import Testing
@testable import NetNewsWire

@MainActor @Suite struct WidgetDataEncoderTests {
	@Test func failedFetchPreservesPublishedDataAndSuccessfulPublishRetainsReferencedIcons() async throws {
		let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
		try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
		defer { try? FileManager.default.removeItem(at: root) }
		let encoder = try #require(WidgetDataEncoder(containerURL: root))
		let icons = root.appendingPathComponent("widgetImages", isDirectory: true)
		let kept = icons.appendingPathComponent("kept")
		let stale = icons.appendingPathComponent("stale")
		try Data("icon".utf8).write(to: kept)
		try Data("old".utf8).write(to: stale)
		let past = Int(Date().addingTimeInterval(-3600).timeIntervalSince1970)
		var times = [timeval(tv_sec: past, tv_usec: 0), timeval(tv_sec: past, tv_usec: 0)]
		#expect(utimes(kept.path, &times) == 0)
		#expect(utimes(stale.path, &times) == 0)
		let article = LatestArticle(id: "fixture", feedTitle: "Fixture", articleTitle: nil, articleSummary: nil, feedIconPath: kept.path, pubDate: "")
		let snapshot = WidgetData(totalUnreadCount: 1, totalTodayCount: 0, totalTodayUnreadCount: 0, totalStarredCount: 0, unreadArticles: [article], starredArticles: [], todayArticles: [], lastUpdateTime: Date(), unreadCountDisplay: nil)
		let dataURL = root.appendingPathComponent("widget-data.json")
		let previous = try JSONEncoder().encode(snapshot)
		try previous.write(to: dataURL)
		encoder.fetchWidgetDataForTesting = { throw CancellationError() }
		await encoder.encodeAndWait()
		#expect(try Data(contentsOf: dataURL) == previous)
		#expect(FileManager.default.fileExists(atPath: kept.path))
		#expect(FileManager.default.fileExists(atPath: stale.path))
		encoder.fetchWidgetDataForTesting = { snapshot }
		await encoder.encodeAndWait()
		let published = try JSONDecoder().decode(WidgetData.self, from: Data(contentsOf: dataURL))
		#expect(published.unreadArticles.first?.feedIconPath == kept.path)
		#expect(FileManager.default.fileExists(atPath: kept.path))
		#expect(!FileManager.default.fileExists(atPath: stale.path))
	}
}
