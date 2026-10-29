# T02 independent review — round 5

Base:`c9ecfa14e884a7ce8895bb13eec3ea8711cbef90`
Reviewed HEAD:`92554d790034867e0d8ca4999f0727149bd97c31`

## Standards

0actionableP1/P2; worst none. Independent Terra high reviewer confirmed exact refs,22commits, nonempty original-base diff and clean whitespace check. Inspected standards, prior reviews, controller/preferences, schema and packaging. Combined output was sometimes truncated; not every line was inspected, and no independent suite/build/UI/production check was performed.

## Spec

1P2: schema signatures omit constraint conflict policies. A processing_jobs idempotency constraint changed to UNIQUE ON CONFLICT REPLACE passed public startup and a second synthetic job replaced the previous one. This violates malformed-current-data refusal before mutation. The reviewer reproduced public stdio readiness and a SQLite write; it did not inspect a live native UI or production data.

## Corrections and pending evidence

The coordinator reproduced6unsafe policies in public engine startup (unique REPLACE/IGNORE/FAIL/ROLLBACK, primaryREPLACE, NOTNULLREPLACE). Canonical table token validation now refuses non-ABORT policy changes before writable opening; explicit ABORT remains valid. Full engine19tests:18pass1optionalreference skip with ResourceWarning as errors; native-controller checks passed.

The original root T01 validator shares this gap. Its snapshot/verify negatives first failed, then passed with the same policy guard; a public restored-write positive confirms normal ABORT retains the first job on duplicate-key failure. Full snapshot suite51passed. T01 issue3 is reopened pending fresh independent review of the narrow root follow-up. Earlier acceptance was historical, not coverage for this newly discovered case.

No source-original, private library, credentials or production service was touched. T30 owns heavyweight native validation, so any current T02 resource packaging must not run a competing Xcode/test host or launch the main acceptance app. Fresh R6 reviews must cover both the full T02 original-base range and this related root T01 patch. Native visual Ready and full parity remain unaccepted.
