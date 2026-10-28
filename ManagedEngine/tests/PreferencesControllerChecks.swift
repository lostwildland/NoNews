import AppKit
import Foundation

@MainActor
final class DeferredPreferencesRequests: ProcessingPreferencesRequesting {
	struct Pending {
		let method: String
		let path: String
		let body: [String: Any]
		let completion: (Result<[String: Any], Error>) -> Void
	}
	private(set) var pending: [Pending] = []

	func request(method: String, path: String, body: [String: Any], completion: @escaping (Result<[String: Any], Error>) -> Void) {
		pending.append(Pending(method: method, path: path, body: body, completion: completion))
	}

	func respond(path: String, bodyKey: String? = nil, bodyValue: String? = nil, value: [String: Any]) {
		guard let index = pending.firstIndex(where: {
			requestMatches($0, path: path, bodyKey: bodyKey, bodyValue: bodyValue)
		}) else { fatalError("No pending \(path) request") }
		let request = pending.remove(at: index)
		request.completion(.success(value))
	}

	private func requestMatches(_ request: Pending, path: String, bodyKey: String?, bodyValue: String?) -> Bool {
		guard request.path == path else { return false }
		guard let bodyKey else { return true }
		return request.body[bodyKey] as? String == bodyValue
	}

	func body(path: String) -> [String: Any] {
		guard let request = pending.first(where: { $0.path == path }) else { fatalError("No pending \(path) request") }
		return request.body
	}

	func bodies(path: String) -> [[String: Any]] { pending.filter { $0.path == path }.map(\.body) }
}

@main
@MainActor
struct PreferencesControllerChecks {
	static func service(_ id: String, _ target: String) -> [String: Any] {
		["id": id, "name": id, "type": "magpie", "endpoint": "http://\(id)", "targets": [target], "stale": false]
	}

