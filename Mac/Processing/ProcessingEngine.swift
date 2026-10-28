import Foundation
import Darwin

@MainActor
final class ProcessingEngine {
	enum State: Equatable {
		case stopped, starting, ready, stopping, failed(String)
	}

	static let shared = ProcessingEngine()
	static let didChange = Notification.Name("ProcessingEngineDidChange")
	private(set) var state: State = .stopped {
		didSet {
			let finished = process == nil && (state == .stopped || isFailed)
			let callbacks = finished ? stopCallbacks : []
			if finished { stopCallbacks.removeAll() }
			NotificationCenter.default.post(name: Self.didChange, object: self)
			for callback in callbacks { callback() }
		}
	}

	private let locate: () -> (URL, URL)?
	private let dataRoot: URL?
	private let timeout: TimeInterval
	private let duplicateOutput: @Sendable (Int32) -> Int32
	private var stopCallbacks: [() -> Void] = []
	private var process: Process?
	private var input: FileHandle?
	private var output: FileHandle?
	private var buffer = Data()
	private var token = ""
	private var nextID = 0
	private var pending: [Int: (Result<[String: Any], Error>) -> Void] = [:]
	private var timers: [Int: Timer] = [:]
	private var startupTimer: Timer?
	private var stopTimer: Timer?
	private var generation = 0
	private var sawReady = false
	private var failureMessage: String?
	// A 200,000-byte prompt can expand sixfold when JSON-escaped.
	private let limit = 1_310_720
	private let writer = DispatchQueue(label: "ProcessingEngine.writer")

	private init() {
		locate = {
			guard let resources = Bundle.main.resourceURL else { return nil }
			let root = resources.appendingPathComponent("ProcessingEngine", isDirectory: true)
			return (root.appendingPathComponent("python/bin/python3"), root.appendingPathComponent("stdio_service.py"))
		}
		let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
		dataRoot = support?.appendingPathComponent("ProcessingEngine", isDirectory: true)
		timeout = 10
		duplicateOutput = { dup($0) }
	}

#if DEBUG
	init(testRuntime: URL, entry: URL, dataRoot: URL, timeout: TimeInterval = 1, duplicateOutput: @escaping @Sendable (Int32) -> Int32 = { dup($0) }) {
		locate = { (testRuntime, entry) }
		self.dataRoot = dataRoot
		self.timeout = timeout
		self.duplicateOutput = duplicateOutput
	}
#endif

