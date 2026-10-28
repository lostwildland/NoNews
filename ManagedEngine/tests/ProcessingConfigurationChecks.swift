import Foundation

@main struct ProcessingConfigurationChecks {
	@MainActor static var maximumPageLatency: TimeInterval = 0
	@MainActor static func wait(_ engine: ProcessingEngine, state: ProcessingEngine.State) async throws {
		for _ in 0..<800 {
			if engine.state == state { return }
			try await Task.sleep(for: .milliseconds(10))
		}
		throw NSError(domain: "Processing configuration state", code: 1)
	}

	@MainActor static func request(_ engine: ProcessingEngine, _ method: String, _ path: String, _ body: [String: Any] = [:]) async throws -> [String: Any] {
		let data: Data = try await withCheckedThrowingContinuation { continuation in
			engine.request(method: method, path: path, body: body) { result in
				do { continuation.resume(returning: try JSONSerialization.data(withJSONObject: result.get())) }
				catch { FileHandle.standardError.write(Data("Request failed: \(method) \(path): \(error)\n".utf8)); continuation.resume(throwing: error) }
			}
		}
		guard let value = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw NSError(domain: "Configuration response", code: 1) }
		return value
	}

	@MainActor static func reportRecord(_ engine: ProcessingEngine, snapshot: String, section: String, index: Int) async throws -> [String: Any] {
		var data = Data()
		var part = 0
		repeat {
			let started = Date()
			let page = try await request(engine, "POST", "/api/config/migration/preview", ["snapshotId": snapshot, "section": section, "index": index, "part": part])
			maximumPageLatency = max(maximumPageLatency, Date().timeIntervalSince(started))
			precondition(page["snapshotId"] as? String == snapshot && page["index"] as? Int == index && page["part"] as? Int == part)
			guard let encoded = page["chunk"] as? String, let chunk = Data(base64Encoded: encoded) else { throw NSError(domain: "Report chunk", code: 1) }
			data.append(chunk)
			guard let next = page["nextPart"] as? Int else { break }
			part = next
		} while true
		guard let row = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw NSError(domain: "Report record", code: 1) }
		return row
	}

	@MainActor static func main() async throws {
		let root = URL(fileURLWithPath: CommandLine.arguments[1])
		let runtime = root.appendingPathComponent("ManagedEngine/.prepared/python/bin/python3")
		let packaged = ProcessInfo.processInfo.environment["NONEWS_CHECK_PACKAGED"] == "1"
		let entry = root.appendingPathComponent(packaged ? "ManagedEngine/.prepared/stdio_service.py" : "ManagedEngine/stdio_service.py")
		let directory = Process()
		let output = Pipe()
		directory.executableURL = runtime
		directory.arguments = ["-B", "-I", root.appendingPathComponent("ManagedEngine/tests/configuration_directory_fixture.py").path]
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
		let lock = Process()
		let lockInput = Pipe()
		let lockOutput = Pipe()
		lock.executableURL = runtime
		lock.arguments = ["-B", "-I", root.appendingPathComponent("ManagedEngine/tests/configuration_lock_fixture.py").path, data.appendingPathComponent("information.sqlite").path]
		lock.standardInput = lockInput
		lock.standardOutput = lockOutput
		try lock.run()
		precondition(String(data: lockOutput.fileHandleForReading.availableData, encoding: .utf8)?.contains("locked") == true)
		var migrationStarted = false
		engine.request(method: "POST", path: "/api/config/migration/preview", body: ["serviceId": serviceID, "browse": true, "cooperative": true]) { result in
			if case .success(let value) = result, value["state"] as? String == "running" { migrationStarted = true }
		}
		for _ in 0..<100 where !migrationStarted { try await Task.sleep(for: .milliseconds(10)) }
		precondition(migrationStarted)
		let previousMutations = engine.unconfirmedMutations
		var callbackCount = 0
		var recoveryID: String?
		engine.request(method: "PUT", path: "/api/config/services", body: ["name": "Stopped fixture", "type": "magpie", "endpoint": "http://127.0.0.1:1"]) { result in
			callbackCount += 1
			if case .failure(ProcessingEngine.EngineError.outcomeUnknown(let identity)) = result { recoveryID = identity }
		}
		guard let queuedID = engine.unconfirmedMutations.first(where: { !previousMutations.contains($0) }) else {
			throw NSError(domain: "Missing queued mutation identity", code: 1)
		}
		var accepted = false
		for _ in 0..<100 {
			let observed = try await request(engine, "POST", "/api/config/migration/operation", ["operationId": queuedID])
			if observed["state"] as? String == "running" { accepted = true; break }
			try await Task.sleep(for: .milliseconds(10))
		}
		precondition(accepted, "Observe service acceptance before testing cancellation of queued work")
		engine.stop()
		try lockInput.fileHandleForWriting.write(contentsOf: Data("release\n".utf8))
		lock.waitUntilExit()
		try await wait(engine, state: .stopped)
		precondition(callbackCount == 1 && recoveryID != nil)
		engine.start()
		try await wait(engine, state: .ready)
		guard let recoveryID else { throw NSError(domain: "Recovery identity", code: 1) }
		let rawRecovery = try await request(engine, "POST", "/api/config/migration/operation", ["operationId": recoveryID])
		print("Stopped-save recovery state: \(rawRecovery)")
		do {
			_ = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Data, Error>) in
				engine.recoverMutation(recoveryID) { result in
					do { continuation.resume(returning: try JSONSerialization.data(withJSONObject: result.get())) }
					catch { continuation.resume(throwing: error) }
				}
			}
			throw NSError(domain: "Expected cancelled save", code: 1)
		} catch ProcessingEngine.EngineError.mutationNotSaved { }
		let servicesAfterStop = try await request(engine, "GET", "/api/config/services")
		precondition(!(servicesAfterStop["services"] as? [[String: Any]] ?? []).contains { $0["name"] as? String == "Stopped fixture" })
		precondition(callbackCount == 1)
		func fixture(_ mutate: Bool) throws {
			let process = Process()
			process.executableURL = runtime
			process.arguments = ["-B", "-I", root.appendingPathComponent("ManagedEngine/tests/configuration_browse_fixture.py").path, data.appendingPathComponent("information.sqlite").path] + (mutate ? ["mutate"] : [])
			try process.run()
			process.waitUntilExit()
			precondition(process.terminationStatus == 0)
		}
		try fixture(false)
		let started = Date()
		let report = try await request(engine, "POST", "/api/config/migration/preview", ["serviceId": serviceID, "browse": true])
		let previewTime = Date().timeIntervalSince(started)
		guard let snapshot = report["snapshotId"] as? String, let counts = report["counts"] as? [String: Int] else { throw NSError(domain: "Browse snapshot", code: 1) }
		precondition(counts["models"] == 2200 && counts["evidence"] == 1)
		let first = try await reportRecord(engine, snapshot: snapshot, section: "models", index: 0)
		precondition(first["kit"] as? String == "native-0000-" + String(repeating: "x", count: 8000))
		try fixture(true)
		engine.stop()
		try await wait(engine, state: .stopped)
		engine.start()
		try await wait(engine, state: .ready)
		let retried = try await reportRecord(engine, snapshot: snapshot, section: "models", index: 0)
		precondition(retried["kit"] as? String == first["kit"] as? String)
		let replacement = try await request(engine, "POST", "/api/config/migration/preview", ["serviceId": serviceID, "browse": true])
		guard let replacementID = replacement["snapshotId"] as? String, let replacementCounts = replacement["counts"] as? [String: Int] else { throw NSError(domain: "Replacement snapshot", code: 1) }
		precondition(replacementID != snapshot && replacementCounts["models"] == 2199)
		let replacementFirst = try await reportRecord(engine, snapshot: replacementID, section: "models", index: 0)
		precondition(replacementFirst["kit"] as? String == "native-0001-" + String(repeating: "x", count: 8000))
		let traversal = Date()
		for index in 0..<2200 {
			let row = try await reportRecord(engine, snapshot: snapshot, section: "models", index: index)
			precondition(row["kit"] as? String == String(format: "native-%04d-", index) + String(repeating: "x", count: 8000))
		}
		let evidence = try await reportRecord(engine, snapshot: snapshot, section: "evidence", index: 0)
		precondition(evidence["detail"] as? String == String(repeating: "文", count: 30000))
		_ = try await request(engine, "POST", "/api/config/migration/release", ["snapshotId": snapshot])
		_ = try await request(engine, "POST", "/api/config/migration/release", ["snapshotId": replacementID])
		print("Native browse: preview \(previewTime)s; 2200 records and multipart evidence \(Date().timeIntervalSince(traversal))s; max page \(maximumPageLatency)s")
		engine.stop()
		try await wait(engine, state: .stopped)
		print("Processing configuration checks passed")
	}
}
