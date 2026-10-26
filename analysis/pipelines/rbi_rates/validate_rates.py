#!/usr/bin/env python3
"""
validate_rates.py — RBI rates stage 1c: footnotes, the unit line, and plausibility
───────────────────────────────────────────────────────────────────────────────────
signals/README, "RBI lending and deposit rates". RBI prints no growth rate, so there is no free
ground truth to check our reading against; these checks stand in for it.

  footnotes   every note the latest release prints, per table, is classified in notes.json, and
              every classified note is still printed (a series-break note that vanished leaves a
              declared break with no source). Both directions, so neither side can drift.
  unit        the release says "(Per cent)" and names the declared table above its header: a switch
              to basis points or a renumbered table cancels in nothing downstream.
  plausible   every level inside the dataset's declared bounds, and every move between two
              consecutive months inside its declared maximum. Months across a declared series break
              are not compared. Population: the consolidated CSV's rows of each declared dataset ×
              its declared codes (the CSV integrity stage has already held the codes to the labels).

    python3 analysis/pipelines/rbi_rates/validate_rates.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "mospi"))
import releases as R                                  # noqa: E402
from core import manifest                             # noqa: E402

PIPELINE = "rbi_rates"


def next_month(p: str) -> str:
    y, m = int(p[:4]), int(p[5:7]) + 1
    return R.month_end(y + (m - 1) // 12, (m - 1) % 12 + 1)


def breaks(notes: dict, name: str) -> set[str]:
    return {v["effective"] for v in notes["notes"].get(name, {}).values() if v["kind"] == "series_break"}


def check_notes(man: dict, notes: dict) -> tuple[list[str], int]:
    errs, n = [], 0
    for name, ds in man["datasets"].items():
        saved = R.saved(name)
        if not saved:
            errs.append(f"{name}: no saved release")
            continue
        doc = R.read(saved[-1])
        declared = notes["notes"].get(name, {})
        for t in doc["notes"]:
            n += 1
            if t not in declared:
                errs.append(f"{name}: unclassified footnote {t!r}: add it to notes.json with its handling")
        for t in sorted(set(declared) - set(doc["notes"])):
            errs.append(f"{name}: notes.json declares {t!r}, which the latest release no longer prints")
        for k, v in declared.items():
            if v["kind"] not in notes["kinds"]:
                errs.append(f"{name}: footnote kind {v['kind']!r} is not declared in notes.json kinds")
        if ds["unit"] not in doc["heads"]:
            errs.append(f"{name}: the release does not say {ds['unit']}; heads {doc['heads']}")
        if not any(h.replace(" ", "").startswith(ds["table"].replace(" ", "") + ":") for h in doc["heads"]):
            errs.append(f"{name}: no '{ds['table']}:' title above the header; heads {doc['heads']}")
    return errs, n


def check_plausible(rows: list[dict], man: dict, notes: dict) -> tuple[list[str], int]:
    errs, n = [], 0
    for name, ds in man["datasets"].items():
        b = ds["plausible"]
        skip = breaks(notes, name)
        series: dict[str, dict[str, float]] = {}
        for r in rows:
            if r["dataset"] == name:
                series.setdefault(r["code"], {})[r["period"]] = float(r["value"])
        for code, s in sorted(series.items()):
            for p, v in sorted(s.items()):
                n += 1
                if not b["min"] <= v <= b["max"]:
                    errs.append(f"{name}: {code} {p} = {v}, outside {b['min']}–{b['max']}%")
                q = next_month(p)
                if q in s and q not in skip:
                    move = s[q] - v
                    if abs(move) > b["max_monthly_move_pp"]:
                        errs.append(f"{name}: {code} {p} → {q} moved {move:+.2f} pp, beyond the declared "
                                    f"{b['max_monthly_move_pp']} pp")
    return errs, n


def main() -> int:
    R.use(PIPELINE)
    man = R.load_manifest()
    notes = json.loads(manifest.path(PIPELINE, "notes").read_text())
    with manifest.path(PIPELINE, "consolidated_csv").open() as f:
        rows = list(csv.DictReader(f))
    e1, n1 = check_notes(man, notes)
    e2, n2 = check_plausible(rows, man, notes)
    for e in e1 + e2:
        print(f"  ✗ {e}", file=sys.stderr)
    if e1 or e2:
        return 1
    print(f"  ✓ {n1} footnotes classified, unit and table checked; {n2} values checked for plausibility")
    return 0


if __name__ == "__main__":
    sys.exit(main())