	static func main() async throws {
		let client = DeferredPreferencesRequests()
		let controller = ProcessingPreferencesViewController(requestClient: client)
		controller.loadView()
		for width: CGFloat in [512, 640] {
			for tab in ["services", "prompts"] {
				let problems = controller.debugLayout(tab, width: width)
				precondition(problems.isEmpty, problems.joined(separator: "\n"))
			}
		}
		precondition(controller.debugEditorHeights().0 >= 160 && controller.debugEditorHeights().1 >= 150)
		controller.debugEditPromptText(String(repeating: "Long instruction line\n", count: 100))
		controller.debugSetReportDetail(String(repeating: "Long report line\n", count: 100))
		precondition(controller.debugEditorHeights().0 > 1000 && controller.debugEditorHeights().1 > 1000)
		controller.debugEditPromptText("")
		controller.debugSetReportDetail("")
		controller.debugSetServiceEditor(["id": "magpie", "name": "Magpie", "type": "magpie", "endpoint": "http://magpie", "credential": "must-clear"])
		precondition(!controller.debugCredentialVisible() && controller.debugCredentialText().isEmpty)
		controller.debugSetServices([service("gateway-a", "target-a"), service("gateway-b", "target-b")])

		controller.debugSelectBinding("gateway-a", selected: "target-a")
		controller.debugSelectBinding("gateway-b", selected: "target-b")
		client.respond(path: "/api/config/services", bodyKey: "id", bodyValue: "gateway-b", value: service("gateway-b", "target-b"))
		client.respond(path: "/api/config/services", bodyKey: "id", bodyValue: "gateway-a", value: service("gateway-a", "target-a"))
		precondition(controller.debugVisibleBinding() == "gateway-b")
		precondition(controller.debugTargets() == ["target-b"])
		controller.debugSetPromptEditor(["id": "prompt-b", "name": "B", "role": "curator", "text": "B", "serviceId": "gateway-b", "target": "target-b"])
		precondition(controller.debugPromptBody()?["serviceId"] as? String == "gateway-b")

		controller.debugShowPrompt("prompt-a")
		controller.debugShowPrompt("prompt-b")
		client.respond(path: "/api/config/prompts", bodyKey: "id", bodyValue: "prompt-b", value: ["id": "prompt-b", "name": "B", "role": "curator", "text": "B", "serviceId": "gateway-b", "target": "target-b"])
		client.respond(path: "/api/config/prompts", bodyKey: "id", bodyValue: "prompt-a", value: ["id": "prompt-a", "name": "A", "role": "curator", "text": "A", "serviceId": "gateway-a", "target": "target-a"])
		precondition(controller.debugPromptSnapshot()["id"] as? String == "prompt-b")
		precondition(controller.debugPromptSnapshot()["text"] as? String == "B")

		controller.debugSetPromptEditor(["id": "prompt-a", "name": "A", "role": "curator", "text": "captured", "serviceId": "gateway-a", "target": "target-a"])
		controller.debugCopyPrompt()
		let copyBody = client.body(path: "/api/config/copy")
		controller.debugEditPromptText("new editor text")
		let configuration = copyBody["configuration"] as? [String: Any]
		precondition(configuration?["text"] as? String == "captured")
		precondition(configuration?["serviceId"] as? String == "gateway-a")
		precondition(configuration?["target"] as? String == "target-a")
		client.respond(path: "/api/config/copy", value: ["id": "copy", "name": "A", "role": "curator", "text": "captured", "serviceId": "gateway-a", "target": "target-a"])
		precondition(controller.debugPromptSnapshot()["text"] as? String == "new editor text")

		let input = MigrationReviewState.Input(serviceID: "gateway-b", choices: ["kit/curator": "target-b"], editorServices: [:])
		controller.debugApplyResult(["status": "applied", "operationId": "apply-1"], input: input)
		precondition(controller.debugApplyAcknowledgement(input).contains("Mappings applied"))
		precondition(controller.debugReadbackFailure(input).contains("Mappings applied"))
		let rejected = controller.debugRecoveryMessage(.invalidConfiguration)
		precondition(rejected.contains("rejected"))
		precondition(!rejected.contains("still being confirmed"))
		precondition(controller.debugRecoveryMessage(.outcomeUnknown("mutation")).contains("still being confirmed"))
		precondition(controller.debugRecoveryMessage(.mutationNotSaved).contains("No configuration change was made"))

		let serviceA: [String: Any] = ["id": "service-a", "name": "A", "type": "openai-compatible",
			"revision": "revision-a", "endpoint": "https://a.example", "credential": "secret-a", "targets": [], "stale": true]
		let serviceB: [String: Any] = ["id": "service-a", "name": "B", "type": "openai-compatible",
			"revision": "revision-b", "endpoint": "https://b.example", "credential": "secret-b", "targets": [], "stale": true]
		controller.debugSetServices([serviceA, serviceB])
		var stored: [String] = []
		controller.debugSetCredentialStore { _, secret in stored.append(secret) }
		controller.debugSetCredentialRead { _ in nil }
		controller.debugSetServiceEditor(serviceA)
		controller.debugSaveService()
		controller.debugSetServiceEditor(serviceB)
		controller.debugSaveService()
		client.respond(path: "/api/config/services", bodyKey: "endpoint", bodyValue: "https://b.example", value: serviceB)
		client.respond(path: "/api/config/services", bodyKey: "endpoint", bodyValue: "https://a.example", value: serviceA)
		let credentialUpdates = client.bodies(path: "/api/config/services").filter { $0["credentialState"] != nil }
		precondition(credentialUpdates.count == 1)
		precondition(credentialUpdates[0]["expectedRevision"] as? String == "revision-b")
		precondition(controller.debugServiceSnapshot()["name"] as? String == "B")
		precondition(stored == ["secret-b"])
		client.respond(path: "/api/config/services", bodyKey: "credentialState", bodyValue: "verified", value: serviceB.merging(["credentialState": "verified"]) { _, new in new })

		let missing = serviceB.filter { $0.key != "credential" }.merging(["credentialState": "verified"]) { _, new in new }
		controller.debugSetServiceEditor(missing)
		controller.debugRefreshService()
		precondition(client.bodies(path: "/api/config/refresh").isEmpty)
		precondition(client.bodies(path: "/api/config/services").contains { $0["credentialState"] as? String == "incomplete" && $0["expectedRevision"] as? String == "revision-b" })
		client.respond(path: "/api/config/services", bodyKey: "credentialState", bodyValue: "incomplete", value: missing.merging(["credentialState": "incomplete"]) { _, new in new })
		precondition(controller.debugServiceSnapshot()["credentialState"] as? String == "incomplete")

		controller.debugSetCredentialStore { _, _ in throw ProcessingEngine.EngineError.operation }
		controller.debugSetServiceEditor(serviceB)
		controller.debugSaveService()
		client.respond(path: "/api/config/services", bodyKey: "endpoint", bodyValue: "https://b.example", value: serviceB)
		precondition(client.bodies(path: "/api/config/services").contains { $0["credentialState"] as? String == "incomplete" })
		client.respond(path: "/api/config/services", bodyKey: "credentialState", bodyValue: "incomplete", value: missing.merging(["credentialState": "incomplete"]) { _, new in new })
		precondition(controller.debugServiceSnapshot()["credentialState"] as? String == "incomplete")
		precondition(controller.debugRecoveryControl().feedback.contains("could not be stored or read"))
		precondition(controller.debugCredentialText() == "secret-b")
		precondition(controller.debugServiceLabel(["id": "gateway-b", "name": "Gateway B", "connectionState": "Authentication failed; directory stale; last checked now"]).contains("Authentication failed"))

		let copyClient = DeferredPreferencesRequests()
		let copyController = ProcessingPreferencesViewController(requestClient: copyClient)
		copyController.loadView()
		copyController.debugSetServices([service("gateway-a", "target-a")])
		let original: [String: Any] = ["id": "original", "name": "Original", "role": "curator", "text": "Text", "serviceId": "gateway-a", "target": "target-a"]
		let copied = original.merging(["id": "copy", "name": "Copy"]) { _, new in new }
		copyController.debugSetPromptEditor(original)
		copyController.debugCopyPrompt()
		copyClient.respond(path: "/api/config/copy", value: copied)
		copyClient.respond(path: "/api/config/prompts", value: ["prompts": [original, copied]])
		precondition(copyController.debugSelectedPromptID() == "copy")
		precondition(copyController.debugPromptBody()?["id"] as? String == "copy")
		copyController.debugCopyPrompt()
		copyClient.respond(path: "/api/config/copy", value: original.merging(["id": "second-copy"]) { _, new in new })
		copyController.debugSetPromptEditor(original)
		copyClient.respond(path: "/api/config/prompts", value: ["prompts": [original, copied]])
		precondition(copyController.debugSelectedPromptID() == "original")
		precondition(copyController.debugPromptBody()?["id"] as? String == "original")

		let returningClient = DeferredPreferencesRequests()
		let returningController = ProcessingPreferencesViewController(requestClient: returningClient)
		returningController.loadView()
		returningController.debugSetServices([service("gateway-a", "target-a")])
		returningController.debugSetPromptEditor(original)
		returningController.debugViewDidAppear()
		returningClient.respond(path: "/api/config/services", value: ["services": [service("gateway-a", "target-a")]])
		returningClient.respond(path: "/api/config/prompts", value: ["prompts": [original]])
		precondition(returningController.debugSelectedPromptID() == "original")
		var removed: [String] = []
		returningController.debugSetCredentialRemove { removed.append($0) }
		returningController.debugRememberPendingCredentialDeletion("service-a")
		returningController.debugRetryPendingCredentialDeletions()
		precondition(removed == ["service-a"] && returningController.debugPendingCredentialDeletions().isEmpty)

		try await checkRecovery()
		print("Preferences controller request wiring checks passed")
	}