	func start() {
		guard process == nil && (state == .stopped || isFailed) else { return }
		guard let (runtime, entry) = locate(), FileManager.default.isExecutableFile(atPath: runtime.path),
			  FileManager.default.isReadableFile(atPath: entry.path) else {
			state = .failed("Processing component is missing. Reinstall the app.")
			return
		}
		guard let dataRoot else {
			state = .failed("Could not open processing data.")
			return
		}
		do {
			try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
		} catch {
			state = .failed("Could not open processing data.")
			return
		}
		generation += 1
		let run = generation
		buffer.removeAll()
		sawReady = false
		failureMessage = nil
		token = UUID().uuidString.replacingOccurrences(of: "-", with: "") + UUID().uuidString.replacingOccurrences(of: "-", with: "")
		let child = Process()
		let stdin = Pipe()
		let stdout = Pipe()
		child.executableURL = runtime
		child.arguments = [entry.path, dataRoot.path]
		child.environment = ["PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "HOME": dataRoot.path]
		child.standardInput = stdin
		child.standardOutput = stdout
		child.standardError = FileHandle.nullDevice
		process = child
		input = stdin.fileHandleForWriting
		output = stdout.fileHandleForReading
		state = .starting
		do {
			try child.run()
			try? stdout.fileHandleForWriting.close()
			let descriptor = duplicateOutput(stdout.fileHandleForReading.fileDescriptor)
			guard descriptor >= 0 else {
				DispatchQueue.global(qos: .utility).async { [weak self] in
					child.waitUntilExit()
					DispatchQueue.main.async { self?.exited(run: run) }
				}
				fail("Processing communication failed.")
				return
			}
			DispatchQueue.global(qos: .utility).async { [weak self] in
				defer { close(descriptor) }
				var bytes = [UInt8](repeating: 0, count: 8192)
				while true {
					let count = Darwin.read(descriptor, &bytes, bytes.count)
					if count < 0 && errno == EINTR { continue }
					guard count > 0 else { break }
					let data = Data(bytes.prefix(count))
					let consumed = DispatchSemaphore(value: 0)
					DispatchQueue.main.async {
						self?.received(data, run: run)
						consumed.signal()
					}
					consumed.wait()
				}
				child.waitUntilExit()
				DispatchQueue.main.async { self?.exited(run: run) }
			}
			write(["token": token])
			startupTimer = Timer.scheduledTimer(withTimeInterval: timeout, repeats: false) { [weak self] _ in
				Task { @MainActor in self?.timedOut(run: run) }
			}
		} catch {
			fail("Could not start processing component.")
		}
	}

	func stop(completion: (() -> Void)? = nil) {
		if state == .stopped {
			completion?()
			return
		}
		if let completion { stopCallbacks.append(completion) }
		guard state != .stopping else { return }
		guard let child = process, child.isRunning else {
			state = .stopping
			generation += 1
			cleanup()
			state = .stopped
			return
		}
		state = .stopping
		startupTimer?.invalidate()
		failPending()
		try? input?.close()
		input = nil
		let run = generation
		stopTimer = Timer.scheduledTimer(withTimeInterval: 3, repeats: false) { [weak self] _ in
			Task { @MainActor in
				guard let self, self.generation == run, self.state == .stopping, let process = self.process, process.isRunning else { return }
				process.terminate()
				let pid = process.processIdentifier
				DispatchQueue.global().asyncAfter(deadline: .now() + 2) {
					if process.isRunning { kill(pid, SIGKILL) }
				}
			}
		}
	}

	func request(method: String, path: String, query: [String: Any] = [:], body: [String: Any] = [:], completion: @escaping (Result<[String: Any], Error>) -> Void) {
		guard state == .ready || state == .starting, process?.isRunning == true, pending.count < 32,
			  [("POST", "/api/settings/processing/probe"), ("GET", "/api/status"), ("GET", "/api/jobs"), ("GET", "/api/settings/processing"), ("PUT", "/api/settings/processing")].contains(where: { $0.0 == method && $0.1 == path }) else {
			completion(.failure(EngineError.unavailable))
			return
		}
		nextID += 1
		let id = nextID
		pending[id] = completion
		timers[id] = Timer.scheduledTimer(withTimeInterval: timeout, repeats: false) { [weak self] _ in
			Task { @MainActor in self?.requestTimedOut(id) }
		}
		write(["id": id, "token": token, "method": method, "path": path, "query": query, "body": body])
	}

	private var isFailed: Bool {
		if case .failed = state { return true }
		return false
	}

	private func write(_ message: [String: Any]) {
		guard let input, let bytes = try? JSONSerialization.data(withJSONObject: message), bytes.count < limit else {
			fail("Invalid processing request.")
			return
		}
		let line = bytes + Data([10])
		let run = generation
		writer.async { [weak self] in
			do { try input.write(contentsOf: line) }
			catch { Task { @MainActor in
				if self?.generation == run, self?.state == .ready { self?.fail("Processing communication failed.") }
			} }
		}
	}

	private func received(_ data: Data, run: Int) {
		guard run == generation, state != .stopping, !data.isEmpty else { return }
		buffer.append(data)
		while let newline = buffer.firstIndex(of: 10) {
			guard newline < limit else { fail("Invalid response from processing component."); return }
			let line = buffer.prefix(upTo: newline)
			buffer.removeSubrange(...newline)
			guard let value = try? JSONSerialization.jsonObject(with: Data(line)) as? [String: Any] else {
				fail("Invalid response from processing component.")
				return
			}
			if state == .starting, value["status"] as? String == "error", let code = value["code"] as? String {
				fail(startupMessage(code))
				return
			} else if state == .starting, !sawReady, value["status"] as? String == "ready" {
				sawReady = true
				request(method: "GET", path: "/api/status") { [weak self] result in
					guard let self, case .success(let status) = result, status["schemaVersion"] is Int else { self?.fail("Processing readiness check failed."); return }
					self.request(method: "GET", path: "/api/settings/processing") { [weak self] result in
						guard let self, case .success(let settings) = result, settings["processors"] is Int else { self?.fail("Processing readiness check failed."); return }
						self.request(method: "POST", path: "/api/settings/processing/probe") { [weak self] result in
							guard let self, case .success(let probe) = result, probe["writable"] as? Bool == true else { self?.fail("Processing data is unavailable. Check access and try again."); return }
							self.startupTimer?.invalidate()
							self.state = .ready
						}
					}
				}
			} else if let id = value["id"] as? Int, let completion = pending[id] {
				guard value["result"] is [String: Any] || value["error"] is String else {
					fail("Invalid response from processing component.")
					return
				}
				pending.removeValue(forKey: id)
				timers.removeValue(forKey: id)?.invalidate()
				if let result = value["result"] as? [String: Any] { completion(.success(result)) }
				else {
					let error: EngineError = value["code"] as? String == "job_record_too_large" ? .jobRecordTooLarge : .operation
					completion(.failure(error))
				}
			} else {
				fail("Invalid response from processing component.")
				return
			}
		}
		if buffer.count >= limit { fail("Invalid response from processing component.") }
	}

	private func requestTimedOut(_ id: Int) {
		guard pending[id] != nil else { return }
		fail("Processing request timed out. Try again.")
	}
	private func timedOut(run: Int) {
		if run == generation && state == .starting { fail("Processing startup timed out. Try again.") }
	}
	private func startupMessage(_ code: String) -> String {
		switch code {
		case "schema_migration_required": return "Processing data needs a verified migration before it can be opened."
		case "schema_newer": return "Processing data was created by a newer version. Update the app."
		case "schema_incomplete": return "Processing data is incomplete. Restore a verified backup."
		case "data_corrupt": return "Processing data could not be read. Restore a verified backup."
		case "data_unavailable": return "Processing data is unavailable. Check access and try again."
		default: return "Processing could not start. Try again."
		}
	}
	private func exited(run: Int) {
		guard run == generation else { return }
		let message = failureMessage
		let stopping = state == .stopping
		state = .stopping
		generation += 1
		cleanup()
		state = message.map { .failed($0) } ?? (stopping ? .stopped : .failed("Processing component stopped unexpectedly. Try again."))
	}
	private func fail(_ message: String) {
		guard state != .stopped && state != .stopping && !isFailed else { return }
		failureMessage = message
		guard let child = process, child.isRunning else {
			state = .stopping
			generation += 1
			cleanup()
			state = .failed(message)
			return
		}
		state = .stopping
		startupTimer?.invalidate()
		failPending()
		try? input?.close()
		input = nil
		child.terminate()
		let pid = child.processIdentifier
		DispatchQueue.global().asyncAfter(deadline: .now() + 2) {
			if child.isRunning { kill(pid, SIGKILL) }
		}
	}
	private func failPending() {
		let callbacks = pending.values
		pending.removeAll()
		for timer in timers.values { timer.invalidate() }
		timers.removeAll()
		for callback in callbacks { callback(.failure(EngineError.unavailable)) }
	}
	private func cleanup() {
		startupTimer?.invalidate()
		stopTimer?.invalidate()
		try? output?.close()
		try? input?.close()
		input = nil
		output = nil
		process = nil
		failPending()
	}
	enum EngineError: Error, Equatable { case unavailable, operation, jobRecordTooLarge }
}
