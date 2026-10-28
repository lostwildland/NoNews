# T03 native configuration: source audit and HIG acceptance

2026-10-28. Source pin `6da5efa249ede069bf8ebccec8ecb86d198da9e2`, `Mac/Preferences/ProcessingPreferencesViewController.swift`. Coordinator source assessment only: no application, Keychain, provider, keyboard, VoiceOver or visual test was run. This does not replace the required paired Standards/Spec review or the bounded rendered UX pass.

## Open source finding: editor responses can change the wrong binding

**P1, source-derived; not runtime-reproduced.** `loadBinding` clears binding state when it starts but accepts every response without checking the currently selected service or editor intent. With requests for A then B, a B response followed by A sets `selectedBinding` to A and adds A's targets while the visible service selection remains B. `promptBody` then uses A's service ID. The native contract requires an explicit service/target binding and forbids silently carrying another service's identifier into it. Backend validation cannot detect a mismatch between a valid request and the user's different visible selection.

The same unscoped callback pattern appears in `showPrompt`, paged history/references and service/prompt save/readback. A delayed prompt load can overwrite a newer selection or New form. A completed service save unconditionally changes `currentService` and clears the credential field, even if another form is being edited. `savePrompt` captures one body, waits for reference discovery, then its Save as Copy branch reads the mutable form again. These are related editor-intent failures requiring one coherent correction, not separate claims of observed data loss.

Root inspected the actual callback sites, request dispatch, binding/body construction, service and prompt selection/reset, shared-save confirmation and readback. The original owner received the finding by steer during R12; root did not edit its active source. Preserve completed durable writes and Keychain updates for their original identity while preventing stale callbacks from replacing a newer editor's values or acknowledgement. Tests must exercise the controller/request wiring; the migration-only state helper does not cover these forms.

Follow-up source checkpoint `00c2665` reports matching editor guards and use of the captured Save as Copy input. The owner explicitly reports that actual controller-wiring regressions remain unwritten. This is a reported source correction awaiting fresh review and behavior tests, not closure of the6da5efa finding.

## HIG references consulted

Apple's official pages were read on 2026-10-28 through their Markdown representations after the documentation renderer returned a JavaScript shell:

- [Settings](https://developer.apple.com/design/human-interface-guidelines/settings): retain the expected macOS settings entry, stable pane toolbar and pane identity; group configuration by task. Keep the existing NNW settings structure.
- [Feedback](https://developer.apple.com/design/human-interface-guidelines/feedback): associate status with its actual action/context, make failures and recovery understandable, and distinguish a completed Apply from a later readback failure. The asynchronous identity defect above is grounded in the product contract; it is not a claimed visual HIG failure.
- [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility): verify familiar, perceivable and adaptable interaction in the running app. Native control classes alone do not establish accessible labels, focus order or announcements.

The current source uses AppKit controls, a secure credential field and selectable report text. The report's scroll view is nested in the pane's scroll view; focus and scrolling need actual inspection. No accessibility or platform-conformance score is assigned from source.

## Required behavioral checks

1. Deliver service A/B responses out of order. The visible service, exact target and saved request binding must agree; no response may erase a newer unsaved credential. An incomplete binding must refuse Save clearly.
2. Deliver prompt/history/reference responses after another selection, New or Cancel. Keep the newer editor's text, identity, binding and used-by/history state. A delayed shared-save/copy confirmation must apply only to its original immutable action or be invalidated explicitly.
3. Fail credential store, read and removal using synthetic identities. Show the actual incomplete/recovery state, preserve unrelated fields and secrets, and keep configuration acknowledgements associated with their originating service. Real Keychain checks require the later grant.
4. Complete Apply, then fail readback; retry without losing the confirmed acknowledgement. Change service/input while old operations finish; historical waiting must not claim that current claims are paused.
5. Browse every report section and a multipart long record with the keyboard. Check tab/focus order, section and record names, Previous/Next/Retry, scroll reachability and full selectable text without trapping focus or truncating stored values.
6. Inspect current-source native windows in light/dark and supported narrow/wide layouts, VoiceOver, Reduce Motion/Transparency and state recovery. Record build/OS/scenario and actual results; include clean setup, processor unavailable and recoverable failure states.

All checks above remain pending unless separately tied to executed current-source evidence. Complete them in the planned bounded native pass after source review and the serialized build grant. No UI evidence is inferred from compilation, a service fixture or the standalone engine check.
