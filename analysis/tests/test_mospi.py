"""
test_mospi.py — the reference pipeline: the fetch contract, the saved release, the calendar
──────────────────────────────────────────────────────────────────────────────────────────
Every way the MoSPI API fails, it fails with status 200. So each clause of the fetch contract is
pinned by a response that breaks exactly that clause, and each stage's failure is driven by data
that should fail it, not only by data that passes (a test that asserts nothing looks exactly like a
test that passes).
"""
import csv
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "analysis" / "pipelines" / "mospi"))

import mospi_api as A                                   # noqa: E402
import releases as R                                    # noqa: E402
import cpi_release                                      # noqa: E402
import consolidate as C                                 # noqa: E402
import validate_csv as V                                # noqa: E402
import validate_published_growth as G                   # noqa: E402
from core import manifest                               # noqa: E402

BASE = [{"param": "base_year", "value": "2022-23", "field": "base_year"}]
IND = BASE + [{"param": "indicator_code", "value": "1", "field": "indicator",
               "expect": "Gross Value Added"}]


def page(rows, total_records, total_pages, msg="Data fetched successfully"):
    return {"data": rows, "msg": msg, "statusCode": True,
            "meta_data": {"page": 1, "totalRecords": total_records, "totalPages": total_pages}}


# ── the fetch contract, one clause at a time ──────────────────────────────────

def test_a_good_page_passes():
    rows = [{"base_year": "2022-23", "index": "1"}]
    assert A.check_page(page(rows, 1, 1), BASE, "u") == rows


@pytest.mark.parametrize("doc, match", [
    ({"data": [], "msg": "No Data Found", "statusCode": True}, "no data"),
    (page([], 0, 1), "no data"),
    (page([{"base_year": "2022-23"}], 0, 1), "totalRecords"),
    ({"html": "<!doctype html>"}, "no `data`"),
])
def test_an_empty_or_foreign_answer_fails(doc, match):
    with pytest.raises(A.FetchError, match=match):
        A.check_page(doc, BASE, "u")


def test_the_silent_old_base_fails():
    """WPI without base_year serves 2011-12 with status 200. The row says so; we read it."""
    with pytest.raises(A.FetchError, match="not honoured"):
        A.check_page(page([{"base_year": "2011-12"}], 1, 1), BASE, "u")


def test_an_ignored_filter_fails():
    """`frequency=` is ignored and the annual rows come back; the row's label gives it away."""
    rows = [{"base_year": "2022-23", "indicator": "Gross Domestic Product"}]
    with pytest.raises(A.FetchError, match="indicator_code"):
        A.check_page(page(rows, 1, 1), IND, "u")


def test_a_short_fetch_fails():
    p1 = page([{"base_year": "2022-23"}], 3, 2)
    with pytest.raises(A.FetchError, match="pages"):
        A.check_complete([p1], p1["data"], "u")
    with pytest.raises(A.FetchError, match="rows, totalRecords"):
        A.check_complete([p1, page([{"base_year": "2022-23"}], 3, 2)],
                         [{"base_year": "2022-23"}] * 2, "u")


def test_data_moving_mid_fetch_fails():
    p1, p2 = page([{"base_year": "2022-23"}], 2, 2), page([{"base_year": "2022-23"}], 3, 2)
    with pytest.raises(A.FetchError, match="changed mid-fetch"):
        A.check_complete([p1, p2], p1["data"] + p2["data"], "u")


def test_fetch_request_reads_every_page():
    served = {1: page([{"base_year": "2022-23", "i": 1}], 3, 2),
              2: page([{"base_year": "2022-23", "i": 2}, {"base_year": "2022-23", "i": 3}], 3, 2)}
    get = lambda url: served[int(url.rsplit("page=", 1)[1])]
    rows = A.fetch_request("https://x/", "e", BASE, 2, workers=2, get=get)
    assert [r["i"] for r in rows] == [1, 2, 3]


