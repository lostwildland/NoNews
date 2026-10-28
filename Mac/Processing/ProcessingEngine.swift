import Foundation
import Darwin

struct MigrationReviewState {
	static func serviceLabel(name: String, id: String) -> String { "\(name) [\(id)]" }
	struct Input: Equatable {
		let serviceID: String
		let choices: [String: String]
		let editorServices: [String: String]
	}
	struct Ticket {
		let generation: UInt
		let input: Input
	}
	struct ApplyTicket {
		let generation: UInt
		let input: Input
	}
	private var generation: UInt = 0
	// Preview retries must not invalidate an in-flight Apply response.
	private var applyGeneration: UInt = 0
	private(set) var reviewed: Input?
	private var lastApply: (input: Input, status: String)?
	mutating func beginApply(_ input: Input) -> ApplyTicket {
		invalidate()
		applyGeneration &+= 1
		return ApplyTicket(generation: applyGeneration, input: input)
	}
	mutating func recordApply(status: String, ticket: ApplyTicket) -> Bool {
		guard ticket.generation == applyGeneration, status == "applied" || status == "waiting" else {
			return false
		}
		lastApply = (ticket.input, status)
		return true
	}
	func applyAcknowledgement(for input: Input?) -> String {
		guard let lastApply, lastApply.input == input else {
			return ""
		}
		switch lastApply.status {
		case "applied": return "Mappings applied. "
		case "waiting": return "The previous Apply waited for running work. "
		default: return ""
		}
	}
	func readbackFailure(for input: Input?) -> String {
		applyAcknowledgement(for: input) + "The routing report could not be read; preview again."
	}
	mutating func invalidate() { generation &+= 1; reviewed = nil }
	mutating func begin(_ input: Input) -> Ticket {
		invalidate()
		return Ticket(generation: generation, input: input)
	}
	func accepts(_ ticket: Ticket, current: Input?) -> Bool {
		ticket.generation == generation && ticket.input == current
	}
	mutating func complete(_ ticket: Ticket, current: Input?) -> Bool {
		guard accepts(ticket, current: current) else { return false }
		reviewed = ticket.input
		return true
	}
	static func status(paused: Bool, waiting: Bool) -> String {
		if paused && waiting { return "Waiting; claims paused" }
		return paused ? "Claims paused" : "Claims active"
	}
}

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
	private var recoveryDefaults = UserDefaults.standard
	private let recoveryKey = "NoNews.Processing.PendingMutationReceipts"
	var unconfirmedMutations: [String] { recoveryDefaults.stringArray(forKey: recoveryKey) ?? [] }
	private func rememberMutation(_ identity: String) {
		var ids = unconfirmedMutations
		if ids.contains(identity) { return }
		guard ids.count < 32 else { return }
		ids.append(identity)
		recoveryDefaults.set(ids, forKey: recoveryKey)
	}
	func forgetMutation(_ identity: String, completion: ((Result<Void, Error>) -> Void)? = nil) {
		request(method: "POST", path: "/api/config/migration/ack", body: ["cooperative": true, "receiptId": identity]) { [weak self] result in
			guard let self, case .success(let value) = result, let operation = value["operationId"] as? String else {
				if case .failure(let error) = result { completion?(.failure(error)) }
				else { completion?(.failure(EngineError.operation)) }
				return
			}
			self.pollAcknowledgement(operation, receipt: identity, completion: completion)
		}
	}

	func acknowledgeUnknownMutations(completion: @escaping (Result<Void, Error>) -> Void) {
		let identities = unconfirmedMutations
		guard !identities.isEmpty else { completion(.success(())); return }
		var remaining = identities.count
		var failure: Error?
		for identity in identities {
			forgetMutation(identity) { result in
				if case .failure(let error) = result, failure == nil { failure = error }
				remaining -= 1
				guard remaining == 0 else { return }
				if let failure { completion(.failure(failure)) }
				else { completion(.success(())) }
			}
		}
	}
	private func pollAcknowledgement(_ operation: String, receipt: String, completion: ((Result<Void, Error>) -> Void)? = nil) {
		request(method: "POST", path: "/api/config/migration/ack", body: ["operationId": operation]) { [weak self] response in
			guard let self else { return }
			guard case .success(let value) = response else {
				if case .failure(let error) = response { completion?(.failure(error)) }
				return
			}
			if value["operationId"] as? String == operation, value["state"] as? String == "complete",
				(value["result"] as? [String: Any])?["acknowledged"] as? Bool == true {
				self.recoveryDefaults.set(self.unconfirmedMutations.filter { $0 != receipt }, forKey: self.recoveryKey)
				completion?(.success(()))
			} else if value["state"] as? String == "running" {
				DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
					self?.pollAcknowledgement(operation, receipt: receipt, completion: completion)
				}
			} else {
				completion?(.failure(EngineError.operation))
			}
		}
	}
	func recoverMutation(_ identity: String, completion: @escaping (Result<[String: Any], Error>) -> Void) {
		pollMutation(identity, completion: completion)
	}

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
		if let defaults = UserDefaults(suiteName: "NoNews.Processing.Tests.\(dataRoot.lastPathComponent)") { recoveryDefaults = defaults }
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

	func observeNativeArticle(_ body: [String: Any], completion: @escaping (Result<[String: Any], Error>) -> Void) {
		request(method: "POST", path: "/api/native/observations", body: body, completion: completion)
	}

	func nativeObservations(namespace: String? = nil, completion: @escaping (Result<[String: Any], Error>) -> Void) {
		var body: [String: Any] = [:]
		if let namespace { body["namespace"] = namespace }
		request(method: "GET", path: "/api/native/observations", body: body, completion: completion)
	}

	func nativeObservation(accountID: String, feedID: String, articleID: String, completion: @escaping ([String: Any]?) -> Void) {
		let namespace = UserDefaults.standard.string(forKey: "NoNews.NativeSource.InstallationNamespace") ?? ""
		request(method: "GET", path: "/api/native/observation", body: ["namespace": namespace, "accountID": accountID, "feedID": feedID, "articleID": articleID]) { result in
			guard case .success(let value) = result else { completion(nil); return }
			completion(value["observation"] as? [String: Any])
		}
	}
	func feedPolicies(namespace: String, accountID: String, completion: @escaping (Result<[String: Any], Error>) -> Void) {
		request(method: "GET", path: "/api/settings/feeds", body: ["namespace": namespace, "accountID": accountID], completion: completion)
	}

	func saveFeedPolicies(_ body: [String: Any], completion: @escaping (Result<[String: Any], Error>) -> Void) {
		request(method: "PUT", path: "/api/settings/feeds", body: body, completion: completion)
	}

	func request(method: String, path: String, query: [String: Any] = [:], body: [String: Any] = [:], completion: @escaping (Result<[String: Any], Error>) -> Void) {
		guard state == .ready || state == .starting, process?.isRunning == true, pending.count < 32,
			  [("POST", "/api/settings/processing/probe"), ("GET", "/api/status"), ("GET", "/api/jobs"), ("GET", "/api/settings/processing"), ("PUT", "/api/settings/processing"),
			   ("GET", "/api/config/services"), ("PUT", "/api/config/services"), ("GET", "/api/config/prompts"), ("PUT", "/api/config/prompts"),
			   ("GET", "/api/config/history"), ("POST", "/api/config/copy"), ("POST", "/api/config/restore"), ("POST", "/api/config/refresh"),
			   ("DELETE", "/api/config/services"), ("DELETE", "/api/config/prompts"), ("GET", "/api/config/references"),
			   ("PUT", "/api/config/references"), ("DELETE", "/api/config/references"), ("POST", "/api/config/render"), ("POST", "/api/config/bind"), ("POST", "/api/config/import-legacy"), ("GET", "/api/config/legacy"),
			   ("POST", "/api/config/migration/preview"), ("POST", "/api/config/migration/pause"), ("POST", "/api/config/migration/apply"), ("POST", "/api/config/migration/release"), ("POST", "/api/config/migration/operation"), ("POST", "/api/config/migration/ack"),
			   ("GET", "/api/native/observations"), ("POST", "/api/native/observations"), ("GET", "/api/native/observation"), ("POST", "/api/native/jobs/claim"), ("POST", "/api/native/jobs/complete"), ("POST", "/api/native/replay"), ("GET", "/api/native/context/results"), ("POST", "/api/native/context/results"), ("GET", "/api/settings/feeds"), ("PUT", "/api/settings/feeds")].contains(where: { $0.0 == method && $0.1 == path }) else {
			completion(.failure(EngineError.unavailable))
			return
		}
		nextID += 1
		let id = nextID
		var message: [String: Any] = ["id": id, "token": token, "method": method, "path": path, "query": query, "body": body]
		let tracked = method != "GET" && !path.hasPrefix("/api/config/migration/") && path != "/api/config/render" && path != "/api/settings/processing/probe"
		let mutation = tracked ? UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased() : nil
		if let mutation { message["mutationId"] = mutation }
		if mutation != nil, unconfirmedMutations.count >= 32 {
			completion(.failure(EngineError.recoveryRequired))
			return
		}
		guard let bytes = try? JSONSerialization.data(withJSONObject: message), bytes.count < limit else {
			completion(.failure(EngineError.invalidRequest))
			return
		}
		if let mutation { rememberMutation(mutation) }
		pending[id] = { result in
			guard let mutation else { completion(result); return }
			if case .failure(let error) = result, error as? EngineError == .unavailable {
				completion(.failure(EngineError.outcomeUnknown(mutation)))
			} else {
				completion(result)
			}
		}
		timers[id] = Timer.scheduledTimer(withTimeInterval: timeout, repeats: false) { [weak self] _ in
			Task { @MainActor in self?.requestTimedOut(id) }
		}
		write(message)
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
				if let result = value["result"] as? [String: Any] {
					if let identity = result["_pendingMutation"] as? String { rememberMutation(identity); pollMutation(identity, completion: completion) }
					else { completion(.success(result)) }
				}
				else {
					let error: EngineError
					switch value["code"] as? String {
					case "job_record_too_large": error = .jobRecordTooLarge
					case "invalid_configuration": error = .invalidConfiguration
					case "render_too_large": error = .renderTooLarge
					case "snapshot_expired": error = .snapshotExpired
					case "migration_busy": error = .migrationBusy
					case "snapshot_capacity": error = .snapshotCapacity
					default: error = .operation
					}
					completion(.failure(error))
				}
			} else {
				fail("Invalid response from processing component.")
				return
			}
		}
		if buffer.count >= limit { fail("Invalid response from processing component.") }
	}

	private func pollMutation(_ identity: String, completion: @escaping (Result<[String: Any], Error>) -> Void) {
		request(method: "POST", path: "/api/config/migration/operation", body: ["operationId": identity]) { [weak self] response in
			switch response {
			case .failure:
				completion(.failure(EngineError.outcomeUnknown(identity)))
			case .success(let value):
				guard value["operationId"] as? String == identity else { completion(.failure(EngineError.operation)); return }
				if value["state"] as? String == "complete", let result = value["result"] as? [String: Any] {
					completion(.success(result))
					self?.forgetMutation(identity)
				} else if value["state"] as? String == "notSaved" {
					self?.forgetMutation(identity)
					completion(.failure(EngineError.mutationNotSaved))
				} else if value["state"] as? String == "rejected" {
					self?.forgetMutation(identity)
					if value["code"] as? String == "invalid_configuration" {
						completion(.failure(EngineError.invalidConfiguration))
					} else {
						completion(.failure(EngineError.mutationRejected))
					}
				} else if value["state"] as? String == "running" {
					DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
						guard let self else { completion(.failure(EngineError.unavailable)); return }
						self.pollMutation(identity, completion: completion)
					}
				} else { completion(.failure(EngineError.outcomeUnknown(identity))) }
			}
		}
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
	enum EngineError: Error, Equatable { case unavailable, operation, jobRecordTooLarge, invalidRequest, invalidConfiguration, renderTooLarge, snapshotExpired, snapshotCapacity, migrationBusy, recoveryRequired, outcomeUnknown(String), mutationNotSaved, mutationRejected }
}
