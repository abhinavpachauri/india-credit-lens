"""
Compute engine — dispatches to SIBC or ATM/POS methods, writes results to SQLite.

Entry point: run_append(pipeline, period, conn, registry)
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from . import sibc as _sibc
from . import atm_pos as _atm_pos
from ..db import refresh_ranges

REPO    = Path(__file__).resolve().parent.parent.parent.parent
CSV     = REPO / "web" / "public" / "data" / "atm_pos_consolidated.csv"


def _resolve_period_label(pipeline: str, period: str) -> str:
    """
    For SIBC: map dataDate (YYYY-MM-DD) → period label ("Jan 2026" etc.)
    using the label_map from sibc module.
    For other pipelines: return period as-is (not used).
    """
    if pipeline != "sibc":
        return period
    label_map = _sibc.build_label_map()
    return label_map.get(period, "")   # empty string → _get_rows falls back to latest


def _upsert(conn: sqlite3.Connection, pipeline: str, period: str, rows: list[dict]) -> int:
    ts = datetime.now().isoformat(timespec="seconds")
    count = 0
    for r in rows:
        if r.get("value") is None and r.get("status") in ("unknown", None):
            continue
        conn.execute(
            """INSERT OR REPLACE INTO signals
               (pipeline, period, metric_id, entity_type, entity_id,
                value, unit, status, spec_version, computed_at)
               VALUES (?,?,?,?,?, ?,?,?,?,?)""",
            (pipeline, period, r["metric_id"],
             r.get("entity_type", "aggregate"),
             r.get("entity_id",   "total"),
             r.get("value"), r.get("unit"), r.get("status"),
             r.get("spec_version", "1.0"), ts)
        )
        count += 1
    return count


def run_append(pipeline: str, period: str,
               conn: sqlite3.Connection, registry: dict) -> dict:
    """
    Compute all Layer-1 signals for (pipeline, period) and write to DB.
    Returns summary dict with counts.
    """
    signals = {sid: s for sid, s in registry["signals"].items()
               if s["pipeline"] == pipeline and s.get("layer") == 1}

    if not signals:
        return {"metric_count": 0, "row_count": 0, "statuses": {}}

    # Load ATM/POS DataFrame once if needed
    df = None
    if pipeline == "atm_pos":
        import pandas as pd
        df = _atm_pos._load_df()

    all_rows: list[dict] = []
    skipped = 0
    period_label = _resolve_period_label(pipeline, period)

    for sig_id, sig in signals.items():
        compute_spec = sig.get("compute")
        if not compute_spec:
            skipped += 1
            continue

        method = compute_spec.get("method", "")

        if pipeline == "sibc":
            rows = _sibc.compute(sig_id, compute_spec, period_label)
        elif pipeline == "atm_pos":
            rows = _atm_pos.compute(sig_id, compute_spec, period, df)
        else:
            rows = []

        spec_version = sig.get("spec_version", "1.0")
        for r in rows:
            r["metric_id"]    = sig_id
            r["spec_version"] = spec_version
        all_rows.extend(rows)

    row_count = _upsert(conn, pipeline, period, all_rows)

    # Refresh metric_ranges for every affected metric
    affected_metrics: set[tuple] = {
        (r["metric_id"], r.get("entity_type", "aggregate"), r.get("entity_id", "total"))
        for r in all_rows
    }
    for metric_id, entity_type, entity_id in affected_metrics:
        refresh_ranges(conn, metric_id, pipeline, entity_type, entity_id)

    # Log
    conn.execute(
        """INSERT INTO ingestion_log (pipeline, period, layer, metric_count, row_count)
           VALUES (?,?,?,?,?)""",
        (pipeline, period, "1", len(signals) - skipped, row_count)
    )
    conn.commit()

    # Status summary
    status_counts: dict[str, int] = {}
    for r in all_rows:
        s = r.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "metric_count": len(signals) - skipped,
        "skipped_no_compute": skipped,
        "row_count": row_count,
        "statuses": status_counts,
    }
