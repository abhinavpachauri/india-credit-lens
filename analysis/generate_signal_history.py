#!/usr/bin/env python3
"""
Signal history layer — cross-pipeline, cross-period signal continuity.

Registry:   analysis/signals/registry.json        — universal signal catalog (90+ signals)
DB:         analysis/signals/signals.db           — computed signal values (primary store)
History:    analysis/signals/history/{pipeline}.json — append-only JSON mirror (human-readable)
Source:
  SIBC layer 1:   analysis/rbi_sibc/merged/sections_merged.json  — computed algorithmically
  SIBC layer 2/3: status = "pending" until those layers are implemented
  ATM/POS layer 1: web/public/data/atm_pos_consolidated.csv      — computed algorithmically

Layer model
-----------
  layer 1 — per-chart data signals: status + value derived algorithmically from source data
  layer 2 — cross-chart synthesis: authored per period from ingested data (future)
  layer 3 — lending ecosystem expert model: generated ~6-monthly (future)

Commands
--------
  append   --pipeline sibc    --period 2026-03-30   Compute SIBC Layer 1 → DB + history JSON
  append   --pipeline atm_pos --period 2026-03-31   Compute ATM/POS Layer 1 → DB + history JSON
  evaluate --pipeline sibc    --period 2026-03-30   LLM interpret Layer 1 signals → evaluations JSON
  evaluate --pipeline atm_pos --period 2026-03-31   LLM interpret Layer 1 signals → evaluations JSON
  status                                             Print current signal states (all pipelines)
  seed                                               (Re)seed registry first_seen from history

Status values: new | active | strengthening | weakening | reversed | absent | unknown | pending

Append is idempotent: running twice for the same period updates the existing entry.

Design principles
-----------------
- DB is authoritative: all Layer 1 values computed by engine → signals.db
- JSON history files mirror DB for human-readable audit trail
- Layer 1 always algorithmic: no LLM input for status or value
- Layer 2/3 status = "pending" until those layers are built
- Scalable: adding a new pipeline = add entry in registry.json + new history/{pipeline}.json
"""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

REPO   = Path(__file__).resolve().parent.parent
ANAL   = REPO / "analysis"
SIG    = ANAL / "signals"
REG    = SIG / "registry.json"
HIST   = SIG / "history"

SECTIONS_MERGED = ANAL / "rbi_sibc" / "merged" / "sections_merged.json"

KNOWN_PIPELINES  = {"sibc", "atm_pos"}
PIPELINE_SOURCES = list(KNOWN_PIPELINES)

VALID_STATUSES = {"new", "active", "strengthening", "weakening", "reversed", "absent", "unknown", "pending"}

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

def save_registry(reg: dict) -> None:
    reg["_meta"]["last_updated"] = date.today().isoformat()
    save_json(REG, reg)

def load_history(pipeline: str) -> dict:
    path = HIST / f"{pipeline}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No history file for pipeline '{pipeline}'. "
            f"Create analysis/signals/history/{pipeline}.json first."
        )
    return load_json(path)

def save_history(pipeline: str, hist: dict) -> None:
    hist["_meta"]["entry_count"] = len(hist["entries"])
    save_json(HIST / f"{pipeline}.json", hist)


# ─── append command ───────────────────────────────────────────────────────────