def test_every_declared_filter_names_the_row_field_that_verifies_it():
    """A filter with nothing to verify it on is a filter that can be ignored unnoticed."""
    for name, ds in manifest.load("mospi")["datasets"].items():
        for req in ds.get("requests", []):
            for f in req["filters"]:
                assert f.get("field"), f"{name}: filter {f['param']} names no row field"


# ── the saved release ─────────────────────────────────────────────────────────

def test_an_unchanged_release_is_the_same_bytes():
    rows = [{"b": 2, "a": 1}, {"a": 0}]
    d1 = {"rows": R.canonical_rows(rows)}
    d2 = {"rows": R.canonical_rows(list(reversed(rows)))}
    assert R.dump(d1) == R.dump(d2)


@pytest.mark.parametrize("row, spec, want", [
    ({"year": 2026, "month": "February"}, {"year": "year", "month": "month"}, "2026-02-28"),
    ({"year": "2026-27", "quarter": "Q1"}, {"fiscal_year": "year", "quarter": "quarter"}, "2026-06-30"),
    ({"year": "2025-26", "quarter": "Q3"}, {"fiscal_year": "year", "quarter": "quarter"}, "2025-12-31"),
    ({"year": "2025-26", "quarter": "Q4"}, {"fiscal_year": "year", "quarter": "quarter"}, "2026-03-31"),
])
def test_periods_land_on_the_sibc_convention(row, spec, want):
    assert R.period_of(row, spec) == want


def test_an_unknown_period_raises():
    with pytest.raises(ValueError):
        R.period_of({"year": 2026, "month": "Sept"}, {"year": "year", "month": "month"})
    with pytest.raises(ValueError):
        R.period_of({"year": "2026", "quarter": "Q1"}, {"fiscal_year": "year", "quarter": "quarter"})


def test_a_label_key_keeps_its_empty_fields():
    fields = ["major_group", "group", "sub_group"]
    assert R.label_key({"major_group": "Fuel & Power"}, fields) != \
        R.label_key({"major_group": "Fuel & Power", "group": "Mineral Oils"}, fields)


# ── CPI, read from the press release ─────────────────────────────────────────

TWO_MONTHS = """PRESS RELEASE OF CONSUMER PRICE INDEX ON BASE 2024=100 FOR JULY, 2026
                     July, 2026 (Provisional)                     June, 2026 (Final)
                     Rural      Urban          Combined      Rural        Urban        Combined
   CPI (General)        4.84         3.96            4.45         4.74         3.93           4.38
   CPI (General)      108.34        107.45         107.94        107.24       106.69        107.00
"""
ONE_MONTH = """FIRST PRESS RELEASE OF CONSUMER PRICE INDEX ON BASE 2024=100
          January, 2026 (Provisional) at Base year 2024=100
       CPI (General)                   2.73                        2.77                    2.75
          CPI (General)                       104.59                              104.30                   104.46
"""


def test_cpi_two_month_release():
    rows = cpi_release.parse(TWO_MONTHS)
    assert [(r["period"], r["index"], r["inflation"], r["status"]) for r in rows] == [
        ("2026-07-31", "107.94", "4.45", "P"), ("2026-06-30", "107.00", "4.38", "F")]


def test_cpi_first_release_has_one_month():
    assert [(r["period"], r["index"]) for r in cpi_release.parse(ONE_MONTH)] == [("2026-01-31", "104.46")]


@pytest.mark.parametrize("text, match", [
    (TWO_MONTHS.replace("2024=100", "2012=100"), "base 2024"),
    (TWO_MONTHS.replace("108.34", ""), "numbers per line"),
    ("\n".join(l for l in TWO_MONTHS.splitlines() if "107.94" not in l), "inflation and index"),
])
def test_a_cpi_table_it_does_not_recognise_raises(text, match):
    with pytest.raises(ValueError, match=match):
        cpi_release.parse(text)


# ── the release diff ─────────────────────────────────────────────────────────

