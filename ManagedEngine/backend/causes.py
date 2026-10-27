"""Why a piece of work failed, in the terms a reader decides with.

A failure is a cause plus a decision. The raw message is the evidence and stays
in the row's detail, but the cause is what picks the sentence, the action and the
grouping — and what turns twenty-one identical rows into one thing to fix.

The clause is not what parks a job: retrying is decided where the fact is known,
by ``AcquisitionResult.retryable`` (a source wall versus our own browser failing)
and by ``jobs.finish(terminal=...)``. This module only reads the message, which
cannot tell those apart.

The quota signals are the same ones the retry policy already uses
(``jobs._provider_unavailable``), so a failure that is retried in the background
is also the failure the page calls a provider outage.

Order is deliberate. A provider that answers 401 is a credential to fix, not a
quota to wait out, and a browser challenge can mention a timeout without being a
network fault, so the narrower cause is tested first.
"""

import re

PROVIDER_AUTH = "provider_auth"
AWAITING_DRAFT = "awaiting_draft"
PROVIDER_QUOTA = "provider_quota"
REMOTE_ERROR = "remote_error"
SOURCE_BROWSER = "source_browser"
SOURCE_NETWORK = "source_network"
MODEL_OUTPUT = "model_output"
UNKNOWN = "unknown"

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (PROVIDER_AUTH, ("http 401", "http 403", "unauthorized", "invalid api",
                     "authentication failed", "permission denied", "refresh_token_invalidated",
                     "upstream_authentication_required", "auth_unavailable", "api_key_invalid",
                     "api key not valid")),
    (AWAITING_DRAFT, ("requires an editor draft", "no editor draft", "editor draft is missing")),
    (PROVIDER_QUOTA, ("provider_unavailable", "model_cooldown", "usage_limit", "quota",
                      "rate limit", "rate_limit", "429", "resource_exhausted", "overloaded",
                      "insufficient balance", "http 402")),
    # Any other refusal from the far end: a 5xx, or a service that says it is down.
    # Kept apart from quota because "wait for the quota" is the wrong advice here —
    # the fix is to retry, whichever service answered.
    (REMOTE_ERROR, ("http 400", "http 404", "http 500", "http 502", "http 503", "http 504", "http 5",
                    "service unavailable", "bad gateway", "gateway timeout", " 503 ")),
    (SOURCE_BROWSER, ("manual_required", "browser", "connect_over_cdp", "challenge",
                      "captcha", "cloudflare", "institutional access required",
                      "full paper unavailable", "only an abstract")),
    (SOURCE_NETWORK, ("urlerror", "readtimeout", "connectionerror", "connection refused",
                      "timed out", "timeout", "fetch failed", "unreachable", "dns",
                      "could not be resolved")),
    (MODEL_OUTPUT, ("score is required", "is not a number", "expecting value", "json",
                    "missing key", "no usable")),
)


def classify(error: str | None) -> str:
    """The cause behind one failure message. Never raises, never returns empty."""
    value = str(error or "").lower()
    if any(source in value for source in ("papererror:", "publisher:", "source fetch")) and "http 403" in value:
        return SOURCE_BROWSER
    if "paper abstract lookup" in value and "http 429" in value:
        return REMOTE_ERROR
    if re.search(r"api[_ ]key\w*\s+(?:is\s+)?(?:missing|invalid|not configured)", value):
        return PROVIDER_AUTH
    for cause, needles in _RULES:
        if any(needle in value for needle in needles):
            return cause
    return UNKNOWN
