# T01 independent review — round 5

Base: `775500c5b007c5917d46f2461544eb4ace8e21ae`
Reviewed HEAD: `596408d57e0ca6f8e33ddd52a54f06d932067ac2`
Independent GPT-6.1 Terra high reviewers confirmed the full original-base diff and reproduced their findings with temporary synthetic public inputs. No full suite, native UI/build, production data or remote service was used.

## Standards

1 P2, worst P2: a SQLite BLOB in ingestion_failures.id reaches asset bindings and manifest JSON serialization, causing an uncaught TypeError. Validate or losslessly encode identities before serialization to satisfy safe input refusal and the no-crashes priority.

## Spec

1 P2, worst P2: missing required defaults are accepted. Removing DEFAULT 0 from items.starred still allows snapshot/verify/restore; the current IO insert omits that field and then fails NOT NULL. Validate required defaults and add public refusal plus restored-write checks, as required by preserving active capabilities and rejecting incomplete/tampered input.

## Coordinator corrections and verification

The common binding boundary now refuses non-text/non-integer identities before publication. A public CLI test first reproduced the traceback and then verifies clean refusal, unchanged DB/asset and no published snapshot. Unknown ordinary table BLOB data remains supported.

The descriptor now records 90 required defaults and 592 column affinities. The gate preserves required default semantics and affinities while accepting harmless TEXT/VARCHAR spelling and extra schema. Public snapshot/verify checks reject missing/wrong defaults and wrong affinity. The initial fixture inadvertently removed an existing unique index; preserving all original indexes and asserting the precise invariant failure eliminated that false positive before the implementation was changed. The corrected tests reproduced the actual admission defect. Restored writes use the source IO item-insert shape and verify default state and generated Raw IDs.

Final 46 focused tests passed with ResourceWarning treated as errors; compilation and original-base diff checks passed before commit. No validation or test was weakened. T01 remains open and unintegrated pending fresh independent review. Personal migration, recovery consumers and live remote readback remain outside this evidence.