def test_a_revision_is_counted_not_failed():
    prev = {("a", "2026-06-30", "index"): ("100.0", ""), ("a", "2026-07-31", "index"): ("101.0", "")}
    new = {**prev, ("a", "2026-07-31", "index"): ("101.5", "")}
    assert C.diff("iip", "snapshot", prev, new)["revised"] == 1


def test_a_key_that_disappears_from_a_snapshot_fails():
    prev = {("a", "2026-06-30", "index"): ("100", ""), ("b", "2026-06-30", "index"): ("1", "")}
    new = {("a", "2026-06-30", "index"): ("100", "")}
    with pytest.raises(C.ConsolidateError, match="disappeared"):
        C.diff("iip", "snapshot", prev, new)
    C.diff("cpi", "increment", prev, new)          # an increment holds only its own months


def test_the_latest_period_moving_backwards_fails():
    prev = {("a", "2026-07-31", "index"): ("1", "")}
    with pytest.raises(C.ConsolidateError, match="backwards"):
        C.diff("cpi", "increment", prev, {("a", "2026-06-30", "index"): ("1", "")})


# ── the release calendar ─────────────────────────────────────────────────────

def test_a_period_past_its_due_date_is_overdue():
    assert V.expected_latest("2026-07-31", "monthly", 12, 5, date(2026, 9, 28)) == "2026-08-31"
    assert V.expected_latest("2026-07-31", "monthly", 28, 5, date(2026, 9, 28)) == "2026-07-31"
    assert V.expected_latest("2026-06-30", "quarterly", 61, 5, date(2026, 9, 28)) == "2026-06-30"


def _csv_rows():
    with manifest.consolidated_csv("mospi").open() as f:
        return list(csv.DictReader(f))


def test_the_calendar_fails_a_missing_month_and_not_a_pending_one():
    man, lab = manifest.load("mospi"), C.labels()
    rows = [r for r in _csv_rows() if r["dataset"] != "cpi"]
    man = {**man, "datasets": {k: v for k, v in man["datasets"].items() if k != "cpi"}}
    errs, _ = V.check(rows, man, lab, date(2026, 9, 28))
    assert not errs, errs
    errs, _ = V.check(rows, man, lab, date(2026, 10, 30))       # IIP Aug now due, and absent
    assert any("iip: OVERDUE" in e for e in errs)


def test_a_gap_inside_a_series_fails():
    man, lab = manifest.load("mospi"), C.labels()
    rows = [r for r in _csv_rows() if not (r["code"] == "nic:24" and r["period"] == "2025-01-31")]
    errs, _ = V.check(rows, man, lab, date(2026, 9, 1))
    assert any("nic:24" in e and "gap" in e for e in errs)


# ── 1c: our growth vs MoSPI's printed rate ───────────────────────────────────

def test_tolerance_is_the_rounding():
    assert G.tolerance(124.8, 117.0, 1, 1) == pytest.approx(0.138, abs=0.001)


def test_known_good_control_passes_every_value():
    """The committed data: zero false rejections over every compared value."""
    errs, buckets, compared, _ = G.check(_csv_rows(), manifest.load("mospi"), C.labels())
    assert not errs, errs[:3]
    assert compared > 1000 and buckets["iip:checked"] == len(set(C.labels()["iip"].values()))


def test_known_bad_control_a_level_one_month_off_is_caught():
    """Measured by enumeration, not sampled: shift ONE series' level by a month and the check must
    fail, for every IIP series. A wrong-period join is the error this stage exists to catch."""
    rows, man, lab = _csv_rows(), manifest.load("mospi"), C.labels()
    missed = []
    for code in sorted(set(lab["iip"].values())):
        shifted = []
        for r in rows:
            if r["dataset"] == "iip" and r["code"] == code and r["measure"] == "index":
                r = {**r, "period": V.next_period(r["period"], 1)}
            shifted.append(r)
        latest = max(r["period"] for r in rows if r["dataset"] == "iip")
        shifted = [r for r in shifted if not (r["dataset"] == "iip" and r["period"] > latest)]
        errs, *_ = G.check(shifted, man, lab)
        if not errs:
            missed.append(code)
    assert not missed, f"a one-month shift went unnoticed for {missed}"


