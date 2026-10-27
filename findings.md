# Execution findings

2026-10-27:
- Native environment: macOS 27.0.1, Xcode 27.1; SDK Swift 6.2 repository baseline, macOS deployment target 15.0.
- APFS available about 20 GiB: stage builds and imports, avoid simultaneous full Xcode builds and unbounded duplicate assets.
- NoNews public GitHub repo lostwildland/NoNews, main d9ec7df; no open issues before this run. Existing worktree has authorized uncommitted planning files.
- Source IO HEAD e9ba73f0b44a781ea68c0670114f9281f66f5cd3 and 106 dirty entries; backend has 90 files, schema module reports version 41. Private runtime constants must become settings; do not vendor personal identifiers/paths/keys blindly.
- NNW local accounts do not sync, iCloud uses CloudKit, other services have their own account sync. New IO state needs an explicit compatible channel and real verification.
- Apple Liquid Glass guidance: https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass and https://developer.apple.com/design/human-interface-guidelines/materials — native navigation/control layer with content readability; do not apply custom blur to all article content.
- Previous Impeccable context ran earlier this session; do not rerun it. Product context now recorded from answered questions, not a new interview.
- Terra catalog: codex/gpt-6.1-terra with reasoningEffort=high and serviceTier=default, available.

- Current settings source confirms prompt history/restore and strict supported placeholder contracts; these are explicitly added to T03. Kit splitting must copy effective saved thresholds and retain old IDs/history, not replace them with seed defaults.
- T01 first implementation attempt returned investigation only (326e7d3), no code/tests. It is not accepted. Owner continuation will be instructed to implement verifiable public snapshot/restore with explicit unresolved-asset failures rather than stop at uncertainty.
- T00 source-copy generation avoids modifying an ordinary build's source. SwiftPM discovers package sources before scheme pre-actions, so the existing secrets generator must run inside the private copy before Xcode starts. New native validation and two independent round-3 reviews passed; the existing scripting-test main-thread warning is recorded without asserting a new regression.
- T01's source image parser already supports reference images, Obsidian embeds, srcset and code masking with explicit reviewed shared-alias bindings. Reuse its pure inventory/resolution behavior; a separate regex scanner that rejects those current forms cannot establish migration parity.
- T02 repeated preparation-only returns are implementation gaps, not external blockers. Keep its ticket open and direct the same owner through concrete native lifecycle and portable-service checkpoints; do not equate staged Python/dependencies or a reference-checkout IPC test with a shipped managed engine.