	static func eventually(_ condition: () -> Bool) async throws {
		for _ in 0..<800 {
			if condition() { return }
			try await Task.sleep(for: .milliseconds(10))
		}
		throw NSError(domain: "Recovery condition timed out", code: 1)
	}

	static func checkRecovery() async throws {
		let root = URL(fileURLWithPath: CommandLine.arguments[1])
		let data = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
		try FileManager.default.createDirectory(at: data, withIntermediateDirectories: true)
		defer { try? FileManager.default.removeItem(at: data) }
		let mode = data.appendingPathComponent("mode")
		func scenario(_ name: String) throws { try Data(name.utf8).write(to: mode, options: .atomic) }
		try scenario("poll-fail")
		let engine = ProcessingEngine(testRuntime: root.appendingPathComponent("ManagedEngine/.prepared/python/bin/python3"),
			entry: root.appendingPathComponent("ManagedEngine/tests/configuration_recovery_fixture.py"), dataRoot: data)
		engine.start()
		try await eventually { engine.state == .ready }
		var outcome: ProcessingEngine.EngineError?
		engine.request(method: "PUT", path: "/api/config/services", body: ["name": "Synthetic"]) { result in
			if case .failure(let error) = result { outcome = error as? ProcessingEngine.EngineError }
		}
		try await eventually { outcome != nil }
		guard case .outcomeUnknown(let identity) = outcome else { throw NSError(domain: "Expected unknown polling outcome", code: 1) }
		precondition(engine.unconfirmedMutations.contains(identity))
		engine.stop()
		try await eventually { engine.state == .stopped }
		precondition(engine.unconfirmedMutations.contains(identity))
		try scenario("complete-ack-fail")
		engine.start()
		try await eventually { engine.state == .ready }
		var recovered = false
		engine.recoverMutation(identity) { result in
			if case .success(let value) = result { recovered = value["id"] as? String == "saved" }
		}
		try await eventually { recovered }
		try await Task.sleep(for: .milliseconds(150))
		precondition(engine.unconfirmedMutations.contains(identity))

		try scenario("ack-pending")
		let controller = ProcessingPreferencesViewController(engine: engine)
		controller.loadView()
		controller.debugAcknowledgeUnknownSaves()
		precondition(!controller.debugRecoveryControl().enabled)
		precondition(controller.debugRecoveryControl().feedback.contains("Acknowledging"))
		precondition(engine.unconfirmedMutations.contains(identity))
		try scenario("ack-fail")
		try await eventually { controller.debugRecoveryControl().feedback.contains("could not be acknowledged") }
		precondition(controller.debugRecoveryControl().enabled && engine.unconfirmedMutations.contains(identity))
		try scenario("ack-wrong")
		controller.debugAcknowledgeUnknownSaves()
		try await eventually { controller.debugRecoveryControl().feedback.contains("could not be acknowledged") }
		precondition(engine.unconfirmedMutations.contains(identity))
		try scenario("ack-pending")
		controller.debugAcknowledgeUnknownSaves()
		engine.stop()
		try await eventually { engine.state == .stopped }
		precondition(!controller.debugRecoveryControl().enabled && engine.unconfirmedMutations.contains(identity))
		engine.start()
		try await eventually { engine.state == .ready }
		controller.debugAcknowledgeUnknownSaves()
		try scenario("ack-success")
		try await eventually { engine.unconfirmedMutations.isEmpty }
		precondition(controller.debugRecoveryControl().hidden)
		precondition(controller.debugRecoveryControl().feedback.contains("receipts acknowledged"))
		try scenario("rejected")
		outcome = nil
		engine.request(method: "PUT", path: "/api/config/services", body: ["name": "Synthetic rejection"]) { result in
			if case .failure(let error) = result { outcome = error as? ProcessingEngine.EngineError }
		}
		try await eventually { outcome != nil }
		precondition(outcome == .invalidConfiguration)
		precondition(controller.debugRecoveryMessage(.mutationRejected).contains("rejected"))
		try await eventually { engine.unconfirmedMutations.isEmpty }
		engine.stop()
		try await eventually { engine.state == .stopped }
		print("Native polling failure/restart, durable rejection and pending/failed/mismatched/successful acknowledgement checks passed")
	}

}
