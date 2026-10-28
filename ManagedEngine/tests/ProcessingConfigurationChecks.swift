import Foundation

@main struct ProcessingConfigurationChecks {
	@MainActor static func wait(_ engine: ProcessingEngine, state: ProcessingEngine.State) async throws {
		for _ in 0..<800 {
			if engine.state == state { return }
			try await Task.sleep(for: .milliseconds(10))
		}
		throw NSError(domain: "Processing configuration state", code: 1)
	}

	@MainActor static func request(_ engine: ProcessingEngine, _ method: String, _ path: String, _ body: [String: Any] = [:]) async throws -> [String: Any] {
		try await withCheckedThrowingContinuation { continuation in
			engine.request(method: method, path: path, body: body) { result in continuation.resume(with: result) }
		}
	}

	@MainActor static func main() async throws {
		let root = URL(fileURLWithPath: CommandLine.arguments[1])
		let runtime = root.appendingPathComponent("ManagedEngine/.prepared/python/bin/python3")
		let entry = root.appendingPathComponent("ManagedEngine/.prepared/stdio_service.py")
		let directory = Process()
		let output = Pipe()
		directory.executableURL = runtime
		directory.arguments = [root.appendingPathComponent("ManagedEngine/tests/configuration_directory_fixture.py").path]
		directory.standardOutput = output
		directory.standardError = FileHandle.nullDevice
		try directory.run()
		defer {
			if directory.isRunning { directory.terminate() }
			directory.waitUntilExit()
		}
		let portData = output.fileHandleForReading.availableData
		guard let port = String(data: portData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), Int(port) != nil else {
			throw NSError(domain: "Synthetic directory", code: 1)
		}
		let data = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
		try FileManager.default.createDirectory(at: data, withIntermediateDirectories: true)
		defer { try? FileManager.default.removeItem(at: data) }
		let engine = ProcessingEngine(testRuntime: runtime, entry: entry, dataRoot: data, timeout: 10)
		engine.start()
		try await wait(engine, state: .ready)
		let service = try await request(engine, "PUT", "/api/config/services", ["name": "Fixture", "type": "magpie", "endpoint": "http://127.0.0.1:\(port)"])
		guard let serviceID = service["id"] as? String else { throw NSError(domain: "Service ID", code: 1) }
		_ = try await request(engine, "POST", "/api/config/refresh", ["id": serviceID])
		let text = String(repeating: "\u{1}", count: 199_996) + "😀"
		let body: [String: Any] = ["name": "Boundary", "role": "curator", "text": text, "serviceId": serviceID, "target": "fixture/Exact"]
		let saved = try await request(engine, "PUT", "/api/config/prompts", body)
		guard let id = saved["id"] as? String, let version = saved["versionId"] as? String else { throw NSError(domain: "Prompt ID", code: 1) }
		precondition(saved["text"] as? String == text)
		engine.stop()
		try await wait(engine, state: .stopped)
		engine.start()
		try await wait(engine, state: .ready)
		let read = try await request(engine, "GET", "/api/config/prompts", ["id": id])
		precondition(read["text"] as? String == text && read["versionId"] as? String == version)
		let old = try await request(engine, "GET", "/api/config/history", ["id": id, "versionId": version])
		precondition(old["text"] as? String == text)
		let copy = try await request(engine, "POST", "/api/config/copy", ["id": id, "name": "Copy"])
		precondition(copy["text"] as? String == text && copy["id"] as? String != id)
		var changed = body
		changed["id"] = id
		changed["text"] = "Changed"
		_ = try await request(engine, "PUT", "/api/config/prompts", changed)
		let restored = try await request(engine, "POST", "/api/config/restore", ["id": id, "versionId": version])
		precondition(restored["text"] as? String == text && restored["serviceId"] as? String == serviceID)
		changed["text"] = text + "x"
		do {
			_ = try await request(engine, "PUT", "/api/config/prompts", changed)
			throw NSError(domain: "Expected oversized refusal", code: 1)
		} catch ProcessingEngine.EngineError.invalidConfiguration { }
		let preserved = try await request(engine, "GET", "/api/config/prompts", ["id": id])
		let status = try await request(engine, "GET", "/api/status")
		precondition(preserved["text"] as? String == text && status["schemaVersion"] is Int && engine.state == .ready)
		engine.stop()
		try await wait(engine, state: .stopped)
		print("Processing configuration checks passed")
	}
}