def test_zero_compared_values_is_a_failure():
    man = manifest.load("mospi")
    rows = [r for r in _csv_rows() if r["measure"] not in ("growth_published", "growth_published_constant",
                                                            "growth_published_current")]
    errs, *_ = G.check(rows, man, C.labels())
    assert any("zero values compared" in e or "no growth_published" in e for e in errs)


# ── the gate: offline, and depends_on ────────────────────────────────────────

def test_offline_skips_only_the_stages_that_say_so():
    from core import gate
    assert gate.should_skip({"skip_if": "offline"}, {"offline": True}, {}, set(), False)
    assert not gate.should_skip({"skip_if": "offline"}, {"offline": False}, {}, set(), False)
    assert not gate.should_skip({}, {"offline": True}, {}, set(), False)


def test_a_dependent_gate_runs_its_references_currency_stage(monkeypatch):
    from core import gate
    fake = {"credit": {"depends_on": ["ref"], "paths": {}, "gate": []},
            "ref": {"currency_stage": "cal", "paths": {"data_dir": "x"}, "modules": {"v": "pipelines/mospi/validate_csv.py"},
                    "gate": [{"id": "cal", "pipeline": "v"}]}}
    monkeypatch.setattr(manifest, "load", lambda p: fake[p])
    [(label, cmd, _)] = gate.reference_currency("credit")
    assert "ref data current" in label and cmd[1].endswith("validate_csv.py")


def test_a_reference_with_no_currency_stage_is_refused(monkeypatch):
    from core import gate
    fake = {"credit": {"depends_on": ["ref"]}, "ref": {"paths": {}, "gate": []}}
    monkeypatch.setattr(manifest, "load", lambda p: fake[p])
    with pytest.raises(SystemExit, match="currency_stage"):
        gate.reference_currency("credit")


def test_every_reference_pipeline_declares_a_currency_stage_it_has():
    for p in manifest.PIPELINE_IDS:
        if manifest.kind(p) == "reference":
            man = manifest.load(p)
            assert man.get("currency_stage") in {s["id"] for s in man["gate"]}, p


# ── a measure that disappears (absence review, 2026-09-28) ───────────────────
# The first controls SHIFTED a level; none REMOVED one. A renamed MoSPI field removed a whole
# measure with every stage green, and 1c filed the missing level as a first-year absence.

def test_a_renamed_value_field_fails_consolidate_not_blanks_it():
    ds = manifest.load("mospi")["datasets"]["iip"]
    row = {"base_year": "2022-23", "year": 2026, "month": "July", "type": "General",
           "category": "General", "sub_category": "", "index_value": "124.8", "growth_rate": "6.7"}
    with pytest.raises(C.ConsolidateError, match="no field 'index'"):
        C.keyed("iip", ds, {"rows": [row]})


def test_a_measure_with_no_series_fails_the_csv_check():
    man, lab = manifest.load("mospi"), C.labels()
    rows = [r for r in _csv_rows() if not (r["dataset"] == "iip" and r["measure"] == "index")]
    errs, _ = V.check(rows, man, lab, date(2026, 9, 10))
    assert any(e.startswith("iip: ") and "/index is declared but has no rows" in e for e in errs)


def test_a_series_that_stops_early_fails_even_if_its_code_is_current():
    man, lab = manifest.load("mospi"), C.labels()
    rows = [r for r in _csv_rows() if not (r["code"] == "nas:gva" and r["measure"] == "constant_price"
                                           and r["period"] == "2026-06-30")]
    errs, _ = V.check(rows, man, lab, date(2026, 9, 10))
    assert any("nas:gva/constant_price ends" in e for e in errs)


