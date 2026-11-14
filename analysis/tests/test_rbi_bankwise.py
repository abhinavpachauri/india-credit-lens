#!/usr/bin/env python3
"""
Phase 1 controls for the bank-wise pipeline (BANKWISE_SPEC.md §4, §5.0, §6), on small synthetic
exports laid out the way DBIE lays them out: a title, a unit line, merged measure headers over
Domestic / Overseas / Global columns, periods on the first row of each block, bold group rows.

Every shape a wrong export can take must raise; a stale or partial re-export must not save as a
clean run; the roster must refuse a name nobody claims.

Run: python3 -m pytest analysis/tests/test_rbi_bankwise.py -q
"""
import datetime
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANALYSIS))
openpyxl = pytest.importorskip("openpyxl")
from openpyxl.styles import Font  # noqa: E402

from core import banks  # noqa: E402


def _own(name, file):
    """This pipeline's modules under their own names (rbi_rates also has `fetch` and `reader`)."""
    import importlib.util
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, file)
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


fetch = _own("rbi_bankwise_fetch", ANALYSIS / "pipelines/rbi_bankwise/fetch.py")
reader = fetch.reader

ROSTER = {"_meta": {"sources": ["rbi_bankwise", "atm_pos"]},
          "banks": [{"id": "alpha", "name": "Alpha", "sources": {"rbi_bankwise": {"names": [{"name": "ALPHA BANK LTD."}]},
                                                                 "atm_pos": {"names": [{"name": "ALPHA BANK"}]}}},
                    {"id": "beta", "name": "Beta", "sources": {"rbi_bankwise": {"names": [{"name": "BETA BANK"}]},
                                                               "atm_pos": {"not_in_source": "test"}}},
                    {"id": "gamma", "name": "Gamma", "sources": {"rbi_bankwise": {"names": [{"name": "GAMMA  BANK"}]},
                                                                 "atm_pos": {"not_in_source": "test"}}}]}
MEASURES = ["Gross Advances", "Gross NPAs"]
DECLARED = {"groups": {"public sector banks": "group:psb", "private sector banks": "group:pvt",
                       "all scheduled commercial banks": "group:scb"},
            "sheets": {"Asset Quality": {"id": "asset_quality",
                                         "columns": [[m, o] for m in MEASURES
                                                     for o in ("Domestic Operation", "Overseas Operation", "Global Operation")]}}}


def export(path, quarters=("2026-06-30",), unit="Crores & Rates/ratios in Per cent", measures=MEASURES,
           rows=None, sheets=("Asset Quality",), scale=1.0):
    """A DBIE-shaped workbook. `rows`: [(name, bold, value)] per quarter."""
    rows = rows or [("ALPHA BANK LTD.", False, 100.0), ("BETA BANK", False, 50.0), ("Public Sector Banks", True, 150.0),
                    ("GAMMA  BANK", False, 10.0), ("Private Sector Banks", True, 10.0),
                    ("All Scheduled Commercial Banks", True, 160.0)]
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title in sheets:
        ws = wb.create_sheet(title)
        ws.cell(2, 2, f"Table 2. {title}")
        ws.cell(4, 2, "Amount in Rs.")
        ws.cell(4, 3, unit)
        col = 4
        for m in measures:
            ws.cell(5, col, m)
            ws.merge_cells(start_row=5, start_column=col, end_row=5, end_column=col + 2)
            for k, o in enumerate(("Domestic Operation", "Overseas Operation", "Global Operation")):
                ws.cell(6, col + k, o)
            col += 3
        ws.cell(6, 2, "Period")
        ws.cell(6, 3, "Banks")
        r = 7
        for q in quarters:
            ws.cell(r, 2, datetime.datetime.fromisoformat(q))
            for name, bold, v in rows:
                c = ws.cell(r, 3, name)
                if bold:
                    c.font = Font(bold=True)
                for j in range(len(measures) * 3):
                    ws.cell(r, 4 + j, v * scale * (1 + j))
                r += 1
        ws.cell(r + 1, 2, "Source: Offsite returns (OSMOS)")
    wb.save(path)
    return path


@pytest.fixture
def resolver():
    return banks.Resolver("rbi_bankwise", ROSTER)


def read(path, resolver, declared=DECLARED):
    return reader.read(path, declared, resolver)


