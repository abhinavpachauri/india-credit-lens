#!/usr/bin/env python3
"""
cpi_release.py — the one MoSPI dataset read from a press release, not the API
─────────────────────────────────────────────────────────────────────────────
The CPI API holds only the 2012 base, ending Dec 2025; the 2024 base is not loaded. Until it is,
each month's press release PDF is the source. It retires the day the API serves base 2024, and it
never falls back to the API's 2012 series (a YoY across two bases is not ours to link).

What one release prints, and all this reads (the table under "A. National Level Indices"):

                     July, 2026 (Provisional)      June, 2026 (Final)
                     Rural  Urban  Combined        Rural  Urban  Combined
    Inflation  CPI (General)  4.84  3.96  4.45      4.74  3.93  4.38
    Index      CPI (General) 108.34 107.45 107.94  107.24 106.69 107.00

So one release gives two months: the current one (P) and the previous one (F). We keep the
Combined column of CPI (General), index and inflation. Every number is required: a table this
reader cannot find, or finds twice, raises rather than returning part of it.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from releases import MONTHS, month_end

MONTH_COL = re.compile(r"([A-Z][a-z]+),\s*(\d{4})\s*\((Provisional|Final)\)")
NUMBERS = re.compile(r"-?\d+\.\d+")
STATUS = {"Provisional": "P", "Final": "F"}


def pdf_text(pdf: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                             capture_output=True, text=True, check=True)
    except FileNotFoundError as e:
        raise SystemExit("✗ pdftotext not found (brew install poppler)") from e
    return out.stdout


def parse(text: str) -> list[dict]:
    """Rows for the month(s) the first national table prints. Raises on any shape it does not know.

    The first table is the one under "A. National Level Indices": a header line naming one month
    (the first release, Jan 2026) or two (every release since), then the CPI (General) inflation
    line, then the CPI (General) index line, three columns (rural, urban, combined) per month.
    The month order follows the header (Aug 2026 printed the older month first), never an
    assumption. Later sections repeat parts of it (April reprints March final), so only the first
    is read.
    """
    lines = text.splitlines()
    head = next((i for i, ln in enumerate(lines) if MONTH_COL.search(ln)
                 and general_lines(lines[i:i + 30])), None)
    if head is None:
        raise ValueError("no '<Month>, <Year> (Provisional|Final)' header before a CPI table")
    # The base is read from the page the table is on (the release title, or the table's own
    # header), not from anywhere in the document: the January release also prints a 2012-base
    # table, further down.
    page_start = max((i for i in range(head) if "\f" in lines[i]), default=0)
    page = re.sub(r"\s*=\s*", "=", "\n".join(lines[page_start:head + 1]).upper())
    if "BASE 2024=100" not in page and "BASE YEAR 2024=100" not in page:
        raise ValueError("the first CPI table is not on a base 2024=100 page")
    months = header_months(lines[head:head + 6])
    general = general_lines(lines[head:head + 30])[:2]
    if len(general) != 2:
        raise ValueError(f"expected the inflation and index lines, found {len(general)}")
    infl, index = general
    # Line order is how the table reads today; it is checked, not assumed. On base 2024=100 an index
    # sits near 100 and an inflation rate is a few percent, so a swapped pair fails here instead of
    # passing every gate until a year of base-2024 history lets 1c compare them (Jan 2027).
    if not all(50 < float(x) < 300 for x in index) or not all(abs(float(x)) < 30 for x in infl):
        raise ValueError(f"CPI lines out of place: index {index}, inflation {infl}")
    want = 3 * len(months)
    if len(infl) != want or len(index) != want:
        raise ValueError(f"{len(months)} month(s) need {want} numbers per line; "
                         f"got {len(infl)} and {len(index)}")
    out = []
    for k, (month, year, status) in enumerate(months):
        if month not in MONTHS:
            raise ValueError(f"unknown month {month!r}")
        combined = 3 * k + 2
        out.append({"series": "CPI (General) Combined", "base_year": "2024",
                    "period": month_end(int(year), MONTHS[month]),
                    "index": index[combined], "inflation": infl[combined], "status": STATUS[status]})
    if len(out) == 2 and out[0]["period"] == out[1]["period"]:
        raise ValueError("both columns name the same month")
    return out


def header_months(block: list[str]) -> list[tuple]:
    """The table's month columns, left to right, from the header block above "Rural".

    Ordered by horizontal position, not by line: Feb 2026 printed "January, 2026 (Final)" on the
    line above "February, 2026 (Provisional)" but in the right-hand column. Line order would have
    swapped the two months' numbers.
    """
    found = []
    for ln in block:
        if "Rural" in ln:
            break
        found += [(m.start(), m.groups()) for m in MONTH_COL.finditer(ln)]
    return [g for _, g in sorted(found)]


DATED = re.compile(r"Dated\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Z][a-z]+),?\s+(\d{4})")


def published(text: str) -> str:
    """The release's own date ("Dated 14th September, 2026"), as ISO. Releases merge in this
    order, so a release without one raises rather than being placed by when we read it."""
    m = DATED.search(text)
    if not m or m.group(2) not in MONTHS:
        raise ValueError("no 'Dated <day> <Month>, <Year>' line: cannot place this release")
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"


def general_lines(window: list[str]) -> list[list[str]]:
    """The number lists of the CPI (General) rows, in order, in the three layouts MoSPI has used:

        CPI (General)   4.84  3.96  4.45 ...        (most months: label and numbers on one line)

        CPI (General)                               (Feb 2026: the numbers on the next line)
        Inflation (%)   3.37  3.02  3.21 ...

        CPI                                         (Aug 2026: the label wraps around the numbers)
                        4.84  3.96  4.45 ...
        (General)
    CFPI rows are never taken: a following line that names CFPI ends the search for numbers.
    """
    out = []
    for i, ln in enumerate(window):
        if "CPI (General)" in ln:
            nums = NUMBERS.findall(ln.split("CPI (General)", 1)[1])
            if not nums:
                nxt = next((l for l in window[i + 1:i + 3] if l.strip()), "")
                nums = [] if "CFPI" in nxt else NUMBERS.findall(nxt)
            out.append(nums)
        elif ln.strip() == "CPI" and i + 2 < len(window) and "(General)" in window[i + 2] \
                and NUMBERS.findall(window[i + 1]) and not window[i + 1].strip()[:1].isalpha():
            out.append(NUMBERS.findall(window[i + 1]))
    return out
