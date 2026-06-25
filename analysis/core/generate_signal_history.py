#!/usr/bin/env python3
"""
Signal history layer — cross-pipeline, cross-period signal continuity.

Registry:   analysis/signals/registry.json        — universal signal catalog (90+ signals)
DB:         analysis/signals/signals.db           — computed signal values (primary store)
Source:
  SIBC layer 1:    web/public/data/rbi_sibc_consolidated.csv  — computed algorithmically
                   period (dataDate) resolved to csv_date via analysis/rbi_sibc/timeline.json
  SIBC layer 2/3:  status = "pending" until those layers are implemented
  ATM/POS layer 1: web/public/data/atm_pos_consolidated.csv   — computed algorithmically

Layer model
-----------
  layer 1 — per-chart data signals: status + value derived algorithmically from source data
  layer 2 — cross-chart synthesis: authored per period from ingested data (future)
  layer 3 — lending ecosystem expert model: generated ~6-monthly (future)

Commands
--------
  append   --pipeline sibc    --period 2026-03-30   Compute SIBC Layer 1 → DB + registry update
  append   --pipeline atm_pos --period 2026-03-31   Compute ATM/POS Layer 1 → DB + registry update
  evaluate --pipeline sibc    --period 2026-03-30   LLM interpret Layer 1 signals → evaluations JSON
  evaluate --pipeline atm_pos --period 2026-03-31   LLM interpret Layer 1 signals → evaluations JSON
  status                                             Print current signal states (all pipelines)
  seed                                               Backfill registry first_seen from signals.db

Status values: new | active | strengthening | weakening | reversed | absent | unknown | pending

Append is idempotent: running twice for the same period updates the existing DB rows.

Design principles
-----------------
- DB is authoritative: all Layer 1 values computed by engine → signals.db
- Layer 1 always algorithmic: no LLM input for status or value
- Layer 2/3 status = "pending" until those layers are built
- Scalable: adding a new pipeline = add entry in registry.json
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO
ANAL   = REPO / "analysis"
SIG    = ANAL / "signals"
REG    = SIG / "registry.json"

KNOWN_PIPELINES  = {"sibc", "atm_pos"}
PIPELINE_SOURCES = list(KNOWN_PIPELINES)

VALID_STATUSES = {"new", "active", "strengthening", "weakening", "declining", "reversed", "absent", "unknown", "pending"}

# ─── helpers ──────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)

def save_json(path: Path, obj: dict | list) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")

def load_registry() -> dict:
    return load_json(REG)

def sync_current_status_from_db(conn, registry: dict) -> int:
    """Roll up registry current_status from the latest-period DB rows. Single-entity signals
    take their one status; multi-entity signals (scan / bank-scan / category-share) take the
    most common status across their entity rows. Returns the number of statuses changed."""
    from collections import Counter
    latest = dict(conn.execute("SELECT metric_id, MAX(period) FROM signals GROUP BY metric_id").fetchall())
    updated = 0
    for metric_id, period in latest.items():
        if metric_id not in registry["signals"]:
            continue
        # entity_type='fy_yoy' rows are auxiliary component rates (e.g. the two
        # FY-end YoY values behind an acceleration), not status-bearing — exclude
        # them so they don't skew the roll-up away from the primary metric status.
        statuses = [r[0] for r in conn.execute(
            "SELECT status FROM signals WHERE metric_id=? AND period=? AND entity_type != 'fy_yoy'", (metric_id, period)
        ).fetchall() if r[0] not in ("unknown", "absent", "pending")]
        if not statuses:
            continue
        rolled = Counter(statuses).most_common(1)[0][0]
        if registry["signals"][metric_id].get("current_status") != rolled:
            registry["signals"][metric_id]["current_status"] = rolled
            updated += 1
    return updated


def save_registry(reg: dict) -> None:
    reg["_meta"]["last_updated"] = date.today().isoformat()
    save_json(REG, reg)


# ─── append command ───────────────────────────────────────────────────────────

def cmd_append(pipeline: str, period: str) -> int:
    """
    Compute Layer 1 signals for (pipeline, period) via the compute engine,
    write results to signals.db, and update current_status in registry.json.
    """
    if pipeline not in KNOWN_PIPELINES:
        print(f"ERROR: unknown pipeline '{pipeline}'. Known: {sorted(KNOWN_PIPELINES)}")
        return 1

    registry = load_registry()

    # ── Step 1: run compute engine → DB ───────────────────────────────────────
    from signals.db import init_db
    from signals.compute.engine import run_append

    print(f"Computing Layer 1 signals for {pipeline} / {period} ...")
    conn    = init_db()
    summary = run_append(pipeline, period, conn, registry)
    print(f"  DB: {summary['row_count']} rows written "
          f"({summary['metric_count']} metrics, {summary.get('skipped_no_compute', 0)} skipped)")

    # ── Step 2: read back aggregate/total rows from DB ────────────────────────
    db_rows = conn.execute(
        "SELECT metric_id, value, status FROM signals "
        "WHERE pipeline=? AND period=? AND entity_type='aggregate' AND entity_id='total'",
        (pipeline, period)
    ).fetchall()
    db_results: dict[str, dict] = {
        row[0]: {"value": row[1], "status": row[2]} for row in db_rows
    }

    # ── Step 3: build full results dict (layer 1 from DB, layer 2/3 = pending) ─
    all_results: dict[str, dict] = {}
    for sig_id, sig in registry["signals"].items():
        if sig["pipeline"] != pipeline:
            continue
        layer = sig.get("layer", 2)
        if layer == 1 and sig_id in db_results:
            res    = db_results[sig_id]
            status = res["status"] or "unknown"
            # Promote to "new" on first appearance
            if (sig.get("first_seen") == period
                    and status not in ("unknown", "absent")):
                status = "new"
            entry_rec: dict = {"status": status}
            if res["value"] is not None:
                entry_rec["value"] = round(res["value"], 4)
            all_results[sig_id] = entry_rec
        elif layer == 1:
            # Layer 1 signal with no compute spec — stays unknown
            all_results[sig_id] = {"status": "unknown"}
        else:
            all_results[sig_id] = {"status": "pending"}

    # ── Step 4: update current_status + first_seen in registry ───────────────
    for sig_id, res in all_results.items():
        if sig_id in registry["signals"]:
            sig = registry["signals"][sig_id]
            sig["current_status"] = res["status"]
            if not sig.get("first_seen"):
                sig["first_seen"] = period
    # multi-entity signals (scan / bank-scan / category-share) have no single status above —
    # roll them up from the DB rows just written so they don't drift back to 'unknown'.
    sync_current_status_from_db(conn, registry)
    save_registry(registry)

    # ── Summary ───────────────────────────────────────────────────────────────
    counts: dict[str, int] = {}
    for res in all_results.values():
        s = res["status"]
        counts[s] = counts.get(s, 0) + 1
    with_value = sum(1 for res in all_results.values() if "value" in res)
    print(f"\n  ✓ {pipeline} / {period} — {len(all_results)} signals  "
          f"({with_value} with numeric value)")
    for status, n in sorted(counts.items()):
        print(f"    {status:<16} {n}")

    return 0


# ─── evaluate command ────────────────────────────────────────────────────────

def cmd_evaluate(pipeline: str, period: str) -> int:
    """
    LLM-interpret Layer 1 signals for (pipeline, period).
    Reads computed values from signals.db, builds domain-grouped context payloads,
    calls Claude (temperature=0, hash-cached), and writes structured evaluations to
    signals/evaluations/{pipeline}/{period}.json.

    Automatically loads the prior period's evaluation (if it exists) and passes
    signal-level prior narratives into the prompt so the LLM can highlight changes.

    Safe to re-run — cache hits skip LLM calls.
    """
    if pipeline not in KNOWN_PIPELINES:
        print(f"ERROR: unknown pipeline '{pipeline}'. Known: {sorted(KNOWN_PIPELINES)}")
        return 1

    from signals.db import init_db
    from signals.evaluate import run_evaluate

    registry = load_registry()
    conn     = init_db()

    print(f"Evaluating Layer 1 signals: {pipeline} / {period} ...")
    summary = run_evaluate(pipeline, period, conn, registry)

    status = "✓" if summary['errors'] == 0 else f"⚠ {summary['errors']} domain(s) failed"
    print(f"\n  {status}  {pipeline} / {period}")
    print(f"    Domains evaluated  : {summary['domains_evaluated']}")
    print(f"    Signals interpreted: {summary['signals_interpreted']}")
    print(f"    LLM calls          : {summary['api_calls']}  |  Cache hits: {summary['cache_hits']}")
    if summary.get('prior_period'):
        print(f"    Prior period used  : {summary['prior_period']} (narrative diff active)")
    else:
        print(f"    Prior period used  : none (first evaluation for this pipeline)")
    if summary['total_tokens']:
        saved = summary['cache_read_tokens']
        print(f"    Tokens used        : {summary['total_tokens']:,}"
              + (f"  |  Cache read: {saved:,} (saved ~{saved//1000}k tokens)" if saved else ""))
    print(f"    Output             : {summary['output_path']}")
    return 0


# ─── status command ───────────────────────────────────────────────────────────

def cmd_status() -> int:
    from signals.db import init_db
    conn = init_db()

    registry = load_registry()
    all_signals = registry["signals"]

    pipelines: dict[str, dict[str, list]] = {}
    for sig_id, sig in all_signals.items():
        pl  = sig["pipeline"]
        dom = sig["domain"]
        pipelines.setdefault(pl, {}).setdefault(dom, []).append(sig)

    for pl, domains in sorted(pipelines.items()):
        row = conn.execute(
            "SELECT COUNT(DISTINCT period), MAX(period) FROM signals WHERE pipeline=?",
            (pl,)
        ).fetchone()
        n_entries   = row[0] if row else 0
        last_period = row[1] if row and row[1] else "(none)"

        print(f"\n{'='*60}")
        print(f"  Pipeline: {pl}  |  {n_entries} period(s)  |  latest: {last_period}")
        print(f"{'='*60}")

        for dom, sigs in sorted(domains.items()):
            print(f"\n  [{dom}]")
            for sig in sigs:
                status = sig.get("current_status", "unknown")
                layer  = sig.get("layer", "?")
                icon   = {
                    "new": "🆕", "active": "✓", "strengthening": "↑",
                    "weakening": "↓", "reversed": "⇄", "absent": "–",
                    "unknown": "?", "pending": "⏳",
                }.get(status, "?")
                print(f"    {icon} L{layer} {sig['id']:<45} {status}")

    return 0


# ─── seed command ─────────────────────────────────────────────────────────────

def cmd_seed() -> int:
    """Backfill registry first_seen + current_status from signals.db.

    current_status sync covers the multi-entity signals (scan / bank-scan / category-share)
    that cmd_append's single-status update skips: for those the latest-period status is rolled
    up to the most common status across their entity rows, so they no longer read 'unknown'.
    """
    from collections import Counter
    from signals.db import init_db
    conn = init_db()

    registry = load_registry()
    first_seen_updated = status_updated = 0

    rows = conn.execute(
        "SELECT metric_id, MIN(period) FROM signals "
        "WHERE status NOT IN ('absent','unknown','pending') "
        "GROUP BY metric_id"
    ).fetchall()
    for metric_id, earliest_period in rows:
        if metric_id not in registry["signals"]:
            continue
        reg_sig = registry["signals"][metric_id]
        existing = reg_sig.get("first_seen", "")
        if not existing or earliest_period < existing:
            reg_sig["first_seen"] = earliest_period
            first_seen_updated += 1

    # current_status sync — latest period per metric, rolled up across entity rows
    status_updated = sync_current_status_from_db(conn, registry)

    save_registry(registry)
    print(f"  ✓ seed complete — {first_seen_updated} first_seen + {status_updated} current_status "
          f"updated from signals.db")
    return 0


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Signal history management — cross-pipeline, cross-period signal continuity."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_append = sub.add_parser("append", help="Append a period's signal statuses to DB + registry")
    p_append.add_argument("--pipeline", required=True, help="Pipeline name (sibc, atm_pos, ...)")
    p_append.add_argument("--period",   required=True, help="Period date YYYY-MM-DD")

    p_eval = sub.add_parser("evaluate", help="LLM-interpret Layer 1 signals for a period")
    p_eval.add_argument("--pipeline", required=True, help="Pipeline name (sibc, atm_pos, ...)")
    p_eval.add_argument("--period",   required=True, help="Period date YYYY-MM-DD")

    sub.add_parser("status", help="Print current signal states across all pipelines")
    sub.add_parser("seed",   help="Backfill registry first_seen from signals.db")

    args = parser.parse_args()

    if args.command == "append":
        return cmd_append(args.pipeline, args.period)
    elif args.command == "evaluate":
        return cmd_evaluate(args.pipeline, args.period)
    elif args.command == "status":
        return cmd_status()
    elif args.command == "seed":
        return cmd_seed()
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