def test_a_good_export_reads_banks_groups_and_membership(tmp_path, resolver):
    got = read(export(tmp_path / "x.xlsx"), resolver)
    q = got["quarters"]["2026-06-30"]
    assert set(q["banks"]) == {"alpha", "beta", "gamma"}
    assert q["groups"]["group:psb"]["members"] == ["alpha", "beta"]
    assert q["groups"]["group:scb"]["members"] == []           # a total of groups closes no bank block
    assert q["banks"]["gamma"]["group"] == "group:pvt"
    assert q["banks"]["alpha"]["sheets"]["asset_quality"]["gross_advances@glb"] == 300.0


def test_a_mislabelled_column_raises(tmp_path, resolver):
    with pytest.raises(reader.ExportShapeError, match="header differs"):
        read(export(tmp_path / "x.xlsx", measures=["Gross NPAs", "Gross Advances"]), resolver)


def test_a_missing_or_extra_sheet_raises(tmp_path, resolver):
    with pytest.raises(reader.ExportShapeError, match="sheets"):
        read(export(tmp_path / "x.xlsx", sheets=("Asset Quality", "Profitability")), resolver)


def test_lakhs_instead_of_crores_raises(tmp_path, resolver):
    with pytest.raises(reader.ExportShapeError, match="not crores"):
        read(export(tmp_path / "x.xlsx", unit="Lakhs & Rates/ratios in Per cent"), resolver)


def test_an_undeclared_bold_row_raises(tmp_path, resolver):
    rows = [("ALPHA BANK LTD.", False, 1.0), ("Payments Bank Group", True, 1.0)]
    with pytest.raises(reader.ExportShapeError, match="not a declared group"):
        read(export(tmp_path / "x.xlsx", rows=rows), resolver)


def test_a_bank_named_like_a_group_is_still_a_bank(tmp_path):
    roster = {"_meta": {"sources": ["rbi_bankwise", "atm_pos"]},
              "banks": [{"id": "anz", "name": "ANZ", "sources": {
                  "rbi_bankwise": {"names": [{"name": "AUSTRALIA AND NEW ZEALAND BANKING GROUP LIMITED"}]},
                  "atm_pos": {"not_in_source": "test"}}}]}
    rows = [("AUSTRALIA AND NEW ZEALAND BANKING GROUP LIMITED", False, 1.0), ("Public Sector Banks", True, 1.0)]
    got = read(export(tmp_path / "x.xlsx", rows=rows), banks.Resolver("rbi_bankwise", roster))
    assert "anz" in got["quarters"]["2026-06-30"]["banks"]


def test_an_unknown_bank_raises(tmp_path, resolver):
    rows = [("DELTA BANK", False, 1.0), ("Public Sector Banks", True, 1.0)]
    with pytest.raises(banks.UnknownBank):
        read(export(tmp_path / "x.xlsx", rows=rows), resolver)


def test_spacing_and_case_do_not_make_a_new_bank(resolver):
    assert resolver("Gamma Bank") == resolver("GAMMA  BANK") == "gamma"


def test_banks_after_the_last_group_row_raise(tmp_path, resolver):
    rows = [("ALPHA BANK LTD.", False, 1.0), ("Public Sector Banks", True, 1.0), ("BETA BANK", False, 1.0)]
    with pytest.raises(reader.ExportShapeError, match="after the last group"):
        read(export(tmp_path / "x.xlsx", rows=rows), resolver)


def test_an_empty_merged_header_is_unlabelled_not_borrowed(tmp_path, resolver):
    """RBI leaves some merged headers empty over columns with data (Asset Quality, Jun 2025)."""
    declared = {**DECLARED, "sheets": {"Asset Quality": {"id": "asset_quality", "columns": [
        [m, o] for m in ["Gross Advances", ""] for o in ("Domestic Operation", "Overseas Operation", "Global Operation")]}}}
    got = read(export(tmp_path / "x.xlsx", measures=["Gross Advances", ""]), resolver, declared)
    cols = got["quarters"]["2026-06-30"]["banks"]["alpha"]["sheets"]["asset_quality"]
    assert "unlabelled_3@dom" in cols and "gross_advances@ovs" in cols


def test_roster_needs_an_answer_for_every_source():
    bad = {"_meta": {"sources": ["rbi_bankwise", "atm_pos"]},
           "banks": [{"id": "x", "name": "X", "sources": {"rbi_bankwise": {"names": [{"name": "X"}]}}}]}
    assert any("no names and no not_in_source for atm_pos" in e for e in banks.validate(bad))


