//
//  Downloader.swift
//  RSWeb
//
//  Created by Brent Simmons on 8/27/16.
//  Copyright © 2016 Ranchero Software, LLC. All rights reserved.
//

import Foundation
import os
import RSCore

public typealias DownloadCallback = @MainActor (DownloadResponse, Error?) -> Swift.Void

/// Simple downloader, for a one-shot download like an image
/// or a web page. For a download-feeds session, see DownloadSession.
/// Caches response for a short time for GET requests. May return cached response.
@MainActor public final class Downloader {
	private struct RequestKey: Hashable, Sendable {
		let url: URL
		let testID: String?
		var cacheKey: String {
			guard let testID else {
				return url.absoluteString
			}
			return "\(testID.utf8.count):\(testID)\(url.absoluteString)"
		}
	}

	public static let shared = Downloader()
	private let urlSession: URLSession
	private var callbacks = [RequestKey: [(callback: DownloadCallback, fromCache: Bool)]]()
	private let cache = DownloadCache.shared

	nonisolated private static let logger = Logger(subsystem: Logger.nnwSubsystem, category: "Downloader")

	private init() {
		let sessionConfiguration = URLSessionConfiguration.ephemeral
		if Platform.isRunningUnitTests {
			sessionConfiguration.protocolClasses = [TestingURLProtocol.self]
		}
		sessionConfiguration.requestCachePolicy = .reloadIgnoringLocalCacheData
		sessionConfiguration.httpShouldSetCookies = false
		sessionConfiguration.httpCookieAcceptPolicy = .never
		sessionConfiguration.httpMaximumConnectionsPerHost = 1
		sessionConfiguration.httpCookieStorage = nil

		if let userAgentHeaders = UserAgent.headers() {
			sessionConfiguration.httpAdditionalHeaders = userAgentHeaders
		}

		urlSession = URLSession(configuration: sessionConfiguration)
	}

	deinit {
		urlSession.invalidateAndCancel()
	}

	public func download(_ url: URL, userAgentStyle: UserAgentStyle = .feed) async throws -> DownloadResponse {
		try await download(URLRequest(url: url), userAgentStyle: userAgentStyle)
	}

	public func download(_ urlRequest: URLRequest, userAgentStyle: UserAgentStyle = .feed) async throws -> DownloadResponse {
		try await withCheckedThrowingContinuation { continuation in
			download(urlRequest, userAgentStyle: userAgentStyle) { downloadResponse, error in
				if let error {
					continuation.resume(throwing: error)
				} else {
					continuation.resume(returning: downloadResponse)
				}
			}
		}
	}

	public func download(_ url: URL, userAgentStyle: UserAgentStyle = .feed, _ callback: @escaping DownloadCallback) {
		assert(Thread.isMainThread)
		download(URLRequest(url: url), userAgentStyle: userAgentStyle, callback)
	}

	public func download(_ urlRequest: URLRequest, userAgentStyle: UserAgentStyle = .feed, _ callback: @escaping DownloadCallback) {
		assert(Thread.isMainThread)

		guard let url = urlRequest.url else {
			Self.logger.fault("Downloader: skipping download for URLRequest without a URL")
			return
		}

		guard url.isHTTPOrHTTPSURL() else {
			Self.logger.debug("Downloader: skipping download for non-http/https URL: \(url)")
			callback(DownloadResponse(data: nil, response: nil, returnedFromCache: false), nil)
			return
		}

		let isCacheableRequest = urlRequest.httpMethod == HTTPMethod.get
		let key = RequestKey(url: url, testID: Platform.isRunningUnitTests ? TestingURLProtocol.currentTestID : nil)

		// Return cached record if available.
		if isCacheableRequest {
			if let cachedRecord = cache[key.cacheKey] {
				Self.logger.debug("Downloader: returning cached record for \(url)")
				callback(DownloadResponse(data: cachedRecord.data, response: cachedRecord.response, returnedFromCache: true), nil)
				return
			}
		}

		// Add callback. If there is already a download in progress for this URL, return early.
		if callbacks[key] == nil {
			Self.logger.debug("Downloader: downloading \(url)")
			callbacks[key] = [(callback, false)]
		} else {
			// A download is already in progress for this URL. Don’t start a separate download.
			// Add the callback to the callbacks array for this URL. This caller is coalesced
			// onto the in-progress download, so it makes no network request of its own.
			Self.logger.debug("Downloader: download in progress for \(url) — adding callback")
			callbacks[key]?.append((callback, true))
			return
		}

		var urlRequestToUse = urlRequest
		if let testID = key.testID {
			urlRequestToUse.setValue(testID, forHTTPHeaderField: TestingURLProtocol.testIDHeaderField)
		}
		switch userAgentStyle {
		case .feed:
			break // the session's user agent
		case .specialCaseFeed:
			urlRequestToUse.setValue(UserAgent.extendedUserAgent, forHTTPHeaderField: HTTPRequestHeader.userAgent)
		case .browser:
			urlRequestToUse.setValue(UserAgent.browserUserAgent, forHTTPHeaderField: HTTPRequestHeader.userAgent)
		}
		urlRequestToUse.addSpecialCaseUserAgentIfNeeded() // Host requirements win over the requested style.

		let task = urlSession.dataTask(with: urlRequestToUse) { (data, response, error) in

			// Don’t cache errors — a retry should hit the network.
			if isCacheableRequest && error == nil {
				Self.logger.debug("Downloader: caching response for \(url)")
				self.cache.add(key.cacheKey, data: data, response: response)
			}

			Task { @MainActor in
				self.callAndReleaseCallbacks(key, data, response, error)
			}
		}
		task.resume()
	}
}

private extension Downloader {

	private func callAndReleaseCallbacks(_ key: RequestKey, _ data: Data? = nil, _ response: URLResponse? = nil, _ error: Error? = nil) {
		assert(Thread.isMainThread)
		let url = key.url

		guard let callbacksForURL = callbacks[key] else {
			assertionFailure("Downloader: downloaded URL \(url) but no callbacks found")
			Self.logger.fault("Downloader: downloaded URL \(url) but no callbacks found")
			return
		}

		// Release before calling — a callback may start a new download of the same URL.
		callbacks[key] = nil

		let count = callbacksForURL.count
		if count == 1 {
			Self.logger.debug("Downloader: calling 1 callback for URL \(url)")
		} else {
			Self.logger.debug("Downloader: calling \(count) callbacks for URL \(url)")
		}

		for entry in callbacksForURL {
			let downloadResponse = DownloadResponse(data: data, response: response, returnedFromCache: entry.fromCache)
			entry.callback(downloadResponse, error)
		}
	}
}
