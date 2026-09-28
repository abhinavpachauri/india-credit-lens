#!/usr/bin/env python3
"""
detect_format.py — MoSPI stage 0.5: MoSPI's labels ↔ our codes, checked in both directions
────────────────────────────────────────────────────────────────────────────────────────
MoSPI identifies a series by its LABEL ("Manufacture Of Basic Metals"), not a code, and a label can
change between releases with nothing else saying so. labels.json maps each label to a stable code
we declare (`nic:24`). This checks the newest data against that map, both ways:

  * a label the map does not know → FAIL. A renamed or new series is a decision (is it the same
    series?), never auto-mapped;
  * a mapped label with no values in the dataset's latest period → FAIL. A series that ended, or
    moved to another level, would otherwise vanish from every table that reads it.

The population is the manifest's datasets × the map's labels, never the release's own keys: an
empty or truncated release would otherwise agree with itself (signals/README, "the consolidated CSV").
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import releases as R                                          # noqa: E402
import consolidate as C                                       # noqa: E402


def current_values(name: str, ds: dict) -> dict:
    """The dataset as the CSV will hold it: the latest snapshot, or every increment merged."""
    releases = C.ordered(name, ds)
    if not releases:
        raise C.ConsolidateError(f"{name}: no saved release")
    if ds["release_scope"] == "snapshot":
        return C.keyed(name, ds, releases[-1][1])
    merged = {}
    for _, doc in releases:
        merged.update(C.keyed(name, ds, doc))
    return merged


def problems() -> tuple[list[str], int]:
    man, lab = R.load_manifest(), C.labels()
    errs, checked = [], 0
    for name, ds in man["datasets"].items():
        if name not in lab:
            errs.append(f"{name}: labels.json has no section for this dataset")
            continue
        vals = current_values(name, ds)
        latest = max(k[1] for k in vals)
        seen = {k[0] for k in vals}
        in_latest = {k[0] for k in vals if k[1] == latest}
        for lk in sorted(seen - lab[name].keys()):
            errs.append(f"{name}: unknown label {lk!r}")
        for lk, code in sorted(lab[name].items()):
            checked += 1
            if lk not in in_latest:
                errs.append(f"{name}: {code} ({lk!r}) has no value in the latest period {latest}")
    return errs, checked


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--check", action="store_true", help="(the only mode; kept for the gate's call)")
    ap.parse_args()
    try:
        errs, checked = problems()
    except (C.ConsolidateError, ValueError, KeyError) as e:
        print(f"  ✗ {e}", file=sys.stderr)
        return 1
    for e in errs:
        print(f"  ✗ {e}", file=sys.stderr)
    if errs:
        return 1
    print(f"  ✓ {checked} labels mapped, every one current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
