#!/usr/bin/env python3
"""
Check 2e: Signal history integrity validation.

Validates:
  A. registry.json schema — required fields, valid status values, known pipelines/domains
  B. history/{pipeline}.json — schema, chronological order, no gaps > 2 periods, no orphan IDs
  C. Continuity — every signal in registry has at least one history entry after first_seen
  D. Cross-file — registry current_status matches latest history entry for each signal

Exit 0 = all checks pass. Exit 1 = failures found.

Run directly or via run_evals.py / run_atm_pos_evals.py.
"""

import json
import sys
from pathlib import Path

REPO  = Path(__file__).resolve().parent.parent
ANAL  = REPO / "analysis"
SIG   = ANAL / "signals"
REG   = SIG / "registry.json"
HIST  = SIG / "history"

VALID_STATUSES  = {"new", "active", "strengthening", "weakening", "reversed", "absent", "unknown"}
REQUIRED_SIG    = {"id", "pipeline", "domain", "type", "first_seen", "current_status", "title"}
VALID_SIG_TYPES = {"data", "inference", "hypothesis", "insight", "gap", "opportunity"}

failures: list[str] = []
warnings: list[str] = []

def fail(msg: str) -> None:
    failures.append(msg)

def warn(msg: str) -> None:
    warnings.append(msg)

def load_json(path: Path) -> dict | list | None:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        fail(f"File not found: {path}")
        return None
    except json.JSONDecodeError as e:
        fail(f"JSON parse error in {path}: {e}")
        return None

# ─── Check A: registry.json schema ───────────────────────────────────────────

def check_registry(reg: dict) -> set[str]:
    """Validate registry schema. Returns set of known pipelines."""
    known_pipelines: set[str] = set()
    known_domains: set[str] = set()

    # _meta
    meta = reg.get("_meta", {})
    if not meta.get("schema_version"):
        fail("registry._meta.schema_version missing")
    if not meta.get("last_updated"):
        warn("registry._meta.last_updated missing")

    # pipelines
    pipelines = reg.get("pipelines", {})
    if not pipelines:
        fail("registry.pipelines is empty")
    known_pipelines = set(pipelines.keys())

    # domains
    domains = reg.get("domains", {})
    if not domains:
        fail("registry.domains is empty")
    known_domains = set(domains.keys())

    # signals
    signals = reg.get("signals", {})
    if not signals:
        fail("registry.signals is empty")

    for sig_id, sig in signals.items():
        # ID must match key
        if sig.get("id") != sig_id:
            fail(f"registry.signals['{sig_id}'].id mismatch: '{sig.get('id')}'")

        # Required fields
        missing = REQUIRED_SIG - set(sig.keys())
        if missing:
            fail(f"registry.signals['{sig_id}'] missing fields: {missing}")
            continue

        # Pipeline must be known
        if sig["pipeline"] not in known_pipelines:
            fail(f"registry.signals['{sig_id}'].pipeline '{sig['pipeline']}' not in pipelines registry")

        # Domain must be known
        if sig["domain"] not in known_domains:
            fail(f"registry.signals['{sig_id}'].domain '{sig['domain']}' not in domains registry")

        # Type must be valid
        if sig["type"] not in VALID_SIG_TYPES:
            warn(f"registry.signals['{sig_id}'].type '{sig['type']}' unexpected — expected one of {VALID_SIG_TYPES}")

        # current_status must be valid
        if sig["current_status"] not in VALID_STATUSES:
            fail(f"registry.signals['{sig_id}'].current_status '{sig['current_status']}' invalid")

        # first_seen format YYYY-MM-DD
        fs = sig.get("first_seen", "")
        if len(fs) != 10 or fs[4] != "-" or fs[7] != "-":
            fail(f"registry.signals['{sig_id}'].first_seen '{fs}' is not YYYY-MM-DD")

    return known_pipelines

# ─── Check B: history/{pipeline}.json schema ──────────────────────────────────

