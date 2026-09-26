"""
Compute engine — dispatches to SIBC or ATM/POS methods, writes results to SQLite.

Entry point: run_append(pipeline, period, conn, registry)

Every pipeline reads from its own consolidated CSV, declared in its manifest.

Which compute module serves a pipeline is DECLARED too (`compute_module`), not branched on
the id. Two `if pipeline == "sibc"` ladders lived here, and they are the reason a third
source looked like it needed a copied compute module: SIBC is not a pipeline-shaped module,
it is a SHAPE — one measure over a code hierarchy — and any source of that shape can use it.

period is always YYYY-MM-DD (the dataDate) for every pipeline.
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from . import csv_sector as _csv_sector
from . import atm_pos as _atm_pos

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import manifest                                          # noqa: E402

#: Compute shape → the module implementing it. A manifest names the shape it is.
MODULES = {"csv_sector": _csv_sector, "atm_pos": _atm_pos}


def module_for(pipeline: str):
    """The compute module a pipeline declares. An undeclared or unknown shape RAISES — a
    pipeline that silently computes nothing is the failure this engine already refuses for
    an unknown method name, and it looks exactly like a source with no signals yet."""
    name = manifest.load(pipeline).get("compute_module")
    if not name:
        raise KeyError(f"{pipeline}: manifest declares no 'compute_module'")
    if name not in MODULES:
        raise KeyError(f"{pipeline}: compute_module '{name}' is not one of {sorted(MODULES)}")
    return MODULES[name]


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

    engine = module_for(pipeline)
    df = engine._load_df(pipeline)

    # dataDate → the date the CSV actually keys on, when the source needs the translation.
    # A module that does not remap says so by not offering a resolver.
    resolver = getattr(engine, "resolve_csv_date", None)
    csv_period = resolver(pipeline, period) if resolver else period

    all_rows: list[dict] = []
    skipped = 0

    for sig_id, sig in signals.items():
        compute_spec = sig.get("compute")
        if not compute_spec:
            skipped += 1
            continue

        rows = engine.compute(sig_id, compute_spec, csv_period, df)

        spec_version = sig.get("spec_version", "1.0")
        for r in rows:
            r["metric_id"]    = sig_id
            r["spec_version"] = spec_version
        all_rows.extend(rows)

    # A metric that recomputed owns its rows for this period OUTRIGHT — replace the set, do
    # not merge into it. `_upsert` is INSERT OR REPLACE, which can add and update but never
    # REMOVE, so a signal that stops emitting a row kind used to leave the old rows behind
    # forever. That had never bitten because no signal had ever emitted fewer rows than
    # before; the denominator rule is the first (priority sector legitimately stops emitting
    # `alloc`/`weight`/`weight_now`), and 456 stale rows survived a full re-append.
    #
    # Scoped to metrics that actually produced rows, deliberately. A metric that produced
    # NOTHING — a failed compute, a data gap — keeps its old rows rather than having them
    # deleted by an error, and freshness reports them as orphans, which is loud. Silently
    # emptying a signal because its compute raised is the worse failure.
    recomputed = {r["metric_id"] for r in all_rows}
    removed = 0
    for metric_id in recomputed:
        removed += conn.execute(
            "DELETE FROM signals WHERE pipeline=? AND period=? AND metric_id=?",
            (pipeline, period, metric_id)).rowcount
    row_count = _upsert(conn, pipeline, period, all_rows)

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
        "rows_replaced": removed,
        "metric_count": len(signals) - skipped,
        "skipped_no_compute": skipped,
        "row_count": row_count,
        "statuses": status_counts,
    }
