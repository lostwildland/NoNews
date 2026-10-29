from __future__ import annotations

def ensure_schema(db) -> None:
    """Create the projection queues. Idempotent; run by the schema pass."""
    db.execute("""CREATE TABLE IF NOT EXISTS observation_projection (
        observation_id INTEGER PRIMARY KEY REFERENCES entry_observations(id),
        desired_read INTEGER NOT NULL, desired_starred INTEGER NOT NULL, status TEXT NOT NULL,
        attempts INTEGER NOT NULL, available_at TEXT NOT NULL, error TEXT)""")
    if "desired_published" not in {row[1] for row in db.execute("PRAGMA table_info(observation_projection)")}:
        db.execute("ALTER TABLE observation_projection ADD COLUMN desired_published INTEGER NOT NULL DEFAULT 0")
    columns = {row[1] for row in db.execute("PRAGMA table_info(observation_projection)")}
    for name, declaration in {"decision_value": "TEXT", "decision_status": "TEXT",
                              "decision_attempts": "INTEGER NOT NULL DEFAULT 0",
                              "decision_available_at": "TEXT", "decision_error": "TEXT"}.items():
        if name not in columns:
            db.execute(f"ALTER TABLE observation_projection ADD COLUMN {name} {declaration}")
    db.execute("""CREATE TABLE IF NOT EXISTS observation_news_labels (
        observation_id INTEGER PRIMARY KEY REFERENCES entry_observations(id),
        draft_id TEXT NOT NULL, label TEXT, status TEXT NOT NULL,
        attempts INTEGER NOT NULL, available_at TEXT NOT NULL, error TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS observation_paper_labels (
        observation_id INTEGER PRIMARY KEY REFERENCES entry_observations(id),
        curator_run_id TEXT NOT NULL, label TEXT, status TEXT NOT NULL,
        attempts INTEGER NOT NULL, available_at TEXT NOT NULL, error TEXT)""")
    if "projection_version" not in {row[1] for row in db.execute("PRAGMA table_info(observation_paper_labels)")}:
        db.execute("ALTER TABLE observation_paper_labels ADD COLUMN projection_version INTEGER NOT NULL DEFAULT 0")
