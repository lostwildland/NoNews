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
  raw_identity_value TEXT NOT NULL,
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
  updated_at TEXT NOT NULL,
  UNIQUE(item_id, observation_id)
);
CREATE INDEX IF NOT EXISTS native_context_item ON native_processing_contexts(item_id);
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
        netloc = host if port is None else f"{host}:{port}"
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
    return f"{namespace}:{account_id}:{feed_id}"


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
    identity = _verified_identity(body)
    if identity and not media_type:
        raise ValueError("Verified identity requires media type")
    if identity:
        identity_type = identity[0]
        compatible = {"url": MEDIA_TYPES, "doi": {"paper", "news"}, "arxiv": {"paper"}, "video": {"video"}}
        if media_type not in compatible.get(identity_type, set()):
            raise ValueError("Identity is incompatible with media type")
    observation_id = _observation_id(namespace, account_id, feed_id, article_id)
    now = utcnow()
    with transaction(db):
        existing = db.execute("SELECT * FROM native_source_observations WHERE id=?", (observation_id,)).fetchone()
        item_id = existing["item_id"] if existing else None
        state = "unresolved"
        identity_type = identity_value = ""
        if identity:
            identity_type, identity_value, raw_identity_value = identity
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
            if not identity and prior_state in {"verified", "conflict"}:
                state = prior_state
                identity_type = existing["identity_type"]
                identity_value = existing["identity_value"]
                item_id = existing["item_id"]
            db.execute("UPDATE native_source_observations SET unique_id=?,feed_url=?,title=?,original_url=?,published_at=?,item_id=?,identity_state=?,identity_type=?,identity_value=?,updated_at=? WHERE id=?",
                       (unique_id, feed_url, title, original_url, published, item_id, state, identity_type, identity_value, now, observation_id))
        else:
            db.execute("INSERT INTO native_source_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (observation_id, namespace, account_id, feed_id, article_id, unique_id, feed_url, title, original_url,
                        published, item_id, state, identity_type, identity_value, now, now))
            if identity:
                db.execute("INSERT INTO native_observation_identities(observation_id,media_type,identity_type,identity_value,raw_identity_value,evidence_state,observed_at) VALUES (?,?,?,?,?,?,?)",
                           (observation_id, media_type, identity_type, identity_value, raw_identity_value, state if state in {"verified", "conflict"} else "verified", now))
        if item_id:
            policy = db.execute("SELECT curator_prompt_id,editor_prompt_id,service_id,media_type,processing_mode,threshold,scoring_strategy,body_strategy,revision FROM native_feed_policies WHERE namespace=? AND account_id=? AND feed_id=?",
                                (namespace, account_id, feed_id)).fetchone()
            context_id = uuid.uuid4().hex
            db.execute("INSERT OR IGNORE INTO native_processing_contexts(id,item_id,observation_id,curator_prompt_id,editor_prompt_id,service_id,media_type,processing_mode,threshold,scoring_strategy,body_strategy,policy_revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (context_id, item_id, observation_id, policy[0] if policy else None, policy[1] if policy else None, policy[2] if policy else None,
                        policy[3] if policy else None, policy[4] if policy else "disabled", policy[5] if policy else None,
                        policy[6] if policy else None, policy[7] if policy else None, policy[8] if policy else 0, now, now))
    return observation(db, observation_id)


def observation(db, identity):
    row = db.execute("SELECT * FROM native_source_observations WHERE id=?", (identity,)).fetchone()
    if row is None:
        raise ValueError("Observation not found")
    result = dict(row)
    result["contexts"] = [dict(item) for item in db.execute("SELECT * FROM native_processing_contexts WHERE observation_id=? ORDER BY created_at,id", (identity,))]
    result["identityEvidence"] = [dict(item) for item in db.execute("SELECT media_type,identity_type,identity_value,raw_identity_value,evidence_state,observed_at FROM native_observation_identities WHERE observation_id=? ORDER BY observed_at,id", (identity,))]
    return result


def list_observations(db, body):
    namespace = _namespace(body.get("namespace")) if body.get("namespace") else None
    sql = "SELECT * FROM native_source_observations"
    args = []
    if namespace:
        sql += " WHERE namespace=?"
        args.append(namespace)
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
            if prior and body.get("revision") is not None and body["revision"] != prior["revision"]:
                raise ValueError("Feed policy changed during save")
            db.execute("INSERT INTO native_feed_policies(namespace,account_id,feed_id,title,media_type,processing_mode,curator_prompt_id,editor_prompt_id,service_id,threshold,scoring_strategy,body_strategy,revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(namespace,account_id,feed_id) DO UPDATE SET title=excluded.title,media_type=excluded.media_type,processing_mode=excluded.processing_mode,curator_prompt_id=excluded.curator_prompt_id,editor_prompt_id=excluded.editor_prompt_id,service_id=excluded.service_id,threshold=excluded.threshold,scoring_strategy=excluded.scoring_strategy,body_strategy=excluded.body_strategy,revision=excluded.revision,updated_at=excluded.updated_at",
                       (namespace, account_id, feed_id, values["title"], values["media_type"], values["processing_mode"], values["curator_prompt_id"], values["editor_prompt_id"], values["service_id"], values["threshold"], values["scoring_strategy"], values["body_strategy"], (prior["revision"] + 1 if prior else 1), now, now))
    return {"feeds": [_policy_row(db.execute("SELECT * FROM native_feed_policies WHERE namespace=? AND account_id=? AND feed_id=?", (namespace, account_id, feed_id)).fetchone()) for feed_id in feed_ids], "affectedSources": affected, "historicalRerun": "explicit-preview-required"}
