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


class _CredentialPattern:
    """Streaming equivalent of the unbounded credential regex."""
    prefix = re.compile(r'api[_ ]key')
    targets = ('missing', 'invalid', 'not configured')

    def __init__(self):
        self.tail = ''
        self.states = set()
        self.matched = False

    def feed(self, chunk):
        combined = self.tail + chunk
        offset = len(self.tail)
        ends = {m.end() - offset for m in self.prefix.finditer(combined) if m.end() > offset}
        self.tail = combined[-6:]
        position = 0
        for end in sorted(ends):
            self._advance(chunk[position:end])
            self.states.add(('word', 0))
            position = end
        self._advance(chunk[position:])

    def _advance(self, text):
        if not self.states or self.matched:
            return
        for ch in text:
            next_states = set()
            for state, index in self.states:
                if state == 'word':
                    if ch.isalnum() or ch == '_':
                        next_states.add((state, 0))
                    if ch.isspace():
                        next_states.add(('space', 0))
                elif state in ('space', 'is_space'):
                    if ch.isspace():
                        next_states.add((state, 0))
                    else:
                        for target in self.targets:
                            if ch == target[0]:
                                next_states.add((target, 1))
                        if state == 'space' and ch == 'i':
                            next_states.add(('optional_i', 0))
                elif state == 'optional_i' and ch == 's':
                    next_states.add(('optional_is', 0))
                elif state == 'optional_is' and ch.isspace():
                    next_states.add(('is_space', 0))
                elif state in self.targets and index < len(state) and ch == state[index]:
                    if index + 1 == len(state):
                        self.matched = True
                        return
                    next_states.add((state, index + 1))
            self.states = next_states
            if not self.states:
                return


def classify_chunks_steps(chunks):
    """Classify a stream without retaining the original message."""
    special = ('papererror:', 'publisher:', 'source fetch', 'http 403',
               'paper abstract lookup', 'http 429')
    needles = set(special)
    for _, terms in _RULES:
        needles.update(terms)
    found = set()
    overlap = max(map(len, needles)) - 1
    tail = ''
    credential = _CredentialPattern()
    for chunk in chunks:
        value = chunk.lower()
        credential.feed(value)
        text = tail + value
        found.update(needle for needle in needles if needle in text)
        tail = text[-overlap:]
        yield None
    if any(source in found for source in special[:3]) and 'http 403' in found:
        return SOURCE_BROWSER
    if 'paper abstract lookup' in found and 'http 429' in found:
        return REMOTE_ERROR
    if credential.matched:
        return PROVIDER_AUTH
    for cause, terms in _RULES:
        if any(needle in found for needle in terms):
            return cause
    return UNKNOWN


def classify_chunks(chunks) -> str:
    steps = classify_chunks_steps(chunks)
    while True:
        try:
            next(steps)
        except StopIteration as result:
            return result.value


def classify(error: str | None) -> str:
    """The cause behind one failure message. Never raises, never returns empty."""
    return classify_chunks((str(error or ''),))
