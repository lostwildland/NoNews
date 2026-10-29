from __future__ import annotations

def ensure_schema(db) -> None:
    """Create the per-job stage checkpoints. Idempotent; run by the schema pass."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS pipeline_stage_runs(
            job_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(job_id, item_id, stage)
        );
        CREATE INDEX IF NOT EXISTS pipeline_stage_runs_item_stage ON pipeline_stage_runs(item_id,stage,status);
    """)
