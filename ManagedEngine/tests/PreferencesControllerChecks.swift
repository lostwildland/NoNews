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
			$0.path == path && (bodyKey == nil || $0.body[bodyKey!] as? String == bodyValue)
		}) else { fatalError("No pending \(path) request") }
		let request = pending.remove(at: index)
		request.completion(.success(value))
	}

	func body(path: String) -> [String: Any] {
		guard let request = pending.first(where: { $0.path == path }) else { fatalError("No pending \(path) request") }
		return request.body
	}
}

@main
@MainActor
struct PreferencesControllerChecks {
	static func service(_ id: String, _ target: String) -> [String: Any] {
		["id": id, "name": id, "type": "magpie", "endpoint": "http://\(id)", "targets": [target], "stale": false]
	}

	static func main() {
		let client = DeferredPreferencesRequests()
		let controller = ProcessingPreferencesViewController(requestClient: client)
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
		print("Preferences controller request wiring checks passed")
	}
}
