"""RBI lending and deposit rates (pipeline #5): the reader, the saver's ordering, the shared stages.

signals/README "RBI lending and deposit rates". The gate's catch rates are measured by injection
(ai_pm_register, 2026-10-26); these pin the behaviours the reviewers asked for.
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "analysis/pipelines/rbi_rates"))
sys.path.insert(0, str(ROOT / "analysis/pipelines/mospi"))

import reader                                            # noqa: E402
import consolidate as C                                  # noqa: E402


def test_a_month_written_as_text_is_a_month_and_anything_else_is_not():
    assert reader.period_of(datetime(2020, 4, 1)) == "2020-04-30"        # first-of-month label
    assert reader.period_of(datetime(2023, 3, 28)) == "2023-03-31"       # a stray day
    assert reader.period_of("July-2023") == "2023-07-31"                 # T2/T3 carry real values here
    assert reader.period_of("Sept-2016") == "2016-09-30"
    assert reader.period_of("Notes: (i) WALRs") is None


def test_the_publication_date_comes_from_the_file_name():
    assert reader.published(Path("MLDRSCB30092026ENG.xlsx")) == "2026-09-30"
    assert reader.published(Path("MLDRSCB31072026E.xlsx")) == "2026-07-31"
    with pytest.raises(reader.ReadError):
        reader.published(Path("rates.xlsx"))


class _Sheet:
    def __init__(self, rows):
        self.rows = rows

    def iter_rows(self, values_only=True):
        return iter(self.rows)


LAB = {"Housing": "sector:housing", "Vehicle": "sector:vehicle"}


def test_an_unknown_column_header_fails_the_read():
    ws = _Sheet([(None, "End Month", "Housing", "Vehicle", "Gold")])
    with pytest.raises(reader.ReadError, match="'Gold' is not in labels.json"):
        reader.read_sheet(ws, LAB, "t")


def test_values_round_to_two_decimals_and_notes_are_kept():
    ws = _Sheet([("(Per cent)",), (None, "End Month", "Housing", "Vehicle"),
                 (None, datetime(2026, 8, 1), 7.700000000000001, 9.57),
                 (None, "Data are provisional.", None, None)])
    rows, notes, heads = reader.read_sheet(ws, LAB, "t")
    assert {r["value"] for r in rows} == {"7.70", "9.57"} and notes == ["Data are provisional."]
    assert heads == ["(Per cent)"]


def test_a_month_twice_in_one_table_fails():
    ws = _Sheet([(None, "Month", "Housing", "Vehicle"), (None, datetime(2026, 8, 1), 7.7, 9.5),
                 (None, "Aug-2026", 7.7, 9.5)])
    with pytest.raises(reader.ReadError, match="appears twice"):
        reader.read_sheet(ws, LAB, "t")


def test_a_rate_has_no_base_and_a_revision_beyond_the_bound_fails():
    ds = {"base_year": None, "label_fields": ["column"], "measures": {"rate": "value"}}
    k = C.keyed("x", ds, {"rows": [{"column": "Housing", "period": "2026-08-31", "value": "7.70"}]})
    assert list(k.values())[0][2] == ""                                   # no base column value
    prev = {("Housing", "2026-08-31", "rate"): ("7.70", "", "")}
    with pytest.raises(C.ConsolidateError, match="beyond the declared 0.25"):
        C.diff("x", "snapshot", prev, {("Housing", "2026-08-31", "rate"): ("8.10", "", "")},
               max_revision_abs=0.25)
    with pytest.raises(C.ConsolidateError, match="disappeared"):          # a truncated file
        C.diff("x", "snapshot", prev, {("Housing", "2026-07-31", "rate"): ("7.70", "", "")})
