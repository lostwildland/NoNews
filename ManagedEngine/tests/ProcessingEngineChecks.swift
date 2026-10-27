import Foundation
import Darwin

@main struct Checks {
	@MainActor static func wait(_ engine: ProcessingEngine, _ expected: (ProcessingEngine.State) -> Bool) async throws {
		for _ in 0..<800 {
			if expected(engine.state) { return }
			try await Task.sleep(for: .milliseconds(10))
		}
		throw NSError(domain: "Timed out waiting for controller", code: 1)
	}

	@MainActor static func main() async throws {
		let root = URL(fileURLWithPath: CommandLine.arguments[1])
		let runtime = root.appendingPathComponent("ManagedEngine/.prepared/python/bin/python3")
		let fixture = root.appendingPathComponent("ManagedEngine/tests/native_fixture.py")
		let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
		try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
		defer { try? FileManager.default.removeItem(at: dir) }
		setenv("INFORMATION_OS_RAW_VAULT", "must-not-reach-child", 1)
		let data = dir.appendingPathComponent("data")
		let exhausted = ProcessingEngine(testRuntime: runtime, entry: fixture, dataRoot: dir.appendingPathComponent("exhausted"), timeout: 0.4, duplicateOutput: { _ in -1 })
		for _ in 0..<2 {
			exhausted.start()
			var quitFinished = false
			exhausted.stop { quitFinished = true }
			try await wait(exhausted) { if case .failed = $0 { return true }; return false }
			precondition(quitFinished)
			exhausted.stop()
			precondition(exhausted.state == .stopped)
		}
		let engine = ProcessingEngine(testRuntime: runtime, entry: fixture, dataRoot: data, timeout: 0.4)
		engine.start()
		try await wait(engine) { $0 == .ready }
		let write: Int = try await withCheckedThrowingContinuation { continuation in
			engine.request(method: "PUT", path: "/api/settings/processing", body: ["processors": 3]) { result in
				continuation.resume(returning: (try? result.get()["processors"] as? Int) ?? -1)
			}
		}
		precondition(write == 3)
		var jobsReturned = false
		var settingReturned = false
		engine.request(method: "GET", path: "/api/jobs") { result in
			jobsReturned = (try? result.get()["jobs"] as? [Any]) != nil
		}
		engine.request(method: "GET", path: "/api/settings/processing") { result in
			settingReturned = (try? result.get()["processors"] as? Int) == 3
		}
		for _ in 0..<100 where !jobsReturned || !settingReturned {
			try await Task.sleep(for: .milliseconds(10))
		}
		precondition(jobsReturned && settingReturned)
		engine.stop()
		engine.stop()
		try await wait(engine) { $0 == .stopped }
		engine.start()
		try await wait(engine) { $0 == .ready }
		let read: Int = try await withCheckedThrowingContinuation { continuation in
			engine.request(method: "GET", path: "/api/settings/processing") { result in
				continuation.resume(returning: (try? result.get()["processors"] as? Int) ?? -1)
			}
		}
		precondition(read == 3)
		engine.stop { engine.start() }
		try await wait(engine) { $0 == .ready }
		engine.stop()
		try await wait(engine) { $0 == .stopped }
		for mode in ["timeout", "closedstdout", "crash", "malformed", "oversize"] {
			let entry = dir.appendingPathComponent(mode + ".py")
			try FileManager.default.copyItem(at: fixture, to: entry)
			let test = ProcessingEngine(testRuntime: runtime, entry: entry, dataRoot: data, timeout: 0.3)
			test.start()
			try await wait(test) { if case .failed = $0 { return true }; return false }
			test.stop()
			precondition(test.state == .stopped)
		}
		for mode in ["requesttimeout", "requestcrash", "badreply"] {
			let entry = dir.appendingPathComponent(mode + ".py")
			try FileManager.default.copyItem(at: fixture, to: entry)
			let test = ProcessingEngine(testRuntime: runtime, entry: entry, dataRoot: data, timeout: 0.3)
			test.start()
			try await wait(test) { $0 == .ready }
			var completed = false
			test.request(method: "PUT", path: "/api/settings/processing", body: ["processors": 2]) { _ in completed = true }
			try await wait(test) { if case .failed = $0 { return true }; return false }
			precondition(completed)
		}
		let retryEntry = dir.appendingPathComponent("retry.py")
		try FileManager.default.copyItem(at: dir.appendingPathComponent("crash.py"), to: retryEntry)
		let retry = ProcessingEngine(testRuntime: runtime, entry: retryEntry, dataRoot: data, timeout: 0.4)
		// Use a crashing script first, then replace only this isolated fixture.
		let crashText = "import sys; sys.exit(1)\n"
		try crashText.write(to: retryEntry, atomically: true, encoding: .utf8)
		retry.start()
		try await wait(retry) { if case .failed = $0 { return true }; return false }
		try FileManager.default.removeItem(at: retryEntry)
		try FileManager.default.copyItem(at: fixture, to: retryEntry)
		retry.start()
		try await wait(retry) { $0 == .ready }
		retry.stop()
		try await wait(retry) { $0 == .stopped }
		let stubbornEntry = dir.appendingPathComponent("stubborn.py")
		try FileManager.default.copyItem(at: fixture, to: stubbornEntry)
		let stubborn = ProcessingEngine(testRuntime: runtime, entry: stubbornEntry, dataRoot: data, timeout: 0.4)
		stubborn.start()
		try await wait(stubborn) { $0 == .ready }
		var stopped = false
		stubborn.stop { stopped = true }
		try await wait(stubborn) { $0 == .stopped }
		precondition(stopped)
		for (code, fragment) in [("schema_migration_required", "verified migration"), ("schema_newer", "newer version"), ("schema_incomplete", "incomplete"), ("data_corrupt", "verified backup"), ("data_unavailable", "Check access"), ("startup_failed", "could not start")] {
			let entry = dir.appendingPathComponent("startup_" + code + ".py")
			try FileManager.default.copyItem(at: fixture, to: entry)
			for _ in 0..<3 {
				let test = ProcessingEngine(testRuntime: runtime, entry: entry, dataRoot: data, timeout: 0.5)
				test.start()
				try await wait(test) { if case .failed = $0 { return true }; return false }
				guard case .failed(let message) = test.state, message.contains(fragment) else { fatalError("Startup reason lost") }
			}
		}
		let ownerEntry = dir.appendingPathComponent("failstubborn.py")
		try FileManager.default.copyItem(at: fixture, to: ownerEntry)
		let ownerData = dir.appendingPathComponent("owner-data")
		let owner = ProcessingEngine(testRuntime: runtime, entry: ownerEntry, dataRoot: ownerData, timeout: 0.3)
		owner.start()
		try await wait(owner) { $0 == .ready }
		owner.request(method: "PUT", path: "/api/settings/processing", body: ["processors": 2]) { _ in }
		try await wait(owner) { $0 == .stopping }
		var quitFinished = false
		owner.stop { quitFinished = true }
		for _ in 0..<20 { owner.start() }
		precondition(!quitFinished)
		let owners = try String(contentsOf: ownerData.appendingPathComponent("owners"), encoding: .utf8)
		let ownerIDs = owners.split(separator: "\n")
		precondition(ownerIDs.count == 1)
		guard let ownerPID = Int32(ownerIDs[0]) else { fatalError("Missing child PID") }
		precondition(kill(ownerPID, 0) == 0)
		try await wait(owner) { if case .failed = $0 { return true }; return false }
		precondition(quitFinished)
		precondition(kill(ownerPID, 0) != 0)
		if CommandLine.arguments.count > 2 {
			let real = ProcessingEngine(testRuntime: runtime, entry: root.appendingPathComponent("ManagedEngine/.prepared/stdio_service.py"), dataRoot: URL(fileURLWithPath: CommandLine.arguments[2]), timeout: 4)
			real.start()
			try await wait(real) { $0 == .ready }
			var cursor: String? = nil
			var count = 0
			var bytes = Data()
			repeat {
				let query: [String: Any] = cursor.map { ["cursor": $0] } ?? [:]
				let frame: Data = try await withCheckedThrowingContinuation { continuation in
					real.request(method: "GET", path: "/api/jobs", query: query) { result in
						guard let object = try? result.get(), let encoded = try? JSONSerialization.data(withJSONObject: object) else {
							continuation.resume(throwing: NSError(domain: "jobs", code: 1)); return
						}
						continuation.resume(returning: encoded)
					}
				}
				guard let object = try JSONSerialization.jsonObject(with: frame) as? [String: Any],
					  let chunk = object["chunk"] as? String, let data = Data(base64Encoded: chunk),
					  let complete = object["recordComplete"] as? Bool else { fatalError("Invalid jobs frame") }
				bytes.append(data)
				if complete {
					guard let job = try JSONSerialization.jsonObject(with: bytes) as? [String: Any], job["id"] is String else { fatalError("Invalid job") }
					count += 1
					bytes.removeAll()
				}
				cursor = object["next"] as? String
			} while cursor != nil
			precondition(count == 201 && bytes.isEmpty)
			real.stop()
			try await wait(real) { $0 == .stopped }
		}
		if CommandLine.arguments.count > 3 {
			let blocked = ProcessingEngine(testRuntime: runtime, entry: root.appendingPathComponent("ManagedEngine/.prepared/stdio_service.py"), dataRoot: URL(fileURLWithPath: CommandLine.arguments[3]), timeout: 4)
			blocked.start()
			try await wait(blocked) { if case .failed = $0 { return true }; return false }
			guard case .failed(let message) = blocked.state, message.contains("verified migration") else { fatalError("Unverified trigger was not reported") }
		}
		let missing = ProcessingEngine(testRuntime: dir.appendingPathComponent("missing"), entry: fixture, dataRoot: data)
		missing.start()
		guard case .failed = missing.state else { fatalError("Missing runtime did not fail") }
		print("ProcessingEngine checks passed")
	}
}
