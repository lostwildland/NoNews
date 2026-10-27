//
//  InitialFeedDownloader.swift
//  NetNewsWire
//
//  Created by Brent Simmons on 9/3/16.
//  Copyright © 2016 Ranchero Software, LLC. All rights reserved.
//

import Foundation
import RSParser
import RSWeb
import FeedFinder

struct InitialFeedDownloader {
	#if DEBUG
	@MainActor static var afterDownloadForTesting: (() async -> Void)?
	#endif

	@MainActor static func download(_ url: URL) async throws -> (ParsedFeed?, URLResponse?) {
		// Route through FeedFinder.downloadAndLog so the fetch shows up in the
		// activity log alongside the candidate fetches that preceded it.
		let downloadResponse = try await FeedFinder.downloadAndLog(url)
		guard let data = downloadResponse.data else {
			return (nil, downloadResponse.response)
		}

		let parserData = ParserData(url: url.absoluteString, data: data)
		let parsedFeed = try await FeedParser.parse(parserData)
		#if DEBUG
		await afterDownloadForTesting?()
		#endif
		return (parsedFeed, downloadResponse.response)
	}
}
