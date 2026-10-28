from __future__ import annotations

SCHEMA = """
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
CREATE TABLE IF NOT EXISTS ai_feed_settings_migration (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  completed_at TEXT,
  report_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS item_feed_contracts (
  item_id TEXT PRIMARY KEY,
  freshrss_feed_id TEXT,
  media_type TEXT,
  processing_mode TEXT NOT NULL DEFAULT 'disabled',
  kit_id TEXT,
  scoring_strategy TEXT,
  body_strategy TEXT,
  pinned_at TEXT NOT NULL,
  refreshed_at TEXT
);
CREATE TABLE IF NOT EXISTS item_material_fingerprints (
  item_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('scoring','body')),
  media_type TEXT NOT NULL,
  strategy TEXT NOT NULL DEFAULT '',
  source_route TEXT NOT NULL DEFAULT '',
  source_identity TEXT NOT NULL DEFAULT '',
  retrieved_at TEXT NOT NULL,
  sha256 TEXT NOT NULL DEFAULT '',
  characters INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL,
  PRIMARY KEY(item_id, role)
);
"""

def ensure_schema(db) -> None:
    """Create the feed-settings and material-fingerprint tables. Idempotent."""
    db.executescript(SCHEMA)
    columns = {row[1] for row in db.execute("PRAGMA table_info(ai_feed_settings)")}
    if "subscription_state" not in columns:
        # A feed FreshRSS stopped listing is still a feed IO knows. The marker
        # keeps it visible instead of dropping it from the source list.
        db.execute("ALTER TABLE ai_feed_settings ADD COLUMN subscription_state TEXT "
                   "NOT NULL DEFAULT 'subscribed'")
    if "contract_origin" not in columns:
        # A row that predates the provenance marker may hold a person's saved
        # contract, so the safe default is "authored": history seeding must not
        # re-derive media/Kit over it.
        db.execute("ALTER TABLE ai_feed_settings ADD COLUMN contract_origin TEXT "
                   "NOT NULL DEFAULT 'authored'")
