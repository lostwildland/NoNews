import Foundation
import os

@MainActor enum WidgetSnapshotStore {
	private static let logger = Logger(subsystem: Logger.nnwSubsystem, category: "WidgetSnapshotStore")

	static func publish(dataURL: URL, imageDirectory: URL, fetch: () async throws -> WidgetData) async throws -> (WidgetData, WidgetData?) {
		let data = try await fetch()
		let encoded = try JSONEncoder().encode(data)
		let previous = (try? Data(contentsOf: dataURL)).flatMap { try? JSONDecoder().decode(WidgetData.self, from: $0) }
		try encoded.write(to: dataURL, options: [.atomic])
		let paths = Set((data.unreadArticles + data.starredArticles + data.todayArticles).compactMap(\.feedIconPath))
		removeStaleIcons(in: imageDirectory, protecting: paths)
		return (data, previous)
	}

	private static func removeStaleIcons(in directory: URL, protecting paths: Set<String>) {
		let fm = FileManager.default
		guard fm.fileExists(atPath: directory.path) else { return }
		#if DEBUG
		let cutoffDate = Date.now.addingTimeInterval(-30)
		#else
		let cutoffDate = Date.now.addingTimeInterval(-7 * 24 * 60 * 60)
		#endif
		do {
			let keys: Set<URLResourceKey> = [.isDirectoryKey, .contentAccessDateKey, .contentModificationDateKey]
			for url in try fm.contentsOfDirectory(at: directory, includingPropertiesForKeys: Array(keys), options: [.skipsHiddenFiles]) {
				let values = try url.resourceValues(forKeys: keys)
				if values.isDirectory == true || paths.contains(url.path) { continue }
				if let lastAccess = values.contentAccessDate ?? values.contentModificationDate, lastAccess < cutoffDate {
					try? fm.removeItem(at: url)
				}
			}
		} catch {
			logger.debug("Unable to remove widget icons: \(error.localizedDescription)")
		}
	}
}
