#!/usr/bin/env python3
"""
Stage 4d — ATM/POS Claim Validator

Validates the reasoning field in every insight:
  1. reasoning field must exist and be well-formed
  2. Every signal key in reasoning.signals must exist in signals.json
  3. Every signal value in reasoning.signals must match signals.json (within tolerance)
  4. reasoning.chain must have ≥ 2 non-empty steps

This is stricter than Stage 4c (which checks numbers against all of signals.json).
Stage 4d checks that the declared reasoning signals are real and current — guarding
against stale values or invented signal paths.

Note: Stage 4d validates the *declared* sources, not completeness. The model may
draw on additional context not listed; the guard rail is honesty at generation time.

Usage:
    python3 analysis/validate_atm_pos_claims.py
    python3 analysis/validate_atm_pos_claims.py --strict   # fail on any warning
"""

import json
import sys
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT
SIGNALS_IN  = ROOT / "analysis/rbi_atm_pos/signals.json"
INSIGHTS_IN = ROOT / "analysis/rbi_atm_pos/insights.json"
DB_PATH     = ROOT / "analysis/signals/signals.db"


def load_db_row_values(period: str) -> dict[str, float]:
    """'{metric_id}:{entity_id}' → value for the period — resolves the
    reasoning.signals keys of relational cards (representation
    'deterministic-db'), whose ground truth is signals.db (kept honest by
    Check 2f), not signals.json."""
    import sqlite3
    if not DB_PATH.exists():
        return {}
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return {f"{r[0]}:{r[1]}": r[2] for r in con.execute(
            "SELECT metric_id, entity_id, value FROM signals "
            "WHERE pipeline='atm_pos' AND period=? AND value IS NOT NULL",
            (period,)).fetchall()}
    finally:
        con.close()

REL_TOL = 0.005   # 0.5% relative tolerance for value matching
ABS_TOL = 0.6     # absolute fallback for values near zero

MIN_CHAIN_STEPS = 2


def get_signal_value(s: dict, key: str) -> float | None:
    """Traverse a dot-path key in the signals dict."""
    node = s
    for part in key.split("."):
        if isinstance(node, dict):
            node = node.get(part)
        elif isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if node is None:
            return None
    return float(node) if isinstance(node, (int, float)) and not isinstance(node, bool) else None


def values_match(declared: float, actual: float) -> bool:
    if actual == 0:
        return abs(declared) < ABS_TOL
    rel = abs(declared - actual) / max(abs(actual), 1e-9)
    return rel <= REL_TOL or abs(declared - actual) <= ABS_TOL


def validate_insight_claims(ins: dict, signals: dict,
                            db_rows: dict[str, float] | None = None) -> list[str]:
    errors   = []
    warnings = []
    iid      = ins.get("id", "?")
    is_reldb = ins.get("representation") == "deterministic-db"

    reasoning = ins.get("reasoning")

    # ── Check 1: reasoning must exist ──────────────────────────────────────────
    if not reasoning:
        errors.append(f"[{iid}] MISSING reasoning — every insight must declare its derivation chain")
        return errors

    # ── Check 2: reasoning.signals must be non-empty ───────────────────────────
    sig_list = reasoning.get("signals")
    if not sig_list:
        errors.append(f"[{iid}] EMPTY reasoning.signals — must declare at least one signal key+value")

    # ── Check 3: each signal key must exist in signals.json ───────────────────
    # ── Check 4: each signal value must match signals.json ────────────────────
    for sig in (sig_list or []):
        key      = sig.get("key", "")
        declared = sig.get("value")
        if not key:
            errors.append(f"[{iid}] EMPTY signal key in reasoning.signals")
            continue
        # Relational cards key their rows '{metric_id}:{entity_id}' and resolve
        # against signals.db; everything else dot-paths into signals.json.
        actual = ((db_rows or {}).get(key) if is_reldb
                  else get_signal_value(signals, key))
        if actual is None:
            errors.append(
                f"[{iid}] INVALID signal key '{key}' — not found in "
                f"{'signals.db (period rows)' if is_reldb else 'signals.json'}"
            )
        elif declared is None:
            errors.append(f"[{iid}] MISSING value for signal '{key}' in reasoning.signals")
        elif not values_match(float(declared), actual):
            errors.append(
                f"[{iid}] STALE value for '{key}': declared={declared}, actual={actual:.4f} "
                f"(diff={abs(float(declared)-actual):.4f}) — regenerate insights to refresh"
            )

    # ── Check 5: chain must have ≥ MIN_CHAIN_STEPS non-empty steps ────────────
    chain = reasoning.get("chain", [])
    non_empty = [s for s in chain if s and s.strip()]
    if len(non_empty) < MIN_CHAIN_STEPS:
        errors.append(
            f"[{iid}] SHORT chain — {len(non_empty)} step(s), need ≥ {MIN_CHAIN_STEPS}. "
            f"Chain must show: signal observation → meaning → lender action"
        )

    return errors


def main():
    strict = "--strict" in sys.argv

    print("Stage 4d — ATM/POS Claim Validator")
    print("=" * 50)

    for path, label in [(SIGNALS_IN, "signals.json"), (INSIGHTS_IN, "insights.json")]:
        if not path.exists():
            print(f"ERROR: {label} not found at {path}")
            sys.exit(1)

    with open(SIGNALS_IN)  as f: signals  = json.load(f)
    with open(INSIGHTS_IN) as f: insights = json.load(f)

    print(f"  Insights: {len(insights)} to validate\n")

    db_rows = load_db_row_values(signals["meta"]["latest_period"]) \
        if any(i.get("representation") == "deterministic-db" for i in insights) else {}

    all_errors   = []
    insight_count = sum(1 for i in insights if i.get("type") != "gap")
    gap_count     = sum(1 for i in insights if i.get("type") == "gap")

    for ins in insights:
        errors = validate_insight_claims(ins, signals, db_rows)
        itype  = ins.get("type", "insight")

        if errors:
            for e in errors:
                all_errors.append(e)
                print(f"  ✗ {e}")
        else:
            chain_len = len((ins.get("reasoning") or {}).get("chain", []))
            sig_count = len((ins.get("reasoning") or {}).get("signals", []))
            print(
                f"  ✓ {ins['id']}  [{itype} / {ins['cut']}]  "
                f"signals={sig_count}  chain={chain_len} steps"
            )

    print(f"\n─────────────────────────────────────────────────────")
    print(f"  Insights: {insight_count}  Gaps: {gap_count}  Total: {len(insights)}")

    if all_errors:
        print(f"\n  FAILED — {len(all_errors)} error(s)")
        sys.exit(1)
    else:
        print(f"\n  ALL CLEAR — {len(insights)} insights claim-validated ✓")
        print(f"  (Stage 4d verifies declared signal keys exist and values are current)")


if __name__ == "__main__":
    main()
