#!/usr/bin/env python3
"""
releases.py — a saved MoSPI release, and the few facts every MoSPI stage agrees on
─────────────────────────────────────────────────────────────────────────────────
IIP and quarterly NAS carry no revision marker, and a revision overwrites the old value in place:
two fetches a month apart can disagree about the same month and nothing says so. The only record
of what MoSPI said on a given day is the release we saved that day, so a release is written before
anything reads it, and never rewritten (signals/README, "saving every release").

Stated once here, because fetch, consolidate and the two validators must agree on them:
  * where a release lives and how it is serialised (deterministic gzip, so an unchanged
    release is byte-identical and git sees no churn);
  * how a row's labels become a lookup key;
  * how a MoSPI period becomes a date (month-end, or quarter-end, the same convention as SIBC,
    so the credit join is on the date).
"""
from __future__ import annotations

import calendar
import gzip
import io
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import manifest  # noqa: E402

PIPELINE = "mospi"
MONTHS = {m: i for i, m in enumerate(calendar.month_name) if m}
QUARTER_END = {"Q1": (0, 6), "Q2": (0, 9), "Q3": (0, 12), "Q4": (1, 3)}   # (year offset, month)


def load_manifest() -> dict:
    return manifest.load(PIPELINE)


def releases_dir() -> Path:
    return manifest.path(PIPELINE, "releases")


# ── serialisation ─────────────────────────────────────────────────────────────

def canonical_rows(rows: list[dict]) -> list[dict]:
    """Rows in one order regardless of page order, so equal content is equal bytes."""
    return sorted(rows, key=lambda r: json.dumps(r, sort_keys=True, ensure_ascii=False))


def dump(doc: dict) -> bytes:
    """Deterministic gzip: fixed mtime, sorted keys. Same content → same bytes."""
    raw = json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=0).encode()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as g:
        g.write(raw)
    return buf.getvalue()


def read(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def saved(dataset: str) -> list[Path]:
    """Every saved release of a dataset, oldest first (the file name is the fetch timestamp)."""
    d = releases_dir() / dataset
    return sorted(d.glob("*.json.gz")) if d.exists() else []


# ── labels and periods ────────────────────────────────────────────────────────

def label_key(row: dict, fields: list[str]) -> str:
    """The lookup key for a row: its label fields in declared order, a missing one as ''.

    Every declared field is present in the key, including the empty ones, so "Fuel & Power ›  › "
    (the group total) and "Fuel & Power › Mineral Oils › " stay distinct.
    """
    return " › ".join("" if row.get(f) in (None, "") else str(row[f]).strip() for f in fields)


def month_end(year: int, month: int) -> str:
    return date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def period_of(row: dict, spec: dict) -> str:
    """A MoSPI period as an ISO date. Raises on anything it does not recognise."""
    if "month" in spec:
        name = str(row[spec["month"]]).strip()
        if name not in MONTHS:
            raise ValueError(f"unknown month {name!r}")
        return month_end(int(row[spec["year"]]), MONTHS[name])
    if "quarter" in spec:
        fy, q = str(row[spec["fiscal_year"]]), str(row[spec["quarter"]])
        if q not in QUARTER_END or len(fy) != 7 or fy[4] != "-":
            raise ValueError(f"unknown quarter {fy!r} {q!r}")
        off, m = QUARTER_END[q]
        return month_end(int(fy[:4]) + off, m)
    raise ValueError(f"period spec {spec!r} names neither a month nor a quarter")
