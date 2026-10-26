#!/usr/bin/env python3
"""
fetch.py — save RBI rates workbooks as releases (stage 0, by hand until two clean cycles)
──────────────────────────────────────────────────────────────────────────────────────────
signals/README, "RBI lending and deposit rates". The user downloads the month's file from RBI; this
reads it (`reader.py`) and saves, per dataset, `releases/{dataset}/{published}T000000Z.json.gz`
with the rows, the footnotes and the unit line, and the raw workbook once under `releases/raw/`.

Releases are ordered by the publication date in the file name, never by when they were saved:
  * a file published on a date already saved, with the same rows → `duplicate`, nothing written;
    with different rows → raises (RBI re-issued a file: a decision, not an overwrite);
  * a file older than the latest saved release → raises (it would read as a revision back in time).

    python3 analysis/pipelines/rbi_rates/fetch.py --xlsx MLDRSCB30092026ENG.xlsx [more files…]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "mospi"))
import reader                                         # noqa: E402
import releases as R                                  # noqa: E402

PIPELINE = "rbi_rates"


def save(path: Path) -> list[str]:
    R.use(PIPELINE)
    man = R.load_manifest()
    labels = json.loads((HERE / "labels.json").read_text())
    got = reader.read(path, man["datasets"], labels)
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    fetched = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out = []
    for name, ds in man["datasets"].items():
        doc = {"dataset": name, "base_year": None, "scope": ds["release_scope"], "source": "release_xlsx",
               "published": got["published"], "fetched": fetched, "source_file": path.name, "sha256": sha,
               "notes": got["notes"][name], "heads": got["heads"][name],
               "rows": R.canonical_rows(got["datasets"][name])}
        prior = [R.read(p) for p in R.saved(name)]
        latest = max((d["published"] for d in prior), default="")
        same_day = [d for d in prior if d["published"] == doc["published"]]
        if same_day:
            if same_day[-1]["rows"] != doc["rows"]:
                raise SystemExit(f"✗ {name}: a release published {doc['published']} is saved with other "
                                 f"rows; RBI re-issued the file? Decide before overwriting anything.")
            out.append(f"{name}: duplicate of the {doc['published']} release, nothing written")
            continue
        if doc["published"] < latest:
            raise SystemExit(f"✗ {name}: {path.name} ({doc['published']}) is older than the latest saved "
                             f"release ({latest}); save releases oldest first")
        target = R.releases_dir() / name / f"{doc['published']}T000000Z.json.gz"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(R.dump(doc))
        out.append(f"{name}: saved {target.name} ({len(doc['rows'])} rows)")
    rawdir = R.releases_dir() / "raw"
    rawdir.mkdir(parents=True, exist_ok=True)
    if not (rawdir / path.name).exists():
        (rawdir / path.name).write_bytes(raw)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--xlsx", type=Path, nargs="+", required=True)
    a = ap.parse_args()
    for f in sorted(a.xlsx, key=lambda p: reader.published(p)):
        for line in save(f):
            print(f"  ✓ {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
