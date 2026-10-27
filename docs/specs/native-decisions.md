# Native decisions and recovery contract

Implementation contract for T13, with T04/T14/T16/T20/T21/T24 dependencies. It applies the accepted Yep/Nope direction to the existing IO command semantics. These are coordinator design decisions within the authorized scope, not an implemented UI or new user-research result. Operate mode: make a decision and continue reading with a clear way back.

## Keep the reader's facts separate

Yep means interested; Nope means not interested. Both are available without a Curator result or Editor draft. The same canonical item shares its human decision across observations; different prompt contexts and NNW account status records remain separate.

NNW read/unread and Star remain their own commands, menus, synchronization and undo behavior. A decision command does not mark an NNW article read/unread, change its Star or represent a completed external collection. Ordinary NNW reading-on-selection behavior still applies when selection changes; do not add a second decision-driven read mutation. IO's old `mark_read` alias means accept AI and `mark_unread` means reopen the human decision: neither is an adapter for NNW article status. Existing IO Star aliases remain compatibility inputs; they do not redefine NNW Star.

## Visible actions and input

Show Yep and Nope as ordinary native decision controls in the article action area and contextual menu, with their current state and accessible descriptions `Interested` and `Not interested`. Use the same commands in the article menu so keyboard users have the full operation; keep normal Tab/Space/Return and focus behavior. Do not repurpose global arrow keys used for reading/navigation or intercept keystrokes inside article text, search or prompt editors. A gesture is an additional input, never the only way to act. Nope is not a trash action and should not use a deletion icon or claim that the original article is removed.

NNW already assigns timeline swipes to Read and Star. Retain those for a new NNW-first installation. A device preference `Swipe actions` offers `Reading` (existing Read/Star) or `Decisions` (right Yep, left Nope), with both mappings described before changing. For an IO migration, use its existing right-select/left-reject behavior as the migration default and disclose that mapping in the import preview; preserve an actual saved input preference when present. Do not invent a stored legacy setting merely because the old UI hardcoded a gesture. This is a choice between the two supported input mappings, not a gesture/workflow editor. Buttons and menu actions remain available in either mode. Never silently replace an existing shortcut or gesture.

## Acknowledgment, commitment and navigation

An IO decision first becomes a durable pending command with its own identity, idempotency key and undo deadline; the default source window is 10 seconds. Only a committed command changes the human decision and its authorization generation. Keep these observable states distinct: sending, pending with Undo, committed, undone and failed. A pending acceptance is not `Saved`, `Collected` or `Processing stopped`. Show a concise pending state until a public read confirms commitment. Do not restart the undo clock on refresh, navigation or process restart.

Capture the canonical item, displayed Curator context where applicable, current list scope/order and navigation position when an action begins. Repeated transport attempts use the same idempotency key. While acknowledgment is unknown, reconcile that command instead of issuing a second command. If the processor is unavailable, keep the prior decision visible with an actionable error; NNW reading and status commands remain usable.

After durable acknowledgment, Yep keeps the current article detail open. If the decision excludes it from the active filter, preserve the detail as the current selection until the user leaves; do not falsify filter membership or counts merely to keep it readable.

