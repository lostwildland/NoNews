-- Synthetic fixture schema extracted from IO source version 41; no runtime imports.

CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY, media_type TEXT NOT NULL CHECK(media_type IN ('news','paper','newsletter','podcast','video')),
  canonical_url TEXT, title TEXT, published_at TEXT, first_ingested_at TEXT NOT NULL,
  review_date TEXT NOT NULL, current_raw_snapshot_id INTEGER,
  human_review_status TEXT NOT NULL DEFAULT 'pending', human_decision TEXT,
  human_curator_run_id TEXT, reviewed_at TEXT, starred INTEGER NOT NULL DEFAULT 0,
  ever_starred INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  review_generation INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS item_identities (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), media_type TEXT NOT NULL,
  identity_type TEXT NOT NULL, identity_value TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(media_type, identity_type, identity_value)
);

CREATE TABLE IF NOT EXISTS raw_snapshots (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), path TEXT NOT NULL,
  source_hash TEXT NOT NULL, retrieved_at TEXT NOT NULL, created_at TEXT NOT NULL,
  provenance TEXT NOT NULL DEFAULT '',
  UNIQUE(item_id, source_hash)
);

CREATE TABLE IF NOT EXISTS editor_drafts(
 id TEXT PRIMARY KEY, item_id TEXT REFERENCES items(id), raw_snapshot_id INTEGER,
 prompt_version_id TEXT, provider TEXT, model TEXT, thinking_effort TEXT,
 input_hash TEXT, artifact_hash TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS private_raw_sources(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 relative_path TEXT NOT NULL, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS body_versions(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 sha256 TEXT NOT NULL,
 characters INTEGER NOT NULL,
 format TEXT NOT NULL DEFAULT 'markdown',
 authority TEXT NOT NULL DEFAULT 'database'
   CHECK(authority IN ('database','imported')),
 source TEXT NOT NULL,
 source_url TEXT NOT NULL DEFAULT '',
 availability TEXT NOT NULL DEFAULT 'usable'
   CHECK(availability IN ('usable','unavailable')),
 availability_reason TEXT NOT NULL DEFAULT '',
 retrieved_at TEXT NOT NULL,
 stored_at TEXT NOT NULL,
 cleaned_at TEXT, cleanup_request_id TEXT);

CREATE TABLE IF NOT EXISTS body_texts(
 snapshot_id INTEGER PRIMARY KEY REFERENCES body_versions(snapshot_id),
 text TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS draft_versions(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 sha256 TEXT NOT NULL,
 characters INTEGER NOT NULL,
 authority TEXT NOT NULL DEFAULT 'database'
   CHECK(authority IN ('database','imported')),
 stored_at TEXT NOT NULL,
 cleaned_at TEXT, cleanup_request_id TEXT);

CREATE TABLE IF NOT EXISTS draft_bodies(
 draft_id TEXT PRIMARY KEY REFERENCES draft_versions(draft_id),
 text TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS literature_files(
 item_id TEXT PRIMARY KEY REFERENCES items(id),
 citekey TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL,
 source TEXT NOT NULL,
 evidence_json TEXT NOT NULL DEFAULT '{}',
 conditional_writer TEXT NOT NULL,
 enabled_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS literature_raws(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 citekey TEXT NOT NULL,
 path TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 bound_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS literature_drafts(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 citekey TEXT NOT NULL,
 file_identity TEXT NOT NULL,
 file_draft_id TEXT NOT NULL,
 path TEXT NOT NULL,
 version INTEGER NOT NULL,
 payload_sha256 TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 bound_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS processing_jobs (
          id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
          stage TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
          available_at TEXT NOT NULL, created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL, error TEXT, result_json TEXT,
          intent_json TEXT
        );

CREATE TABLE IF NOT EXISTS ai_feed_settings (
  freshrss_feed_id TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT '',
  folders_json TEXT NOT NULL DEFAULT '[]',
  processing_mode TEXT NOT NULL DEFAULT 'disabled'
    CHECK(processing_mode IN ('disabled','normal','important')),
  media_type TEXT CHECK(media_type IS NULL OR
    media_type IN ('news','paper','newsletter','podcast','video')),
  kit_id TEXT,
  scoring_strategy TEXT,
  body_strategy TEXT,
  last_seen_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  subscription_state TEXT NOT NULL DEFAULT 'subscribed',
  contract_origin TEXT NOT NULL DEFAULT 'authored'
);

CREATE TABLE IF NOT EXISTS app_settings(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS media_upload_intents(
        object_key TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, object_json TEXT NOT NULL, payload BLOB NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(object_key,owner_kind,owner_id,source_ref));

CREATE TABLE IF NOT EXISTS media_receipts(
        id INTEGER PRIMARY KEY,
        owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL, raw_snapshot_id INTEGER,
        status TEXT NOT NULL, images_total INTEGER NOT NULL DEFAULT 0,
        uploaded INTEGER NOT NULL DEFAULT 0, reused INTEGER NOT NULL DEFAULT 0,
        skipped INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
        bytes_total INTEGER NOT NULL DEFAULT 0, detail_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS media_objects(
        key TEXT PRIMARY KEY, namespace TEXT NOT NULL,
        sha256 TEXT NOT NULL, stored_sha256 TEXT NOT NULL, ext TEXT NOT NULL,
        bytes INTEGER NOT NULL, width INTEGER NOT NULL DEFAULT 0, height INTEGER NOT NULL DEFAULT 0,
        transcoded_from TEXT NOT NULL DEFAULT '', public_url TEXT NOT NULL,
        verified_at TEXT, created_at TEXT NOT NULL,
        UNIQUE(namespace, stored_sha256));

CREATE TABLE IF NOT EXISTS media_pending(
        id INTEGER PRIMARY KEY,
        owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL, source_ref TEXT NOT NULL,
        staging_path TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TEXT, last_error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
        UNIQUE(owner_kind, owner_id, source_ref));

CREATE TABLE IF NOT EXISTS media_raw_activation_intents (
    id TEXT PRIMARY KEY, item_id TEXT NOT NULL, expected_snapshot_id INTEGER,
    old_mapping_json TEXT NOT NULL, old_authority_json TEXT NOT NULL, citekey TEXT NOT NULL,
    candidate_hash TEXT NOT NULL, preimage_json TEXT, quarantine_path TEXT,
    state TEXT NOT NULL, snapshot_id INTEGER, receipt_id TEXT);
