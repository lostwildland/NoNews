import Foundation

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
		engine.stop()
		try await wait(engine) { $0 == .stopped }
		for mode in ["timeout", "crash", "malformed", "oversize"] {
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
		let missing = ProcessingEngine(testRuntime: dir.appendingPathComponent("missing"), entry: fixture, dataRoot: data)
		missing.start()
		guard case .failed = missing.state else { fatalError("Missing runtime did not fail") }
		print("ProcessingEngine checks passed")
	}
}