def test_a_missing_level_is_not_a_first_year_absence():
    man, lab = manifest.load("mospi"), C.labels()
    rows = [r for r in _csv_rows() if not (r["dataset"] == "iip" and r["measure"] == "index")]
    errs, buckets, *_ = G.check(rows, man, lab)
    assert buckets["iip:no_level"] == len(set(lab["iip"].values())) and errs


def test_one_pairing_cannot_cover_for_another():
    man, lab = manifest.load("mospi"), C.labels()
    rows = [r for r in _csv_rows() if not (r["dataset"] == "nas" and r["measure"] == "constant_price")]
    errs, buckets, *_ = G.check(rows, man, lab)
    assert buckets["nas:checked"] == 0 and any("no constant_price at all" in e for e in errs)


# ── population + plausibility review, 2026-09-28 ─────────────────────────────

def test_known_bad_control_nas_is_caught_too():
    """The first catch rate was IIP-only. NAS has quarterly steps, a 4-period lag and integer
    levels (a wider tolerance), so it is measured on its own, by enumeration: for every NAS code
    with a printed rate, (a) its constant-price level one quarter late, (b) current and constant
    swapped. Each must fail the stage."""
    rows, man, lab = _csv_rows(), manifest.load("mospi"), C.labels()
    codes = sorted(set(lab["nas"].values()) - set(man["datasets"]["nas"]["no_printed_rate_codes"]))
    latest = max(r["period"] for r in rows if r["dataset"] == "nas")
    missed = []
    for code in codes:
        shifted = [{**r, "period": V.next_period(r["period"], 3)}
                   if (r["dataset"], r["code"], r["measure"]) == ("nas", code, "constant_price") else r
                   for r in rows]
        shifted = [r for r in shifted if not (r["dataset"] == "nas" and r["period"] > latest)]
        swap = {"constant_price": "current_price", "current_price": "constant_price"}
        swapped = [{**r, "measure": swap.get(r["measure"], r["measure"])}
                   if (r["dataset"], r["code"]) == ("nas", code) else r for r in rows]
        for label, bad in (("shift", shifted), ("swap", swapped)):
            if not G.check(bad, man, lab)[0]:
                missed.append(f"{code}:{label}")
    assert not missed, f"undetected: {missed}"


def test_a_level_series_that_starts_late_is_not_a_first_year_absence():
    man, lab = manifest.load("mospi"), C.labels()
    rows = [r for r in _csv_rows() if not (r["code"] == "nic:24" and r["measure"] == "index"
                                           and r["period"] < "2025-06-30")]
    errs, *_ = G.check(rows, man, lab)
    assert any("nic:24 index starts" in e for e in errs)


def test_a_row_without_its_own_base_fails_consolidate():
    ds = manifest.load("mospi")["datasets"]["cpi"]
    row = {"series": "CPI (General) Combined", "period": "2026-07-31", "index": "107.94",
           "inflation": "4.45", "status": "P"}
    with pytest.raises(C.ConsolidateError, match="no base_year"):
        C.keyed("cpi", ds, {"rows": [row]})


def test_cpi_rows_carry_the_base_of_their_own_page():
    assert {r["base_year"] for r in cpi_release.parse(TWO_MONTHS)} == {"2024"}


def test_cpi_swapped_index_and_inflation_lines_fail():
    lines = TWO_MONTHS.splitlines()
    swapped = "\n".join(lines[:3] + [lines[4], lines[3]])
    with pytest.raises(ValueError, match="out of place"):
        cpi_release.parse(swapped)


def test_an_unexpected_unit_fails_the_fetch():
    rows = [{"base_year": "2022-23", "unit": "₹ Lakh Crore"}]
    with pytest.raises(A.FetchError, match="unit"):
        A.check_page(page(rows, 1, 1), BASE, "u", verify=[{"field": "unit", "expect": "₹ Crore"}])


def test_every_nas_request_verifies_its_unit():
    for req in manifest.load("mospi")["datasets"]["nas"]["requests"]:
        assert any(v["field"] == "unit" for v in req.get("verify", [])), req["filters"]


