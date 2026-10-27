# Native processing configuration contract

T03/T04/T11 implementation detail under the accepted full-parity specification. This resolves ordinary product choices within the authorized scope; it is not implementation or runtime acceptance. The visitor mode is Operate: configure one reusable instruction with its execution choice, then return to reading.

## Native surface and primary journey

Keep NNW's `PreferencesWindowController`, native toolbar categories and cached pane controllers. Extend the Processing pane delivered by T02 with Services, Prompts and Sources sections; do not add a separate top-level toolbar item per role, provider or prompt. T03 adds Services and Prompts. T04 supplies the actual source-policy surface. Engine availability remains visible without replacing these forms with an engine dashboard.

Services lists configured connections by the user's name and a textual connection/catalog state. Its detail form shows the connection type, endpoint and secure credential control where the protocol requires one. `Refresh Models` or `Refresh Targets` fetches the directory only; it never sends an article, prompt or inference request. A successful directory read is labelled as a directory check, not proof that generation works. Retain the last observed directory and its timestamp on failure, visibly stale.

Prompts lists saved entries grouped under Curator and Editor. The detail editor has a name, role, prompt text, service and explicit model/target selection together, plus `Used by` and `History`. Use `Target` for a Magpie route and `Model` when the selected service exposes an actual requested model. These are binding choices, not role defaults. Switching service does not silently carry an unrelated provider's model identifier to the new service.

Creating a prompt does not require configuring a feed or producing a sample result. Save validates locally, persists the complete configuration and returns an observable saved state; Cancel preserves the previous version. No prompt test-run command or conversational onboarding is added. Empty services and prompts each have one direct add action and explain that ordinary reading continues without AI. An unavailable processor leaves existing configuration visible and disables mutation with a concise recovery action.

The implementation owner must support Magpie and document the additional direct/compatible service protocol actually implemented. Do not claim arbitrary-provider compatibility, expose unsupported controls, or manufacture a target catalogue. All selected service/target identifiers survive reload and process restart.

## Existing Magpie protocol and routing migration

The source adapter reads `GET /v1/models` and submits generation to `POST /v1/chat/completions`; a Magpie target is the exact opaque `model` request value, not an inferred upstream model name. Its endpoint normalization rejects embedded credentials, query and fragment and avoids a duplicate trailing `/v1`. The source connection has no upstream credential field: Magpie owns upstream authentication/routing. A direct or protected compatible connection must document and securely implement its own actual authentication protocol rather than pretending that an upstream key belongs to a Magpie route. New installation/configuration performs no gateway discovery or inference without the reader's requested action.

Keep the source's directory check distinct from inference: cached target IDs and last-check time remain visible on refresh failure, and an endpoint change invalidates the previous endpoint's directory. Preserve requested target, `X-Magpie-Provider`, `X-Magpie-Model` and response-reported model as separate facts; missing actual provenance stays unknown. Do not lowercase/relabel target IDs or fill missing actual-model metadata with the route name.

Retain the implemented legacy-target migration as an explicit advanced action, not a side effect of saving a prompt or endpoint. Preview original Kit/role/provider/model bindings, proposed exact/explicit target matches, unresolved bindings and pending/running work. Pause new claims, let existing runs drain and show the source `waiting` state without rewriting contracts while runs remain active. Apply reviewed mappings against a current directory and preserve mapping evidence. Only eligible unfinished stage contexts change; completed result provenance, job identities and explicit queued Editor targets remain intact. Unresolved work stays blocked, not silently cancelled or rerouted. The migration commands perform no inference, historical requeue or content/integration write themselves. Applying mappings may resume existing eligible claims under the current processing policy; show that effective state, recheck normal execution guards, and never bypass passive post-import activation or execution ownership. T03 implements the configuration/command boundary; T27 verifies imported mappings and T11 exercises actual runner continuity.

## Save, reuse and references

One Save commits the name, instructions and execution binding as a coherent configuration; validation or persistence failure cannot expose newly saved instructions with the previous binding, or the reverse. Credentials remain in secure centralized storage, referenced by service, and are excluded from prompt sharing, synchronized ordinary settings, errors and logs. A partial credential-storage failure leaves the connection explicitly incomplete rather than reporting a working save.

An unchanged prompt text does not add a text-history version. Renaming or changing its model must not manufacture text changes or rewrite historical runs. Historical IO prompt-version IDs, timestamps and exact contents remain intact. `History` previews read-only text versions; `Restore Text` saves the selected older text as the new current text, retaining the current visibly selected service/model. If that text is already current, restoration is a no-op. The UI must state that this action restores instructions; it must not imply that an old model or old result is being restored. A later configuration-history feature is not required to deliver existing IO text history.

Before changing a prompt shared by sources, show the affected source names/count and offer `Save Changes` or `Save as Copy`. The copy has independent identity and references; it does not take over existing sources. No existing source binding changes as a side effect of merely duplicating a prompt. The actual source list is owned by T04; T03 must implement the durable reference checks and test them without presenting synthetic sources to users.

Removing a prompt or service cannot leave silent dangling live references. Show the references and require an explicit replacement/unbind operation, or refuse removal until they are resolved. Preserve instruction/model provenance already referenced by historical results. A removed or inaccessible connection is an actionable unavailable binding, never a reason to select a different provider. Do not add a hidden fallback/default inheritance layer.

An unchanged existing Magpie target remains visible and can be retained while its cached directory is stale, matching IO. A newly selected target must pass the protocol's current catalogue/identifier validation. Do not relabel a stale observation as proof the target was deleted. Changing an endpoint invalidates the old endpoint's directory result; a valid old catalogue cannot validate a newly configured host.

