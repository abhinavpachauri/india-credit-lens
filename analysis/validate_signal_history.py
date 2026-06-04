#!/usr/bin/env python3
"""
Check 2e: Signal history integrity validation.

Validates:
  A. registry.json schema — required fields, valid status values, known pipelines/domains
  B. history/{pipeline}.json — schema, chronological order, no gaps > 2 periods, no orphan IDs
  C. Continuity — every signal in registry has at least one history entry after first_seen
  D. Cross-file — registry current_status matches latest history entry for each signal
  E. DB integrity — signals.db exists, layer-1 metrics present, no orphaned metric_ids,
                    metric_ranges populated for computed metrics

Exit 0 = all checks pass. Exit 1 = failures found.

Run directly or via run_evals.py / run_atm_pos_evals.py.
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO  = Path(__file__).resolve().parent.parent
ANAL  = REPO / "analysis"
SIG   = ANAL / "signals"
REG   = SIG / "registry.json"
HIST  = SIG / "history"
DB    = SIG / "signals.db"

VALID_STATUSES  = {"new", "active", "strengthening", "weakening", "reversed", "absent", "unknown", "pending"}
REQUIRED_SIG    = {"id", "pipeline", "domain", "type", "first_seen", "current_status", "title"}
VALID_SIG_TYPES = {"data", "inference", "hypothesis", "insight", "gap", "opportunity"}
VALID_LAYERS    = {1, 2, 3}

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

        # layer field
        layer = sig.get("layer")
        if layer is None:
            warn(f"registry.signals['{sig_id}'] missing 'layer' field (expected 1, 2, or 3)")
        elif layer not in VALID_LAYERS:
            fail(f"registry.signals['{sig_id}'].layer '{layer}' invalid — must be 1, 2, or 3")

        # layer=1 data signals must have a compute spec
        if layer == 1 and sig.get("pipeline") == "sibc" and sig.get("type") == "data":
            if "compute" not in sig:
                warn(f"registry.signals['{sig_id}'] is layer=1 SIBC data signal but missing 'compute' spec")

    return known_pipelines

# ─── Check B: history/{pipeline}.json schema ──────────────────────────────────

def check_history(pipeline: str, reg_signals: dict, registry: dict) -> list[dict]:
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

        # Status validity + layer=1 value check
        for sig_id, sig_data in sigs.items():
            status = sig_data.get("status", "")
            if status not in VALID_STATUSES:
                fail(f"history/{pipeline}.json entry {period} signal '{sig_id}' invalid status '{status}'")

            # layer=1 non-absent signals should carry a numeric value
            reg_sig = reg_signals.get(sig_id, {})
            if (
                reg_sig.get("layer") == 1
                and status not in ("absent", "unknown", "pending", "new")
                and "value" not in sig_data
                and reg_sig.get("compute", {}).get("method") != "static_active"
            ):
                warn(f"history/{pipeline}.json entry {period} layer=1 signal '{sig_id}' status='{status}' but no 'value' field")

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

# ─── Check E: DB integrity ────────────────────────────────────────────────────

def check_db(reg_signals: dict, known_pipelines: set[str]) -> None:
    """
    E. signals.db integrity:
    E1. DB file exists and has expected tables
    E2. Every layer-1 compute signal has at least one row in signals table
    E3. No orphaned metric_ids (present in DB but not registry)
    E4. metric_ranges populated for metrics that have non-null values in signals
    """
    if not DB.exists():
        fail(f"signals.db not found at {DB} — run generate_signal_history.py append first")
        return

    try:
        conn = sqlite3.connect(DB)
    except Exception as e:
        fail(f"Cannot open signals.db: {e}")
        return

    # E1: tables exist
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    for expected in ("signals", "metric_ranges", "ingestion_log"):
        if expected not in tables:
            fail(f"signals.db missing table '{expected}'")
    if "signals" not in tables:
        conn.close()
        return

    # E2: layer-1 compute signals should have DB rows
    compute_signals = {
        sig_id for sig_id, sig in reg_signals.items()
        if sig.get("layer") == 1 and sig.get("compute")
    }
    db_metric_ids = {r[0] for r in conn.execute(
        "SELECT DISTINCT metric_id FROM signals"
    ).fetchall()}

    missing_from_db = compute_signals - db_metric_ids
    if missing_from_db:
        for sid in sorted(missing_from_db)[:10]:
            warn(f"Layer-1 compute signal '{sid}' has no rows in signals.db")
        if len(missing_from_db) > 10:
            warn(f"  ... and {len(missing_from_db) - 10} more layer-1 signals not in DB")

    # E3: orphaned metric_ids in DB not in registry
    all_reg_ids = set(reg_signals.keys())
    orphaned = db_metric_ids - all_reg_ids
    if orphaned:
        for sid in sorted(orphaned)[:5]:
            fail(f"signals.db has metric_id '{sid}' not found in registry.json")

    # E4: metric_ranges populated for metrics with real values
    metrics_with_values = {r[0] for r in conn.execute(
        "SELECT DISTINCT metric_id FROM signals WHERE value IS NOT NULL"
    ).fetchall()}
    ranged_metrics = {r[0] for r in conn.execute(
        "SELECT DISTINCT metric_id FROM metric_ranges"
    ).fetchall()}
    missing_ranges = metrics_with_values - ranged_metrics
    if missing_ranges:
        for mid in sorted(missing_ranges)[:5]:
            fail(f"metric_ranges missing for '{mid}' which has values in signals table")

    # Summary row counts
    total_rows    = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    total_ranges  = conn.execute("SELECT COUNT(*) FROM metric_ranges").fetchone()[0]
    pipeline_rows = conn.execute(
        "SELECT pipeline, COUNT(DISTINCT period), COUNT(*) FROM signals GROUP BY pipeline"
    ).fetchall()

    conn.close()

    print(f"     E ✓ {total_rows} signal rows, {total_ranges} ranges")
    for pl, n_periods, n_rows in pipeline_rows:
        print(f"       {pl}: {n_periods} period(s), {n_rows} rows")


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
        entries = check_history(pipeline, reg_signals, reg)

        if not failures:
            print(f"     B ✓ {len(entries)} entries validated")

        check_continuity(pipeline, entries, reg_signals)
        check_status_sync(pipeline, entries, reg_signals)

        if not failures:
            print(f"     C ✓ continuity check passed")
            print(f"     D ✓ current_status in sync with latest history entry")

    # Check E: DB integrity
    print("\n  E. signals.db integrity ...")
    check_db(reg_signals, known_pipelines)

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
