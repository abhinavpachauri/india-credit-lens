"""The driver register (SYSTEM_MODEL_SPEC §16 Step 6c): seed, derived status, validation.

The validator is a guard, so it is measured by injection: the seeded register is the known-good
control (0 errors), and each rule is shown to catch one injected fault.
"""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import explainability as X          # noqa: E402

REG = X.seed("sibc")


def _one(mutate):
    reg = copy.deepcopy(REG)
    mutate(reg)
    return X.validate("sibc", reg)


def test_the_seeded_register_validates():
    assert X.validate("sibc", REG) == []


def test_every_line_of_the_model_is_in_the_register():
    model = X.gs.load_json(X.gs.pipeline_cfg("sibc")["model"])
    assert set(REG["lines"]) == {n["urn"] for n in X.lines(model)}


def _first(reg, cls=None, has=None):
    return next(h for h in reg["hypotheses"]
                if (cls is None or h["class"] == cls) and (has is None or has in h["driver"]))


@pytest.mark.parametrize("name, mutate, needle", [
    ("a line with no applies list",
     lambda r: r["lines"].pop(next(iter(r["lines"]))), "has no applies list"),
    ("not applicable without a reason",
     lambda r: next(iter(r["lines"].values()))["applies"]["funding"].pop("reason"), "without a reason"),
    ("a computed kind given a hypothesis",
     lambda r: _first(r).update({"class": "arithmetic"}), "class must be one of"),
    ("approved without a sign",
     lambda r: _first(r, has="source").update({"approved": {"by": "user"}}), "without a declared sign"),
    ("a fixed lag beyond the 0-9 window",
     lambda r: _first(r, has="series").update({"approved": {"by": "user"}, "lag": 12}), "a fixed lag must be"),
    ("a series the reference CSV lacks",
     lambda r: _first(r, has="series").update({"driver": {"pipeline": "mospi", "series": ["wpi/nope"]}}),
     "not in the MoSPI CSV"),
    ("a hypothesis in a not-applicable cell",
     lambda r: _first(r, cls="credit_price").update({"line": "icl:sibc/Statement1/II"}), "marked not applicable"),
    ("a line outside the model",
     lambda r: _first(r).update({"line": "icl:sibc/Statement1/zz"}), "not in the model"),
    ("a duplicate id",
     lambda r: r["hypotheses"][1].update({"id": r["hypotheses"][0]["id"]}), "duplicate id"),
    ("a reference to a driver result that does not exist",
     lambda r: _first(r).setdefault("tests", []).append("driver:h9999@2026-01-01#1"), "not recorded"),
    ("admitted without a supported test",
     lambda r: _first(r, has="source").update({"admitted": {"by": "user"}}), "admitted without a supported test"),
])
def test_each_rule_catches_its_injected_fault(name, mutate, needle):
    assert any(needle in e for e in _one(mutate)), name


# ── status is derived, never typed ────────────────────────────────────────────────────────

def test_status_comes_from_tests_then_data():
    h = {"driver": {"source": "x"}, "tests": []}
    assert X.status(h, {}) == "data_missing"
    assert X.status({"driver": {"pipeline": "mospi", "series": ["a"]}, "tests": []}, {}) == "ready"
    assert X.status({**h, "tests": ["t1", "t2"]}, {"t1": "supported", "t2": "not_supported"}) == "not_supported"
    assert X.status({**h, "admitted": {"by": "user"}}, {}) == "admitted"


def test_a_deflator_is_imported_as_a_driver_only_where_prices_apply():
    """CPI on personal loans exists to show real credit; it is not a claim that prices drive them."""
    assert not any(h["line_label"] == "Vehicle Loans" and h["class"] == "input_prices"
                   for h in REG["hypotheses"])
    assert any(h["line_label"] == "Fertiliser" and h["class"] == "input_prices" and "series" in h["driver"]
               for h in REG["hypotheses"])


def test_every_applicable_cell_has_at_least_one_hypothesis():
    """A gap is a placeholder naming its source, never an empty cell that reads as complete."""
    filled = {(h["line"], h["class"]) for h in REG["hypotheses"]}
    for urn, line in REG["lines"].items():
        for cls, cell in line["applies"].items():
            if cell["status"] == "applies":
                assert (urn, cls) in filled, (line["label"], cls)


# ── step 2: the completeness grid ─────────────────────────────────────────────────────────

