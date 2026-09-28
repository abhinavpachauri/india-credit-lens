#!/usr/bin/env python3
"""
cpi_dashboard.py — the CPI "download data" workbook on MoSPI's CPI page
──────────────────────────────────────────────────────────────────────
The second of CPI's two publications (the press release is the first; `cpi_release.py`). What it
adds is history: the base-2024 All-India Combined general index back to Jan 2025, which gives CPI
a year back, so stage 1c can check MoSPI's printed inflation against the index instead of waiting
for Jan 2027. What it lacks, and how each gap is covered:

  * it lags the press release (on 2026-09-28 it still ended in July), so it never decides the
    newest month: releases merge in publication order (consolidate.ordered);
  * it states no base: its rows are recorded as base 2024 because the sheet is the base-2024
    dashboard, and that claim is held to account where both publications give a month, since a
    revision beyond `max_revision_pct` fails (a 2012-base index is ~200, not ~104);
  * it states no P/F flag: MoSPI's convention is that a month is provisional in its first release
    and final from the next, so the workbook's last month is P and every earlier one F. The press
    releases state the flag for the months they cover, and agree with this (checked in the tests);
  * its cells mix text and numbers, and its year column mixes both: parsed here, once, strictly.

Everything else raises: a sheet, header, state or description it does not recognise, a month out
of sequence, or an index outside 50–300.
"""
from __future__ import annotations

import io
import re

import openpyxl

from releases import MONTHS, month_end

SHEET = "CPI Combined"
HEADER = ("Year", "Month", "State", "Description", "Combined")
FILE_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


def published(file_name: str) -> str:
    """The workbook's date, from its file name ("…Dashboard Data-12.08.2026.xlsx"), as ISO.

    The file states no date inside it; the name is the only one MoSPI gives. No date raises."""
    m = FILE_DATE.search(file_name)
    if not m:
        raise ValueError(f"no dd.mm.yyyy date in the workbook's name {file_name!r}")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def parse(data: bytes) -> list[dict]:
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheets = [ws for ws in wb.worksheets if ws.title.strip() == SHEET]
    if len(sheets) != 1:
        raise ValueError(f"expected one sheet named {SHEET!r}; found {[w.title for w in wb.worksheets]}")
    rows = [r for r in sheets[0].iter_rows(values_only=True) if any(c not in (None, "") for c in r)]
    head = next((i for i, r in enumerate(rows) if tuple(str(c).strip() for c in r[:5]) == HEADER), None)
    if head is None:
        raise ValueError(f"no header row {HEADER}")
    out = []
    for r in rows[head + 1:]:
        year, month, state, desc, value = (str(c).strip() if c is not None else "" for c in r[:5])
        if state != "ALL India" or desc != "General Index (All Groups)":
            raise ValueError(f"unexpected row {r[:5]}: only the All-India general index is read")
        if month not in MONTHS or not re.fullmatch(r"\d{4}", year):
            raise ValueError(f"unexpected period {year!r} {month!r}")
        index = float(value)
        if not 50 < index < 300:
            raise ValueError(f"index {index} for {month} {year} is not a base-2024 level")
        out.append({"series": "CPI (General) Combined", "base_year": "2024",
                    "period": month_end(int(year), MONTHS[month]), "index": f"{index:.2f}"})
    if not out:
        raise ValueError("the sheet holds no rows")
    periods = [r["period"] for r in out]
    if periods != sorted(set(periods)):
        raise ValueError("months are out of order or repeated")
    for r in out:
        r["status"] = "P" if r["period"] == periods[-1] else "F"
    return out