def cmd_append(pipeline: str, period: str) -> int:
    """
    Compute Layer 1 signals for (pipeline, period) via the compute engine,
    write results to signals.db, then mirror the aggregate-level values into
    the history/{pipeline}.json file and update current_status in registry.json.
    """
    if pipeline not in KNOWN_PIPELINES:
        print(f"ERROR: unknown pipeline '{pipeline}'. Known: {sorted(KNOWN_PIPELINES)}")
        return 1

    registry = load_registry()
    hist     = load_history(pipeline)

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

    # ── Step 4: write to history JSON (human-readable mirror) ─────────────────
    entry = {
        "period":      period,
        "appended_at": datetime.now().isoformat(timespec="seconds"),
        "signals":     all_results,
    }
    existing_idx = next(
        (i for i, e in enumerate(hist["entries"]) if e["period"] == period), None
    )
    if existing_idx is not None:
        print(f"  Updating existing JSON entry for period {period}.")
        hist["entries"][existing_idx] = entry
    else:
        hist["entries"].append(entry)
    hist["entries"].sort(key=lambda e: e["period"])
    save_history(pipeline, hist)

    # ── Step 5: update current_status + first_seen in registry ───────────────
    for sig_id, res in all_results.items():
        if sig_id in registry["signals"]:
            sig = registry["signals"][sig_id]
            sig["current_status"] = res["status"]
            if not sig.get("first_seen"):
                sig["first_seen"] = period
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
    calls Claude API (temperature=0, hash-cached), and writes structured evaluations to
    signals/evaluations/{pipeline}/{period}.json.

    Requires ANTHROPIC_API_KEY env var. Safe to re-run — cache hits skip API calls.
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

    print(f"\n  ✓ {pipeline} / {period}")
    print(f"    Domains evaluated  : {summary['domains_evaluated']}")
    print(f"    Signals interpreted: {summary['signals_interpreted']}")
    print(f"    API calls          : {summary['api_calls']}")
    print(f"    Cache hits         : {summary['cache_hits']}")
    print(f"    Output             : {summary['output_path']}")
    return 0


# ─── status command ───────────────────────────────────────────────────────────

def cmd_status() -> int:
    registry = load_registry()
    all_signals = registry["signals"]

    pipelines: dict[str, dict[str, list]] = {}
    for sig_id, sig in all_signals.items():
        pl  = sig["pipeline"]
        dom = sig["domain"]
        pipelines.setdefault(pl, {}).setdefault(dom, []).append(sig)

    for pl, domains in sorted(pipelines.items()):
        hist_path = HIST / f"{pl}.json"
        if hist_path.exists():
            hist = load_json(hist_path)
            last_period = hist["entries"][-1]["period"] if hist["entries"] else "(none)"
            n_entries   = len(hist["entries"])
        else:
            last_period = "(no history file)"
            n_entries   = 0

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
    registry = load_registry()
    updated  = 0

    for pl in PIPELINE_SOURCES:
        hist_path = HIST / f"{pl}.json"
        if not hist_path.exists() or not hist_path.stat().st_size:
            continue
        hist = load_json(hist_path)
        if not hist["entries"]:
            continue

        for entry in sorted(hist["entries"], key=lambda e: e["period"]):
            for sig_id, sig_data in entry["signals"].items():
                if sig_id not in registry["signals"]:
                    continue
                status = sig_data.get("status", "unknown")
                if status in ("absent", "unknown", "pending"):
                    continue
                reg_sig = registry["signals"][sig_id]
                existing_first = reg_sig.get("first_seen", "")
                if not existing_first or entry["period"] < existing_first:
                    reg_sig["first_seen"] = entry["period"]
                    updated += 1

    save_registry(registry)
    print(f"  ✓ seed complete — {updated} first_seen values updated")
    return 0


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Signal history management — cross-pipeline, cross-period signal continuity."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_append = sub.add_parser("append", help="Append a period's signal statuses to history")
    p_append.add_argument("--pipeline", required=True, help="Pipeline name (sibc, atm_pos, ...)")
    p_append.add_argument("--period",   required=True, help="Period date YYYY-MM-DD")

    p_eval = sub.add_parser("evaluate", help="LLM-interpret Layer 1 signals for a period")
    p_eval.add_argument("--pipeline", required=True, help="Pipeline name (sibc, atm_pos, ...)")
    p_eval.add_argument("--period",   required=True, help="Period date YYYY-MM-DD")

    sub.add_parser("status", help="Print current signal states across all pipelines")
    sub.add_parser("seed",   help="Backfill registry first_seen from existing history entries")

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
