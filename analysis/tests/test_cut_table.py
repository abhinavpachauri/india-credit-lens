"""
test_cut_table.py — the Layer 1 table (DASHBOARD_SPEC §17)
──────────────────────────────────────────────────────────
The table is the densest surface the platform publishes: forty cuts, two hundred rows,
seven numbers a row. Nobody proofreads that, so its properties are asserted here.

The pair shape this project settled on: drive the LOGIC synthetically, so fixing the data
can never untest the check, and assert separately that the live artifact is clean.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import table_rows as T                                       # noqa: E402
from guards import validate_cut_table as V                             # noqa: E402

DATA = ROOT / "web" / "public" / "data"
DB = ROOT / "analysis" / "signals" / "signals.db"


# ── the properties, driven directly ───────────────────────────────────────────

def test_a_whole_is_not_a_share_of_itself():
    """The total row's `of_cut` is None, not "100%".

    It read "100%" in the first draft — a literal that traces to nothing, on the one surface
    where every number is checked against a stored value. 100% is the definition of the
    denominator, not a measurement of it."""
    con = sqlite3.connect(DB)
    try:
        t = T.build(con, "sibc", "2026-08-31", "sibc-ind-size")
    finally:
        con.close()
    assert t["total"]["of_cut"] is None


def test_a_cell_carries_both_what_is_drawn_and_what_orders():
    """`display` is authoritative and gate-checked; `sort` orders and is never drawn.
    Splitting them is what lets the browser sort without letting it format."""
    c = T.Cell.of(17.6917, T._pct)
    assert c.display == "17.7%" and c.sort == 17.6917
    assert T.Cell.of(None, T._pct) is None, "a missing value is a missing cell, never a zero"


def test_levels_are_quoted_in_indian_units():
    assert T._rs(3228774.0) == "₹32.29L Cr"
    assert T._rs(48007.0) == "₹48,007 Cr"
    assert T._count(122857894) == "12.29 crore"


def test_unit_conversions_land_in_the_right_order_of_magnitude():
    """The one class of error traceability CANNOT catch.

    Every gate here checks a drawn number against its stored value — and a unit conversion
    leaves the stored value untouched. `rs_thousands` shipped as `v / 100` instead of
    `v / 1e4`, so a month of debit-card ATM withdrawals drew as Rs 219 LAKH CRORE: larger
    than the entire bank credit book, past every check, caught only by reading it and asking
    whether it could be true.
    """
    # 2,193,083,000 thousands of rupees = Rs 2.19 lakh crore.
    assert T.UNIT_FMT["rs_thousands"](2_193_083_000.0) == "\u20b92.19L Cr"
    # 11,595 THOUSANDS of rupees = Rs 1.16 crore. My first version of this line passed
    # 11,595,122 and "proved" the formatter wrong; the input was 1000x out, not the code.
    assert T.UNIT_FMT["rs_thousands"](11_595.1225) == "\u20b91.16 Cr", "a small metric keeps its precision"
    # and a sanity band on every payments money cut, so a future unit cannot drift silently
    doc = json.loads((DATA / "atm_pos_table.json").read_text())
    for stem, t in doc["cuts"].items():
        if not stem.endswith("-val-category") or not t["total"]["size"]:
            continue
        rupees = t["total"]["size"]["sort"] * 1000
        # Wide on purpose: POS cash withdrawals are genuinely Rs 1.16 crore and card
        # e-commerce is Rs 1.3 lakh crore. The band catches an order-of-magnitude slip, not
        # a small metric.
        assert 1e6 < rupees < 1e14, f"{stem}: total reads {t['total']['size']['display']}"


def test_the_flow_column_says_which_direction_it_is_a_share_of():
    """`new` is a share of the NET, and the net can be negative. Eleven of twenty-six payments
    cuts are contracting; a column headed "New" over them contradicts the band above, which
    already says "took X% of the contraction"."""
    doc = json.loads((DATA / "atm_pos_table.json").read_text())
    assert {t["flow_label"] for t in doc["cuts"].values()} <= {"New", "Of fall"}
    assert any(t["flow_label"] == "Of fall" for t in doc["cuts"].values()), \
        "no contracting cut in the live feed — this test would be vacuous"


def test_the_run_is_the_signals_own_series_not_a_recomputation():
    """The Run column must come from the growth signal's stored rows, so the sparkline and
    the Growth cell can never tell different stories."""
    con = sqlite3.connect(DB)
    try:
        t = T.build(con, "sibc", "2026-08-31", "sibc-ind-size")
        large = next(p for p in t["parts"] if p["entity"] == "Large")
        stored = [v for (v,) in con.execute(
            "SELECT value FROM signals WHERE pipeline='sibc' AND metric_id='sibc-ind-size-yoy-scan' "
            "AND entity_id='Large' ORDER BY period")]
    finally:
        con.close()
    assert large["run"] == [round(v, 4) for v in stored][-len(large["run"]):]
    assert abs(large["run"][-1] - large["growth"]["sort"]) < 1e-6, \
        "the last reading and the Growth cell are the same number"


def test_the_pairing_rule_is_structural():
    """A share of new money cannot be published without that part's speed and acceleration.
    The movement card enforced this in its builder; a table enforces it by existing — so the
    assertion is simply that a row carrying `new` also carries `growth`."""
    con = sqlite3.connect(DB)
    try:
        for stem in ("sibc-ind-size", "sibc-services", "cc-category"):
            pipeline = "sibc" if stem.startswith("sibc") else "atm_pos"
            period = "2026-08-31" if pipeline == "sibc" else "2026-07-31"
            t = T.build(con, pipeline, period, stem)
            if not t:
                continue
            for row in t["parts"]:
                if row["new"] is not None and row["size"] and row["size"]["sort"]:
                    assert row["growth"] is not None, f"{stem}/{row['entity']}: share without speed"
    finally:
        con.close()


# ── the live artifacts ────────────────────────────────────────────────────────

def test_every_cut_with_a_table_covers_every_part_it_has():
    """A table that silently drops a part is worse than no table: the shares stop summing and
    nothing says why."""
    for pipeline, period in (("sibc", "2026-08-31"), ("atm_pos", "2026-07-31")):
        doc = json.loads((DATA / f"{pipeline}_table.json").read_text())
        con = sqlite3.connect(DB)
        try:
            for stem, table in doc["cuts"].items():
                etype = T._member_type(con, pipeline, doc["_meta"]["period"], f"{stem}-size-scan")
                n = con.execute(
                    "SELECT COUNT(*) FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
                    "AND entity_type=?", (pipeline, doc["_meta"]["period"],
                                          f"{stem}-size-scan", etype)).fetchone()[0]
                assert len(table["parts"]) == n, f"{stem}: {len(table['parts'])} rows for {n} parts"
        finally:
            con.close()


def test_the_live_tables_are_traceable_on_both_pipelines():
    """Separate from the synthetic tests above, deliberately: a check that only asserts the
    live feed is clean stops asserting anything the moment someone fixes the defect it found."""
    for pipeline in ("sibc", "atm_pos"):
        assert V.validate(pipeline) == []