SPLIT_LABEL = """PRESS RELEASE OF CONSUMER PRICE INDEX ON BASE 2024=100 FOR AUGUST, 2026
                                   July, 2026 (Final)                       August, 2026 (Provisional)
                         Rural            Urban         Combined         Rural      Urban       Combined
                        CPI
                                         4.84             3.96            4.45          5.23        4.31          4.82
                      (General)
         Inflation
                         CFPI            5.79             5.05            5.52          6.13        5.64          5.95
                        CPI
                                        108.34           107.45          107.95        109.27      108.07        108.74
                      (General)
          Index
                         CFPI           109.21           109.70          109.39        110.70      110.72        110.71
"""


def test_cpi_august_2026_layout_older_month_first_and_a_wrapped_label():
    """Aug 2026 printed the older month first and wrapped "CPI (General)" around the numbers.
    Months follow the header, and CFPI rows are never taken for CPI."""
    rows = cpi_release.parse(SPLIT_LABEL)
    assert [(r["period"], r["index"], r["inflation"], r["status"]) for r in rows] == [
        ("2026-07-31", "107.95", "4.45", "F"), ("2026-08-31", "108.74", "4.82", "P")]


# ── CPI from two publications: press release + dashboard workbook ─────────────

import io                                                # noqa: E402
import cpi_dashboard                                     # noqa: E402

SPLIT_HEADER = """PRESS RELEASE OF CONSUMER PRICE INDEX ON BASE 2024=100 FOR FEBRUARY, 2026
                                                                                         January, 2026 (Final)
                                            February, 2026 (Provisional)
                                           Rural      Urban          Combined Rural             Urban       Combined
                       CPI (General)
      Inflation (%)                         3.37          3.02           3.21         2.73         2.75           2.74
                             CFPI
                                            3.46          3.48           3.47         1.96         2.44           2.13
                       CPI (General)
                                           104.74       104.37         104.57        104.59       104.28         104.45
          Index
                             CFPI          103.79       104.04         103.88        103.89       104.31         104.04
"""


def test_cpi_february_2026_layout_months_ordered_by_column_not_line():
    """Feb 2026 printed January (the RIGHT column) on the line above February (the LEFT one)."""
    rows = cpi_release.parse(SPLIT_HEADER)
    assert [(r["period"], r["index"], r["inflation"], r["status"]) for r in rows] == [
        ("2026-02-28", "104.57", "3.21", "P"), ("2026-01-31", "104.45", "2.74", "F")]


def test_a_release_is_placed_by_its_own_date():
    assert cpi_release.published("x\n  Dated 14th September, 2026\n") == "2026-09-14"
    with pytest.raises(ValueError, match="Dated"):
        cpi_release.published("no date here")
    assert cpi_dashboard.published("CPI updated_July_ 2026_Dashboard Data-12.08.2026.xlsx") == "2026-08-12"
    with pytest.raises(ValueError, match="dd.mm.yyyy"):
        cpi_dashboard.published("CPI dashboard.xlsx")


def workbook(rows, sheet="CPI Combined ", header=("Year", "Month", "State", "Description", "Combined")):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(("All India Consumer Price Index",))
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_the_workbook_reads_mixed_text_and_numbers():
    rows = cpi_dashboard.parse(workbook([
        ("2025", "December", "ALL India", "General Index (All Groups)", "104.10"),
        (2026, "January", "ALL India", "General Index (All Groups)", 104.45)]))
    assert [(r["period"], r["index"], r["status"], r["base_year"]) for r in rows] == [
        ("2025-12-31", "104.10", "F", "2024"), ("2026-01-31", "104.45", "P", "2024")]


