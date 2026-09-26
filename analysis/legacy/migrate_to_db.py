"""
Migrate existing history/sibc.json + history/atm_pos.json → signals.db

Reads aggregate-level entries from both history files and inserts them into
the signals table. Rows with status='pending' and no value are imported with
value=None and status='unknown' (to be overwritten on next append run).
After insert, refreshes metric_ranges for all migrated metrics.

Safe to run multiple times — INSERT OR REPLACE overwrites cleanly.
"""

from __future__ import annotations
import json
from pathlib import Path

from .db import init_db, refresh_ranges

HISTORY_DIR = Path(__file__).parent / "history"
SIBC_HISTORY  = HISTORY_DIR / "sibc.json"
ATMPOS_HISTORY = HISTORY_DIR / "atm_pos.json"


def _migrate_pipeline(conn, path: Path, pipeline: str) -> int:
    if not path.exists():
        print(f"  {path.name} not found — skipping")
        return 0

    with open(path) as f:
        data = json.load(f)

    entries = data.get("entries", [])
    total = 0
    affected: set[tuple] = set()

    for entry in entries:
        period = entry["period"]
        signals = entry.get("signals", {})
        ts = entry.get("appended_at", "")

        for metric_id, sig in signals.items():
            value  = sig.get("value")          # may be None for pending
            status = sig.get("status", "unknown")

            # Map old status vocabulary to new DB vocabulary
            if status == "new":
                status = "active"
            elif status == "pending":
                status = "unknown"

            if value is None and status == "unknown":
                # Still write the row so the period is represented
                pass

            conn.execute(
                """INSERT OR REPLACE INTO signals
                   (pipeline, period, metric_id, entity_type, entity_id,
                    value, unit, status, computed_at)
                   VALUES (?,?,?,?,?, ?,?,?,?)""",
                (pipeline, period, metric_id,
                 "aggregate", "total",
                 value, None, status, ts)
            )
            affected.add((metric_id, "aggregate", "total"))
            total += 1

    conn.commit()

    # Refresh ranges for all migrated metrics
    for metric_id, entity_type, entity_id in affected:
        refresh_ranges(conn, metric_id, pipeline, entity_type, entity_id)

    conn.commit()
    return total


def migrate() -> None:
    conn = init_db()
    print("Migrating history files → signals.db")

    n_sibc   = _migrate_pipeline(conn, SIBC_HISTORY,   "sibc")
    n_atm    = _migrate_pipeline(conn, ATMPOS_HISTORY,  "atm_pos")

    # Log migration in ingestion_log
    if n_sibc:
        conn.execute(
            "INSERT INTO ingestion_log (pipeline, period, layer, metric_count, row_count) "
            "VALUES (?,?,?,?,?)",
            ("sibc", "migration", "1", n_sibc, n_sibc)
        )
    if n_atm:
        conn.execute(
            "INSERT INTO ingestion_log (pipeline, period, layer, metric_count, row_count) "
            "VALUES (?,?,?,?,?)",
            ("atm_pos", "migration", "1", n_atm, n_atm)
        )
    conn.commit()

    print(f"  SIBC rows migrated:   {n_sibc}")
    print(f"  ATM/POS rows migrated:{n_atm}")
    print(f"  Total:                {n_sibc + n_atm}")
    print("Done.")


if __name__ == "__main__":
    migrate()