def test_a_cell_is_complete_only_when_every_hypothesis_in_it_is_tested():
    yes = {"status": "applies"}
    tested = {"driver": {"pipeline": "mospi", "series": ["a"]}, "tests": ["t"]}
    untested = {"driver": {"source": "x"}, "tests": []}
    assert X.cell([tested], {"t": "not_supported"}, yes) == ("✗", True)
    assert X.cell([tested], {"t": "supported"}, yes) == ("✓", True)
    assert X.cell([tested, untested], {"t": "supported"}, yes) == ("✓…", False)
    assert X.cell([untested], {}, yes) == ("·", False)
    assert X.cell([], {}, {"status": "not_applicable", "reason": "r"}) == ("–", True)


def test_the_grid_counts_every_applicable_cell_once():
    import json
    term, md = X.report("sibc", with_moves=False)
    reg = json.loads(X.register_path("sibc").read_text())
    for k in X.OUTSIDE:
        n = sum(1 for l in reg["lines"].values() if l["applies"][k]["status"] == "applies")
        assert f"/{n:2}" in term or f"/{n}" in term, k


# ── step 3: the generic driver test's controls (spec §16 Step 6c) ──────────────────────────

import random as _random                                          # noqa: E402
from core import relationship_test as RT                           # noqa: E402


def _series(n=30, lag=1, slope=0.8, noise=0.3, seed=7):
    """A driver, a credit line that follows it `lag` months later with `slope`, and a tide."""
    rnd = _random.Random(seed)
    a = {k: rnd.gauss(0, 1) for k in range(n)}
    t = {k: rnd.gauss(0, 1) for k in range(n + lag)}
    b = {k + lag: slope * a[k] + 0.2 * t[k + lag] + rnd.gauss(0, noise) for k in range(n)}
    return a, b, t


def test_a_planted_driver_is_supported_with_its_slope():
    a, b, t = _series()
    r = RT.judge(a, b, t, t, sign=1, lag=1)
    assert r["verdict"] == "supported" and 0.6 < r["slope"] < 1.0


def test_the_same_driver_shuffled_is_not_supported():
    a, b, t = _series()
    vals = list(a.values()); _random.Random(3).shuffle(vals)
    r = RT.judge(dict(zip(a, vals)), b, t, t, sign=1, lag=1)
    assert r["verdict"] in ("not_supported", "too_short")


def test_a_flipped_sign_reads_opposite():
    a, b, t = _series()
    assert RT.judge(a, b, t, t, sign=-1, lag=1)["verdict"] == "opposite"


def test_the_wrong_lag_is_not_rescued_by_the_right_one():
    """Other lags are reported, never used: declared at lag 0, the lag-1 link does not count."""
    a, b, t = _series()
    r = RT.judge(a, b, t, t, sign=1, lag=0)
    assert r["verdict"] != "supported" and r["lags"][1]["p"] < 0.05


def test_a_short_history_is_too_short_not_a_null():
    a, b, t = _series(n=8)
    assert RT.judge(a, b, t, t, sign=1, lag=1)["verdict"] == "too_short"


# ── each line's own delay: found on earlier months, confirmed on later ones ────────────────

@pytest.mark.parametrize("lag", [1, 5])
def test_a_planted_delay_is_found_and_confirmed(lag):
    """Construction is not consumer durables: a 5-month catch-up is found as surely as a 1-month one."""
    a, b, t = _series(n=60, lag=lag, seed=11)
    r = RT.discover_confirm(a, b, t, t, sign=1)
    assert r["discovery"]["lag"] == lag and r["verdict"] == "supported"


def test_a_shuffled_driver_finds_a_best_delay_but_does_not_confirm():
    a, b, t = _series(n=60, lag=3, seed=11)
    vals = list(a.values()); _random.Random(5).shuffle(vals)
    r = RT.discover_confirm(dict(zip(a, vals)), b, t, t, sign=1)
    assert r["discovery"]["lag"] is not None and r["verdict"] != "supported"


def test_confirmation_never_reads_the_discovery_months():
    a, b, t = _series(n=60, lag=2, seed=11)
    first = RT.discover_confirm(a, b, t, t, sign=1)
    cut, lag = first["discovery"]["cutoff"], first["discovery"]["lag"]
    scrambled = {k: (v * -3 if k <= cut else v) for k, v in b.items()}
    again = RT.discover_confirm(a, scrambled, t, t, sign=1, cutoff=cut, lag=lag)
    assert again["lags"][lag] == first["lags"][lag]


def test_a_history_too_short_to_split_is_too_short():
    a, b, t = _series(n=15, lag=1)
    assert RT.discover_confirm(a, b, t, t, sign=1)["verdict"] == "too_short"
