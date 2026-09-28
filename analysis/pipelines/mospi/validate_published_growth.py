#!/usr/bin/env python3
"""
validate_published_growth.py — MoSPI stage 1c: our growth, computed from the level, vs MoSPI's own
─────────────────────────────────────────────────────────────────────────────────────────────────
The free ground truth, as NBFC's gate 1c: MoSPI prints a growth rate beside most levels. If our YoY
from the level disagrees with it beyond rounding, one of us has the wrong period, series or base,
and every 1f number built on the level inherits it.

What is compared is declared per dataset (`printed_growth`): the printed measure, the level it is
computed from, how many periods back a year is, and the decimals each is printed to.

Tolerance is the rounding and nothing else, derived per row rather than set as a constant: the
printed rate's own half-unit, plus how far the two rounded levels can move a ratio. For an IIP index
of 124.8 against 117.0, printed to one decimal, that is 0.05 + 100 × (0.05/117.0 + 0.05×124.8/117.0²)
≈ 0.14 pp. A fixed 0.05 would fail on correct data; a fixed 0.2 would pass a wrong month.

Population: every (dataset, code) in labels.json, each one ending in exactly one bucket:
  checked                 → compared at every period with both a printed rate and a level a year back;
  no_printed_rate         → the dataset prints none (all of WPI), or the manifest declares the
                            code as printing none (`no_printed_rate_codes`: NAS PFCE);
  no_level_a_year_back    → a level exists, but never a year back of a printed period (the first
                            year of a base; MoSPI links those across bases, we never do);
  no_level                → FAILS: the level series is missing entirely (a renamed field, a
                            truncated CSV). Kept apart from the legitimate case above, and judged
                            per printed pairing, so one pairing's comparisons cannot cover another;
and the stage FAILS if it checked zero values, if any compared value misses, if a code has a level in
the latest period but no printed rate there, or if printed rates are missing where a level a year
back exists beyond `printed_rate_missing_max`. The NBFC version printed ✓ on zero checks; this one
cannot. (The population narrows to the concordance's codes in phase 2; checking every code is the
stronger check meanwhile.)
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import releases as R                                          # noqa: E402
import consolidate as C                                       # noqa: E402
from validate_csv import STEP_MONTHS, next_period             # noqa: E402
from core import manifest                                     # noqa: E402


def back(period: str, n: int, step: int) -> str:
    """The period n steps before `period` (step in months)."""
    y, m = int(period[:4]), int(period[5:7]) - n * step
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return R.month_end(y, m)


def tolerance(cur: float, prev: float, printed_dec: int, operand_dec: int) -> float:
    half_p, half_o = 0.5 * 10 ** -printed_dec, 0.5 * 10 ** -operand_dec
    return half_p + 100 * (half_o / abs(prev) + half_o * abs(cur) / prev ** 2)


def check(rows: list[dict], man: dict, lab: dict) -> tuple[list[str], Counter, int, int]:
    series: dict[tuple, dict[str, float]] = {}
    for r in rows:
        series.setdefault((r["dataset"], r["code"], r["measure"]), {})[r["period"]] = float(r["value"])
    errs, buckets, compared, missing = [], Counter(), 0, 0
    for name, ds in man["datasets"].items():
        step = STEP_MONTHS[ds["cadence"]]
        latest = max((p for k, ps in series.items() if k[0] == name for p in ps), default="")
        first = min((p for k, ps in series.items() if k[0] == name for p in ps), default="")
        for code in sorted(set(lab[name].values())):
            if not ds["printed_growth"] or code in ds.get("no_printed_rate_codes", []):
                buckets[f"{name}:no_printed_rate"] += 1
                continue
            pairing_states = []
            for pg in ds["printed_growth"]:
                levels = series.get((name, code, pg["computed_from"]), {})
                printed = series.get((name, code, pg["printed"]), {})
                if not levels:
                    errs.append(f"{name}: {code} has no {pg['computed_from']} at all, so its "
                                f"{pg['printed']} cannot be checked (not a first-year absence)")
                    pairing_states.append("no_level")
                    continue
                if min(levels) > first:
                    errs.append(f"{name}: {code} {pg['computed_from']} starts {min(levels)}, after "
                                f"the dataset's first period {first}: a truncated level is not "
                                f"the first year of a base")
                for p in sorted(printed.keys() - levels.keys()):
                    errs.append(f"{name}: {code} prints {pg['printed']} for {p} with no "
                                f"{pg['computed_from']} that period")
                if latest in levels and latest not in printed:
                    errs.append(f"{name}: {code} has {pg['computed_from']} for {latest} but no "
                                f"{pg['printed']} (a current printed value is missing)")
                n_before = compared
                for p, cur in sorted(levels.items()):
                    prev = levels.get(back(p, pg["lag_periods"], step))
                    if prev is None:
                        continue
                    if p not in printed:
                        missing += 1
                        continue
                    ours = 100 * (cur / prev - 1)
                    tol = tolerance(cur, prev, pg["printed_decimals"], pg["operand_decimals"])
                    compared += 1
                    if abs(ours - printed[p]) > tol:
                        errs.append(f"{name}: {code} {pg['printed']} {p}: MoSPI {printed[p]:.2f}, "
                                    f"ours {ours:.3f} (tolerance {tol:.3f})")
                # Zero compared with levels present means no level a year back exists: the one
                # legitimate absence (the first year of a base). Counted per PAIRING, so one
                # pairing's comparisons cannot stand in for another's.
                pairing_states.append("checked" if compared > n_before else "no_level_a_year_back")
            state = ("no_level" if "no_level" in pairing_states else
                     "no_level_a_year_back" if "no_level_a_year_back" in pairing_states else "checked")
            buckets[f"{name}:{state}"] += 1
    if missing > man.get("printed_rate_missing_max", 0):
        errs.append(f"{missing} printed rate(s) missing where a level a year back exists "
                    f"(allowed: {man.get('printed_rate_missing_max', 0)})")
    if compared == 0:
        errs.append("zero values compared: this stage checked nothing, which is a failure")
    return errs, buckets, compared, missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.parse_args()
    with manifest.path(R.PIPELINE, "consolidated_csv").open() as f:
        rows = list(csv.DictReader(f))
    errs, buckets, compared, missing = check(rows, R.load_manifest(), C.labels())
    print("  · " + " · ".join(f"{k} {v}" for k, v in sorted(buckets.items())))
    for e in errs[:25]:
        print(f"  ✗ {e}", file=sys.stderr)
    if len(errs) > 25:
        print(f"  ✗ … and {len(errs) - 25} more", file=sys.stderr)
    if errs:
        return 1
    print(f"  ✓ {compared} values checked against MoSPI's printed rate, all within rounding")
    return 0


if __name__ == "__main__":
    sys.exit(main())
