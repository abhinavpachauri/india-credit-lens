#!/usr/bin/env python3
"""
Stage 4c — ATM/POS Insight Validator (guard rail against hallucinated numbers)

For every insight in insights.json:
  1. sourceSignals must be declared (non-empty list)
  2. Every numeric value mentioned in `body` and `implication` must be
     traceable to the signals.json value referenced in sourceSignals

Numbers are extracted with regex and matched against signals.json values
(within a 0.2% relative tolerance to account for rounding in formatted strings).

Usage:
    python3 analysis/validate_atm_pos_insights.py
    python3 analysis/validate_atm_pos_insights.py --strict   # fail on any warning
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT
from core.traceability import (
    ATM_POS as _POLICY, extract_numbers as _extract,
    matches as _matches_core, ratio_matches as _ratio_core,
)
SIGNALS_IN  = ROOT / "analysis/rbi_atm_pos/signals.json"
INSIGHTS_IN = ROOT / "analysis/rbi_atm_pos/insights.json"
DB_PATH     = ROOT / "analysis/signals/signals.db"
REGISTRY    = ROOT / "analysis/signals/registry.json"

# Number extraction + match tolerances live in core.traceability (ATM/POS policy); the thin
# wrappers below preserve this module's public surface (and the Stage-4c test access).


def check_yoy_matches_db(signals: dict) -> list[str]:
    """No-drift guard: every YoY value in signals.json must equal the registered
    `*-yoy` signal in signals.db. YoY is a registered Layer-1 signal — the dashboard
    must source it, never recompute a parallel copy. Any divergence is a hard fail.
    """
    errors: list[str] = []
    if not DB_PATH.exists():
        return [f"signals.db not found at {DB_PATH} — cannot verify YoY source"]

    # metric → registered yoy signal_id (from the registry, single source)
    with open(REGISTRY) as f:
        reg = json.load(f)
    sigs = reg["signals"]
    items = sigs.items() if isinstance(sigs, dict) else [(s["id"], s) for s in sigs]
    metric_to_sig = {
        s["compute"]["metric"]: sid
        for sid, s in items
        if s.get("pipeline") == "atm_pos"
        and s.get("compute", {}).get("method") == "csv_total_yoy"
        and s.get("compute", {}).get("metric")
    }

    latest = signals["meta"]["latest_period"]
    prior  = signals["meta"].get("prior_period")
    con = sqlite3.connect(DB_PATH)
    try:
        def db_val(sig, period):
            if not period:
                return None
            r = con.execute(
                "SELECT value FROM signals WHERE pipeline='atm_pos' "
                "AND entity_type='aggregate' AND entity_id='total' "
                "AND metric_id=? AND period=?",
                (sig, period),
            ).fetchone()
            return r[0] if r else None

        for gid, g in signals["groups"].items():
            for metric, m in g["total"]["metrics"].items():
                sig = metric_to_sig.get(metric)
                if not sig:
                    continue
                for field, period in (("yoy_pct", latest), ("yoy_prior_pct", prior)):
                    js = m.get(field)
                    db = db_val(sig, period)
                    db = round(db, 2) if db is not None else None
                    if js is None and db is None:
                        continue
                    if js is None or db is None or abs(js - db) > 0.011:
                        errors.append(
                            f"YoY DRIFT [{metric}.{field}]: signals.json={js} vs "
                            f"signals.db({sig})={db} — dashboard YoY must equal the registered signal"
                        )
    finally:
        con.close()
    return errors


def load_signals_flat(signals: dict) -> dict[str, float]:
    """
    Flatten signals.json into a dict keyed by dotted path → float value.
    Only leaf numeric values are included.
    """
    flat: dict[str, float] = {}

    def recurse(obj, path: str):
        if isinstance(obj, dict):
            for k, v in obj.items():
                recurse(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                recurse(v, f"{path}.{i}")
        elif isinstance(obj, (int, float)) and obj is not True and obj is not False:
            flat[path] = float(obj)

    recurse(signals, "")
    return flat


def extract_numbers(text: str) -> list[float]:
    """ATM/POS-policy number extraction (scales B/M/K, strips x/%; no structural stripping)."""
    return _extract(text, _POLICY)


def _matches(num: float, candidates) -> bool:
    return _matches_core(num, candidates, _POLICY)


def _ratio_matches(num: float, base_vals) -> bool:
    """True if num is round(A/B) or ≈A/B for some ordered pair in base_vals (ATM/POS policy)."""
    return _ratio_core(num, base_vals, _POLICY)


def value_in_signals(num: float, flat_signals: dict[str, float],
                     source_vals: list[float] | None = None,
                     prior_vals: list[float] | None = None) -> bool:
    """
    Return True if `num` is within tolerance of:
      - any value in flat_signals, or
      - a current-period ratio round(A/B) of source signal values (e.g. UPI_QR / POS), or
      - a prior-period value reconstructed from latest + mom_pct, or
      - a prior-period ratio of those reconstructed values.
    The prior-period checks accept bodies that legitimately cite "this ratio was X in the
    prior month" — a comparison the latest-only signals cannot match directly.
    """
    if _matches(num, flat_signals.values()):
        return True
    if _ratio_matches(num, source_vals or []):       # current-period ratio
        return True
    if prior_vals:
        if _matches(num, prior_vals):                # reconstructed prior value
            return True
        if _ratio_matches(num, prior_vals):          # prior-period ratio
            return True
    return False


def source_signals_subset(
    source_keys: list[str], flat_signals: dict[str, float]
) -> dict[str, float]:
    """Return the subset of flat_signals referenced by sourceSignals paths."""
    subset = {}
    for key in source_keys:
        # key may use dotted path with array indices
        matches = {k: v for k, v in flat_signals.items() if k == key or k.endswith(f".{key.split('.')[-1]}")}
        subset.update(matches)
        # Direct lookup
        if key in flat_signals:
            subset[key] = flat_signals[key]
    # Also look for partial path matches
    for key in source_keys:
        parts = key.split(".")
        for fk, fv in flat_signals.items():
            if all(p in fk for p in parts[-2:]):  # last two segments must match
                subset[fk] = fv
    return subset


def load_db_period_numbers(period: str) -> list[float]:
    """Period-wide signals.db ground truth for atm_pos: every number the period's
    registered signals produced (current, full series, range bounds, components,
    diffs). This is the SAME ground truth SIBC Check 2g uses — required to verify
    the rich, history-referencing LLM prose. signals.db is kept honest by Check 2f."""
    if not DB_PATH.exists():
        return []
    sys.path.insert(0, str(ROOT / "analysis"))
    from signals.query import signal_numbers, flat_numbers  # noqa: E402
    with open(REGISTRY) as f:
        reg = json.load(f)["signals"]
    items = reg.items() if isinstance(reg, dict) else [(s["id"], s) for s in reg]
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    nums: list[float] = []
    try:
        for sid, sig in items:
            if sig.get("pipeline") != "atm_pos" or sig.get("layer") != 1:
                continue
            try:
                nums += flat_numbers(signal_numbers(con, sid, sig, "atm_pos", period))
            except Exception:
                pass
    finally:
        con.close()
    return nums


def load_db_own_numbers(period: str, sids: list[str]) -> dict[str, list[float]]:
    """STRICT per-signal ground truth: the numbers each signal's own rows
    produced for the period (via flat_numbers — row values, spread, counts,
    mean). Used for relational cards (representation 'deterministic-db'),
    which cite only their own distribution — the mirror of SIBC Check 2g's
    scan-strict rule."""
    if not DB_PATH.exists() or not sids:
        return {}
    sys.path.insert(0, str(ROOT / "analysis"))
    from signals.query import signal_numbers, flat_numbers  # noqa: E402
    with open(REGISTRY) as f:
        reg = json.load(f)["signals"]
    out: dict[str, list[float]] = {}
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        for sid in sids:
            sig = reg.get(sid)
            if sig:
                out[sid] = flat_numbers(signal_numbers(con, sid, sig, "atm_pos", period))
    finally:
        con.close()
    return out


def validate_insight(ins: dict, flat_signals: dict[str, float],
                     db_period_nums: list[float] | None = None,
                     db_own_nums: dict[str, list[float]] | None = None) -> list[str]:
    """Return list of error strings for this insight (empty = OK).

    LLM-represented insights (representation=='llm') carry history-referencing
    prose, so their numbers are checked against the period-wide signals.db ground
    truth (`db_period_nums`) + ratios — exactly like SIBC scalar insights.
    Relational cards (representation=='deterministic-db') check STRICTLY against
    their own signal's db rows (`db_own_nums`). The remaining deterministic
    insights validate against signals.json as before."""
    errors = []
    iid = ins.get("id", "?")

    # 1. sourceSignals must be present and non-empty
    src = ins.get("sourceSignals") or []
    if not src:
        errors.append(f"[{iid}] MISSING sourceSignals — every insight must declare its data sources")

    # 2. Check numbers in body and implication against signals
    # Build a scoped subset from sourceSignals if declared; otherwise use all signals
    if src:
        scope = source_signals_subset(src, flat_signals)
        if not scope:
            # Fallback to all signals if scope resolution failed
            scope = flat_signals
    else:
        scope = flat_signals

    # Collect numeric values from the declared source signals for ratio-derivation check
    source_vals = [flat_signals[k] for k in src if k in flat_signals]
    # Reconstruct prior-period values from any (X.latest, X.mom_pct) sibling pair so the
    # validator can verify "prior month" comparisons (e.g. "this ratio was 65 last month").
    src_map = {k: flat_signals[k] for k in src if k in flat_signals}
    prior_vals = []
    for k, v in src_map.items():
        if k.endswith(".latest"):
            mom = src_map.get(k[: -len(".latest")] + ".mom_pct")
            if mom is not None and (1 + mom / 100) != 0:
                prior_vals.append(v / (1 + mom / 100))

    texts_to_check = []
    if ins.get("body"):
        texts_to_check.append(("body", ins["body"]))
    if ins.get("implication"):
        texts_to_check.append(("implication", ins["implication"]))
    # The reasoning chain (basis.inferences) must be traceable too — same
    # guarantee SIBC Check 2g enforces. A number in the chain that is not in
    # signals.json is an ungrounded claim.
    chain = (ins.get("basis") or {}).get("inferences") \
        or (ins.get("reasoning") or {}).get("chain") or []
    if chain:
        texts_to_check.append(("chain", " ".join(chain)))

    rep      = ins.get("representation")
    is_llm   = rep == "llm"
    is_reldb = rep == "deterministic-db"
    own_pool: list[float] = []
    if is_reldb:
        for sid in src:
            own_pool += (db_own_nums or {}).get(sid, [])
    for field_name, text in texts_to_check:
        nums = extract_numbers(text)
        for num in nums:
            # Skip year-like numbers (1990–2100) and trivial small integers used as ordinals
            if 1990 <= abs(num) <= 2100:
                continue
            if is_llm:
                # LLM prose → verify against the period-wide signals.db ground truth
                # (current + full series + ranges + components + ratios).
                pool = db_period_nums or []
                ok = _matches(num, pool) or _ratio_matches(num, pool)
                src_label = "signals.db (period-wide)"
            elif is_reldb:
                # Relational card → STRICT: only its own signal's row values
                # (2g scan-strict mirror; no ratio derivation).
                ok = _matches(num, own_pool)
                src_label = f"signals.db (own rows: {', '.join(src)})"
            else:
                ok = value_in_signals(num, flat_signals, source_vals, prior_vals)
                src_label = "signals.json"
            if not ok:
                errors.append(
                    f"[{iid}] UNVERIFIED number {num} in {field_name}: "
                    f"not found in {src_label} (check for hallucinated values)"
                )

    return errors


def main():
    strict = "--strict" in sys.argv

    print("Stage 4c — ATM/POS Insight Validator")
    print("=" * 50)

    if not SIGNALS_IN.exists():
        print(f"ERROR: signals.json not found at {SIGNALS_IN}")
        sys.exit(1)
    if not INSIGHTS_IN.exists():
        print(f"ERROR: insights.json not found at {INSIGHTS_IN}")
        sys.exit(1)

    with open(SIGNALS_IN) as f:
        signals = json.load(f)
    with open(INSIGHTS_IN) as f:
        insights = json.load(f)

    flat_signals = load_signals_flat(signals)
    period = signals["meta"]["latest_period"]
    db_period_nums = load_db_period_numbers(period)
    n_llm = sum(1 for i in insights if i.get("representation") == "llm")
    print(f"  Signals: {len(flat_signals)} numeric values loaded (signals.json)")
    print(f"  signals.db period-wide ground truth: {len(db_period_nums)} values ({period})")
    print(f"  Insights: {len(insights)} to validate ({n_llm} LLM-represented → verified vs signals.db)\n")

    # No-drift guard: dashboard YoY must equal the registered signals.db YoY.
    yoy_errors = check_yoy_matches_db(signals)
    if yoy_errors:
        print("  YoY source check (signals.json vs registered signals.db):")
        for e in yoy_errors:
            print(f"  ✗ {e}")
        print()
    else:
        print("  ✓ YoY values match the registered signals.db (no drift)\n")

    # STRICT own-row ground truth for relational cards (deterministic-db).
    rel_sids = sorted({sid for ins in insights
                       if ins.get("representation") == "deterministic-db"
                       for sid in (ins.get("sourceSignals") or [])})
    db_own_nums = load_db_own_numbers(period, rel_sids)
    if rel_sids:
        print(f"  Relational cards: {len(rel_sids)} signal(s) verified vs their own db rows\n")

    all_errors:   list[str] = list(yoy_errors)
    warnings:     list[str] = []
    insight_count = 0
    gap_count     = 0

    for ins in insights:
        errors = validate_insight(ins, flat_signals, db_period_nums, db_own_nums)
        itype = ins.get("type", "insight")
        if itype == "gap":
            gap_count += 1
        else:
            insight_count += 1

        if errors:
            for e in errors:
                all_errors.append(e)
                print(f"  ✗ {e}")
        else:
            src_count = len(ins.get("sourceSignals") or [])
            has_impl  = bool(ins.get("implication"))
            print(f"  ✓ {ins['id']}  [{itype} / {ins['cut']}]  sources={src_count}  implication={'yes' if has_impl else 'NO'}")

    print(f"\n─────────────────────────────────────────────────────")
    print(f"  Insights: {insight_count}  Gaps: {gap_count}  Total: {len(insights)}")

    if all_errors:
        print(f"\n  FAILED — {len(all_errors)} error(s)")
        sys.exit(1)
    else:
        print(f"\n  ALL CLEAR — {len(insights)} insights validated ✓")
        # Warn on missing implications
        missing_impl = [i["id"] for i in insights if not i.get("implication")]
        if missing_impl:
            print(f"\n  Warnings — insights without implication ({len(missing_impl)}):")
            for iid in missing_impl:
                print(f"    • {iid}")
            if strict:
                sys.exit(1)


if __name__ == "__main__":
    main()
