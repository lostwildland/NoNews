from __future__ import annotations

import json

from .core import InformationDB

def ensure_schema(db) -> None:
    """Create the job queue. Idempotent; run by the schema pass, not per job."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS processing_jobs (
          id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
          stage TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
          available_at TEXT NOT NULL, created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL, error TEXT, result_json TEXT,
          intent_json TEXT
        );
        CREATE INDEX IF NOT EXISTS processing_jobs_pending ON processing_jobs(status,available_at);
    """)
    if "magpie_block_reason" not in {row[1] for row in db.execute("PRAGMA table_info(processing_jobs)")}:
        db.execute("ALTER TABLE processing_jobs ADD COLUMN magpie_block_reason TEXT")
    # One bulk run (see /api/queue) is addressable as a batch so it can be
    # reported and stopped on its own instead of by guessing at row ids.
    columns = {row[1] for row in db.execute("PRAGMA table_info(processing_jobs)")}
    if "editor_target" not in columns:
        db.execute("ALTER TABLE processing_jobs ADD COLUMN editor_target TEXT")
    if "batch_id" not in columns:
        db.execute("ALTER TABLE processing_jobs ADD COLUMN batch_id TEXT")
    if "intent_json" not in columns:
        db.execute("ALTER TABLE processing_jobs ADD COLUMN intent_json TEXT")
    if "decision_generation" not in columns:
        # The human-decision generation at claim time. A Reject or a later
        # Select increments the item's generation, so a late result from this
        # job is refused instead of writing withdrawn content back.
        db.execute("ALTER TABLE processing_jobs ADD COLUMN decision_generation INTEGER")
    if "native_context_id" not in columns:
        db.execute("ALTER TABLE processing_jobs ADD COLUMN native_context_id TEXT")

    if "origin" not in columns:
        # Who asked for this run. ``automatic`` is the only value that a feed's
        # ``disabled`` setting stops: an explicit user command keeps its existing
        # permission semantics instead of quietly gaining a new refusal.
        db.execute("ALTER TABLE processing_jobs ADD COLUMN origin TEXT")
    # Every page load and the schedule_selected pass ask "is this item queued?";
    # without this SQLite builds a transient index per query.
    db.execute("CREATE INDEX IF NOT EXISTS processing_jobs_item ON processing_jobs(item_id,status)")

class JobQueue:

    def __init__(self, state: InformationDB, service=None):
        self.state, self.db = (state, state.db)
        self.service = service

    def retryable(self, job):
        return job['status'] == 'failed' and job['stage'] in {'auto', 'acquisition', 'curator', 'editor', 'tags', 'maintenance', 'media'} and (not self.failure_resolved(job))

    def failure_resolved(self, job):
        """A later successful run of each failed stage supersedes this failure."""
        if job['status'] != 'failed':
            return False
        if job['stage'] == 'media':
            return False
        if job['stage'] == 'historical_curator':
            return bool(self.db.execute("SELECT 1 FROM processing_jobs j\n                JOIN pipeline_stage_runs p ON p.job_id=j.id AND p.item_id=j.item_id\n                    AND p.stage='curator' AND p.status='ready'\n                JOIN curator_runs c ON c.id=json_extract(p.result_json,'$.run_id')\n                    AND c.item_id=j.item_id AND c.status='succeeded' AND c.score BETWEEN 0 AND 10\n                WHERE j.item_id=? AND j.stage='historical_curator' AND j.status='succeeded'\n                    AND j.updated_at>? AND p.updated_at>? AND c.finished_at>? LIMIT 1", (job['item_id'], job['updated_at'], job['updated_at'], job['updated_at'])).fetchone())
        if job['stage'] != 'auto':
            stages = [job['stage']]
        else:
            try:
                result = json.loads(job['result_json'] or '{}')
            except (TypeError, json.JSONDecodeError):
                return False
            if not isinstance(result, dict) or not isinstance(result.get('stages'), dict):
                return False
            stages = [stage for stage, value in result['stages'].items() if stage in {'scoring', 'acquisition', 'curator', 'editor'} and isinstance(value, dict) and (value.get('status') == 'failed')]
        if not stages:
            return False
        successes = {'scoring': "SELECT 1 FROM pipeline_stage_runs WHERE item_id=? AND stage='scoring' AND status='ready' AND updated_at>? LIMIT 1", 'acquisition': "SELECT 1 FROM pipeline_stage_runs WHERE item_id=? AND stage='acquisition' AND status='ready' AND updated_at>? LIMIT 1", 'curator': "SELECT 1 FROM curator_runs WHERE item_id=? AND status='succeeded' AND finished_at>? LIMIT 1", 'editor': 'SELECT 1 FROM editor_drafts WHERE item_id=? AND created_at>? LIMIT 1', 'maintenance': "SELECT 1 FROM pipeline_stage_runs WHERE item_id=? AND stage='maintenance' AND status='ready' AND updated_at>? LIMIT 1", 'media': "SELECT 1 FROM pipeline_stage_runs WHERE item_id=? AND stage='media' AND status='ready' AND updated_at>? LIMIT 1"}
        for stage in stages:
            if self.db.execute("SELECT 1 FROM stage_state WHERE item_id=? AND stage=?\n                AND status='failed' AND updated_at<=?", (job['item_id'], stage, job['updated_at'])).fetchone():
                return False
            if stage not in successes or not self.db.execute(successes[stage], (job['item_id'], job['updated_at'])).fetchone():
                return False
        return True
