# Prompt output preferences and legacy continuity

Implementation detail for the accepted user-controlled prompt/content language requirement. These are coordinator product choices under the authorized configurability scope, not runtime evidence or new questions for the user. UI localization remains English in this release.

## User-facing configuration

Keep these options in the existing prompt editor's Advanced disclosure, beside its output-requirements explanation. They belong to the reusable prompt, not to each source, the service, or the whole app. Curator and Editor remain independently selectable.

| Control | Choices | New prompt | Imported IO prompt |
| --- | --- | --- | --- |
| Title language | Follow instructions / Chinese | Follow instructions | Preserve the effective existing Chinese-title requirement where that role/material enforces it |
| Typography | Preserve generated text / Chinese editorial style | Preserve generated text | Preserve the existing applicable formatting behavior |

`Follow instructions` accepts a nonempty title in the language specified by the user's prompt. It does not claim to detect that language or certify translation quality. `Chinese` retains the existing usable-Chinese-title check where a generated title is required; an incompatible response is an output failure, not a zero score or a provider switch. The UI explains the required title alongside the prompt so a hidden language rule cannot contradict the visible instructions.

Typography is a formatting preference, independent of title language. Chinese editorial style retains the existing prose quotation, punctuation and spacing behavior where it currently applies. Preserve generated text performs no automatic conversion to Chinese punctuation. Neither option may damage protected code, links, image references, source identities or evidence flags. Original/source material is not restyled or translated by a generated-output preference.

Save, copy, affected-source preview and restart persistence follow the existing coherent prompt-save contract. Changing a preference affects eligible future processing only; it does not reformat stored results, requeue history or trigger inference. Restore Text retains the currently displayed execution binding and output preferences, and says so. Copy creates an independent configuration with the same visible preferences.

## Processing and migration boundary

Language and typography are preferences; finite 0–10 score validation, required reasons/materials, title-only unscored behavior, malformed/truncated response refusal and identity/provenance are mandatory. Do not make these invariants optional in order to accept another language. Do not add arbitrary schema/workflow editing.

Bind output preferences at the same run boundary as the effective prompt version/model configuration. A saved edit cannot change validation or formatting midway through an already bound run. Keep explicit queued Editor targets and source-compatible contract adoption unchanged. Imported active contexts receive their applicable legacy requirements; missing/ambiguous historical evidence stays explicit rather than being reclassified under new-user defaults.

Preserve imported prompt text, exact historical result JSON, hashes, version IDs and title fields, including `title_zh`. Do not rename historical keys or reinterpret an old result when a user selects Follow instructions. An internal adapter may accept a neutral generated-title field for new configurations and the documented legacy field for compatible imported configurations; it must preserve raw output and unambiguous provenance. User-facing controls do not expose or require maintenance of those internal JSON keys. New non-Chinese titles must not be labelled as verified Chinese translations or written to a destination's Chinese-only metadata field merely because a legacy key was reused internally.

For Paper title-only processing, absent verified abstract material still yields no score or relevance decision. A model's unsolicited score is discarded under the existing rule. Show Title only when only that fact is known; translation success requires the applicable explicit requirement, not merely a successful model call. Switching language never unlocks full-text fallback for abstract scoring or automatic collection.

## Required observable checks

- T03: create a new prompt with the new-user defaults; copy/change/save/reload/restart both preferences coherently with the binding. Restore Text retains the shown preferences. No save/refresh action generates content.
- T06/T11: synthetic English and Chinese scored output retain equal mandatory score/reason/material validation. A Chinese-required result without a usable Chinese title fails explicitly; Follow instructions does not fail merely for lacking CJK characters. Title-only output remains unscored in both configurations.
- T11: English quotes/parentheses remain intact under Preserve generated text. Existing Chinese editorial transformations remain available under their configured option; code/link/image syntax stays intact. A preference save during a run does not change that run's result contract.
- T12/T16/T17: native rendering and external adapters distinguish original title, generated title and legacy Chinese translation; stored historical text/aliases/metadata are preserved. UI language never rewrites content.
- T27: imported source fixtures retain current Chinese workflow and exact historical bytes/IDs; new-user defaults do not override imported effective preferences. Unknown bindings remain recoverable errors, not silent rewrites.

These are acceptance requirements, not tests that have been run. Existing IO behavior must be retained as a configurable path before the port can claim language-independent output.

## Source evidence

Read-only source checkout inspected 2026-10-28, dirty HEAD `e9ba73f0b44a781ea68c0670114f9281f66f5cd3`; this SHA does not identify all inspected working-tree bytes. No user prompt, private database or runtime configuration was read.

- `backend/ai_client.py:_answer_violation` and `backend/paper_abstract.py:usable_title_zh` require a CJK-bearing title for the applicable scored/title-only response.
- `backend/pipeline.py:_curator_call` repeats title-only validation and applies `lint_curator_output`; `_news_markdown` consumes the legacy title field.
- `backend/ai/note_lint.py` changes quotation/parenthesis style, CJK punctuation and spacing while masking selected Markdown spans. This is authored-output formatting, not a universal language invariant.
- `backend/reading_notes.py` and `backend/zotero.py` use Chinese-title validation when creating existing title aliases/metadata. Port those downstream consumers with the explicit title provenance; changing the request validator alone is insufficient.
