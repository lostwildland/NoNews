## Parent

https://github.com/lostwildland/NoNews/issues/1

## What to build

The owner can use all prior IO abilities in NoNews and a new user can independently configure the product, backed by final parity evidence.

## Acceptance criteria

- [ ] Every active capability and newly discovered active source behavior has an accepted ticket plus meaningful test/runtime evidence; retired items are honestly separated.
- [ ] Run full appropriate macOS/iOS builds and tests, integration/migration/sync live readback and independently aggregated Standards/Spec reviews.
- [ ] Resolve the synthetic account fixture's database-close/remove diagnostics documented in [native test SQLite evidence](../acceptance/t02-test-diagnostics.md); preserve affected tests/assertions and verify that cleanup waits for database work. Passing counts alone do not clear data-integrity diagnostics.
- [ ] No material code/UX/accessibility/data-integrity issue remains; private final evidence is locally accessible with redacted public summary.
- [ ] Each completed ticket has commit and remote ref, review base/HEAD and test outcome; goal is not completed while live prerequisites remain pending.
- [ ] Clean abandoned changes and deliver runnable app, migration/rollback guide and known limitations without award claims.

## Native fixture shutdown contract

The independently executable fixture repair must close admission before draining/removing its owned directory. Already accepted work completes and persists. Account/background initialization, retained Feed/FeedSettings, direct article/sync/settings database calls and callback paths must not submit SQL after closing. Keep owner-level retry after a real busy close; retain the failed handle/directory and coordinate concurrent close callers.

Preserve existing nonthrowing native API signatures where possible. On a closing/closed account, synchronous or nonthrowing async reads may return their documented empty/nil/zero shape before invoking the database. Throwing/result-based APIs report a controlled closed/cancelled error. Every accepted or rejected callback/continuation completes exactly once. Retained property setters refuse the change without replacing the previously accepted in-memory value, posting a successful change notification, saving OPML or submitting SQL. A failed close remains closed to new application work while allowing close retry. Do not fake a reopened connection or simply drop queue blocks whose continuations still need completion.

Implement rejection at real owner/database boundaries and inspect all callers. Add behavioral during-close and after-close checks, retain the existing red admission regression until green, preserve pre-close writes and the actual descriptor/inode checks. No test skips, sleeps, console suppression or broad directory cleanup. This repair does not claim to change or validate production AccountManager deletion; full T30 still requires the rest of its original acceptance.

## Blocked by

- https://github.com/lostwildland/NoNews/issues/7
- https://github.com/lostwildland/NoNews/issues/8
- https://github.com/lostwildland/NoNews/issues/9
- https://github.com/lostwildland/NoNews/issues/10
- https://github.com/lostwildland/NoNews/issues/11
- https://github.com/lostwildland/NoNews/issues/12
- https://github.com/lostwildland/NoNews/issues/13
- https://github.com/lostwildland/NoNews/issues/14
- https://github.com/lostwildland/NoNews/issues/15
- https://github.com/lostwildland/NoNews/issues/16
- https://github.com/lostwildland/NoNews/issues/17
- https://github.com/lostwildland/NoNews/issues/18
- https://github.com/lostwildland/NoNews/issues/19
- https://github.com/lostwildland/NoNews/issues/20
- https://github.com/lostwildland/NoNews/issues/21
- https://github.com/lostwildland/NoNews/issues/22
- https://github.com/lostwildland/NoNews/issues/23
- https://github.com/lostwildland/NoNews/issues/24
- https://github.com/lostwildland/NoNews/issues/25
- https://github.com/lostwildland/NoNews/issues/28
- https://github.com/lostwildland/NoNews/issues/29
- https://github.com/lostwildland/NoNews/issues/30
- https://github.com/lostwildland/NoNews/issues/31

## Delivery contract

One GPT-6.1 Terra high implementation/test owner. Preserve all existing active IO capabilities; follow the accepted product specification. Read the ticket and comments, record its starting commit, use public behavioral test seams, focused checks and required native verification. Commit and push a ticket branch; return base/head SHAs, tests, evidence and remaining gaps. Orchestrator coordinates independent Standards and Spec review before acceptance. No private database content, credentials or personal runtime constants in public source/issues/fixtures. Do not close the parent spec.