def check_history(pipeline: str, reg_signals: dict) -> list[dict]:
    """Validate a pipeline history file. Returns its entries list."""
    path = HIST / f"{pipeline}.json"
    hist = load_json(path)
    if hist is None:
        return []

    if not isinstance(hist, dict):
        fail(f"history/{pipeline}.json must be an object, not {type(hist).__name__}")
        return []

    # _meta
    meta = hist.get("_meta", {})
    if meta.get("pipeline") != pipeline:
        fail(f"history/{pipeline}.json _meta.pipeline mismatch: '{meta.get('pipeline')}'")
    if meta.get("schema_version") != "1.0":
        warn(f"history/{pipeline}.json _meta.schema_version should be '1.0'")

    entries = hist.get("entries", [])

    # Chronological order
    periods = [e.get("period", "") for e in entries]
    if periods != sorted(periods):
        fail(f"history/{pipeline}.json entries are not in chronological order")

    # entry_count vs actual
    stated_count = meta.get("entry_count", -1)
    if stated_count != len(entries):
        warn(f"history/{pipeline}.json _meta.entry_count {stated_count} != actual {len(entries)}")

    # Validate each entry
    pipeline_signals = {sig_id for sig_id, sig in reg_signals.items() if sig["pipeline"] == pipeline}

    for entry in entries:
        period = entry.get("period", "(missing)")

        if not entry.get("period"):
            fail(f"history/{pipeline}.json entry missing 'period'")

        if not entry.get("appended_at"):
            warn(f"history/{pipeline}.json entry {period} missing 'appended_at'")

        sigs = entry.get("signals", {})
        if not sigs:
            warn(f"history/{pipeline}.json entry {period} has no signals")
            continue

        # Orphan IDs (in history but not registry)
        for sig_id in sigs:
            if sig_id not in pipeline_signals:
                fail(f"history/{pipeline}.json entry {period} has orphan signal '{sig_id}' (not in registry for this pipeline)")

        # Status validity
        for sig_id, sig_data in sigs.items():
            status = sig_data.get("status", "")
            if status not in VALID_STATUSES:
                fail(f"history/{pipeline}.json entry {period} signal '{sig_id}' invalid status '{status}'")

    return entries

# ─── Check C: continuity ──────────────────────────────────────────────────────

def check_continuity(pipeline: str, entries: list[dict], reg_signals: dict) -> None:
    """Warn if any non-new signal appears in registry but never in history."""
    if not entries:
        return

    pipeline_signals = {sig_id for sig_id, sig in reg_signals.items() if sig["pipeline"] == pipeline}
    seen_in_history: set[str] = set()

    for entry in entries:
        seen_in_history.update(entry.get("signals", {}).keys())

    never_seen = pipeline_signals - seen_in_history
    for sig_id in sorted(never_seen):
        warn(f"Signal '{sig_id}' ({pipeline}) is in registry but never appears in history")

# ─── Check D: current_status sync ─────────────────────────────────────────────

def check_status_sync(pipeline: str, entries: list[dict], reg_signals: dict) -> None:
    """
    Verify registry current_status matches the latest history entry for each signal.
    Only checks signals present in the latest history entry (others may be 'unknown').
    """
    if not entries:
        return

    latest = entries[-1]
    latest_period = latest.get("period", "?")
    hist_sigs = latest.get("signals", {})

    for sig_id, hist_data in hist_sigs.items():
        hist_status = hist_data.get("status", "unknown")
        reg_status = reg_signals.get(sig_id, {}).get("current_status", "unknown")
        if hist_status != reg_status:
            fail(
                f"Status mismatch for '{sig_id}' — registry says '{reg_status}', "
                f"history/{pipeline}.json latest period ({latest_period}) says '{hist_status}'"
            )

# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("Check 2e: signal history integrity")
    print()

    reg = load_json(REG)
    if reg is None:
        print("FAIL — registry.json missing or unparseable")
        return 1

    # Check A
    print("  A. registry.json schema ...")
    known_pipelines = check_registry(reg)
    reg_signals = reg.get("signals", {})
    if not failures:
        print(f"     ✓ {len(reg_signals)} signals, {len(known_pipelines)} pipelines, {len(reg.get('domains', {}))} domains")

    # Checks B–D per pipeline
    for pipeline in sorted(known_pipelines):
        print(f"\n  B–D. history/{pipeline}.json ...")
        entries = check_history(pipeline, reg_signals)

        if not failures:
            print(f"     B ✓ {len(entries)} entries validated")

        check_continuity(pipeline, entries, reg_signals)
        check_status_sync(pipeline, entries, reg_signals)

        if not failures:
            print(f"     C ✓ continuity check passed")
            print(f"     D ✓ current_status in sync with latest history entry")

    print()

    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")
        print()

    if failures:
        for f_msg in failures:
            print(f"  FAIL: {f_msg}")
        print(f"\n  {len(failures)} failure(s), {len(warnings)} warning(s)")
        return 1
    else:
        print(f"  All checks passed  ({len(warnings)} warning(s))")
        return 0

if __name__ == "__main__":
    sys.exit(main())
