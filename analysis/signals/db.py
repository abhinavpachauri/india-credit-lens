"""
SQLite layer for India Credit Lens signal computation.

DB:     analysis/signals/signals.db
Tables:
  signals        — computed fact table (pipeline × period × metric × entity)
  metric_ranges  — rolling stats per metric, updated after every append
  ingestion_log  — one row per pipeline/period append run
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "signals.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    pipeline     TEXT    NOT NULL,
    period       TEXT    NOT NULL,
    metric_id    TEXT    NOT NULL,
    entity_type  TEXT    NOT NULL DEFAULT 'aggregate',
    entity_id    TEXT    NOT NULL DEFAULT 'total',
    value        REAL,
    unit         TEXT,
    status       TEXT,
    data_status  TEXT    DEFAULT 'provisional',
    computed_at  TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (pipeline, period, metric_id, entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS metric_ranges (
    metric_id    TEXT    NOT NULL,
    pipeline     TEXT    NOT NULL,
    entity_type  TEXT    NOT NULL DEFAULT 'aggregate',
    entity_id    TEXT    NOT NULL DEFAULT 'total',
    min_value    REAL,
    max_value    REAL,
    mean_value   REAL,
    p25_value    REAL,
    p75_value    REAL,
    period_count INTEGER DEFAULT 0,
    last_period  TEXT,
    last_value   REAL,
    last_status  TEXT,
    updated_at   TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (metric_id, entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline     TEXT    NOT NULL,
    period       TEXT    NOT NULL,
    layer        TEXT,
    metric_count INTEGER,
    row_count    INTEGER,
    computed_at  TEXT    DEFAULT (datetime('now'))
);
"""


def get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(path: Path = DB_PATH) -> sqlite3.Connection:
    """Create tables if not present. Returns open connection."""
    conn = get_conn(path)
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def refresh_ranges(conn: sqlite3.Connection, metric_id: str,
                   pipeline: str, entity_type: str = "aggregate",
                   entity_id: str = "total") -> None:
    """Recompute metric_ranges for one (metric_id, entity_type, entity_id) triple."""
    rows = conn.execute(
        """SELECT value, period, status FROM signals
           WHERE metric_id=? AND pipeline=? AND entity_type=? AND entity_id=?
             AND value IS NOT NULL
           ORDER BY period""",
        (metric_id, pipeline, entity_type, entity_id)
    ).fetchall()

    if not rows:
        return

    values = [r[0] for r in rows]
    sv = sorted(values)
    n  = len(sv)
    p25 = sv[max(0, int(n * 0.25) - 1)]
    p75 = sv[min(n - 1, int(n * 0.75))]
    last = rows[-1]

    conn.execute(
        """INSERT OR REPLACE INTO metric_ranges
           (metric_id, pipeline, entity_type, entity_id,
            min_value, max_value, mean_value, p25_value, p75_value,
            period_count, last_period, last_value, last_status, updated_at)
           VALUES (?,?,?,?, ?,?,?,?,?, ?,?,?,?, datetime('now'))""",
        (metric_id, pipeline, entity_type, entity_id,
         min(values), max(values), sum(values) / n, p25, p75,
         n, last[1], last[0], last[2])
    )
