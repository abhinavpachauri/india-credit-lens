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


def test_every_cell_carries_its_whole_stored_history():
    """A cell is the top of a series (§20), and the series it ships must be the signal's own
    stored rows — so the chart a cell opens and the cell itself can never tell different
    stories. Asserted over EVERY column, not the one that used to be the sparkline."""
    con = sqlite3.connect(DB)
    try:
        t = T.build(con, "sibc", "2026-08-31", "sibc-ind-size",
                    parent_yoy="sibc-industry-yoy")
        large = next(p for p in t["parts"] if p["entity"] == "Large")
        for col, metric in t["columns"].items():
            cell = large.get(col)
            if not cell or not cell.get("series"):
                continue
            etype = "alloc" if col == "new" else ("weight_now" if col == "of_cut" else None)
            q = ("SELECT value FROM signals WHERE pipeline='sibc' AND metric_id=? "
                 "AND entity_id='Large'" + (" AND entity_type=?" if etype else "") + " ORDER BY period")
            stored = [round(v, 4) for (v,) in con.execute(q, (metric,) + ((etype,) if etype else ()))]
            drawn = [v for v in cell["series"] if v is not None]
            assert drawn == stored, f"{col} chart is not {metric}'s own rows"
            assert abs(drawn[-1] - cell["sort"]) < 1e-6, f"{col} cell is not the top of its series"
            assert len(cell["series"]) == len(t["periods"][col]), \
                f"{col} series and axis are different lengths"
    finally:
        con.close()


def test_a_columns_depth_is_its_own():
    """Payments stores 31 readings of a level and 19 of its YoY, because a year-on-year rate
    cannot exist until a year has passed. One axis for the whole table would have to invent
    the missing readings or discard the ones that exist."""
    con = sqlite3.connect(DB)
    try:
        t = T.build(con, "atm_pos", "2026-07-31", "cc-category")
    finally:
        con.close()
    assert len(t["periods"]["size"]) > len(t["periods"]["growth"]), \
        "the level and its YoY have the same depth — this test has stopped measuring anything"


