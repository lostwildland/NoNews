## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

A reader configures a service and creates reusable Curator/Editor prompts that explicitly bind a model or gateway target.

Native forms, coherent save/reference/history behavior, source-backed variable handling and run timing are specified in [native-processing-configuration.md](../specs/native-processing-configuration.md). This supplements the same ticket; its T02 dependency remains required.

Implementation may start only from independently reviewed, accepted and integrated T02 API commits. If that code boundary is accepted while native UI observation is unavailable, explicitly record the remaining T02 visual evidence as open rather than claiming ticket completion. Do not build against an unreviewed worker branch or treat T03 implementation as proof of either ticket's UI acceptance. Final acceptance still requires the original native evidence.

## Acceptance criteria

- [ ] Native Settings store secrets securely and validate nonsecret endpoint/target configuration; directory refresh performs no inference.
- [ ] Prompt create/edit/copy/rename/delete and references are functional; Curator and Editor are independently composable.
- [ ] Each prompt binds its service/target; no hidden inheritance, mandatory Kit pairing or per-feed model override.
- [ ] Invalid target/authentication/output errors remain distinct and never become zero scores or silent alternate providers.
- [ ] Magpie requested target and actual/reported model provenance remain separate; sharing instructions excludes secrets.

- [ ] Prompt history can be browsed and a prior version restored as a new current version; supported input placeholders and legacy aliases remain valid, while unknown placeholders fail before a model request.
- [ ] Saving instructions and their service/target binding is coherent: a failed save leaves the prior configuration intact. Unchanged text does not grow history; Restore Text retains the visibly selected execution binding and never rewrites historical runs.
- [ ] Native save/read/copy/history/restore preserve prompts up to the inclusive 200,000 UTF-8 byte bound, including multibyte and escaped text, across restart. Extend the bounded T02 transport rather than silently reducing the product limit; oversize refusal preserves saved state and unrelated processing.
- [ ] Existing Magpie legacy-routing preview, pause/drain/apply and unresolved pending-work behavior remain accessible through explicit configured actions; no inference, historical requeue, completed-provenance rewrite or queued Editor target substitution occurs on save/migration.
- [ ] Prompt output preferences preserve imported Chinese-title/typography behavior while new prompts can follow their own language instructions without automatic Chinese formatting; coherent save/copy/restore and run binding follow [native-output-preferences.md](../specs/native-output-preferences.md).

## Blocked by

- https://github.com/lostwildland/NoNews/issues/4

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
