"""Runtime settings that a human may change while the bridge runs.

The processor count is the first of these. It used to be a startup flag, which
made every experiment a restart: change the number, stop the queue, start it
again. Storing it here lets the supervisor in ``server.py`` grow or shrink the
worker set while the queue keeps draining -- each worker finishes the job it
holds and then exits, so nothing is interrupted mid-call.
"""
from __future__ import annotations

import sqlite3

# Four workers is enough to keep the browser, the model call and the database
# busy without paying for provider concurrency limits; each extra worker is
# another scraped tab and another in-flight model call.
DEFAULT_PROCESSORS = 4
MAX_PROCESSORS = 8


def ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS app_settings(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL)""")


def _read(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def processors(db: sqlite3.Connection, *, fallback: int | None = None) -> int:
    """How many AI workers should be running, clamped to what we can support."""
    raw = _read(db, "processors")
    if raw is None:
        return clamp(fallback if fallback is not None else DEFAULT_PROCESSORS)
    try:
        return clamp(int(raw))
    except (TypeError, ValueError):
        return clamp(fallback if fallback is not None else DEFAULT_PROCESSORS)


def clamp(value: int) -> int:
    return max(1, min(int(value), MAX_PROCESSORS))


def save_processors(db: sqlite3.Connection, value: int, *, at: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("processors must be a number")
    if not 1 <= value <= MAX_PROCESSORS:
        raise ValueError(f"processors must be between 1 and {MAX_PROCESSORS}")
    db.execute("""INSERT INTO app_settings(key,value,updated_at) VALUES ('processors',?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
               (str(value), at))
    return value
