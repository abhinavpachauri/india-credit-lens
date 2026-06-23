#!/usr/bin/env python3
"""
Golden tests for the SIBC date-normalisation remap (update_web_data._canonical_month_end).

This is the most dangerous untested logic in the pipeline: RBI publishes the fortnightly
Bank Credit figure on the first Friday *after* a month-end, which can land in the next
month (Apr 4–5 = March data; May 2–3 = April data). A wrong remap silently shifts a whole
period's numbers onto the wrong month-end, corrupting every downstream signal. It was
human-gated only — these pin every documented rule + the off-by-one boundaries.

Run: python3 -m pytest analysis/tests/test_date_normalization.py -q
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import update_web_data as uwd  # noqa: E402

cme = uwd._canonical_month_end


@pytest.mark.parametrize("raw, expected", [
    # Apr 1–7 → Mar 31 (post-FY-end Bank Credit release = March data)
    (date(2024, 4, 5), date(2024, 3, 31)),
    (date(2025, 4, 4), date(2025, 3, 31)),
    (date(2024, 4, 1), date(2024, 3, 31)),
    (date(2024, 4, 7), date(2024, 3, 31)),     # inclusive upper boundary
    # May 1–7 → Apr 30 (post-April Bank Credit release = April data)
    (date(2024, 5, 3), date(2024, 4, 30)),
    (date(2025, 5, 2), date(2025, 4, 30)),
    (date(2024, 5, 7), date(2024, 4, 30)),     # inclusive upper boundary
    # generic intra-month snapshot → same month-end
    (date(2024, 3, 22), date(2024, 3, 31)),
    (date(2025, 3, 21), date(2025, 3, 31)),
    (date(2024, 1, 26), date(2024, 1, 31)),
    # February leap vs non-leap
    (date(2024, 2, 23), date(2024, 2, 29)),    # 2024 leap
    (date(2025, 2, 21), date(2025, 2, 28)),    # 2025 non-leap
    # already canonical
    (date(2026, 3, 31), date(2026, 3, 31)),
])
def test_canonical_month_end(raw, expected):
    assert cme(raw) == expected


def test_april_boundary_off_by_one():
    # Apr 7 is still post-FY (→ Mar 31); Apr 8 is a genuine April snapshot (→ Apr 30)
    assert cme(date(2024, 4, 7)) == date(2024, 3, 31)
    assert cme(date(2024, 4, 8)) == date(2024, 4, 30)


def test_may_boundary_off_by_one():
    # May 7 → Apr 30; May 8 is a genuine May snapshot → May 31
    assert cme(date(2024, 5, 7)) == date(2024, 4, 30)
    assert cme(date(2024, 5, 8)) == date(2024, 5, 31)


def test_no_cross_year_leak():
    # The Apr/May rules only ever shift within the same calendar year.
    assert cme(date(2024, 4, 3)).year == 2024
    assert cme(date(2024, 5, 3)).year == 2024