def test_a_dated_alias_does_not_resolve_outside_its_dates():
    roster = {"_meta": {"sources": ["rbi_bankwise", "atm_pos"]},
              "banks": [{"id": "new", "name": "New", "sources": {
                  "rbi_bankwise": {"names": [{"name": "OLD NAME", "to": "2024-12-31"}, {"name": "NEW NAME", "from": "2025-01-01"}]},
                  "atm_pos": {"not_in_source": "test"}}}]}
    r = banks.Resolver("rbi_bankwise", roster)
    assert r("OLD NAME", "2024-09-30") == "new"
    with pytest.raises(banks.UnknownBank):
        r("OLD NAME", "2025-06-30")


# ── saving (§4) ───────────────────────────────────────────────────────────────

@pytest.fixture
def saving(tmp_path, monkeypatch, resolver):
    real = reader.read                                   # the patched name is the same module's
    monkeypatch.setattr(fetch.reader, "read", lambda p: real(p, DECLARED, resolver))
    return tmp_path / "releases"


def test_new_then_unchanged_then_stale(tmp_path, saving):
    x = export(tmp_path / "x.xlsx", quarters=("2026-03-31", "2026-06-30"))
    assert sum("NEW" in line for line in fetch.save([x], root=saving, today="2026-11-14")) == 2
    with pytest.raises(fetch.SaveRefused, match="no quarter in this export is new"):
        fetch.save([x], root=saving, today="2026-11-15")
    out = fetch.save([x], no_new_expected=True, root=saving, today="2026-11-15")
    assert "2 saved quarter(s) re-read, 0 changed" in out[-1]


def test_a_revision_is_refused_listed_then_accepted_keeping_the_old(tmp_path, saving):
    fetch.save([export(tmp_path / "a.xlsx")], root=saving, today="2026-11-14")
    b = export(tmp_path / "b.xlsx", scale=1.01)
    with pytest.raises(fetch.SaveRefused, match="was revised"):
        fetch.save([b], no_new_expected=True, root=saving, today="2026-11-15")
    fetch.save([b], no_new_expected=True, accept={"2026-06-30"}, root=saving, today="2026-11-15")
    assert len(list((saving / "2026-06-30").glob("*.json.gz"))) == 2


def test_a_removed_bank_is_a_revision(tmp_path, saving):
    fetch.save([export(tmp_path / "a.xlsx")], root=saving, today="2026-11-14")
    rows = [("ALPHA BANK LTD.", False, 100.0), ("Public Sector Banks", True, 100.0),
            ("GAMMA  BANK", False, 10.0), ("Private Sector Banks", True, 10.0), ("All Scheduled Commercial Banks", True, 110.0)]
    with pytest.raises(fetch.SaveRefused, match="removed bank beta"):
        fetch.save([export(tmp_path / "b.xlsx", rows=rows)], no_new_expected=True, root=saving, today="2026-11-15")


def test_a_new_quarter_must_re_read_the_saved_ones(tmp_path, saving):
    fetch.save([export(tmp_path / "a.xlsx", quarters=("2026-03-31",))], root=saving, today="2026-11-14")
    with pytest.raises(fetch.SaveRefused, match="does not re-read"):
        fetch.save([export(tmp_path / "b.xlsx", quarters=("2026-06-30",))], root=saving, today="2026-11-15")
    out = fetch.save([export(tmp_path / "c.xlsx", quarters=("2026-03-31", "2026-06-30"))], root=saving, today="2026-11-15")
    assert any("NEW        2026-06-30" in line for line in out)


def test_a_backfill_of_older_quarters_saves(tmp_path, saving):
    fetch.save([export(tmp_path / "a.xlsx", quarters=("2026-06-30",))], root=saving, today="2026-11-14")
    out = fetch.save([export(tmp_path / "b.xlsx", quarters=("2002-03-31",))], root=saving, today="2026-11-15")
    assert any("NEW        2002-03-31" in line for line in out)


def test_the_live_roster_validates():
    assert banks.validate(banks.load()) == []


# ── calendar (§4) ─────────────────────────────────────────────────────────────

calendar_check = _own("rbi_bankwise_calendar", ANALYSIS / "pipelines/rbi_bankwise/validate_calendar.py")
TODAY = datetime.date(2026, 11, 14)


def test_current_when_the_newest_saved_is_at_or_past_the_due_quarter():
    ok, lines = calendar_check.check({"2026-06-30"}, "2026-03-31", 165, required=False, today=TODAY)
    assert ok and "current" in lines[0]
    assert "missing 1 (2026-03-31)" in lines[1] and "not yet required" in lines[1]


def test_overdue_fails():
    ok, lines = calendar_check.check({"2025-12-31"}, "2025-12-31", 165, required=False, today=TODAY)
    assert not ok and "OVERDUE" in lines[0]


