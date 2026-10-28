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
	}
}
