#!/usr/bin/env python3
"""
Signal history layer — cross-pipeline, cross-period signal continuity.

Registry:   analysis/signals/registry.json        — universal signal catalog (70+ signals)
History:    analysis/signals/history/{pipeline}.json — append-only per-period entries
Snapshot:   analysis/rbi_sibc/merged/signal_snapshot.json  — SIBC: Claude writes during Stage 5
            web/public/data/atm_pos_insights.json          — ATM/POS: auto-derived

Commands
--------
  append --pipeline sibc    --period 2026-03-30   Append SIBC period from signal_snapshot.json
  append --pipeline atm_pos --period 2026-03-31   Append ATM/POS period from insights.json
  status                                           Print current signal states (all pipelines)
  seed                                             (Re)seed registry first_seen from history

Status values: new | active | strengthening | weakening | reversed | absent | unknown

Append is idempotent: running twice for the same period updates the existing entry.

Design principles
-----------------
- Append-only: never rewrite past entries; the entry_count in _meta is informational
- Pipeline-isolated: sibc.json and atm_pos.json are never mixed
- Scalable: adding a new pipeline = add entry in registry.json + new history/{pipeline}.json
- Claude-writable: SIBC uses signal_snapshot.json (authored by Claude during Stage 5)
- Auto-derivable: ATM/POS uses atm_pos_insights.json (status inferred from presence/absence)
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

# Pipeline-specific source paths
PIPELINE_SOURCES = {
    "sibc": {
        "snapshot": ANAL / "rbi_sibc" / "merged" / "signal_snapshot.json",
        "auto_snapshot": False,
    },
    "atm_pos": {
        "snapshot": REPO / "web" / "public" / "data" / "atm_pos_insights.json",
        "auto_snapshot": True,
    },
}

VALID_STATUSES = {"new", "active", "strengthening", "weakening", "reversed", "absent", "unknown"}

# ─── helpers ──────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)

def save_json(path: Path, obj: dict | list) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
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

# ─── ATM/POS auto-derive ──────────────────────────────────────────────────────

def derive_atm_pos_statuses(period: str, registry: dict) -> dict[str, str]:
    """
    Derive signal statuses from atm_pos_insights.json for a given period.
    - Signals present in the file: "active"
    - Signals absent from the file: "absent"
    - Signals not yet seen (first_seen == period): "new"
    """
    src = PIPELINE_SOURCES["atm_pos"]["snapshot"]
    if not src.exists():
        raise FileNotFoundError(f"ATM/POS insights not found: {src}")

    insights = load_json(src)
    present_ids = {i["id"] for i in insights}

    statuses: dict[str, str] = {}
    for sig_id, sig in registry["signals"].items():
        if sig["pipeline"] != "atm_pos":
            continue
        if sig_id in present_ids:
            status = "new" if sig.get("first_seen") == period else "active"
        else:
            status = "absent"
        statuses[sig_id] = status

    return statuses

# ─── SIBC snapshot-derive ─────────────────────────────────────────────────────

def derive_sibc_statuses(period: str, registry: dict) -> dict[str, str]:
    """
    Read signal_snapshot.json written by Claude during Stage 5.
    Expected structure:
    {
      "period": "2026-03-30",
      "signals": {
        "<signal_id>": {
          "status": "active" | "strengthening" | ...,
          "note": "..."          // optional free-text
        },
        ...
      }
    }
    Signals in registry but missing from snapshot → "unknown"
    """
    src = PIPELINE_SOURCES["sibc"]["snapshot"]
    if not src.exists():
        raise FileNotFoundError(
            f"SIBC signal_snapshot.json not found: {src}\n"
            f"Claude must write this file during Stage 5 analysis before calling append."
        )

    snap = load_json(src)
    snap_period = snap.get("period", "")
    if snap_period != period:
        print(
            f"  WARNING: snapshot period '{snap_period}' does not match requested period '{period}'. "
            f"Proceeding anyway."
        )

    snap_signals = snap.get("signals", {})
    statuses: dict[str, str] = {}

    for sig_id, sig in registry["signals"].items():
        if sig["pipeline"] != "sibc":
            continue
        if sig_id in snap_signals:
            raw = snap_signals[sig_id]
            if isinstance(raw, dict):
                status = raw.get("status", "unknown")
            else:
                status = str(raw)
            if status not in VALID_STATUSES:
                print(f"  WARNING: unknown status '{status}' for {sig_id} — defaulting to 'unknown'")
                status = "unknown"
        else:
            status = "unknown"
        statuses[sig_id] = status

    return statuses

# ─── append command ───────────────────────────────────────────────────────────

def cmd_append(pipeline: str, period: str) -> int:
    if pipeline not in PIPELINE_SOURCES:
        print(f"ERROR: unknown pipeline '{pipeline}'. Known: {list(PIPELINE_SOURCES.keys())}")
        return 1

    registry = load_registry()
    hist = load_history(pipeline)

    # Derive statuses
    print(f"Deriving signal statuses for {pipeline} / {period} ...")
    if PIPELINE_SOURCES[pipeline]["auto_snapshot"]:
        statuses = derive_atm_pos_statuses(period, registry)
    else:
        statuses = derive_sibc_statuses(period, registry)

    if not statuses:
        print(f"ERROR: no signals found for pipeline '{pipeline}' in registry.")
        return 1

    # Build entry
    entry = {
        "period": period,
        "appended_at": datetime.now().isoformat(timespec="seconds"),
        "signals": {
            sig_id: {"status": status}
            for sig_id, status in statuses.items()
        },
    }

    # Upsert (idempotent)
    existing = next((i for i, e in enumerate(hist["entries"]) if e["period"] == period), None)
    if existing is not None:
        print(f"  Updating existing entry for period {period}.")
        hist["entries"][existing] = entry
    else:
        hist["entries"].append(entry)

    # Sort entries chronologically
    hist["entries"].sort(key=lambda e: e["period"])
    save_history(pipeline, hist)

    # Update current_status in registry for each signal
    for sig_id, status in statuses.items():
        if sig_id in registry["signals"]:
            registry["signals"][sig_id]["current_status"] = status

    save_registry(registry)

    # Summary
    counts: dict[str, int] = {}
    for s in statuses.values():
        counts[s] = counts.get(s, 0) + 1

    print(f"\n  ✓ {pipeline} / {period} — {len(statuses)} signals recorded")
    for status, n in sorted(counts.items()):
        print(f"    {status:<14} {n}")

    return 0

# ─── status command ───────────────────────────────────────────────────────────

def cmd_status() -> int:
    registry = load_registry()
    all_signals = registry["signals"]

    # Group by pipeline, then domain
    pipelines: dict[str, dict[str, list]] = {}
    for sig_id, sig in all_signals.items():
        pl = sig["pipeline"]
        dom = sig["domain"]
        pipelines.setdefault(pl, {}).setdefault(dom, []).append(sig)

    for pl, domains in sorted(pipelines.items()):
        # Load history to get last entry period
        hist_path = HIST / f"{pl}.json"
        if hist_path.exists():
            hist = load_json(hist_path)
            last_period = hist["entries"][-1]["period"] if hist["entries"] else "(none)"
            n_entries = len(hist["entries"])
        else:
            last_period = "(no history file)"
            n_entries = 0

        print(f"\n{'='*60}")
        print(f"  Pipeline: {pl}  |  {n_entries} period(s)  |  latest: {last_period}")
        print(f"{'='*60}")

        for dom, sigs in sorted(domains.items()):
            print(f"\n  [{dom}]")
            for sig in sigs:
                status = sig.get("current_status", "unknown")
                icon = {
                    "new": "🆕", "active": "✓", "strengthening": "↑",
                    "weakening": "↓", "reversed": "⇄", "absent": "–",
                    "unknown": "?",
                }.get(status, "?")
                print(f"    {icon} {sig['id']:<45} {status}")

    return 0

# ─── seed command ─────────────────────────────────────────────────────────────

def cmd_seed() -> int:
    """
    Backfill registry first_seen from history files.
    Useful if registry was created before history entries existed.
    """
    registry = load_registry()
    updated = 0

    for pl in PIPELINE_SOURCES:
        hist_path = HIST / f"{pl}.json"
        if not hist_path.exists() or not hist_path.stat().st_size:
            continue
        hist = load_json(hist_path)
        if not hist["entries"]:
            continue

        # First entry period where each signal appears as non-absent / non-unknown
        for entry in sorted(hist["entries"], key=lambda e: e["period"]):
            for sig_id, sig_data in entry["signals"].items():
                if sig_id not in registry["signals"]:
                    continue
                status = sig_data.get("status", "unknown")
                if status in ("absent", "unknown"):
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
    p_append.add_argument("--period", required=True, help="Period date YYYY-MM-DD")

    sub.add_parser("status", help="Print current signal states across all pipelines")
    sub.add_parser("seed", help="Backfill registry first_seen from existing history entries")

    args = parser.parse_args()

    if args.command == "append":
        return cmd_append(args.pipeline, args.period)
    elif args.command == "status":
        return cmd_status()
    elif args.command == "seed":
        return cmd_seed()
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
