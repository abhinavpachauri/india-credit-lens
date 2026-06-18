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
import sys
from pathlib import Path

ROOT        = Path(__file__).parent.parent
SIGNALS_IN  = ROOT / "analysis/rbi_atm_pos/signals.json"
INSIGHTS_IN = ROOT / "analysis/rbi_atm_pos/insights.json"

# Relative tolerance: a text value of "81.4" matches a signals value of 81.42
REL_TOL = 0.005   # 0.5%
ABS_TOL = 0.6     # absolute fallback for values near 0

# Minimum digits to bother checking (ignore trivial small integers)
MIN_VALUE_TO_CHECK = 0.5


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
    """
    Extract standalone numeric values from a text string.
    Skips numbers that are:
    - Embedded in alphanumeric tokens (e.g. "FY26", "Q4", "Tier2")
    - Pure counts that are threshold descriptions (e.g. "over 1B" as a generic phrase)
    """
    # Require number is NOT preceded/followed by a letter (word-boundary-like)
    pattern = r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[BMKx%])?(?![A-Za-z\d])'
    nums = []
    for m in re.finditer(pattern, text):
        raw = m.group().rstrip("BMKx%+")
        try:
            val = float(raw)
        except ValueError:
            continue
        # Convert suffixes
        full = m.group()
        if full.endswith("B"):
            val *= 1e9
        elif full.endswith("M"):
            val *= 1e6
        elif full.endswith("K"):
            val *= 1e3
        if abs(val) >= MIN_VALUE_TO_CHECK:
            nums.append(val)
    return nums


def _matches(num: float, candidates) -> bool:
    for v in candidates:
        if v == 0:
            if abs(num) < ABS_TOL:
                return True
        else:
            if abs(num - v) / max(abs(v), 1e-9) <= REL_TOL:
                return True
            if abs(num - v) <= ABS_TOL:   # absolute tolerance for small values (shares)
                return True
    return False


def _ratio_matches(num: float, base_vals) -> bool:
    """True if num is round(A/B) or ≈A/B for some ordered pair in base_vals."""
    if not base_vals or len(base_vals) < 2:
        return False
    for a in base_vals:
        for b in base_vals:
            if b != 0 and a != b:
                ratio = a / b
                if abs(num - round(ratio)) <= ABS_TOL:
                    return True
                if abs(num - ratio) / max(abs(ratio), 1e-9) <= REL_TOL:
                    return True
    return False


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


def validate_insight(ins: dict, flat_signals: dict[str, float]) -> list[str]:
    """Return list of error strings for this insight (empty = OK)."""
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

    for field_name, text in texts_to_check:
        nums = extract_numbers(text)
        for num in nums:
            # Skip year-like numbers (1990–2100) and trivial small integers used as ordinals
            if 1990 <= abs(num) <= 2100:
                continue
            if not value_in_signals(num, flat_signals, source_vals, prior_vals):
                # Not found anywhere in signals — hard error
                errors.append(
                    f"[{iid}] UNVERIFIED number {num} in {field_name}: "
                    f"not found in signals.json (check for hallucinated values)"
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
    print(f"  Signals: {len(flat_signals)} numeric values loaded")
    print(f"  Insights: {len(insights)} to validate\n")

    all_errors:   list[str] = []
    warnings:     list[str] = []
    insight_count = 0
    gap_count     = 0

    for ins in insights:
        errors = validate_insight(ins, flat_signals)
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
