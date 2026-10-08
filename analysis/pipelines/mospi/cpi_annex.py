#!/usr/bin/env python3
"""
cpi_annex.py — the press release's own Excel annex, from MoSPI's eSankhyiki catalogue
────────────────────────────────────────────────────────────────────────────────────
Each CPI press release since Feb 2026 is published with its tables as Excel files in the
eSankhyiki data catalogue. The one read here is the table titled

    All India Combined (General) level index and inflation (Base Year : 2024=100)

which holds, in one sheet, everything the PDF reader (`cpi_release.py`) and the dashboard
workbook (`cpi_dashboard.py`) give between them:

    Month    Index                     Inflation (%)
             Rural   Urban   Combined  Rural  Urban  Combined
    Jan-25   101.81  101.49  101.67                              ← index back to Jan 2025
    ...
    Jul-26   108.34  107.45  107.95    4.84   3.96   4.45
    Aug-26*  109.27  108.07  108.74    5.23   4.31   4.82        ← * = provisional
    *Index and Inflation for the month of August 2026 are provisional.

We keep the Combined index and inflation. It is selected by that title, never by its annex number:
"Annex-IV" was a state-wise table on base 2012 until Dec 2025, and another state table in Jan 2026.

Seven releases (Feb–Aug 2026) showed how loosely the sheet is kept, and each variation is read:
the sheet's name changes, the "Annexure-IV" line is sometimes absent, a row of column numerals
"(i) … (vii)" sometimes sits under the header, a month is sometimes a date cell (March 2026), and a
number is sometimes text ("3.40"). Everything else raises: a header it does not know, a month out
of sequence, a level outside 50–300, an inflation rate that stops before the last month, or a
provisional mark on any month but the last, or one the footnote does not name.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime

import openpyxl

from releases import MONTHS, month_end

TITLE = "All India Combined (General) level index and inflation"
CATALOGUE_TITLE = re.compile(r"All India Combined \(General\) level index and inflation "
                             r"\(Base Year\s*:\s*2024\s*=\s*100\)")
SUBHEAD = ("Rural", "Urban", "Combined", "Rural", "Urban", "Combined")
MONTH_CELL = re.compile(r"([A-Z][a-z]{2})-(\d{2})(\*?)")
SHORT = {m[:3]: i for m, i in MONTHS.items()}
FOOTNOTE = re.compile(r"for the month of ([A-Z][a-z]+) (\d{4}) (?:is|are) provisional")
RELEASE_DATE = re.compile(r"(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})")


def is_the_table(table_name: str) -> bool:
    """True for the catalogue entry this module reads. The title carries the base, so an entry
    without 'Base Year : 2024=100' is never taken, whatever its annex number."""
    return CATALOGUE_TITLE.fullmatch(" ".join(table_name.split())) is not None


def published(release_date: str) -> str:
    """The catalogue's release date ("14 Sep 2026") as ISO. Releases merge in this order, so an
    entry without one raises rather than being placed by when we fetched it."""
    m = RELEASE_DATE.fullmatch(release_date.strip())
    if not m or m.group(2) not in SHORT:
        raise ValueError(f"release date {release_date!r} is not '<day> <Mon> <year>'")
    return date(int(m.group(3)), SHORT[m.group(2)], int(m.group(1))).isoformat()


def parse(data: bytes) -> list[dict]:
    rows = the_rows(data)
    head = next((i for i, r in enumerate(rows) if text(r[0]) == "Month"), None)
    if head is None or text(rows[head][1]) != "Index" or text(rows[head][4]) != "Inflation (%)":
        raise ValueError("no 'Month | Index | Inflation (%)' header")
    if tuple(text(c) for c in rows[head + 1][1:7]) != SUBHEAD:
        raise ValueError(f"the header's second line is not {SUBHEAD}")
    body = rows[head + 2:]
    if body and text(body[0][0]) == "(i)":
        body = body[1:]

    out, note = [], None
    for r in body:
        if text(r[0]).startswith("*"):
            note = text(r[0])
            break
        (year, month), starred = month_of(r[0])
        out.append({"series": "CPI (General) Combined", "base_year": "2024",
                    "period": month_end(year, month), "index": level(r[3], year, month),
                    "inflation": rate(r[6]), "status": "P" if starred else "F"})
    if not out:
        raise ValueError("the table holds no months")
    in_sequence(out)
    provisional_is_last_and_named(out, note)
    inflation_runs_to_the_end(out)
    return out


def the_rows(data: bytes) -> list[tuple]:
    """The non-empty rows of the one sheet that carries the table's title, at least 7 cells wide."""
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    found = []
    for ws in wb.worksheets:
        rows = [tuple(r) + (None,) * (7 - len(r)) for r in ws.iter_rows(values_only=True)
                if any(c not in (None, "") for c in r)]
        if any(text(r[0]) == TITLE for r in rows[:4]):
            found.append(rows)
    if len(found) != 1:
        raise ValueError(f"expected one sheet titled {TITLE!r}; found {len(found)} in "
                         f"{[w.title for w in wb.worksheets]}")
    return found[0]


def text(cell) -> str:
    return "" if cell is None else " ".join(str(cell).split())


def month_of(cell) -> tuple[tuple[int, int], bool]:
    """((year, month), provisional?) from 'Aug-26*', 'Jan-25' or a date cell."""
    if isinstance(cell, datetime):
        return (cell.year, cell.month), False
    m = MONTH_CELL.fullmatch(text(cell))
    if not m or m.group(1) not in SHORT:
        raise ValueError(f"unexpected month cell {cell!r}")
    return (2000 + int(m.group(2)), SHORT[m.group(1)]), m.group(3) == "*"


def number(cell) -> float:
    try:
        return float(text(cell))
    except ValueError:
        raise ValueError(f"not a number: {cell!r}") from None


def level(cell, year: int, month: int) -> str:
    x = number(cell)
    if not 50 < x < 300:
        raise ValueError(f"index {x} for {year}-{month:02d} is not a base-2024 level")
    return f"{x:.2f}"


def rate(cell) -> str:
    if text(cell) == "":
        return ""
    x = number(cell)
    if abs(x) >= 30:
        raise ValueError(f"inflation {x} is not a rate: are the index and inflation columns swapped?")
    return f"{x:.2f}"


def in_sequence(out: list[dict]) -> None:
    for a, b in zip(out, out[1:]):
        y, m = map(int, a["period"][:7].split("-"))
        nxt = month_end(y + m // 12, m % 12 + 1)
        if b["period"] != nxt:
            raise ValueError(f"{b['period']} follows {a['period']}: months missing or out of order")


def provisional_is_last_and_named(out: list[dict], note: str | None) -> None:
    starred = [r["period"] for r in out if r["status"] == "P"]
    if starred != [out[-1]["period"]]:
        raise ValueError(f"expected only the last month marked provisional; marked: {starred}")
    m = FOOTNOTE.search(note or "")
    if not m or m.group(1) not in MONTHS or \
            month_end(int(m.group(2)), MONTHS[m.group(1)]) != out[-1]["period"]:
        raise ValueError(f"the footnote {note!r} does not name {out[-1]['period']} as provisional")


def inflation_runs_to_the_end(out: list[dict]) -> None:
    """Inflation starts a year after the base's first month and, once started, never stops."""
    first = next((i for i, r in enumerate(out) if r["inflation"]), None)
    if first is None or any(not r["inflation"] for r in out[first:]):
        raise ValueError("the inflation column is empty or stops before the last month")
