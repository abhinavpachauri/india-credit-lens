"""§21 — the real-economy columns on the Layer 1 table (core/real_cells.py), on the shipped data."""
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import absence, real_cells                         # noqa: E402

CUTS = json.loads((ROOT / "web/public/data/sibc_table.json").read_text())["cuts"]


def test_only_cuts_with_1f_signals_get_the_columns():
    with_real = {k for k, t in CUTS.items() if t.get("real_economy")}
    assert with_real and with_real <= {k for k in CUTS if real_cells.f1_signals("sibc", k)}
    for k, t in CUTS.items():
        if k not in with_real:
            assert not ({"real_credit", "output"} & set(t["columns"]))


def test_a_column_the_cut_can_never_fill_is_not_drawn():
    """Personal Loans have no output measure (half is housing): no column of dashes claiming one."""
    assert "output" not in CUTS["sibc-pl"]["columns"]
    assert "real_credit" in CUTS["sibc-pl"]["columns"]


def test_same_entity_same_number():
    """Industry is the industry-by-type total and a main-table part: one reading, both places."""
    main = next(p for p in CUTS["sibc-main"]["parts"] if p["entity"].startswith("Industry"))
    for col in ("real_credit", "output"):
        assert CUTS["sibc-industry-type"]["total"][col]["sort"] == main[col]["sort"]
        assert CUTS["sibc-industry-type"]["total"][col]["period"] == main[col]["period"]


def test_every_empty_cell_says_why_and_carries_no_number():
    for t in CUTS.values():
        for row in [t["total"], *t["parts"]]:
            for col in ("real_credit", "output"):
                c = row.get(col)
                if c and c["sort"] is None:
                    assert c["display"] == "—" and c["note"]
                    assert c["reason"] in absence.STATIC or c["reason"] in absence.PER_PERIOD


def test_coverage_counts_cells_with_a_value_not_what_is_mapped():
    cells = [({"sort": 1.0}, 30.0), ({"sort": None, "reason": "not_released"}, 50.0),
             ({"sort": None, "reason": "no_counterpart"}, 20.0)]
    assert real_cells.coverage_line("output", "Output", cells) == \
        "Output: 1 of 3 parts · 30.0% of this table's credit · 1 awaiting MoSPI."


def test_a_quarterly_cell_on_a_monthly_table_is_labelled():
    assert CUTS["sibc-industry-type"]["total"]["real_credit"]["period_label"] == "Q1"
    assert all(p.get("real_credit", {}).get("period_label") is None for p in CUTS["sibc-industry-type"]["parts"])
