#!/usr/bin/env python3
"""
detect_format.py — gate stage 0: has RBI changed the statement?

Three releases, one format. That is a sample of three, and the fourth release is the real
test — so this stage is deliberately LOUD rather than tolerant. Every finding it reports is
a thing that would otherwise be absorbed silently: a dropped sector becomes a sector that
simply stops having values, a renamed one becomes a new entity with no history, and a
re-indented row becomes a child of the wrong parent.

The extractor already refuses a file whose codes and indentation disagree, or that has lost
its total. This stage asks the different question — not "can I read it?" but "is it the same
statement as last time?" — and answers it against the most recent release we already hold.

    python3 analysis/pipelines/nbfc/detect_format.py {xlsx}     # compare a new file
    python3 analysis/pipelines/nbfc/detect_format.py --check    # re-check what is ingested
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from pipelines.nbfc.extract_nbfc import parse                          # noqa: E402

DATA_DIR = ROOT / "analysis" / "rbi_nbfc"


def shape(doc: dict) -> dict:
    return {
        "statement": doc["statement"],
        "dated_columns": len(doc["dates"]),
        "sectors": {s["code"]: s["sector"] for s in doc["sectors"]},
        "parents": {s["code"]: s["parent_code"] for s in doc["sectors"]},
    }


def compare(new: dict, ref: dict, ref_period: str) -> list[str]:
    findings = []
    if new["statement"] != ref["statement"]:
        findings.append(f"statement title changed:\n      was: {ref['statement']}\n"
                        f"      now: {new['statement']}")
    if new["dated_columns"] != ref["dated_columns"]:
        findings.append(f"dated columns {ref['dated_columns']} → {new['dated_columns']} — "
                        f"the release's own history window changed shape")
    gone = set(ref["sectors"]) - set(new["sectors"])
    added = set(new["sectors"]) - set(ref["sectors"])
    if gone:
        findings.append(f"sector code(s) DROPPED vs {ref_period}: "
                        + ", ".join(f"{c} ({ref['sectors'][c]})" for c in sorted(gone)))
    if added:
        findings.append(f"sector code(s) ADDED vs {ref_period}: "
                        + ", ".join(f"{c} ({new['sectors'][c]})" for c in sorted(added)))
    for c in sorted(set(new["sectors"]) & set(ref["sectors"])):
        if new["sectors"][c] != ref["sectors"][c]:
            findings.append(f"{c} renamed: {ref['sectors'][c]!r} → {new['sectors'][c]!r} "
                            f"— a rename orphans the entity's history")
        if new["parents"][c] != ref["parents"][c]:
            findings.append(f"{c} moved parent: {ref['parents'][c]} → {new['parents'][c]} "
                            f"— it now decomposes a different cut")
    return findings


def latest_ingested(before: str | None = None) -> tuple[dict, str] | tuple[None, None]:
    periods = sorted(p.name for p in DATA_DIR.glob("*/") if (p / "sections.json").exists())
    if before:
        periods = [p for p in periods if p < before]
    if not periods:
        return None, None
    return json.loads((DATA_DIR / periods[-1] / "sections.json").read_text()), periods[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("xlsx", type=Path, nargs="?")
    ap.add_argument("--check", action="store_true",
                    help="re-check every ingested release against the one before it")
    a = ap.parse_args()

    if a.check:
        periods = sorted(p.name for p in DATA_DIR.glob("*/")
                         if (p / "sections.json").exists())
        if len(periods) < 2:
            print(f"✓ {len(periods)} release(s) ingested — nothing to compare yet")
            return 0
        problems = 0
        for prev, cur in zip(periods, periods[1:]):
            new = json.loads((DATA_DIR / cur / "sections.json").read_text())
            ref = json.loads((DATA_DIR / prev / "sections.json").read_text())
            found = compare(shape(new), shape(ref), prev)
            for f in found:
                print(f"  ✗ {cur}: {f}")
            problems += len(found)
        if problems:
            print(f"\n✗ {problems} format change(s) across {len(periods)} releases")
            return 1
        print(f"✓ format stable across all {len(periods)} ingested releases "
              f"({periods[0]} … {periods[-1]})")
        return 0

    if not a.xlsx:
        ap.error("give an xlsx, or --check")
    new = parse(a.xlsx)
    ref, ref_period = latest_ingested(before=new["period"])
    if ref is None:
        print(f"✓ {a.xlsx.name}: first release for this source — nothing to compare against. "
              f"{len(new['sectors'])} sectors, {len(new['dates'])} dated columns.")
        return 0
    found = compare(shape(new), shape(ref), ref_period)
    for f in found:
        print(f"  ✗ {f}")
    if found:
        print(f"\n✗ {a.xlsx.name} differs in shape from {ref_period}. Read the findings "
              f"before ingesting — a silently absorbed change misattributes history.")
        return 1
    print(f"✓ {a.xlsx.name}: same shape as {ref_period} — "
          f"{len(new['sectors'])} sectors, {len(new['dates'])} dated columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
