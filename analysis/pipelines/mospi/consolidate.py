#!/usr/bin/env python3
"""
consolidate.py — MoSPI stage 0.7/0.8: saved releases → the consolidated CSV + a release log
──────────────────────────────────────────────────────────────────────────────────────────
The CSV is the single source of truth a 1f signal reads (signals/README §1f). It is rebuilt from
the committed releases alone, never from the network, so `--check` (stage 0.8) and the pre-commit
freshness guard can reproduce it exactly.

    one row per (dataset, base_year, period, code, measure), plus value and status

  * snapshot datasets (the API ones): the CSV holds the LATEST release. Every release is kept.
  * increment datasets (CPI, from press releases): each release adds a month or two, and a later
    release's value for the same key replaces an earlier one (provisional → final).

The release diff runs over every consecutive pair of releases, and sorts each difference:
  * a value changed   → a revision. News about the data, so it WARNS and is logged; never fails.
  * a key disappeared → FAILS (a snapshot only). MoSPI dropping a series or a month is not
                        something to absorb silently.
  * the latest period moved backwards → FAILS.
  * a row on another base year → FAILS. The fetch contract already refuses it; this holds for
                        releases saved before any future change to that contract.

Usage:
    python3 analysis/pipelines/mospi/consolidate.py            # write CSV + release log
    python3 analysis/pipelines/mospi/consolidate.py --check    # rebuild in memory; fail on drift
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import releases as R                                          # noqa: E402
from core import manifest                                     # noqa: E402

COLUMNS = ["dataset", "base_year", "period", "code", "measure", "value", "status"]


class ConsolidateError(Exception):
    pass


def labels() -> dict:
    return json.loads(manifest.path(R.PIPELINE, "labels").read_text())


def measures_for(ds: dict, row: dict, fields: list[str], source: str | None = None) -> dict:
    """{our measure: source field} for this row.

    A dataset fed by several publications (`sources`, CPI) reads each release with its own
    publication's map: the workbook carries no inflation column, and must not be read as one
    that left it blank. Otherwise `measures_by_label` wins on the first label field.
    """
    if source is not None and "sources" in ds:
        if source not in ds["sources"]:
            raise ConsolidateError(f"a release from undeclared source {source!r}")
        return ds["sources"][source]["measures"]
    by = ds.get("measures_by_label", {})
    return by.get(str(row.get(fields[0]) or "").strip(), ds["measures"])


def ordered(name: str, ds: dict) -> list[tuple]:
    """[(path, release)] in the order they are applied.

    Snapshots in fetch order. Increments in PUBLICATION order: the CPI workbook lags the press
    release, so a workbook fetched after the August release still describes 12 Aug, and applying it
    by fetch time would put July's provisional value back over its final one. Ties (two
    publications on one day) fall back to fetch order.
    """
    docs = [(f, R.read(f)) for f in R.saved(name)]
    if ds["release_scope"] == "snapshot":
        return docs
    for f, d in docs:
        if not d.get("published"):
            raise ConsolidateError(f"{name}: release {f.name} records no publication date")
    return sorted(docs, key=lambda fd: (fd[1]["published"], fd[0].name))


def keyed(name: str, ds: dict, doc: dict) -> dict:
    """{(label_key, period, measure): (value, status)} for one release. Blank values are skipped."""
    fields = ds["label_fields"]
    out = {}
    for row in doc["rows"]:
        # The row's OWN base, never the declaration: 1b checks the CSV's base column, and a column
        # stamped from the manifest would only ever agree with the manifest.
        if "base_year" not in row:
            raise ConsolidateError(f"{name}: a row carries no base_year of its own")
        if str(row["base_year"]) != ds["base_year"]:
            raise ConsolidateError(f"{name}: a row on base {row['base_year']!r}, "
                                   f"declared {ds['base_year']!r}")
        period = row["period"] if "period" in row else R.period_of(row, ds["period"])
        lk = R.label_key(row, fields)
        for measure, field in measures_for(ds, row, fields, doc.get("source")).items():
            if field not in row:
                # A renamed field (`index` → `index_value`) would otherwise read as MoSPI leaving
                # every cell blank, and the whole measure would leave the CSV with all stages green.
                raise ConsolidateError(f"{name}: a row has no field {field!r} for measure "
                                       f"{measure!r}; its fields are {sorted(row)}")
            v = row[field]
            if v in (None, ""):
                continue
            key = (lk, period, measure)
            if key in out:
                raise ConsolidateError(f"{name}: {key} appears twice in one release")
            out[key] = (str(v).strip(), row.get(ds.get("status_field", ""), "") or "",
                        str(row["base_year"]))
    return out


def diff(name: str, scope: str, prev: dict, new: dict, max_revision_pct: float | None = None) -> dict:
    """What changed between two consecutive releases. Raises on the failing kinds."""
    revised = sorted(k for k in new.keys() & prev.keys() if new[k][0] != prev[k][0])
    if max_revision_pct is not None:
        for k in revised:
            a, b = float(prev[k][0]), float(new[k][0])
            if a and abs(b - a) / abs(a) * 100 > max_revision_pct:
                raise ConsolidateError(f"{name}: {k} moved {a} → {b}, beyond the declared "
                                       f"{max_revision_pct}% revision: a different series or base?")
    gone = sorted(prev.keys() - new.keys())
    if scope == "snapshot" and gone:
        raise ConsolidateError(f"{name}: {len(gone)} key(s) disappeared from the newer release, "
                               f"e.g. {gone[:3]}")
    last_prev = max(k[1] for k in prev)
    last_new = max(k[1] for k in new)
    if last_new < last_prev:
        raise ConsolidateError(f"{name}: latest period moved backwards ({last_prev} → {last_new})")
    return {"revised": len(revised), "revised_sample": [list(k) for k in revised[:5]],
            "new_keys": len(new.keys() - prev.keys())}


def build() -> tuple[str, str, list[str]]:
    """(csv text, release-log json text, warnings). Pure: reads committed files only."""
    man, lab = R.load_manifest(), labels()
    records, log, warnings = [], {}, []
    for name, ds in man["datasets"].items():
        releases = ordered(name, ds)
        if not releases:
            raise ConsolidateError(f"{name}: no saved release under {R.releases_dir() / name}")
        scope, current, entries, prev = ds["release_scope"], {}, [], None
        for f, doc in releases:
            k = keyed(name, ds, doc)
            if not k:
                raise ConsolidateError(f"{name}: release {f.name} holds no values")
            entry = {"release": f.name, "rows": len(doc["rows"]), "values": len(k),
                     "periods": [min(x[1] for x in k), max(x[1] for x in k)]}
            for field in ("source", "published", "source_file"):
                if doc.get(field):
                    entry[field] = doc[field]
            if prev is not None:
                d = diff(name, scope, prev if scope == "snapshot" else current, k,
                         ds.get("max_revision_pct"))
                entry.update(d)
                if d["revised"]:
                    warnings.append(f"{name}: {d['revised']} value(s) revised in {f.name}, "
                                    f"e.g. {d['revised_sample'][:2]}")
            current = k if scope == "snapshot" else {**current, **k}
            prev = k
            entries.append(entry)
        log[name] = {"scope": scope, "base_year": ds["base_year"], "releases": entries}
        codes = lab[name]
        for (lk, period, measure), (value, status, base) in current.items():
            if lk not in codes:
                raise ConsolidateError(f"{name}: unknown label {lk!r}; add it to labels.json "
                                       f"(a new MoSPI label is a decision, never auto-mapped)")
            records.append([name, base, period, codes[lk], measure,
                            repr(float(value)), status])
    records.sort()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    w.writerows(records)
    return buf.getvalue(), json.dumps(log, indent=2, ensure_ascii=False) + "\n", warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--check", action="store_true", help="fail if the committed files are stale")
    args = ap.parse_args()
    try:
        csv_text, log_text, warnings = build()
    except (ConsolidateError, ValueError, KeyError) as e:
        print(f"  ✗ {e}", file=sys.stderr)
        return 1
    for w in warnings:
        print(f"  ⚠ revision: {w}")
    targets = {manifest.path(R.PIPELINE, "consolidated_csv"): csv_text,
               manifest.path(R.PIPELINE, "release_log"): log_text}
    n = csv_text.count("\n") - 1
    if args.check:
        stale = [p.name for p, text in targets.items() if not p.exists() or p.read_text() != text]
        if stale:
            print(f"  ✗ stale: {', '.join(stale)}; run consolidate.py", file=sys.stderr)
            return 1
        print(f"  ✓ consolidated CSV + release log fresh ({n} rows)")
        return 0
    for p, text in targets.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    print(f"  ✓ Wrote {n} rows → {manifest.path(R.PIPELINE, 'consolidated_csv').name} + release log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
