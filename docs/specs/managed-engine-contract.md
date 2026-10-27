# App-managed processing engine: observable contract

T02 product/technical boundary. It is independent of T00 build-script implementation; a real native build and isolated launch are still required as evidence. Existing IO capabilities remain the eventual full scope, delivered through later tickets rather than replaced by a healthy-looking empty service.

## Install and lifecycle

The installed NoNews app owns its processing component and data directories. It must start from its own bundle/resources and container, not an absolute IO checkout, active personal bridge, /usr/bin/python3 or developer virtualenv. A development build may have a clearly marked preparation step that stages a redistributable runtime and dependencies; the delivered app may not require the user to run that step or separately install Python/FreshRSS. The build records packaged dependencies, licenses and runtime integrity. Missing packaging is an explicit error, not silently replaced by a host interpreter.

Starting creates or opens a NoNews-owned database using real IO schema/service contracts. Existing source IO databases, runtime processes and installed NNW containers are never auto-discovered as writable destinations. New empty data must work without an Obsidian vault or FreshRSS server. Legacy imported file authority is preserved rather than reassigned by the clean-install default.

Ordinary startup must not run destructive historical retirement against an imported library. Unsupported populated historical/newer databases are retained and surfaced for verified migration before journal/schema mutation. A current version marker alone does not prove that required schema structure is present; malformed current data must not be reported Ready because only the settings subset happens to work. Additional unknown tables/columns remain preserved.

Canonical IO v41 defines no triggers. An additional trigger on a canonical table requires verified migration before writable startup, retaining its definition/data unchanged; a successful rollback probe cannot certify its later effects. Existing noncanonical legacy structures remain preserved. Job history retains recorded errors/results rather than substituting mutable current-stage observations for original failure evidence.

The controller exposes stopped, starting, ready, stopping and failed states, meaningful errors, a bounded startup timeout and idempotent stop. Ordinary NNW reading remains usable if processing fails. Shutdown preserves durable work and never labels running work cancelled merely because the app window closes.

## Private command/read boundary

Use a private authenticated channel appropriate to the app sandbox, with per-launch secret protection and bounded messages/timeouts. No unauthenticated network listener, arbitrary filesystem command execution or browser-exposed personal API. IPC diagnostics exclude tokens, prompt/body contents and credentials. Reject unknown operations and malformed input before dispatch.

Readiness must be backed by the actual IO application/database service: prove a real read (for example schema/status or empty job/source listing) and a real settings round trip through its public dispatch boundary. An independent toy HTTP health endpoint does not prove the processor started. Advanced business flows belong to their later tickets, but real service code and schema must underlie the lifecycle.

The readiness write/read check targets the actual local processing setting inside a rollback-only transaction, not a separate temporary database or a committed health-marker row. Preserve the original value, absence, timestamp and other rows, including on probe failure; do not overwrite imported settings or repeatedly update their history at launch. A read-only or write-rejecting database produces a meaningful unavailable/failed state before Ready. This verifies local settings storage, not model quality or external integration credentials.

## Reuse and portability

Prefer compatible existing backend behavior and database structures over a wholesale language rewrite. A portable app bootstrap supplies explicit configured roots and optional integrations; it does not reuse the personal source CLI bootstrap that requires fixed vaults/write gates. Only sanitized reusable source and needed public schema resources enter the public repo. Include provenance and exact scope; do not copy private data, personal constants, credentials, generated caches or the entire source working tree indiscriminately.

The child process receives a minimal explicit environment. Do not inherit personal INFORMATION_OS_* writer gates, alternate raw/vault paths, token or deployment credential settings. External writers are inert until the user configures and enables their targets. Starting and checking readiness perform no inference, acquisition or external write.

## Native integration and verification

Connect lifecycle/status to the native app and a coherent Settings/Activity entry using standard AppKit controls. Avoid new visual architecture. Preserve original accounts/read/Star; app identity/profile isolation must be proved before real launch. Do not disable sandbox/release protections to make a process start.

Focused behavior checks: clean start/readiness, real public settings/read round trip, missing runtime, bad authentication/operation, timeout, crash/restart, stop/restart with data persistence, no ambient external writer flags, and bundle path discovery outside the source checkout. Python/public IPC tests can run while T00 owns the heavy Xcode build; native full-build/launch verification is serialized and must remain explicitly pending if not yet run.
