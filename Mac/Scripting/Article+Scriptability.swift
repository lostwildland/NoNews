//
//  Article+Scriptability.swift
//  NetNewsWire
//
//  Created by Olof Hellman on 1/23/18.
//  Copyright © 2018 Olof Hellman. All rights reserved.
//

import Foundation
import Account
import Articles

@objc(ScriptableArticle)
@MainActor final class ScriptableArticle: NSObject, UniqueIDScriptingObject, @preconcurrency ScriptingObjectContainer {
    let article: Article
    nonisolated(unsafe) let container: ScriptingObjectContainer

    init (_ article: Article, container: ScriptingObjectContainer) {
        self.article = article
        self.container = container
    }

    @objc(objectSpecifier)
    nonisolated override var objectSpecifier: NSScriptObjectSpecifier? {
        let scriptObjectSpecifier = self.container.makeFormUniqueIDScriptObjectSpecifier(forObject: self)
        return scriptObjectSpecifier
    }

    // MARK: - ScriptingObject protocol

    nonisolated var scriptingKey: String {
        "articles"
    }

    // MARK: - UniqueIdScriptingObject protocol

    // articles have id in the NetNewsWire database and id in the feed
    // article.uniqueID here is the feed unique id

    @objc(uniqueId)
    nonisolated var scriptingUniqueID: Any {
        article.uniqueID
    }

    // MARK: - ScriptingObjectContainer protocol

    nonisolated var scriptingClassDescription: NSScriptClassDescription {
        return self.classDescription as! NSScriptClassDescription
    }

    func deleteElement(_ element: ScriptingObject) {
        print("delete event not handled")
    }

    // MARK: - Scriptable properties

    @objc(url)
    var url: String? {
		article.preferredLink
    }

    @objc(permalink)
    var permalink: String? {
        article.link
    }

    @objc(externalUrl)
    var externalUrl: String? {
        article.externalLink
    }

    @objc(title)
    var title: String {
        article.title ?? ""
    }

    @objc(contents)
    var contents: String {
       article.contentText ?? ""
    }

    @objc(html)
    var html: String {
        article.contentHTML ?? ""
    }

    @objc(summary)
    var summary: String {
        article.summary ?? ""
    }

    @objc(datePublished)
    var datePublished: Date? {
        article.datePublished
    }

    @objc(dateModified)
    var dateModified: Date? {
        article.dateModified
    }

    @objc(dateArrived)
    var dateArrived: Date {
        article.status.dateArrived
    }

    @objc(read)
    var read: Bool {
		get {
			article.status.boolStatus(forKey: .read)
		}
		set {
			markForScript(.read, flag: newValue)
		}
    }

    @objc(starred)
    var starred: Bool {
		get {
			article.status.boolStatus(forKey: .starred)
		}
		set {
			markForScript(.starred, flag: newValue)
		}
    }

	private func markForScript(_ key: ArticleStatus.Key, flag: Bool) {
		guard let command = NSScriptCommand.current() else {
			markArticles([article], statusKey: key, flag: flag)
			return
		}
		command.suspendExecution()
		markArticles([article], statusKey: key, flag: flag) { result in
			if let error = result.failed.values.first {
				command.scriptErrorNumber = -128
				command.scriptErrorString = error.localizedDescription
			}
			command.resumeExecution(withResult: nil)
		}
	}

    @objc(deleted)
    var deleted: Bool {
        false
    }

    @objc(imageURL)
    var imageURL: String {
        article.imageLink ?? ""
    }

    @objc(authors)
    var authors: NSArray {
        let articleAuthors = article.authors ?? []
        return articleAuthors.map { ScriptableAuthor($0, container: self) } as NSArray
    }

	@objc(feed)
	var feed: ScriptableFeed? {
		guard let parentFeed = self.article.feed else {
			return nil
		}
		return ScriptableFeed.scriptableFeed(for: parentFeed)
	}
}
