"""Per-bank tables: each bank's pace, the minimum base, flagged cells and each bank's book.

Spec: BANKWISE_SPEC §8b (the five view gaps), DECISIONS 2026-11-20 (minimum base 0.25%; pace as
a generic family). Small frames drive the rules; the live store is read only for the properties
every bank must hold.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signals.compute import atm_pos as A          # noqa: E402
from core import bank_tables as B                 # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "analysis/signals/signals.db"


def _frame(series: dict[str, list[float]], start="2025-01-31") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(next(iter(series.values()))), freq="ME")
    rows = []
    for i, d in enumerate(dates):
        ds = d.strftime("%Y-%m-%d")
        for b, v in series.items():
            if v[i] is not None:
                rows.append(dict(report_date=ds, bank_name=b, bank_category="Private Sector Banks",
                                 record_type="bank", metric="m", value=v[i], unit="count"))
    return pd.DataFrame(rows)


# ── pace ──────────────────────────────────────────────────────────────────────

def test_pace_is_this_periods_growth_less_the_last():
    # A: 100 a year before both readings; 120 now, 110 a month ago -> 20% - 10% = +10 pp.
    df = _frame({"A": [100.0, 100.0] + [100.0] * 10 + [110.0, 120.0]})
    rows = A.csv_bank_acceleration({"metric": "m"}, "2026-02-28", df)
    assert len(rows) == 1 and abs(rows[0]["value"] - 10.0) < 1e-9 and rows[0]["unit"] == "pp"


def test_a_bank_with_no_year_ago_book_has_no_pace():
    df = _frame({"A": [None, None] + [100.0] * 12, "B": [50.0] * 14})
    ids = {r["entity_id"] for r in A.csv_bank_acceleration({"metric": "m"}, "2026-02-28", df)}
    assert ids == {"B"}


def test_pace_across_a_declared_merger_is_absent_with_its_reason():
    """Live store: SBI absorbed its associates in Apr 2017, so its pace a quarter later is not a
    number. Every row is either a value or a declared reason, never a silent gap."""
    df = A._load_df("rbi_bankwise")
    rows = A.csv_bank_acceleration({"metric": "major_sectoral.gross_advances@dom"}, "2018-03-31", df)
    sbi = next(r for r in rows if r["entity_id"] == "state-bank-of-india")
    assert sbi["value"] is None and sbi["reason"] == "merger_break"


# ── minimum base ──────────────────────────────────────────────────────────────

def _table(parts):
    return {"parts": [{"entity": e, "growth": {"display": "1%", "sort": 1.0}} for e in parts],
            "unsortable": ["growth"]}


def test_minimum_base_marks_only_banks_under_the_share_a_year_earlier():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE signals (pipeline, period, metric_id, entity_type, entity_id, value, unit)")
    rows = [("p", "2025-06-30", "s", "bank", "big", 9990.0), ("p", "2025-06-30", "s", "bank", "tiny", 10.0),
            ("p", "2025-06-30", "s", "bank", "edge", 25.0),
            ("p", "2025-06-30", "t", "aggregate", "total", 10000.0)]
    conn.executemany("INSERT INTO signals VALUES (?,?,?,?,?,?,'crore')", rows)
    t = _table(["big", "tiny", "edge", "new"])
    B.mark_small_base(conn, "p", "2026-06-30", t, {"size": "s", "total_size": "t"})
    marked = {p["entity"] for p in t["parts"] if p.get("small_base")}
    assert marked == {"tiny"}                 # 0.1% marked; 0.25% exactly is not; no base, no mark
    assert "unsortable" not in t and t["notes"] == [B.SMALL_BASE_NOTE]


def test_the_rule_constant_is_the_decision():
    assert B.MIN_BASE_SHARE == 0.25 and "0.25%" in B.SMALL_BASE_NOTE


# ── flags ─────────────────────────────────────────────────────────────────────

def test_a_flag_touches_its_quarter_and_the_comparisons_that_read_it():
    dates = ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31",
             "2026-03-31", "2026-06-30"]
    q = "2025-03-31"
    assert B._touched(q, "size", dates) == {q}
    assert B._touched(q, "growth", dates) == {q, "2026-03-31"}
    assert B._touched(q, "pace", dates) == {q, "2025-06-30", "2026-03-31", "2026-06-30"}


def test_every_bank_flag_on_a_shipped_measure_is_found():
    """Population: the flags on the measures the tables draw, enumerated from the record."""
    idx = B._flag_index("rbi_bankwise")
    from pipelines.rbi_bankwise import cuts
    measures = {l["metric"] for l in cuts.BOOK["lines"]} | {cuts.BOOK["whole"],
                                                            "major_sectoral.non_food_credit_gross_advances@dom"}
    assert sum(len(v) for (_, m), v in idx.items() if m in measures) == 48


# ── each bank's book ──────────────────────────────────────────────────────────

def test_every_book_is_its_banks_lines_and_they_add_to_its_whole_book():
    """Each bank's lines, as shares of its own book, add to ~100% (food + the four sectors +
    other non-food), and the pinned row is the same number as the bank's row in all credit."""
    conn = sqlite3.connect(DB)
    reg = json.loads((ROOT / "analysis/signals/registry.json").read_text())["signals"]
    period = conn.execute("SELECT MAX(period) FROM signals WHERE pipeline='rbi_bankwise'").fetchone()[0]
    books = B.books(conn, "rbi_bankwise", period, reg)
    assert len(books) > 80
    top = {"Agriculture", "Industry", "Services", "Retail", "Food credit", "Other non-food"}
    off = []
    for bank, t in books.items():
        shares = [p["of_book"]["sort"] for p in t["parts"] if p["entity"] in top and p.get("of_book")]
        if shares and abs(sum(shares) - 100) > 1.0:
            off.append((bank, round(sum(shares), 1)))
    assert len(off) <= 2, off                   # RBI's own isolated inconsistencies, if any
