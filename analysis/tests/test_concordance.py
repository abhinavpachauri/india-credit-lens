"""
test_concordance.py — the credit ↔ real-economy join, and the check that keeps it honest
───────────────────────────────────────────────────────────────────────────────────────
A wrong match still yields a plausible percentage, so nothing downstream could catch it. Each rule
of cross/validate_concordance.py is pinned by a copy of the real file broken in exactly one way.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from cross import validate_concordance as VC                          # noqa: E402
from core import absence                                               # noqa: E402

REAL = VC.CONCORDANCE_DIR / "sibc__mospi.json"
STEEL = "icl:sibc/Statement2/2.13.1"
FOOD = "icl:sibc/Statement2/2.2"
INDUSTRY = "icl:sibc/Statement1/2"


def run(tmp_path, mutate=None, name="sibc__mospi.json"):
    doc = json.loads(REAL.read_text())
    if mutate:
        mutate(doc)
    p = tmp_path / name
    p.write_text(json.dumps(doc))
    return VC.check_file(p)


def test_the_committed_concordance_is_valid():
    errs, notes = VC.check_file(REAL)
    assert not errs, errs
    assert any("requires_signals: false" in n for n in notes), "the phase-3 flag must be visible"


def test_a_part_left_out_fails_instead_of_vanishing(tmp_path):
    errs, _ = run(tmp_path, lambda d: d["parts"].pop(STEEL))
    assert any(STEEL in e and "missing" in e for e in errs)


def test_a_part_the_credit_data_does_not_have_fails(tmp_path):
    errs, _ = run(tmp_path, lambda d: d["parts"].update({"icl:sibc/Statement2/2.99": d["parts"][FOOD]}))
    assert any("2.99" in e for e in errs)


def test_a_cut_parent_is_a_part_too(tmp_path):
    errs, _ = run(tmp_path, lambda d: d["parts"].pop(INDUSTRY))
    assert any(INDUSTRY in e and "missing" in e for e in errs)


@pytest.mark.parametrize("series, match", [
    ("wpi/nic:99", "has no"),                  # no such code
    ("iip/nic:10", "cannot serve as deflator"),  # IIP is output, not a price
    ("gdp/nic:10", "names no reference dataset"),
])
def test_a_series_that_does_not_measure_the_part_fails(tmp_path, series, match):
    errs, _ = run(tmp_path, lambda d: d["parts"][FOOD].update({"deflator": {"series": [series]}}))
    assert any(match in e for e in errs), errs


def test_a_monthly_part_matched_to_a_quarterly_series_fails(tmp_path):
    errs, _ = run(tmp_path, lambda d: d["parts"][FOOD].update(
        {"output": {"series": ["nas/nas:manufacturing"]}}))
    assert any("quarterly" in e and "cadence_mismatch" in e for e in errs)


def test_an_undeclared_reason_fails(tmp_path):
    errs, _ = run(tmp_path, lambda d: d["parts"][STEEL].update({"output": {"absent": "not_released"}}))
    assert any("not a static reason" in e for e in errs), "a per-period reason must not be declared"


def test_an_approximation_on_a_leaf_fails(tmp_path):
    errs, _ = run(tmp_path, lambda d: d["parts"][STEEL].update({"approximate": "nonfood_vs_gdp"}))
    assert any("leaf" in e for e in errs)


def test_several_series_need_a_declared_combination(tmp_path):
    two = {"series": ["iip/nic:24", "iip/nic:25"]}
    errs, _ = run(tmp_path, lambda d: d["parts"]["icl:sibc/Statement2/2.13"].update({"output": two}))
    assert any("need combine" in e for e in errs)
    errs, _ = run(tmp_path, lambda d: d["parts"]["icl:sibc/Statement2/2.13"].update(
        {"output": {**two, "combine": "sum"}}))
    assert any("only NAS levels are additive" in e for e in errs)


def test_weights_must_equal_the_cited_table(tmp_path):
    def mutate(d):
        d["sources"]["iip_2022_23"] = {"citation": "PIB PRID 2267531", "weights": {
            "iip/nic:24": 9.06, "iip/nic:25": 2.50}}
        d["parts"]["icl:sibc/Statement2/2.13"]["output"] = {
            "series": ["iip/nic:24", "iip/nic:25"], "combine": "weighted",
            "weights": {"iip/nic:24": 9.06, "iip/nic:25": 2.51}, "weight_source": "iip_2022_23"}
    errs, _ = run(tmp_path, mutate)
    assert any("differs" in e for e in errs)


def test_a_file_name_that_disagrees_with_its_pipelines_fails(tmp_path):
    errs, _ = run(tmp_path, name="nbfc__mospi.json")
    assert any("names sibc__mospi" in e for e in errs)


def test_phase_3_flag_enforces_the_registry_both_ways(tmp_path):
    errs, _ = run(tmp_path, lambda d: d.update({"requires_signals": True}))
    assert sum("1f registry entries" in e for e in errs) == len(json.loads(REAL.read_text())["cuts"])


def test_every_static_reason_in_the_file_is_in_the_closed_list():
    doc = json.loads(REAL.read_text())
    used = {p[r]["absent"] for p in doc["parts"].values() for r in ("output", "deflator") if "absent" in p[r]}
    assert used <= set(absence.STATIC)
    assert not set(absence.STATIC) & set(absence.PER_PERIOD)


# ── absence review, 2026-09-29 ────────────────────────────────────────────────

def test_a_cut_dropped_from_the_file_fails(tmp_path):
    """Dropping a whole cut (its entry and its parts) used to leave a smaller file that passed:
    the required cuts are the credit manifest's, not the file's own list."""
    def drop(d):
        d["cuts"].pop("sibc-infra-sub")
        for u in [u for u in d["parts"] if u.startswith("icl:sibc/Statement2/2.18.")]:
            d["parts"].pop(u)
    errs, _ = run(tmp_path, drop)
    assert any("sibc-infra-sub" in e and "requires it" in e for e in errs)


def test_1f_entries_with_the_flag_still_off_fail(tmp_path, monkeypatch):
    """The flag cannot outlive its reason: once 1f entries exist, leaving it false fails."""
    real = VC.registry_cuts
    monkeypatch.setattr(VC, "registry_cuts",
                        lambda p: (real(p)[0], {"sibc-main": ["csv_sector_real_growth"]}))
    errs, _ = run(tmp_path)
    assert any("requires_signals is false" in e for e in errs)


def test_the_verdict_line_says_when_the_registry_check_is_off(capsys):
    assert VC.main.__code__                                        # the gate shows this one line
    import sys as _s
    argv = _s.argv
    _s.argv = ["validate_concordance.py", "--reference", "mospi"]
    try:
        assert VC.main() == 0
    finally:
        _s.argv = argv
    last = [l for l in capsys.readouterr().out.splitlines() if "✓" in l][-1]
    assert "registry check OFF" in last and last.index("OFF") < 60, "must survive the gate's 60-char note"


def test_every_primary_pipeline_with_a_concordance_runs_it_in_its_own_gate():
    """The credit data can break the join (a new or renamed code), so the credit gate runs it too."""
    from core import manifest
    for f in VC.CONCORDANCE_DIR.glob("*__*.json"):
        credit, reference = f.stem.split("__")
        for p in (credit, reference):
            assert any(s.get("core") == "validate_concordance" for s in manifest.load(p)["gate"]), p


# ── population review, 2026-09-29: enumerated, not sampled ───────────────────

_DOC = json.loads(REAL.read_text())


@pytest.mark.parametrize("part", sorted(_DOC["parts"]))
def test_every_part_dropped_is_caught(tmp_path, part):
    errs, _ = run(tmp_path, lambda d: d["parts"].pop(part))
    assert any(part in e and "missing" in e for e in errs)


@pytest.mark.parametrize("stem", sorted(_DOC["cuts"]))
def test_every_cut_dropped_with_its_parts_is_caught(tmp_path, stem):
    def drop(d):
        cut = d["cuts"].pop(stem)
        prefix = f"icl:sibc/{cut['statement'].replace(' ', '')}/{cut['parent_code']}."
        for u in [u for u in d["parts"] if u.startswith(prefix)]:
            d["parts"].pop(u)
    errs, _ = run(tmp_path, drop)
    assert any(stem in e for e in errs)


def test_a_registry_cut_nobody_classified_fails(tmp_path, monkeypatch):
    real = VC.registry_cuts
    monkeypatch.setattr(VC, "registry_cuts",
                        lambda p: (real(p)[0] | {("Statement 2", "2.15")}, real(p)[1]))
    errs, _ = run(tmp_path)
    assert any("2.15" in e and "neither includes nor excludes" in e for e in errs)


def _weighted(d, part, codes, assign):
    table = {"iip/nic:26": 2.01, "iip/nic:27": 3.22, "iip/nic:28": 5.06, "iip/nic:29": 6.47, "iip/nic:30": 2.03}
    d["sources"]["iip_2022_23"] = {"citation": "test", "weights": table, "assign": assign}
    d["parts"][part]["output"] = {"series": codes, "combine": "weighted",
                                  "weights": {c: table[c] for c in codes}, "weight_source": "iip_2022_23"}


def test_a_weighted_code_moved_to_another_part_fails(tmp_path):
    """Correct weights, wrong part: nic:27 taken from Engineering into Vehicles."""
    assign = {"icl:sibc/Statement2/2.14": ["iip/nic:26", "iip/nic:27", "iip/nic:28"],
              "icl:sibc/Statement2/2.15": ["iip/nic:29", "iip/nic:30"]}
    def mutate(d):
        _weighted(d, "icl:sibc/Statement2/2.14", ["iip/nic:26", "iip/nic:28"], assign)
        _weighted(d, "icl:sibc/Statement2/2.15", ["iip/nic:29", "iip/nic:30", "iip/nic:27"], assign)
    errs, _ = run(tmp_path, mutate)
    assert sum("assignment" in e for e in errs) == 2


def test_a_weighted_code_in_two_parts_fails(tmp_path):
    assign = {"icl:sibc/Statement2/2.14": ["iip/nic:26", "iip/nic:27"],
              "icl:sibc/Statement2/2.15": ["iip/nic:29", "iip/nic:27"]}
    def mutate(d):
        _weighted(d, "icl:sibc/Statement2/2.14", ["iip/nic:26", "iip/nic:27"], assign)
        _weighted(d, "icl:sibc/Statement2/2.15", ["iip/nic:29", "iip/nic:27"], assign)
    errs, _ = run(tmp_path, mutate)
    assert any("serves one part" in e for e in errs)


def test_the_leaf_rule_reads_the_statement_too():
    """SIBC reuses codes across statements: Statement 1 '2.2' (Medium, a leaf) is not Statement 2
    '2.2' (Food Processing, a parent). Keyed on the code alone, a leaf there would pass as a parent."""
    rows, _ = VC.credit_rows("sibc")
    kids = {(r["statement"], r["parent_code"]) for r in rows}
    assert ("Statement 2", "2.2") in kids and ("Statement 1", "2.2") not in kids
