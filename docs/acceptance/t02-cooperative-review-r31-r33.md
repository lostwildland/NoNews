# T02 cooperative-history review and native observation

Current source candidate: `920efefd61fb993a850241719a4d99e5691023b6`. Original ticket base: `c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`. This record supplements earlier group reviews; it does not accept T02 or authorize personal migration.

## Standards

R31 completed all eleven cooperative-history correction paths at `20d62dd` and found one P2: a frame seek/read failure retained its spool and idle timer. The coordinator's new Application.handle regression reproduced both failures, then passed after immediate snapshot cleanup. It checks the actual spool closure, canceled timer, cleared state, continued status and exact fresh read.

The [R32 correction review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-frame-native-standards-20261028-r32) completed all seven changed paths and connected cleanup/native-error seams with zero actionable P1/P2 findings. The [R33 packaging delta review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-packaging-final-delta-standards-20261028-r33) completed all eight changed packaging paths since `eb6a156`, plus connected CI/source/cache/manifest/signing seams, with zero actionable P1/P2 findings. Fifteen other packaging blobs are unchanged; the remaining deleted CI configuration is absent at both heads.

## Spec

R31 completed the same eleven-path correction and found one P2: the native controller discarded the stable capacity error code. The coordinator reproduced that lost distinction through the public native request boundary, then added the accessible, allowlisted `EngineError.jobRecordTooLarge` case. Invalid queries and unknown codes remain generic operation failures; all leave the service Ready.

The [R32 correction review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-frame-native-spec-20261028-r32) completed all seven paths with zero actionable P1/P2 findings. The [R33 packaging delta review](t3-thread://v1/thread:delegated-task:command%3Amcp%3A5334bca8-6b5e-41fd-84da-2093ead29d99%3Adelegate-task%3Anonews-t02-packaging-final-delta-spec-20261028-r33) completed all eight changed paths and requested seams with zero actionable P1/P2 findings. Its count of sixteen unchanged mapped paths includes the CI configuration already absent at both heads.

Reviewers did not rerun the coordinator's tests or native/bundle checks. The coordinator's focused frame regression, public Swift-controller script, prepared-source/manifest checks, compilation and whitespace checks pass. The 61-pass Python suite and historical native/CI counts retain their earlier source boundaries. Final connected assessment, current appropriate full native plan and signed relocated bundle remain pending.

## Observed native Settings

After the user confirmed an unlocked Mac, CUA successfully opened the previously verified isolated `/tmp/nonews-t02-r11-installed/NetNewsWire.app`. The initial inventory had no acceptance app process; this observation used an exact-path launch, not an ambiguous bundle-ID selection. The coordinator dismissed the isolated updater prompt with Don't Check, opened Settings through the app menu and selected Processing. Both accessibility text and screenshot showed **Processing Ready** and **Stop**. No processing setting was changed.

![Native Processing Ready](assets/t02-r11-processing-ready.jpg)

This artifact was built from `91fdf89b306c53c65b97df2662348e81db80ce5e`, before cooperative preparation and the R32 corrections. Its sandbox identity and deep strict signature were reverified immediately before opening. At observation, app PID 1927 owned bundled child PID 1932. These PIDs are historical evidence, not reusable stop targets. The native capture limitation is resolved for this artifact; it is not a visible-Ready claim for `920efef` or a complete UI/UX audit. T30 was briefly held away from app/test actions, then notified of the observation and released to reverify/stop the isolated app before its serialized validation.