def test_a_history_gap_fails_once_required():
    ok, _ = calendar_check.check({"2026-06-30"}, "2026-03-31", 165, required=True, today=TODAY)
    assert not ok


# ── checks against RBI's own totals (§5), on the committed probe quarters ─────

vb = _own("rbi_bankwise_validate", ANALYSIS / "pipelines/rbi_bankwise/validate_bankwise.py")


@pytest.fixture(scope="module")
def probe():
    import json as _json
    st = vb.structure(_json.loads((ANALYSIS / "pipelines/rbi_bankwise/sheets.json").read_text()))
    return st, vb.load_quarters()


def _unexcepted(p, q, st):
    return [x for k, fl in vb.check_quarter(q, st).items() for x in fl if not vb.excepted(k, p, x)]


PROBE = ("2024-09-30", "2025-06-30", "2026-06-30")     # pinned: clean in every check (2026-11-14)


def test_the_probe_quarters_pass_every_check_with_nothing_flagged(probe):
    st, Q = probe
    for p in PROBE:
        assert _unexcepted(p, Q[p], st) == [], p
    assert vb.scale({p: Q[p] for p in PROBE}, st) == []


def test_the_gate_passes_on_every_saved_quarter(probe):
    st, Q = probe
    ok, _, _ = vb.run(Q, st)
    assert ok


def test_a_column_wide_error_fails_the_gate(probe):
    """A reading error maps a column the same way for every bank: swap two columns for every row."""
    st, Q = probe
    p, sid = PROBE[-1], "major_sectoral"
    c1, c2 = "industry_gross_advances@dom", "services_gross_advances@dom"
    rows = list(Q[p]["banks"].values()) + list(Q[p]["groups"].values())
    for e in rows:
        d = e["sheets"][sid]; d[c1], d[c2] = d[c2], d[c1]
    try:
        patterns, _, _, _ = vb.classify({p: Q[p]}, st)
        assert patterns
    finally:
        for e in rows:
            d = e["sheets"][sid]; d[c1], d[c2] = d[c2], d[c1]


def test_one_bank_disagreeing_is_flagged_not_failed(probe):
    st, Q = probe
    p = PROBE[-1]
    cols = Q[p]["banks"]["bank-of-baroda"]["sheets"]["major_sectoral"]
    old = cols["industry_gross_advances@dom"]
    cols["industry_gross_advances@dom"] = old + 100
    try:
        patterns, flags, _, _ = vb.classify({p: Q[p]}, st)
        assert not patterns
        assert any(f["entity"] in ("bank-of-baroda", "group:psb") for f in flags)
    finally:
        cols["industry_gross_advances@dom"] = old


def test_a_shifted_bank_cell_breaks_its_group_sum(probe):
    st, Q = probe
    p = PROBE[-1]
    cols = Q[p]["banks"]["bank-of-baroda"]["sheets"]["major_sectoral"]
    old = cols["industry_gross_advances@dom"]
    cols["industry_gross_advances@dom"] = old + 100
    try:
        assert any("group:psb" in x and "industry_gross_advances" in x for x in _unexcepted(p, Q[p], st))
    finally:
        cols["industry_gross_advances@dom"] = old


def test_ratio_means_the_word_not_the_letters(probe):
    st, _ = probe
    assert "2_1_electricity_generation" in st["infrastructure_financing_items"]["amounts"]
    assert "c_total_rwas_operational_risk_standalone@glb" in st["capital_adequacy"]["amounts"]
    assert "capital_ratio_crar_standalone@glb" in st["capital_adequacy"]["ratios"]


def test_named_exceptions_cover_only_what_they_name(probe):
    st, Q = probe
    p = sorted(Q)[-1]
    assert vb.excepted("5.4", p, "hdfc-bank profitability 7_net_operating_income_april_to_date_5_6@dom: x")
    assert not vb.excepted("5.4", p, "axis-bank profitability 7_net_operating_income_april_to_date_5_6@dom: x")
    assert not vb.excepted("5.4", p, "hdfc-bank profitability 3_net_interest_income_nii_april_to_date_1_2@dom: x")


def test_lakhs_trips_the_scale_guard(probe):
    import copy
    st, Q = probe
    p = sorted(Q)[-1]
    q = copy.deepcopy(Q[p])
    q["groups"]["group:scb"]["sheets"]["major_sectoral"]["gross_advances@dom"] *= 100
    assert vb.scale({**Q, p: q}, st)
