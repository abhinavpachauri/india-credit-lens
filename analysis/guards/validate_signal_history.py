#!/usr/bin/env python3
"""
Check 2e: Signal history integrity validation.

Validates:
  A. registry.json schema — required fields, valid status values, known pipelines/domains
  B. signals.db integrity — tables present, layer-1 metrics have rows, no orphaned metric_ids,
                            metric_ranges populated, registry current_status matches DB latest
  C. Continuity — every L1 compute signal in registry has at least one DB row

Exit 0 = all checks pass. Exit 1 = failures found.

Run directly or via run_evals.py / run_atm_pos_evals.py.
"""

import json
import sqlite3
import sys
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO
ANAL  = REPO / "analysis"
SIG   = ANAL / "signals"
REG   = SIG / "registry.json"
DB    = SIG / "signals.db"

VALID_STATUSES  = {"new", "active", "strengthening", "weakening", "stable", "declining", "reversed", "absent", "unknown", "pending", "retired"}
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

        # first_seen format YYYY-MM-DD (None allowed for signals not yet appended)
        fs = sig.get("first_seen")
        if fs is not None and (not isinstance(fs, str) or len(fs) != 10 or fs[4] != "-" or fs[7] != "-"):
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


# ─── Check B: signals.db integrity ───────────────────────────────────────────

