import Foundation

@main struct MigrationReviewStateChecks {
	static func main() {
		var state = MigrationReviewState()
		let first = MigrationReviewState.Input(serviceID: "gateway-a", choices: ["role": "a"], editorServices: [:])
		let second = MigrationReviewState.Input(serviceID: "gateway-b", choices: ["role": "b"], editorServices: ["job": "gateway-b"])
		let old = state.begin(first)
		let current = state.begin(second)
		precondition(state.complete(current, current: second))
		precondition(!state.complete(old, current: second))
		precondition(state.reviewed == second)
		state.invalidate()
		precondition(state.reviewed == nil && !state.complete(current, current: second))
		let changed = state.begin(first)
		precondition(!state.complete(changed, current: second))
		precondition(MigrationReviewState.status(paused: true, waiting: true) == "Waiting; claims paused")
		precondition(MigrationReviewState.status(paused: true, waiting: false) == "Claims paused")
		precondition(MigrationReviewState.status(paused: false, waiting: true) == "Claims active")
		let applyA = state.beginApply(first)
		_ = state.begin(second)
		precondition(state.recordApply(status: "applied", ticket: applyA))
		precondition(state.applyAcknowledgement(for: second).isEmpty)
		precondition(state.readbackFailure(for: second) == "The routing report could not be read; preview again.")
		precondition(state.applyAcknowledgement(for: first) == "Mappings applied. ")
		for _ in 0..<2 {
			_ = state.begin(first)
			precondition(state.readbackFailure(for: first) == "Mappings applied. The routing report could not be read; preview again.")
		}
		let applyB = state.beginApply(second)
		precondition(state.recordApply(status: "waiting", ticket: applyB))
		precondition(state.applyAcknowledgement(for: first).isEmpty)
		precondition(!state.recordApply(status: "applied", ticket: applyA))
		precondition(state.readbackFailure(for: second) == "The previous Apply waited for running work. The routing report could not be read; preview again.")
		precondition(state.applyAcknowledgement(for: second) + MigrationReviewState.status(paused: false, waiting: true) == "The previous Apply waited for running work. Claims active")
		precondition(!state.recordApply(status: "unknown", ticket: applyB))
		precondition(MigrationReviewState.serviceLabel(name: "Gateway", id: "first") != MigrationReviewState.serviceLabel(name: "Gateway", id: "second"))
	}
}