@pytest.mark.parametrize("rows, match", [
    ([("2026", "January", "Assam", "General Index (All Groups)", 104.4)], "unexpected row"),
    ([("2026", "January", "ALL India", "General Index (All Groups)", 198.0 * 2)], "not a base-2024"),
    ([("2026", "Feb", "ALL India", "General Index (All Groups)", 104.4)], "unexpected period"),
    ([("2026", "February", "ALL India", "General Index (All Groups)", 104.5),
      ("2026", "January", "ALL India", "General Index (All Groups)", 104.4)], "out of order"),
])
def test_a_workbook_it_does_not_recognise_raises(rows, match):
    with pytest.raises(ValueError, match=match):
        cpi_dashboard.parse(workbook(rows))


def test_a_workbook_without_the_combined_sheet_raises():
    with pytest.raises(ValueError, match="CPI Combined"):
        cpi_dashboard.parse(workbook([], sheet="CPI Rural"))


def test_each_publication_is_read_with_its_own_measures():
    """The workbook has no inflation column; it must not be read as one that left it blank."""
    ds = manifest.load("mospi")["datasets"]["cpi"]
    row = {"series": "CPI (General) Combined", "base_year": "2024", "period": "2026-01-31",
           "index": "104.45", "status": "F"}
    got = C.keyed("cpi", ds, {"source": "dashboard_xlsx", "rows": [row]})
    assert list(got) == [("CPI (General) Combined", "2026-01-31", "index")]
    with pytest.raises(C.ConsolidateError, match="no field 'inflation'"):
        C.keyed("cpi", ds, {"source": "release_pdf", "rows": [row]})


def test_a_level_jump_between_publications_fails():
    """The workbook states no base; a 2012-base index (~200) arriving over a base-2024 one must stop
    the run, not warn as a revision."""
    k = ("CPI (General) Combined", "2026-01-31", "index")
    C.diff("cpi", "increment", {k: ("104.46", "P", "2024")}, {k: ("104.45", "F", "2024")}, 1.0)
    with pytest.raises(C.ConsolidateError, match="beyond"):
        C.diff("cpi", "increment", {k: ("104.46", "P", "2024")}, {k: ("198.0", "F", "2024")}, 1.0)


def test_releases_merge_in_publication_order_not_fetch_order(monkeypatch, tmp_path):
    """The workbook (published 12 Aug) fetched AFTER the August release (14 Sep) must not put
    July's provisional 107.94 back over its final 107.95."""
    def rel(published, rows, source):
        return {"source": source, "published": published, "rows": rows}
    jul = {"series": "CPI (General) Combined", "base_year": "2024", "period": "2026-07-31"}
    aug_pdf = rel("2026-09-14", [{**jul, "index": "107.95", "inflation": "4.45", "status": "F"}], "release_pdf")
    workbook_ = rel("2026-08-12", [{**jul, "index": "107.94", "status": "P"}], "dashboard_xlsx")
    d = tmp_path / "cpi"
    d.mkdir()
    (d / "2026-09-28T010000Z.json.gz").write_bytes(R.dump(aug_pdf))        # fetched first
    (d / "2026-09-28T020000Z.json.gz").write_bytes(R.dump(workbook_))      # fetched later
    monkeypatch.setattr(R, "releases_dir", lambda: tmp_path)
    ds = manifest.load("mospi")["datasets"]["cpi"]
    order = [doc["published"] for _, doc in C.ordered("cpi", ds)]
    assert order == ["2026-08-12", "2026-09-14"]


def test_known_bad_control_cpi_is_caught():
    """CPI's check exists only because the workbook gives a year back. Measured the same way:
    the index one month late must fail, and so must a year-back level taken from the wrong year."""
    rows, man, lab = _csv_rows(), manifest.load("mospi"), C.labels()
    latest = max(r["period"] for r in rows if r["dataset"] == "cpi")
    shifted = [{**r, "period": V.next_period(r["period"], 1)}
               if (r["dataset"], r["measure"]) == ("cpi", "index") else r for r in rows]
    shifted = [r for r in shifted if not (r["dataset"] == "cpi" and r["period"] > latest)]
    assert G.check(shifted, man, lab)[0]
    assert G.check(_csv_rows(), man, lab)[1]["cpi:checked"] == 1
