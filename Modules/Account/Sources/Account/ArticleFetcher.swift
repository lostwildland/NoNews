//
//  ArticleFetcher.swift
//  NetNewsWire
//
//  Created by Brent Simmons on 2/4/18.
//  Copyright © 2018 Ranchero Software, LLC. All rights reserved.
//

import Foundation
import Articles
import ArticlesDatabase

@MainActor public protocol ArticleFetcher {
	func fetchArticles() throws -> Set<Article>
	func fetchArticlesAsync() async throws -> Set<Article>
	func fetchUnreadArticles() throws -> Set<Article>
	func fetchUnreadArticlesAsync() async throws -> Set<Article>
}

extension Feed: ArticleFetcher {

	public func fetchArticles() throws -> Set<Article> {
		guard let account else { throw CancellationError() }
		return try account.fetchArticles(.feed(self))
	}

	public func fetchArticlesAsync() async throws -> Set<Article> {
		guard let account else {
			throw CancellationError()
		}
		return try await account.fetchArticlesAsync(.feed(self))
	}

	public func fetchUnreadArticles() throws -> Set<Article> {
		try fetchArticles().unreadArticles()
	}

	public func fetchUnreadArticlesAsync() async throws -> Set<Article> {
		guard let account else {
			throw CancellationError()
		}
		// TODO: fetch only unread articles rather than filtering.
		let articles = try await account.fetchArticlesAsync(.feed(self))
		return articles.unreadArticles()
	}
}

extension Folder: ArticleFetcher {

	public func fetchArticles() throws -> Set<Article> {
		guard let account else {
			throw CancellationError()
		}
		return try account.fetchArticles(.folder(self, false))
	}

	public func fetchArticlesAsync() async throws -> Set<Article> {
		guard let account else {
			throw CancellationError()
		}
		return try await account.fetchArticlesAsync(.folder(self, false))
	}

	public func fetchUnreadArticles() throws -> Set<Article> {
		guard let account else {
			throw CancellationError()
		}
		return try account.fetchArticles(.folder(self, true))
	}

	public func fetchUnreadArticlesAsync() async throws -> Set<Article> {
		guard let account else {
			throw CancellationError()
		}
		return try await account.fetchArticlesAsync(.folder(self, true))
	}
}