def check_db(reg_signals: dict, known_pipelines: set[str]) -> sqlite3.Connection | None:
    """
    B1. DB file exists and has expected tables.
    B2. Every layer-1 compute signal has at least one row in signals table (continuity).
    B3. No orphaned metric_ids (present in DB but not registry).
    B4. metric_ranges populated for metrics that have non-null values.
    B5. registry current_status matches the latest DB row status per L1 signal.

    Returns the open connection for reuse, or None on failure.
    """
    if not DB.exists():
        fail(f"signals.db not found at {DB} — run core/generate_signal_history.py append first")
        return None

    try:
        conn = sqlite3.connect(DB)
    except Exception as e:
        fail(f"Cannot open signals.db: {e}")
        return None

    # B1: tables exist
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    for expected in ("signals", "metric_ranges", "ingestion_log"):
        if expected not in tables:
            fail(f"signals.db missing table '{expected}'")
    if "signals" not in tables:
        conn.close()
        return None

    # B2: layer-1 compute signals should have DB rows (continuity)
    compute_signals = {
        sig_id for sig_id, sig in reg_signals.items()
        if sig.get("layer") == 1 and sig.get("compute")
    }
    db_metric_ids = {r[0] for r in conn.execute(
        "SELECT DISTINCT metric_id FROM signals"
    ).fetchall()}

    # Some methods are ANOMALY-SURFACED: they emit a row only when something is
    # worth flagging, so zero rows is their honest null, not a continuity gap.
    # `sibc-services-divergence` sat as a standing WARN for months for exactly
    # this reason — verified 2026-09-09 by recompute: it examines all 10 services
    # children in every period and flags none, because the flag rule requires
    # OPPOSITE YoY signs and every services sub-sector is growing.
    #
    # But "no rows" is also what an unwired signal looks like, and this project
    # has met that costume ten times. So the null is only accepted when the
    # method is demonstrably alive somewhere: if NO signal on the method has a
    # single row anywhere in the DB, the method itself is dead and that FAILS.
    # Declared here, beside the reader, so the two cannot drift.
    ANOMALY_SURFACED = {
        "csv_sector_divergence",   # child contradicts parent — flagged rows only
        "csv_bank_divergence",     # bank contradicts its category
    }

    def method_of(sig_id: str) -> str:
        return ((reg_signals.get(sig_id, {}).get("compute") or {}).get("method", ""))

    live_methods = {
        method_of(mid) for mid in db_metric_ids if method_of(mid)
    }

    missing_from_db = compute_signals - db_metric_ids
    unexplained, honest_nulls = [], []
    for sid in sorted(missing_from_db):
        method = method_of(sid)
        if method in ANOMALY_SURFACED:
            if method in live_methods:
                honest_nulls.append(sid)          # flagged nothing; the method works
            else:
                fail(f"'{sid}' has no rows AND no signal on method '{method}' has "
                     f"any — the method is not producing, which is indistinguishable "
                     f"from an honest null unless we say so")
        else:
            unexplained.append(sid)

    for sid in unexplained[:10]:
        warn(f"Layer-1 compute signal '{sid}' has no rows in signals.db")
    if len(unexplained) > 10:
        warn(f"  ... and {len(unexplained) - 10} more layer-1 signals not in DB")
    for sid in honest_nulls:
        print(f"     B · {sid}: 0 rows — anomaly-surfaced, nothing flagged (expected)")

    # B3: orphaned metric_ids in DB not in registry
    all_reg_ids = set(reg_signals.keys())
    orphaned = db_metric_ids - all_reg_ids
    if orphaned:
        for sid in sorted(orphaned)[:5]:
            fail(f"signals.db has metric_id '{sid}' not found in registry.json")

    # B4: metric_ranges populated for metrics with real values
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

    # B5: registry current_status matches latest DB status per L1 signal
    db_latest_status: dict[str, str] = {}
    for row in conn.execute(
        """SELECT s.metric_id, s.status
           FROM signals s
           WHERE s.entity_type='aggregate' AND s.entity_id='total'
             AND s.period = (
               SELECT MAX(s2.period) FROM signals s2
               WHERE s2.metric_id=s.metric_id AND s2.pipeline=s.pipeline
             )"""
    ).fetchall():
        db_latest_status[row[0]] = row[1]

    status_mismatches = 0
    for sig_id, sig in reg_signals.items():
        if sig.get("layer") != 1:
            continue
        reg_status = sig.get("current_status", "unknown")
        db_status  = db_latest_status.get(sig_id)
        if db_status and db_status != reg_status:
            fail(
                f"Status mismatch '{sig_id}' — registry='{reg_status}', DB latest='{db_status}'"
            )
            status_mismatches += 1

    # B6: no published `alloc` may exceed the whole it is a share of
    #
    # `alloc` = 100 * delta_i / net answers "of the net new units, how many went
    # here". When entities move against each other the net shrinks toward zero
    # while the numerators do not, so one entity's share of the net can exceed
    # 100% — "of every Rs 100 of new credit, telecoms took Rs 137" is
    # arithmetically true and reads as impossible.
    #
    # `coherence_min` is what stops that reaching a card, and it is measured:
    # catch 100% (16/16 unsafe windows withheld), false rejection 7.6%, over all
    # 134 momentum windows (analysis/measure_coherence_threshold.py). But the
    # margin is thin — the highest coherence carrying an unsafe window is 0.864
    # against a threshold of 0.90 — so a new cut could land in that gap. This
    # asserts the OUTCOME the threshold exists to produce, instead of trusting
    # the threshold to keep producing it.
    impossible = conn.execute(
        """SELECT pipeline, metric_id, period, entity_id, value
           FROM signals
           WHERE entity_type='alloc' AND ABS(value) > 100.0
           ORDER BY ABS(value) DESC"""
    ).fetchall()
    for pl, mid, per, eid, val in impossible[:5]:
        fail(
            f"impossible allocation share — {mid} {per} ({pl}): "
            f"'{eid}' at {val:.1f}% of net. A share cannot exceed the whole; "
            f"coherence_min should have withheld this window."
        )

    # Summary
    total_rows   = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    total_ranges = conn.execute("SELECT COUNT(*) FROM metric_ranges").fetchone()[0]
    pipeline_rows = conn.execute(
        "SELECT pipeline, COUNT(DISTINCT period), COUNT(*) FROM signals GROUP BY pipeline"
    ).fetchall()

    print(f"     B ✓ {total_rows} signal rows, {total_ranges} ranges")
    for pl, n_periods, n_rows in pipeline_rows:
        print(f"       {pl}: {n_periods} period(s), {n_rows} rows")
    if not unexplained:
        print(f"     B ✓ continuity: all {len(compute_signals)} L1 compute signals accounted for")
    if not status_mismatches:
        print(f"     B ✓ status sync: registry matches DB latest for all L1 signals")
    if not impossible:
        n_alloc = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE entity_type='alloc'"
        ).fetchone()[0]
        print(f"     B ✓ allocation sanity: all {n_alloc} alloc shares within 100% of net")

    return conn


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

    # Check B (includes continuity + status sync, both sourced from DB)
    print("\n  B. signals.db integrity ...")
    conn = check_db(reg_signals, known_pipelines)
    if conn:
        conn.close()

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