After durable acknowledgment, Nope advances to the next different canonical item in the current result order and scope. Skip duplicate observations of the item just judged. Continue pagination only within that same scope; do not invoke NNW's cross-source next-unread wrapping. At the end, show `You're done with this list` with the current scope still visible. Do not change feeds, reset filters or open unrelated content.

User navigation takes precedence over asynchronous responses. If the user has independently changed article, scope or order before acknowledgment, update the decision state without stealing selection. An eventual failure restores the affected item/status and offers `Show Article`; automatically return only when the user is still at the successor chosen by this same action. Do not resurrect a row for an older command over a newer confirmed decision.

## Undo and later changes

Undo cancels the specific pending command before its stored deadline. Integrate that operation with native Edit > Undo while it is actually eligible, preserving unrelated NNW undo entries. Do not register an unbounded inverse operation that pretends to reverse a committed IO command. Do not promise Redo for an undone external-effect command by resending its old idempotency key.

Use the service's success/refusal as authority, including the deadline boundary and a concurrent worker commit. If Undo loses that race, read the actual command state. For a committed decision explain `This decision has already been saved. You can change it.` For an expired but still pending command explain `The undo window ended. This decision is still pending.` Do not label an expired deadline as proof of commitment. Never display a successful undo before its public readback. Reconnect/restart recovers the original command state rather than turning an unknown outcome into Undecided.

Successful Undo of Yep leaves the article open. Successful Undo of Nope returns to the prior article if the reader is still at the automatically selected successor in the same scope; otherwise it preserves the user's current reading and offers `Show Article`. Restore the prior decision, not necessarily Undecided. Other observations update together without changing their independent NNW read/Star facts.

After commitment, Yep, Nope and `Clear Decision` remain explicit ways to change the human decision through new audited commands. Clear Decision maps to the existing IO reopen behavior, producing Undecided; it is not NNW Mark Unread and does not itself run a model. A change while an earlier command is pending must first resolve/cancel that command, or follow its confirmed commitment with a new command. Do not allow two unknown operations to race into contradictory UI claims. Later changes cannot promise that removed body bytes, completed collection or adopted issue content have been reversed.

## Side effects and configuration

On committed Nope, retain IO's transactional decision, authorization-generation change, pending processing cancellation, pending collection withdrawal and durable cleanup request. A running job can finish computation, but its old-generation body/draft write is refused. A later Yep or Clear Decision uses the existing guards and does not revive older work. The pending undo window is not a promise that processing has already stopped. Never interrupt a file/database write merely to make a spinner disappear.

Nope cleanup and Yep-to-collection linkage are visible settings with explicit scope and consequences. Preserve imported owner values; a new unconfigured integration is inactive. A disabled optional cleanup policy must still retain decision/cancellation/late-write protection. Changes do not silently execute historical actions, replan existing recovery deadlines or remove protected/adopted material. The exact retention/execution checks are owned by T21 and remain mandatory.

When Yep linkage is enabled, a committed Yep can authorize the existing collection workflow; show its effective destination and separate `Queued`, `Collecting`, `Collected` and failure states from the human decision. Capture the action's configured linkage/destination identity so changing a setting cannot redirect an already accepted command to an unrelated target. Recheck current authorization and target access before any external write; enabling linkage later does not retroactively collect old Yep items. Disabling/revoking access cannot be bypassed by an older pending command. Retain uncertain receipt evidence for reconciliation rather than inventing a new attempt.

Nope or Clear Decision withdraws only eligible pending intents under the source rules, not a verified existing Zotero parent or adopted issue block. A saved decision is not an external-success receipt. Collection, adoption and export remain separately accessible actions without an artificial requirement to open/read a Draft first. Actual media/material eligibility, target ownership and anti-overwrite checks still apply.

## Required observable checks

| Scenario | Required evidence |
| --- | --- |
| No AI result, failed AI, or no Draft | Yep/Nope and Clear Decision work through the real public command boundary; NNW read/Star facts are unchanged by the decision command |
| Same content in two feeds with different prompts | One decision/history, two preserved observations and independent prompt results; Nope skips the duplicate |
| Pending/committed/failed and acknowledgment loss | Same command identity on retry, true state after restart, no false Saved/Collected or doubled side effect |
| Yep under an Undecided-only filter | Detail remains open; actual membership/counts update correctly |
| Nope at a page boundary or end of list | Same scope/order, next different item or honest completion state; no cross-source wrapping |
| Navigate elsewhere before response | Late acknowledgment/failure/undo does not steal the new selection |
| Undo before, at and after deadline | Before succeeds, at/after refuses; actual previous decision restored only on success; native undo does not erase NNW status history |
| Undo races a worker commit | Exactly one outcome, confirmed state and correct navigation; no external rollback claim |
| Clear Decision after a committed Nope | Undecided, changed authorization generation, correct pending-intent/cleanup treatment, no NNW Mark Unread or inference |
| Nope, then Yep, then old result arrives | Old write still refused; only newly authorized work can write; reuse T24's two-device stale-event schedule |
| Linked/unlinked Yep and changed/revoked target | Correct captured destination and current authorization, no history replay, separate observed delivery receipts |
| Native input/accessibility | Buttons, menus, optional gesture mappings, focus/escape/keyboard, VoiceOver state and non-color feedback; inspect actual native UI |

Tests use synthetic items and controlled clocks at public seams, not private-owner data or hardcoded internal helpers. T13 records actual behavior; T16/T20/T21/T24 supply their connected integration/activity/retention/sync evidence. Batched native inspection covers normal/narrow windows, light/dark and supported accessibility settings. No render or screenshot is claimed by this document.

## Source evidence and deliberate changes

2026-10-28 read-only IO checkout: dirty HEAD `e9ba73f0b44a781ea68c0670114f9281f66f5cd3`. Source tests below were read, not executed as NoNews evidence.

- `backend/core.py`: enqueue/undo/commit, action aliases, manual decisions, reopen, generation checks and collection-intent withdrawal. SHA-256 `17c00866752ad7fea41b44d5be39703c8553f9b4afcfa3e8a91f2cf28683293e`.
- `backend/server.py`: review action acknowledgment with command ID/deadline and undo refusal. SHA-256 `c0ef0cddb50f2caa186d2634c2c630be6d25239b8278159525ed333267bc9647`.
- `extensions/InformationOS/static/native-ai.js`: pending versus committed feedback, duplicate observations, navigation tickets and failed-command restoration. SHA-256 `f6f77ca418d5d9e5333d5e3d6aff47f55e586d70adc7d04aff0e7f0af38923c2`. Its Select-advances behavior and committed FreshRSS-read mutation are superseded by the user's Yep-stays and independent NNW-status decisions; do not port them blindly.
- `extensions/InformationOS/static/normal-view.js`: existing decision gestures. SHA-256 `abde1541ba167420c5e491e0ad51960199f2cb936d1ffc8ef97873bbd16965fd`.
- `tests/test_core.py`, `tests/test_http_commands.py`, `tests/test_command_integration.py`: default undo boundary, reopened decisions, idempotency and pinned batch intent.
- NoNews `Mac/MainWindow/Timeline/TimelineViewController.swift`: existing native Read/Star swipe mappings and next-unread selection. `Shared/Commands/MarkStatusCommand.swift`: account-scoped read/Star undo. These remain native reader behavior, not IO aliases.
