from __future__ import annotations

import hashlib
import json
import re
import uuid
from urllib.parse import urlsplit, urlunsplit

from .core import transaction, utcnow

MEDIA_TYPES = {"news", "paper", "newsletter", "podcast", "video"}
MODES = {"disabled", "normal", "important"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS native_source_observations(
  id TEXT PRIMARY KEY,
  namespace TEXT NOT NULL,
  account_id TEXT NOT NULL,
  feed_id TEXT NOT NULL,
  article_id TEXT NOT NULL,
  unique_id TEXT NOT NULL DEFAULT '',
  feed_url TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  original_url TEXT NOT NULL DEFAULT '',
  published_at TEXT,
  item_id TEXT REFERENCES items(id),
  identity_state TEXT NOT NULL CHECK(identity_state IN ('verified','unresolved','conflict')),
  identity_type TEXT NOT NULL DEFAULT '',
  identity_value TEXT NOT NULL DEFAULT '',
  raw_identity_value TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(namespace, account_id, feed_id, article_id)
);
CREATE INDEX IF NOT EXISTS native_observation_item ON native_source_observations(item_id);
CREATE INDEX IF NOT EXISTS native_observation_feed ON native_source_observations(namespace, account_id, feed_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS native_observation_identities(
  id INTEGER PRIMARY KEY,
  observation_id TEXT NOT NULL REFERENCES native_source_observations(id),
  media_type TEXT NOT NULL,
  identity_type TEXT NOT NULL,
  identity_value TEXT NOT NULL,
  raw_identity_value TEXT NOT NULL DEFAULT '',
  evidence_state TEXT NOT NULL CHECK(evidence_state IN ('verified','conflict')),
  observed_at TEXT NOT NULL,
  UNIQUE(observation_id, media_type, identity_type, identity_value)
);
CREATE INDEX IF NOT EXISTS native_observation_identity_lookup ON native_observation_identities(observation_id, observed_at);
CREATE TABLE IF NOT EXISTS native_processing_contexts(
  id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL REFERENCES items(id),
  observation_id TEXT NOT NULL REFERENCES native_source_observations(id),
  curator_prompt_id TEXT,
  editor_prompt_id TEXT,
  service_id TEXT,
  media_type TEXT,
  processing_mode TEXT NOT NULL DEFAULT 'disabled',
  threshold REAL,
  scoring_strategy TEXT,
  body_strategy TEXT,
  policy_revision INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS native_context_item ON native_processing_contexts(item_id);
CREATE TABLE IF NOT EXISTS native_context_results(
  context_id TEXT NOT NULL REFERENCES native_processing_contexts(id),
  result_type TEXT NOT NULL CHECK(result_type IN ('curator','draft','material')),
  result_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(context_id, result_type, result_id)
);
CREATE INDEX IF NOT EXISTS native_context_results_lookup ON native_context_results(context_id, result_type, created_at DESC);
CREATE TABLE IF NOT EXISTS native_feed_policies(
  namespace TEXT NOT NULL,
  account_id TEXT NOT NULL,
  feed_id TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  media_type TEXT CHECK(media_type IS NULL OR media_type IN ('news','paper','newsletter','podcast','video')),
  processing_mode TEXT NOT NULL DEFAULT 'disabled' CHECK(processing_mode IN ('disabled','normal','important')),
  curator_prompt_id TEXT,
  editor_prompt_id TEXT,
  service_id TEXT,
  threshold REAL,
  scoring_strategy TEXT,
  body_strategy TEXT,
  revision INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(namespace, account_id, feed_id)
);
"""


def ensure_schema(db) -> None:
    db.executescript(SCHEMA)
    context_sql = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='native_processing_contexts'").fetchone()
    if context_sql and "UNIQUE(item_id, observation_id)" in (context_sql[0] or ""):
        db.execute("ALTER TABLE native_processing_contexts RENAME TO native_processing_contexts_legacy")
        db.executescript(SCHEMA)
        legacy_columns = {row[1] for row in db.execute("PRAGMA table_info(native_processing_contexts_legacy)")}
        target_columns = ["id", "item_id", "observation_id", "curator_prompt_id", "editor_prompt_id", "service_id", "media_type", "processing_mode", "threshold", "scoring_strategy", "body_strategy", "policy_revision", "created_at", "updated_at"]
        expressions = []
        for column in target_columns:
            if column in legacy_columns:
                expressions.append(column)
            elif column == "processing_mode":
                expressions.append("'disabled'")
            elif column == "policy_revision":
                expressions.append("0")
            elif column in {"created_at", "updated_at"}:
                expressions.append("''")
            else:
                expressions.append("NULL")
        db.execute(f"INSERT INTO native_processing_contexts({','.join(target_columns)}) SELECT {','.join(expressions)} FROM native_processing_contexts_legacy")
        db.execute("DROP TABLE native_processing_contexts_legacy")

    columns = {row[1] for row in db.execute("PRAGMA table_info(native_processing_contexts)")}
    additions = {
        "media_type": "TEXT",
        "processing_mode": "TEXT NOT NULL DEFAULT 'disabled'",
        "scoring_strategy": "TEXT",
        "body_strategy": "TEXT",
        "policy_revision": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, declaration in additions.items():
        if name not in columns:
            db.execute(f"ALTER TABLE native_processing_contexts ADD COLUMN {name} {declaration}")
    if "raw_identity_value" not in {row[1] for row in db.execute("PRAGMA table_info(native_source_observations)")}:
        db.execute("ALTER TABLE native_source_observations ADD COLUMN raw_identity_value TEXT NOT NULL DEFAULT ''")
    if "raw_identity_value" not in {row[1] for row in db.execute("PRAGMA table_info(native_observation_identities)")}:
        db.execute("ALTER TABLE native_observation_identities ADD COLUMN raw_identity_value TEXT NOT NULL DEFAULT ''")
    policy_columns = {row[1] for row in db.execute("PRAGMA table_info(native_feed_policies)")}
    if "service_id" not in policy_columns:
        db.execute("ALTER TABLE native_feed_policies ADD COLUMN service_id TEXT")


def _text(value, field, *, required=False, maximum=4096):
    if not isinstance(value, str) or (required and not value.strip()) or len(value.encode("utf-8")) > maximum:
        raise ValueError(f"Invalid {field}")
    return value.strip()


def _namespace(value):
    value = _text(value, "namespace", required=True, maximum=128)
    if not re.fullmatch(r"[A-Za-z0-9._~-]+", value):
        raise ValueError("Invalid namespace")
    return value


def _verified_identity(body):
    identity_type = _text(body.get("identityType", ""), "identity type", maximum=64).lower()
    value = _text(body.get("identityValue", ""), "identity value", maximum=2048)
    if not identity_type and not value:
        return None
    if not identity_type or not value or not re.fullmatch(r"[a-z][a-z0-9_-]{1,31}", identity_type):
        raise ValueError("Invalid content identity")
    if identity_type == "url":
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
            raise ValueError("Unsupported content URL")
        host = parts.hostname.casefold() if parts.hostname else ""
        if not host:
            raise ValueError("Unsupported content URL")
        port = parts.port
        if (parts.scheme, port) in {("http", 80), ("https", 443)}:
            port = None
        netloc_host = f"[{host}]" if ":" in host else host
        netloc = netloc_host if port is None else f"{netloc_host}:{port}"
        value = urlunsplit((parts.scheme.casefold(), netloc, parts.path or "/", parts.query, ""))
    elif identity_type == "doi":
        if not re.fullmatch(r"10\.\d{4,9}/\S+", value, re.IGNORECASE):
            raise ValueError("Unsupported DOI")
        value = value.casefold()
    elif identity_type == "arxiv":
        if not re.fullmatch(r"(?:arxiv:)?\d{4}\.\d{4,5}(?:v\d+)?", value, re.IGNORECASE):
            raise ValueError("Unsupported arXiv identity")
        value = value.casefold().removeprefix("arxiv:")
    elif identity_type == "video":
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", value):
            raise ValueError("Unsupported video identity")
    else:
        raise ValueError("Unsupported content identity type")
    return identity_type, value, _text(body.get("identityValue", ""), "identity value", required=True, maximum=2048)


def _observation_id(namespace, account_id, feed_id, article_id):
    raw = "\0".join((namespace, account_id, feed_id, article_id)).encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _feed_key(namespace, account_id, feed_id):
    return json.dumps([namespace, account_id, feed_id], ensure_ascii=True, separators=(",", ":"))


def _item_for_identity(db, media_type, identity_type, identity_value, title, url, published):
    row = db.execute("SELECT item_id FROM item_identities WHERE media_type=? AND identity_type=? AND identity_value=?",
                     (media_type, identity_type, identity_value)).fetchone()
    if row:
        return row[0], "verified"
    item_id = uuid.uuid4().hex
    now = utcnow()
    db.execute("INSERT INTO items(id,media_type,canonical_url,title,published_at,first_ingested_at,review_date,created_at,updated_at) "
               "VALUES (?,?,?,?,?,?,?,?,?)",
               (item_id, media_type, url or None, title or None, published, now, now, now, now))
    db.execute("INSERT INTO item_identities(item_id,media_type,identity_type,identity_value,created_at) VALUES (?,?,?,?,?)",
               (item_id, media_type, identity_type, identity_value, now))
    return item_id, "verified"


def _policy_row(row):
    if row is None:
        return None
    result = dict(row)
    result["threshold"] = float(result["threshold"]) if result["threshold"] is not None else None
    return result


def observe(db, body):
    namespace = _namespace(body.get("namespace"))
    account_id = _text(body.get("accountID"), "account ID", required=True, maximum=256)
    feed_id = _text(body.get("feedID"), "feed ID", required=True, maximum=256)
    article_id = _text(body.get("articleID"), "article ID", required=True, maximum=512)
    unique_id = _text(body.get("uniqueID", ""), "unique ID", maximum=1024)
    title = _text(body.get("title", ""), "title", maximum=4096)
    feed_url = _text(body.get("feedURL", ""), "feed URL", maximum=2048)
    original_url = _text(body.get("originalURL", ""), "original URL", maximum=2048)
    published = _text(body.get("publishedAt", ""), "published date", maximum=128) or None
    media_type = _text(body.get("mediaType", ""), "media type", maximum=32).lower()
    if not media_type:
        policy = db.execute("SELECT media_type FROM native_feed_policies WHERE namespace=? AND account_id=? AND feed_id=?", (namespace, account_id, feed_id)).fetchone()
        media_type = policy[0] if policy and policy[0] else ""
    if media_type and media_type not in MEDIA_TYPES:
        raise ValueError("Unsupported media type")
    try:
        identity = _verified_identity(body)
    except ValueError:
        if not body.get("allowUnresolved"):
            raise
        identity = None
        identity_type = _text(body.get("identityType", ""), "identity type", maximum=64).lower()
        identity_value = _text(body.get("identityValue", ""), "identity value", maximum=2048)
        raw_identity_value = identity_value
    else:
        identity_type = identity_value = raw_identity_value = ""
    if identity:
        identity_type, identity_value, raw_identity_value = identity
        compatible = {"url": MEDIA_TYPES, "doi": {"paper", "news"}, "arxiv": {"paper"}, "video": {"video"}}
        if media_type and media_type not in compatible.get(identity_type, set()):
            raise ValueError("Identity is incompatible with media type")
    observation_id = _observation_id(namespace, account_id, feed_id, article_id)
    now = utcnow()
    with transaction(db):
        existing = db.execute("SELECT * FROM native_source_observations WHERE id=?", (observation_id,)).fetchone()
        state = "unresolved"
        item_id = existing["item_id"] if existing else None
        if identity:
            identity_type, identity_value, raw_identity_value = identity
            if media_type:
                prior_identity = (existing["identity_type"], existing["identity_value"]) if existing and existing["identity_type"] else None
                if existing and existing["item_id"] and prior_identity and prior_identity != (identity_type, identity_value):
                    state = "conflict"
                    item_id = existing["item_id"]
                else:
                    item_id, state = _item_for_identity(db, media_type, identity_type, identity_value, title, original_url, published)
                    if existing and existing["item_id"] and item_id != existing["item_id"]:
                        state = "conflict"
                        item_id = existing["item_id"]
                conflict = db.execute("SELECT item_id FROM native_source_observations WHERE namespace=? AND account_id=? AND feed_id=? AND article_id=? AND item_id IS NOT NULL AND item_id<>?",
                                      (namespace, account_id, feed_id, article_id, item_id)).fetchone()
                if conflict:
                    state = "conflict"
                    item_id = existing["item_id"] if existing else None
        if existing:
            if identity:
                db.execute("INSERT OR IGNORE INTO native_observation_identities(observation_id,media_type,identity_type,identity_value,raw_identity_value,evidence_state,observed_at) VALUES (?,?,?,?,?,?,?)",
                           (observation_id, media_type, identity_type, identity_value, raw_identity_value, state if state in {"verified", "conflict"} else "verified", now))
            prior_state = existing["identity_state"]
            if (not identity) and (prior_state in {"verified", "conflict"} or existing["raw_identity_value"]):
                state = prior_state
                identity_type = existing["identity_type"]
                identity_value = existing["identity_value"]
                raw_identity_value = existing["raw_identity_value"]
                item_id = existing["item_id"]
            db.execute("UPDATE native_source_observations SET unique_id=?,feed_url=?,title=?,original_url=?,published_at=?,item_id=?,identity_state=?,identity_type=?,identity_value=?,raw_identity_value=?,updated_at=? WHERE id=?",
                       (unique_id, feed_url, title, original_url, published, item_id, state, identity_type, identity_value, raw_identity_value, now, observation_id))
        else:
            db.execute("INSERT INTO native_source_observations(id,namespace,account_id,feed_id,article_id,unique_id,feed_url,title,original_url,published_at,item_id,identity_state,identity_type,identity_value,raw_identity_value,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (observation_id, namespace, account_id, feed_id, article_id, unique_id, feed_url, title, original_url,
                        published, item_id, state, identity_type, identity_value, raw_identity_value, now, now))
            if identity:
                db.execute("INSERT INTO native_observation_identities(observation_id,media_type,identity_type,identity_value,raw_identity_value,evidence_state,observed_at) VALUES (?,?,?,?,?,?,?)",
                           (observation_id, media_type, identity_type, identity_value, raw_identity_value, state if state in {"verified", "conflict"} else "verified", now))
        if item_id:
            policy = db.execute("SELECT curator_prompt_id,editor_prompt_id,service_id,media_type,processing_mode,threshold,scoring_strategy,body_strategy,revision FROM native_feed_policies WHERE namespace=? AND account_id=? AND feed_id=?",
                                (namespace, account_id, feed_id)).fetchone()
            existing_context = db.execute("SELECT id,processing_mode FROM native_processing_contexts WHERE item_id=? AND observation_id=?", (item_id, observation_id)).fetchone()
            context_id = existing_context[0] if existing_context else uuid.uuid4().hex
            db.execute("INSERT OR IGNORE INTO native_processing_contexts(id,item_id,observation_id,curator_prompt_id,editor_prompt_id,service_id,media_type,processing_mode,threshold,scoring_strategy,body_strategy,policy_revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (context_id, item_id, observation_id, policy[0] if policy else None, policy[1] if policy else None, policy[2] if policy else None,
                        policy[3] if policy else None, policy[4] if policy else "disabled", policy[5] if policy else None,
                        policy[6] if policy else None, policy[7] if policy else None, policy[8] if policy else 0, now, now))
            if (existing_context[1] if existing_context else (policy[4] if policy else "disabled")) in {"normal", "important"}:
                db.execute("INSERT OR IGNORE INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,intent_json,origin,decision_generation,native_context_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", ("native-" + context_id, item_id, "auto", "native:" + context_id, "pending", now, now, now, json.dumps({"nativeContextID": context_id, "policyRevision": policy[8]}), "automatic", 0, context_id))
    return observation(db, observation_id)



def replay(db, body):
    namespace = _namespace(body.get("namespace"))
    context_id = _text(body.get("contextID"), "context ID", required=True, maximum=64)
    row = db.execute("SELECT c.item_id,o.namespace,o.account_id,o.feed_id,p.curator_prompt_id,p.editor_prompt_id,p.service_id,p.media_type,p.processing_mode,p.threshold,p.scoring_strategy,p.body_strategy,p.revision FROM native_processing_contexts c JOIN native_source_observations o ON o.id=c.observation_id LEFT JOIN native_feed_policies p ON p.namespace=o.namespace AND p.account_id=o.account_id AND p.feed_id=o.feed_id WHERE c.id=? AND o.namespace=?", (context_id, namespace)).fetchone()
    if row is None:
        raise ValueError("Context not found")
    if row[8] not in {"disabled", "normal", "important"} or row[12] is None:
        raise ValueError("Current source policy is unavailable for replay")
    observation_id = db.execute("SELECT observation_id FROM native_processing_contexts WHERE id=?", (context_id,)).fetchone()[0]
    replay_context_id = uuid.uuid4().hex
    now = utcnow()
    db.execute("INSERT INTO native_processing_contexts(id,item_id,observation_id,curator_prompt_id,editor_prompt_id,service_id,media_type,processing_mode,threshold,scoring_strategy,body_strategy,policy_revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (replay_context_id, row[0], observation_id, row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], now, now))
    job_id = "native-replay-" + uuid.uuid4().hex
    db.execute("INSERT INTO processing_jobs(id,item_id,stage,idempotency_key,status,available_at,created_at,updated_at,intent_json,origin,decision_generation,native_context_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (job_id, row[0], "auto", job_id, "pending", now, now, now, json.dumps({"nativeContextID": replay_context_id, "policyRevision": row[12], "preview": True}), "user", 0, replay_context_id))
    return {"jobID": job_id, "contextID": replay_context_id, "historicalRerun": "queued"}


def context_results(db, method, body):
    namespace = _namespace(body.get("namespace"))
    context_id = _text(body.get("contextID"), "context ID", required=True, maximum=64)
    origin_context_id = _text(body.get("originContextID"), "origin context ID", required=True, maximum=64)
    if origin_context_id != context_id or db.execute("SELECT 1 FROM native_processing_contexts c JOIN native_source_observations o ON o.id=c.observation_id WHERE c.id=? AND o.namespace=? AND c.item_id=(SELECT item_id FROM native_processing_contexts WHERE id=?)", (origin_context_id, namespace, context_id)).fetchone() is None:
        raise ValueError("Context provenance mismatch")
    if method == "GET":
        for result_type, stage, table_key in (("curator", "curator", "run_id"), ("draft", "editor", "draft_id")):
            rows = db.execute("SELECT json_extract(p.result_json, '$." + table_key + "') FROM processing_jobs j JOIN pipeline_stage_runs p ON p.job_id=j.id WHERE j.native_context_id=? AND p.stage=? AND p.result_json IS NOT NULL", (context_id, stage)).fetchall()
            with transaction(db):
                for result_row in rows:
                    if result_row[0]:
                        db.execute("INSERT OR IGNORE INTO native_context_results(context_id,result_type,result_id,created_at) VALUES (?,?,?,?)", (context_id, result_type, result_row[0], utcnow()))
        if method == "POST":
            result_type = _text(body.get("resultType"), "result type", required=True, maximum=32)
            result_id = _text(body.get("resultID"), "result ID", required=True, maximum=256)
            if result_type not in {"curator", "draft", "material"}:
                raise ValueError("Unsupported context result")
            if result_type == "curator":
                row = db.execute("SELECT item_id,prompt_version_id FROM curator_runs WHERE id=?", (result_id,)).fetchone()
            elif result_type == "draft":
                row = db.execute("SELECT item_id,prompt_version_id FROM editor_drafts WHERE id=?", (result_id,)).fetchone()
            else:
                row = db.execute("SELECT item_id,provenance FROM raw_snapshots WHERE id=?", (result_id,)).fetchone()
            context_item = db.execute("SELECT item_id,curator_prompt_id,editor_prompt_id FROM native_processing_contexts WHERE id=?", (context_id,)).fetchone()
            if row is None or context_item is None or row[0] != context_item[0]:
                raise ValueError("Context result does not belong to item")
            if result_type == "curator":
                if not context_item[1] or db.execute("SELECT 1 FROM prompt_versions WHERE id=? AND kit_id=? AND role='curator'", (row[1], context_item[1])).fetchone() is None:
                    raise ValueError("Curator result does not match context prompt")
            elif result_type == "draft":
                if not context_item[2] or db.execute("SELECT 1 FROM prompt_versions WHERE id=? AND kit_id=? AND role='editor'", (row[1], context_item[2])).fetchone() is None:
                    raise ValueError("Editor result does not match context prompt")
            else:
                try:
                    provenance = json.loads(row[1]) if row[1] else {}
                except (TypeError, json.JSONDecodeError):
                    provenance = {}
                if not isinstance(provenance, dict) or provenance.get("contextID") != context_id:
                    raise ValueError("Material result provenance does not match context")
            with transaction(db):
                db.execute("INSERT OR IGNORE INTO native_context_results(context_id,result_type,result_id,created_at) VALUES (?,?,?,?)", (context_id, result_type, result_id, utcnow()))
    return {"contextID": context_id, "results": [dict(row) for row in db.execute("SELECT result_type,result_id,created_at FROM native_context_results WHERE context_id=? ORDER BY created_at DESC,result_id", (context_id,))]}

def observation(db, identity, namespace=None):
    if namespace is not None:
        namespace = _namespace(namespace)
    row = db.execute("SELECT * FROM native_source_observations WHERE id=?" + (" AND namespace=?" if namespace else ""), (identity, namespace) if namespace else (identity,)).fetchone()
    if row is None:
        raise ValueError("Observation not found")
    result = dict(row)
    result["contexts"] = [dict(item) for item in db.execute("SELECT * FROM native_processing_contexts WHERE observation_id=? ORDER BY created_at,id", (identity,))]
    result["identityEvidence"] = [dict(item) for item in db.execute("SELECT media_type,identity_type,identity_value,raw_identity_value,evidence_state,observed_at FROM native_observation_identities WHERE observation_id=? ORDER BY observed_at,id", (identity,))]
    return result


def observation_by_binding(db, body):
    namespace = _namespace(body.get("namespace"))
    account_id = _text(body.get("accountID"), "account ID", required=True, maximum=256)
    feed_id = _text(body.get("feedID"), "feed ID", required=True, maximum=256)
    article_id = _text(body.get("articleID"), "article ID", required=True, maximum=512)
    row = db.execute("SELECT id FROM native_source_observations WHERE namespace=? AND account_id=? AND feed_id=? AND article_id=?", (namespace, account_id, feed_id, article_id)).fetchone()
    if row is None:
        return {"observation": None}
    return {"observation": observation(db, row[0])}

def list_observations(db, body):
    namespace = _namespace(body.get("namespace"))
    sql = "SELECT * FROM native_source_observations WHERE namespace=?"
    args = [namespace]
    sql += " ORDER BY updated_at DESC,id DESC LIMIT ?"
    limit = body.get("limit", 100)
    if not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("Invalid observation limit")
    args.append(limit)
    return {"observations": [dict(row) for row in db.execute(sql, args)]}


def feeds(db, method, body):
    namespace = _namespace(body.get("namespace"))
    account_id = _text(body.get("accountID"), "account ID", required=True, maximum=256)
    if method == "GET":
        rows = db.execute("SELECT * FROM native_feed_policies WHERE namespace=? AND account_id=? ORDER BY title,feed_id",
                          (namespace, account_id)).fetchall()
        known = {row["feed_id"] for row in rows}
        for observation_row in db.execute("SELECT feed_id,MAX(feed_url) AS feed_url,MAX(title) AS title FROM native_source_observations WHERE namespace=? AND account_id=? GROUP BY feed_id ORDER BY feed_id", (namespace, account_id)):
            if observation_row["feed_id"] not in known:
                rows.append({"namespace": namespace, "account_id": account_id, "feed_id": observation_row["feed_id"], "title": observation_row["title"] or observation_row["feed_id"], "media_type": None, "processing_mode": "disabled", "curator_prompt_id": None, "editor_prompt_id": None, "service_id": None, "threshold": None, "scoring_strategy": None, "body_strategy": None, "revision": 0, "created_at": None, "updated_at": None})
        return {"feeds": [_policy_row(row) for row in rows]}
    feed_ids = body.get("feedIDs") if isinstance(body.get("feedIDs"), list) else [body.get("feedID")]
    feed_ids = [_text(value, "feed ID", required=True, maximum=256) for value in feed_ids]
    if not feed_ids or len(set(feed_ids)) != len(feed_ids):
        raise ValueError("Invalid feed selection")
    changes = {key: body.get(key) for key in ("title", "mediaType", "processingMode", "curatorPromptID", "editorPromptID", "serviceID", "threshold", "scoringStrategy", "bodyStrategy") if key in body}
    if "mediaType" in changes and changes["mediaType"] not in (None, *MEDIA_TYPES):
        raise ValueError("Unsupported media type")
    if "processingMode" in changes and changes["processingMode"] not in MODES:
        raise ValueError("Unsupported processing mode")
    if "threshold" in changes and (changes["threshold"] is not None and (not isinstance(changes["threshold"], (int, float)) or not 0 <= changes["threshold"] <= 10)):
        raise ValueError("Invalid threshold")
    for key in ("curatorPromptID", "editorPromptID"):
        if changes.get(key) and db.execute("SELECT 1 FROM app_settings WHERE key=?", ("nonews.prompt." + changes[key],)).fetchone() is None:
            raise ValueError("Prompt not found")
    for key in ("scoringStrategy", "bodyStrategy"):
        if changes.get(key) is not None and changes[key] not in {"", "default", "abstract", "full", "transcript", "captions"}:
            raise ValueError("Unsupported material strategy")
    now = utcnow()
    affected = []
    with transaction(db):
        for feed_id in feed_ids:
            prior = db.execute("SELECT * FROM native_feed_policies WHERE namespace=? AND account_id=? AND feed_id=?", (namespace, account_id, feed_id)).fetchone()
            observation_count = db.execute("SELECT COUNT(*) FROM native_source_observations WHERE namespace=? AND account_id=? AND feed_id=?", (namespace, account_id, feed_id)).fetchone()[0]
            affected.append({"feedID": feed_id, "sourceName": (prior["title"] if prior and prior["title"] else feed_id), "observationCount": observation_count})
            values = dict(prior) if prior else {"title": "", "media_type": None, "processing_mode": "disabled", "curator_prompt_id": None, "editor_prompt_id": None, "service_id": None, "threshold": None, "scoring_strategy": None, "body_strategy": None, "revision": 0}
            values.update({"title": changes.get("title", values["title"]), "media_type": changes.get("mediaType", values["media_type"]),
                           "processing_mode": changes.get("processingMode", values["processing_mode"]), "curator_prompt_id": changes.get("curatorPromptID", values["curator_prompt_id"]),
                           "editor_prompt_id": changes.get("editorPromptID", values["editor_prompt_id"]), "service_id": changes.get("serviceID", values["service_id"]), "threshold": changes.get("threshold", values["threshold"]),
                           "scoring_strategy": changes.get("scoringStrategy", values["scoring_strategy"]), "body_strategy": changes.get("bodyStrategy", values["body_strategy"])})
            for prompt_id, role in ((values["curator_prompt_id"], "curator"), (values["editor_prompt_id"], "editor")):
                if prompt_id:
                    prompt_row = db.execute("SELECT value FROM app_settings WHERE key=?", ("nonews.prompt." + prompt_id,)).fetchone()
                    if prompt_row is None or json.loads(prompt_row[0]).get("role") != role:
                        raise ValueError("Prompt role does not match feed policy")
            if values["service_id"] and db.execute("SELECT 1 FROM app_settings WHERE key=?", ("nonews.service." + values["service_id"],)).fetchone() is None:
                raise ValueError("Service not found")
            if values["processing_mode"] in {"normal", "important"}:
                if not values["media_type"] or not values["curator_prompt_id"] or not values["service_id"]:
                    raise ValueError("Enabled feed policy requires media and a Curator prompt")
                strategies = {values["scoring_strategy"], values["body_strategy"]} - {None, "", "default"}
                allowed = {"news": {"abstract", "full"}, "paper": {"abstract", "full"}, "newsletter": {"abstract", "full"}, "podcast": {"transcript", "full"}, "video": {"captions", "full"}}
                if any(strategy not in allowed.get(values["media_type"], set()) for strategy in strategies):
                    raise ValueError("Material strategy is incompatible with media")
            if prior and body.get("revision") is not None and body["revision"] != prior["revision"]:
                raise ValueError("Feed policy changed during save")
            db.execute("INSERT INTO native_feed_policies(namespace,account_id,feed_id,title,media_type,processing_mode,curator_prompt_id,editor_prompt_id,service_id,threshold,scoring_strategy,body_strategy,revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(namespace,account_id,feed_id) DO UPDATE SET title=excluded.title,media_type=excluded.media_type,processing_mode=excluded.processing_mode,curator_prompt_id=excluded.curator_prompt_id,editor_prompt_id=excluded.editor_prompt_id,service_id=excluded.service_id,threshold=excluded.threshold,scoring_strategy=excluded.scoring_strategy,body_strategy=excluded.body_strategy,revision=excluded.revision,updated_at=excluded.updated_at",
                       (namespace, account_id, feed_id, values["title"], values["media_type"], values["processing_mode"], values["curator_prompt_id"], values["editor_prompt_id"], values["service_id"], values["threshold"], values["scoring_strategy"], values["body_strategy"], (prior["revision"] + 1 if prior else 1), now, now))
            for role in ("curator", "editor"):
                db.execute("DELETE FROM app_settings WHERE key LIKE 'nonews.reference.%' AND json_extract(value,'$.sourceId')=? AND json_extract(value,'$.role' )=?", (_feed_key(namespace, account_id, feed_id), role))
            for prompt_id, role in ((values["curator_prompt_id"], "curator"), (values["editor_prompt_id"], "editor")):
                if prompt_id:
                    from . import configuration
                    reference_id = uuid.uuid5(uuid.NAMESPACE_URL, _feed_key(namespace, account_id, feed_id) + "\0" + role).hex
                    configuration._store(db, "reference", {"id": reference_id, "sourceId": _feed_key(namespace, account_id, feed_id), "name": values["title"] or feed_id, "role": role, "promptId": prompt_id})
    return {"feeds": [_policy_row(db.execute("SELECT * FROM native_feed_policies WHERE namespace=? AND account_id=? AND feed_id=?", (namespace, account_id, feed_id)).fetchone()) for feed_id in feed_ids], "affectedSources": affected, "historicalRerun": "explicit-preview-required"}
