#!/usr/bin/env python3
"""
reader.py — one RBI "Lending and Deposit Rates of SCBs" workbook → rows, notes and the unit line
──────────────────────────────────────────────────────────────────────────────────────────────────
signals/README, "RBI lending and deposit rates". Every file carries the full history of nine tables;
the manifest names the six we read (sheet, table number, unit). What the reader refuses, rather
than guesses:
  * a sheet the manifest names and the file lacks, or a header row it cannot find;
  * a column header no label maps (a new RBI column is a decision, never auto-mapped);
  * a row label that is neither a date nor a month written as text ("July-2023" is both real and
    text, in T2 and T3): RBI labels months by their first day until Dec 2020 and by month end
    after, with stray days, so every label maps to its month's end;
  * the same month twice in one table.
Values are rounded to RBI's printed two decimals: some releases carry unrounded floats (15
decimals), and comparing those would report hundreds of revisions that are not revisions.
"""
from __future__ import annotations

import calendar
import re
import warnings
from datetime import date, datetime
from pathlib import Path

HEADER = ("End Month", "Month", "Month-End")
TEXT_MONTH = re.compile(r"^([A-Za-z]+)[-\s]+(\d{4})$")
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
MONTHS["sept"] = 9
FILE_DATE = re.compile(r"MLDRSCB(\d{2})(\d{2})(\d{4})", re.I)


class ReadError(Exception):
    pass


def published(path: Path) -> str:
    """The publication date in the file name (MLDRSCB30092026ENG.xlsx → 2026-09-30)."""
    m = FILE_DATE.search(path.name)
    if not m:
        raise ReadError(f"{path.name}: no MLDRSCB{{ddmmyyyy}} date in the file name")
    return date(int(m[3]), int(m[2]), int(m[1])).isoformat()


def month_end(y: int, m: int) -> str:
    return date(y, m, calendar.monthrange(y, m)[1]).isoformat()


def period_of(label) -> str | None:
    """The month a row label names, as its month end; None if it is not a month at all."""
    if isinstance(label, datetime):
        return month_end(label.year, label.month)
    if isinstance(label, str):
        m = TEXT_MONTH.match(label.strip())
        if m and m[1].lower() in MONTHS:
            return month_end(int(m[2]), MONTHS[m[1].lower()])
    return None


def _text(c) -> str:
    return " ".join(str(c).split())


def read_sheet(ws, labels: dict[str, str], where: str) -> tuple[list[dict], list[str], list[str]]:
    rows = list(ws.iter_rows(values_only=True))
    hi = next((i for i, r in enumerate(rows)
               if any(isinstance(c, str) and c.strip() in HEADER for c in r)), None)
    if hi is None:
        raise ReadError(f"{where}: no header row ({' / '.join(HEADER)})")
    hdr = rows[hi]
    first = next(j for j, c in enumerate(hdr) if isinstance(c, str) and c.strip() in HEADER)
    cols = {}
    for j, c in enumerate(hdr):
        if j <= first or c is None or not _text(c):
            continue
        name = _text(c)
        if name not in labels:
            raise ReadError(f"{where}: column {name!r} is not in labels.json")
        cols[j] = name
    if set(cols.values()) != set(labels):
        raise ReadError(f"{where}: columns {sorted(cols.values())}, labels.json declares {sorted(labels)}")
    heads = [_text(c) for r in rows[:hi] for c in r if isinstance(c, str) and _text(c)]
    out, notes, seen = [], [], set()
    for r in rows[hi + 1:]:
        label = r[first] if first < len(r) else None
        nums = [j for j in cols if j < len(r) and isinstance(r[j], (int, float))]
        if label is None and not nums:
            text = " ".join(_text(c) for c in r if isinstance(c, str) and _text(c))
            if text:
                notes.append(text)
            continue
        if not nums:
            if isinstance(label, str) and _text(label):
                notes.append(" ".join(_text(c) for c in r if isinstance(c, str) and _text(c)))
                continue
            raise ReadError(f"{where}: a row labelled {label!r} holds no values")
        period = period_of(label)
        if period is None:
            raise ReadError(f"{where}: row label {label!r} is not a month")
        if period in seen:
            raise ReadError(f"{where}: {period} appears twice")
        seen.add(period)
        for j in nums:
            out.append({"column": cols[j], "period": period, "value": f"{round(float(r[j]), 2):.2f}"})
    return out, notes, heads


def read(path: Path, datasets: dict, labels: dict) -> dict:
    """{"published", "datasets": {name: rows}, "notes": {name: [..]}, "heads": {name: [..]}}."""
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {"published": published(path), "datasets": {}, "notes": {}, "heads": {}}
    for name, ds in datasets.items():
        if ds["sheet"] not in wb.sheetnames:
            raise ReadError(f"{path.name}: no sheet {ds['sheet']!r} ({name})")
        rows, notes, heads = read_sheet(wb[ds["sheet"]], labels[name], f"{path.name} {ds['table']}")
        out["datasets"][name], out["notes"][name], out["heads"][name] = rows, notes, heads
    return out