def test_the_parent_row_states_its_share_of_the_book():
    """Industry is 21.7% of all bank credit, and until this build the parent row said "—"
    while the row for the same sector in Main Sectors said 21.7%. The number is the PARENT'S
    OWN published row over the denominator, never the sum of the parts: for main sectors
    those differ by 4.9% because RBI attributes Rs 10.72L crore to no sector."""
    con = sqlite3.connect(DB)
    try:
        t = T.build(con, "sibc", "2026-08-31", "sibc-ind-size", parent_yoy="sibc-industry-yoy")
        main = T.build(con, "sibc", "2026-08-31", "sibc-main")
    finally:
        con.close()
    assert t["total"]["of_book"], "the cut's own share of the book is missing"
    same = next(p for p in main["parts"] if p["entity"].startswith("Industry"))
    assert t["total"]["of_book"]["display"] == same["of_book"]["display"], \
        "the same sector reads differently as a parent row and as a part"


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
    nothing says why.

    The size signal is read from the table's own DECLARED columns, not rebuilt from the stem:
    a bank breakout's scan has been called `cc-bank-scan` since the first ingestion, and a test
    that reconstructs ids by convention fails on the one cut whose name does not follow it —
    which is the same defect it is supposed to catch, wearing the other hat.
    """
    for pipeline, period in (("sibc", "2026-08-31"), ("atm_pos", "2026-07-31")):
        doc = json.loads((DATA / f"{pipeline}_table.json").read_text())
        con = sqlite3.connect(DB)
        try:
            for stem, table in doc["cuts"].items():
                size_id = (table.get("columns") or {}).get("size", f"{stem}-size-scan")
                etype = T._member_type(con, pipeline, doc["_meta"]["period"], size_id)
                n = con.execute(
                    "SELECT COUNT(*) FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
                    "AND entity_type=?", (pipeline, doc["_meta"]["period"],
                                          size_id, etype)).fetchone()[0]
                assert len(table["parts"]) == n, f"{stem}: {len(table['parts'])} rows for {n} parts"
        finally:
            con.close()


def test_the_live_tables_are_traceable_on_both_pipelines():
    """Separate from the synthetic tests above, deliberately: a check that only asserts the
    live feed is clean stops asserting anything the moment someone fixes the defect it found."""
    for pipeline in ("sibc", "atm_pos"):
        assert V.validate(pipeline) == []


def test_every_computed_table_is_reachable_from_the_dashboard():
    """No table may be computed, gated, shipped — and rendered nowhere. BOTH pipelines.

    This is the failure this work was about, and it has now happened twice in two shapes. The
    first: seven SIBC tables had no surface, because the credit adapter kept a HAND-WRITTEN map
    beside a payments adapter that DERIVES its list. The second, found by widening this test to
    the pipeline it was not watching: payments reconstructed each cut's stem from its metric's
    name, which is right for 23 of 26 cuts and wrong for `credit_cards`, `debit_cards` and
    `pos_terminals` — every group's ANCHOR table, the card fleets and the POS fleet.

    So the test that exists to police hand-maintained lists was itself scoped to one pipeline.
    A check's population is a design decision, and this is the third time that has cost us.

    Reachable means (§19/§20): a dimension owns the cut, a row opens into it, or — on payments
    — a measure filter resolves to it through the metric the sidecar declares.
    """
    import re
    web = ROOT / "web" / "components" / "read"

    sibc = json.loads((DATA / "sibc_table.json").read_text())
    declared = set(re.findall(r'stem:\s*"([^"]+)"', (web / "SibcReadMode.tsx").read_text()))
    via_row = {p["sub_cut"] for t in sibc["cuts"].values() for p in t["parts"] if p.get("sub_cut")}
    unreachable = set(sibc["cuts"]) - declared - via_row
    assert not unreachable, (
        f"computed and rendered nowhere: {sorted(unreachable)} — either a dimension must own "
        f"each, or a row must open into it")

    # Payments resolves a cut by the METRIC it measures, so reachability is checked the same
    # way the adapter resolves it: every metric named in SECTION_DEFS must find a cut, and
    # every cut must be found by one.
    pay = json.loads((DATA / "atm_pos_table.json").read_text())
    defs = (ROOT / "web" / "lib" / "atm_pos_data.ts").read_text()
    block = defs[defs.index("export const SECTION_DEFS"):defs.index("export const GROUP_LABELS")]
    named = set(re.findall(r'(?:metric|valMetric|volMetric):\s*(?:\[([^\]]*)\]|"([^"]+)")', block))
    metrics = {m.strip().strip('"') for pair in named for part in pair if part
               for m in part.split(",") if m.strip()}
    carried = {t["metric"] for t in pay["cuts"].values() if t.get("metric")}
    assert not metrics - carried, f"a section names {sorted(metrics - carried)}, which no cut measures"
    assert not carried - metrics, (
        f"computed and rendered nowhere: {sorted(carried - metrics)} — no payments section "
        f"measures it, so the measure filter can never reach it")
    assert set(pay["cuts"]) == {s for s, t in pay["cuts"].items() if t.get("metric")}, \
        "a payments cut ships without the metric it measures, so the adapter must guess its name"


def test_a_sub_cut_is_joined_to_a_row_that_actually_exists():
    """The join is code -> CSV name -> row entity, done in Python. If it silently missed, the
    row would simply never offer to open — an absence, which is the shape that hides."""
    doc = json.loads((DATA / "sibc_table.json").read_text())
    named = {p["sub_cut"] for t in doc["cuts"].values() for p in t["parts"] if p.get("sub_cut")}
    assert named, "no row offers a sub-cut — the join produced nothing"
    for stem in named:
        assert stem in doc["cuts"], f"a row opens into {stem}, which is not a table"


def test_a_bank_breakout_is_a_cut_like_any_other():
    """The 63 reporting banks were in the store from the first ingestion and no surface could
    show one of them beside its own growth: the bank scan fed concentration cards and nothing
    else. A breakout is the SAME table at a different level, so it is a cut — not a nested row
    under a bank category, which the banks are not children of.

    Discovery is by METHOD and METRIC, never by name: `cc-bank-scan` does not follow the stem
    convention and never will.
    """
    doc = json.loads((DATA / "atm_pos_table.json").read_text())
    banks = {s: t for s, t in doc["cuts"].items() if t.get("level") == "bank"}
    assert len(banks) == 3, f"expected the three fleet metrics to break out by bank, got {sorted(banks)}"
    for stem, t in banks.items():
        assert t.get("metric"), f"{stem} does not say which metric it breaks out"
        assert len(t["parts"]) > 20, f"{stem} has {len(t['parts'])} banks — that is a category table"
        # A bank breakout has no 12-month allocation window and no acceleration, and six
        # columns of dashes would claim it does.
        assert set(t["columns"]) == {"size", "of_cut", "growth"}, \
            f"{stem} declares {sorted(t['columns'])}"


def test_the_breakouts_parent_row_is_the_same_total_the_category_table_shows():
    """One signal, two tables. The parent of the bank breakout is the metric's own published
    total — not the sum of the reporting banks, and not a second stored copy of it."""
    doc = json.loads((DATA / "atm_pos_table.json").read_text())
    for stem, t in doc["cuts"].items():
        if t.get("level") != "bank":
            continue
        sibling = next(c for c in doc["cuts"].values()
                       if c.get("metric") == t["metric"] and c.get("level") != "bank")
        assert t["total"]["size"]["display"] == sibling["total"]["size"]["display"], \
            f"{stem}: the fleet total differs between the bank and category views"

