import Darwin
import Foundation
import Testing
@testable import NetNewsWire

@MainActor @Suite struct WidgetSnapshotStoreTests {
	@Test func failedFetchPreservesSnapshotAndSuccessfulPublishProtectsReferencedIcons() async throws {
		let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
		try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
		defer { try? FileManager.default.removeItem(at: root) }
		let images = root.appendingPathComponent("images", isDirectory: true)
		try FileManager.default.createDirectory(at: images, withIntermediateDirectories: false)
		let kept = images.appendingPathComponent("kept")
		let stale = images.appendingPathComponent("stale")
		try Data("icon".utf8).write(to: kept)
		try Data("old".utf8).write(to: stale)
		let past = Int(Date().addingTimeInterval(-3600).timeIntervalSince1970)
		var times = [timeval(tv_sec: past, tv_usec: 0), timeval(tv_sec: past, tv_usec: 0)]
		#expect(utimes(kept.path, &times) == 0 && utimes(stale.path, &times) == 0)
		let article = LatestArticle(id: "fixture", feedTitle: "Fixture", articleTitle: nil, articleSummary: nil, feedIconPath: kept.path, pubDate: "")
		let snapshot = WidgetData(totalUnreadCount: 1, totalTodayCount: 0, totalTodayUnreadCount: 0, totalStarredCount: 0, unreadArticles: [article], starredArticles: [], todayArticles: [], lastUpdateTime: Date(), unreadCountDisplay: nil)
		let dataURL = root.appendingPathComponent("widget-data.json")
		let previous = try JSONEncoder().encode(snapshot)
		try previous.write(to: dataURL)
		await #expect(throws: CancellationError.self) {
			_ = try await WidgetSnapshotStore.publish(dataURL: dataURL, imageDirectory: images) { throw CancellationError() }
		}
		#expect(try Data(contentsOf: dataURL) == previous)
		#expect(FileManager.default.fileExists(atPath: kept.path) && FileManager.default.fileExists(atPath: stale.path))
		let invalid = WidgetData(totalUnreadCount: 1, totalTodayCount: 0, totalTodayUnreadCount: 0, totalStarredCount: 0, unreadArticles: [article], starredArticles: [], todayArticles: [], lastUpdateTime: Date(timeIntervalSince1970: .infinity), unreadCountDisplay: nil)
		await #expect(throws: (any Error).self) {
			_ = try await WidgetSnapshotStore.publish(dataURL: dataURL, imageDirectory: images) { invalid }
		}
		#expect(try Data(contentsOf: dataURL) == previous)
		#expect(FileManager.default.fileExists(atPath: kept.path) && FileManager.default.fileExists(atPath: stale.path))
		try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: root.path)
		defer { try? FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: root.path) }
		await #expect(throws: (any Error).self) {
			_ = try await WidgetSnapshotStore.publish(dataURL: dataURL, imageDirectory: images) { snapshot }
		}
		try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: root.path)
		#expect(try Data(contentsOf: dataURL) == previous)
		#expect(FileManager.default.fileExists(atPath: kept.path) && FileManager.default.fileExists(atPath: stale.path))
		_ = try await WidgetSnapshotStore.publish(dataURL: dataURL, imageDirectory: images) { snapshot }
		let published = try JSONDecoder().decode(WidgetData.self, from: Data(contentsOf: dataURL))
		#expect(published.unreadArticles.first?.feedIconPath == kept.path)
		#expect(FileManager.default.fileExists(atPath: kept.path))
		#expect(!FileManager.default.fileExists(atPath: stale.path))
	}
}