## Variables and output contracts

Expose discoverable input-variable help beside the editor, without asking users to maintain JSON output schemas. Keep existing role/material contracts and legacy aliases. IO supplies `description` as an alias of `content`, and Paper abstract material also supplies `content`/`description`; a non-Paper route does not gain an abstract merely because a template requests it.

Validate the template before interpolation and substitute once. Source material containing literal `{{content}}`, LaTeX braces or another template-like expression remains source text; it is never recursively interpreted as instructions. Unknown names fail before a model request, with the variable named and the applicable inputs explained. A prompt using a valid media-specific input is checked for compatibility when assigned to that media and for material availability at execution. Migration preserves invalid legacy text with an actionable configuration error rather than silently rewriting it.

Maintain the 200 KB nonempty text bound from IO. Preserve current Curator numeric-score/output validation, Editor output validation and truncated/malformed-response errors. Directory/network/authentication/invalid-target/material/output failures stay distinct; none become a zero score, a successful empty result or an alternate-provider retry.

Personal output language and typography rules become explicit prompt preferences, with source-compatible imported defaults and language-independent new-user defaults. Follow [native-output-preferences.md](native-output-preferences.md); do not copy the source's Chinese-title and prose-formatting checks as universal requirements. Mandatory material/score/output integrity checks remain enforced.

## Configuration timing: preserve the IO boundary

These are distinct boundaries, not one blanket promise that everything freezes when a queue entry is created:

- Automatic ingestion work uses the feed contract pinned to the item. Editing a feed affects later item admission and does not rewrite historical item contracts or enqueue history. The current disabled policy still prevents automatic/scheduled spending.
- Explicit user and batch commands adopt the current compatible feed contract. A media mismatch is a visible refusal, not automatic reclassification. The native rerun/batch UI exposes the chosen scope and retains prior results.
- At processing-run binding, IO resolves and freezes the effective threshold, both roles' prompt-version IDs and model configurations. Saving configuration while a run is executing cannot mix old Curator rules with new Editor rules inside that run. A missing/deleted bound prompt produces an explicit refusal rather than a lookup of the newest prompt.
- A queued explicit Editor job can already carry a pinned `editor_target`. Preserve that job-specific pin and the existing actual-model checks; do not overwrite it with a newly selected prompt target during execution or retry. A route name, actual upstream model and model self-report remain separate provenance facts.

The port must test restart/retry semantics against the source job and stage owners. Do not replace them with the research proposal that every later-created stage independently picks current settings, or claim a stronger queue-wide snapshot guarantee without implementing and documenting a source-compatible migration.

## Required observable checks

The T03 owner exercises native configuration backed by the managed service: service creation/reload, read-only directory refresh, prompt creation with an explicit binding, independent Curator/Editor reuse, copy/rename/reference-safe removal, no-op text save, text history/restore, failed coherent save, unavailable/stale binding, and secure credential failure. Tests inspect persisted public readback after restart; a populated form alone is insufficient.

T03/T04/T11 jointly test a configuration save during a running synthetic pipeline, an automatically admitted item after a feed edit, explicit rerun adoption, a queued pinned-Editor target, and an unresolved/missing bound prompt. Expected configuration IDs/material/output must be asserted independently of the implementation helper under test. No inference is made merely to save or refresh configuration.

Native acceptance uses one batched inspection of empty, configured, saving and unavailable states, keyboard focus/escape/cancel, VoiceOver labels, narrow-window overflow and supported appearances. Use stock AppKit controls, NNW typography/spacing and system materials; do not apply blur to prompt text. One correction/confirmation batch follows material findings. Screenshot and live-provider checks remain unproven until actually performed.

## Source evidence

Read-only IO working tree inspected on 2026-10-28; HEAD `e9ba73f0b44a781ea68c0670114f9281f66f5cd3` is dirty and does not identify all inspected bytes. No personal database/configuration or prompt contents were read.

- `backend/service.py`: `save_prompt`, `prompt`, `restore_prompt`, `save_model`, `settings` — database authority, nonempty/size guard, no-op text saves, role-scoped restore, separate existing model records and stale-catalog exception for an unchanged binding.
- `backend/pipeline.py`: `process`, `_bind_run_contract`, `_freeze_run_values`, `_saved_prompt`, `_fill_prompt`, `_task_config`, explicit Editor job handling — admission versus run boundaries, bound versions, single-pass interpolation and pinned target exception.
- `backend/magpie.py`: `normalize_url`, `status`, `refresh` — credential-free normalized URL, cached directory, staleness and explicit no-inference distinction.
- `backend/magpie_migration.py`: `preview`, `pause`, `apply`, `prepare_startup` — explicit old-binding mapping, drain-first transition, pending-block evidence and preserved completed provenance; these source paths were read, not executed.
- `backend/ai_client.py`: `RuntimeAIClient._complete` — requested target versus actual provider/model and response self-report, invalid/truncated-output handling.
- `tests/test_prompt_contract.py`, `tests/test_prompt_placeholders.py`, `tests/test_magpie.py` provide source test intent; these source tests were read, not rerun or treated as live NoNews proof.
- NoNews `Mac/Preferences/PreferencesWindowController.swift` and `Technotes/SwiftUI-UIKit-AppKit-Guidelines.markdown` establish the native pane framework and AppKit/xib authority. Final T02 implementation remains its accepted dependency, not a guessed API supplied by this document.
