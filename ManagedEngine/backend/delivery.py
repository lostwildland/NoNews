from __future__ import annotations

def ensure_schema(db) -> None:
    """Create the newsletter outbox. Idempotent; run by the schema pass."""
    db.execute("""CREATE TABLE IF NOT EXISTS newsletter_outbox (
        command_id TEXT PRIMARY KEY REFERENCES commands(id), item_id TEXT NOT NULL REFERENCES items(id),
        target_date TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        available_at TEXT NOT NULL, draft_id TEXT, expected_file_hash TEXT, error TEXT)""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(newsletter_outbox)")}
    # The freeze copy that wrote these is gone, and the version is pinned in
    # draft_id instead; nothing reads them.
    for dead in ("title", "source_url", "artifact_path"):
        if dead in columns:
            db.execute(f"ALTER TABLE newsletter_outbox DROP COLUMN {dead}")
    if "expected_file_hash" not in columns:
        db.execute("ALTER TABLE newsletter_outbox ADD COLUMN expected_file_hash TEXT")
    if "draft_id" not in columns:
        db.execute("ALTER TABLE newsletter_outbox ADD COLUMN draft_id TEXT")
    if "revision_id" not in columns:
        db.execute("ALTER TABLE newsletter_outbox ADD COLUMN revision_id TEXT")
    # The issue identity and the section digest a publish pinned. They are
    # delivery evidence, not a second copy of the issue: ``section_hash`` is the
    # block bytes as written, so a later replacement can prove whether a human
    # edited it. Additive columns keep older databases readable.
    delivery_columns = {row[1] for row in db.execute("PRAGMA table_info(deliveries)")}
    for column, ddl in (("issue_id", "TEXT"), ("issue_date", "TEXT"),
                        ("section_hash", "TEXT")):
        if column not in delivery_columns:
            db.execute(f"ALTER TABLE deliveries ADD COLUMN {column} {ddl}")
