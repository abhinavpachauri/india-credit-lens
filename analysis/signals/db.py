"""
SQLite layer for India Credit Lens signal computation.

DB:     analysis/signals/signals.db
Tables:
  signals        — computed fact table (pipeline × period × metric × entity)
  ingestion_log  — one row per pipeline/period append run

spec_version on signals:
  Tracks which version of the signal definition produced each row.
  Set from registry.json signals[id].spec_version at compute time.
  When a signal spec changes, bump spec_version in the registry and
  re-run append for all historical periods — stale rows are identifiable
  by the old spec_version value.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "signals.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    pipeline      TEXT    NOT NULL,
    period        TEXT    NOT NULL,
    metric_id     TEXT    NOT NULL,
    entity_type   TEXT    NOT NULL DEFAULT 'aggregate',
    entity_id     TEXT    NOT NULL DEFAULT 'total',
    value         REAL,
    unit          TEXT,
    status        TEXT,
    spec_version  TEXT    DEFAULT '1.0',
    data_status   TEXT    DEFAULT 'provisional',
    computed_at   TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (pipeline, period, metric_id, entity_type, entity_id)
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

CREATE TABLE IF NOT EXISTS llm_cache (
    input_hash     TEXT    NOT NULL,
    prompt_version TEXT    NOT NULL,
    pipeline       TEXT,
    period         TEXT,
    domain         TEXT,
    result         TEXT    NOT NULL,
    model          TEXT,
    tokens_used    INTEGER,
    created_at     TEXT    DEFAULT (datetime('now')),
    PRIMARY KEY (input_hash, prompt_version)
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
    # metric_ranges (rolling min/max/percentiles per metric) was rewritten on every append and
    # read by nothing, and no guard compared it — derived data nobody checks is how silent
    # staleness starts. Removed 2026-09-26; this drops it from any copy of the DB that has it.
    conn.execute("DROP TABLE IF EXISTS metric_ranges")
    # WITHOUT statistics SQLite ignores the history index and falls back to scanning every
    # row for the pipeline — measured at 18ms a query over 151,000 rows, which is how a
    # five-second helper became a ten-minute one. ANALYZE is what makes the index chosen.
    conn.execute("ANALYZE")
    conn.commit()
    return conn


