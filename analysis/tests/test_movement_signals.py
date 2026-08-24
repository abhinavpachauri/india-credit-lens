"""Movement family — compute, the coherence router, and the pairing rule.

Every regime is driven EXPLICITLY. The lesson from the payments migration is that a
branch behind a condition the current month does not meet is invisible to any golden:
SIBC is coherence 1.000 in all ten observed periods, so the contested and handover
sentences would never once render in a test that only asserts against live data.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import relational_insights as RI          # noqa: E402
from signals.compute import sibc                    # noqa: E402

MAIN = {"parent_code": "III", "statement": "Statement 1", "child_level": 1,
        "entity_type": "sector", "window": 12}


def _rows(fn, period="2026-06-30"):
    return fn(MAIN, period, sibc._load_df())


def _by(rows, entity_type):
    return {r["entity_id"]: r["value"] for r in rows if r["entity_type"] == entity_type}


# ── compute ───────────────────────────────────────────────────────────────────

def test_momentum_emits_children_plus_net_gross_coherence():
    rows = _rows(sibc.csv_sector_momentum)
    agg = _by(rows, "aggregate")
    assert set(agg) == {"total", "gross_movement", "coherence"}
    sectors = _by(rows, "sector")
    assert len(sectors) == 4
    assert abs(sum(sectors.values()) - agg["total"]) < 1.0
    assert agg["gross_movement"] >= abs(agg["total"])


def test_coherence_is_one_when_every_sector_moves_the_same_way():
    """Not a fact about the code — a fact about Indian credit right now. If this
    ever fails, a sector has started contracting and the card should switch regime."""
    agg = _by(_rows(sibc.csv_sector_momentum), "aggregate")
    assert agg["coherence"] == 1.0


def test_allocation_shares_sum_to_a_hundred_and_match_contribution_when_aligned():
    rows = _rows(sibc.csv_sector_allocation)
    alloc, contrib = _by(rows, "alloc"), _by(rows, "contribution")
    assert len(alloc) == 4 and len(contrib) == 4
    assert abs(sum(alloc.values()) - 100.0) < 0.01
    for k in alloc:                       # at coherence 1.0 net == gross
        assert abs(alloc[k] - contrib[k]) < 1e-6


def test_allocation_withholds_alloc_rows_below_the_coherence_threshold(monkeypatch):
    """The gated branch, driven directly — live SIBC data never reaches it.

    Contribution rows must SURVIVE: below the threshold the reading changes, it is
    never suppressed (signals/README.md — coherence routes, it does not gate)."""
    monkeypatch.setattr(sibc, "_deltas",
                        lambda p, per, df: ({"A": 100.0, "B": -90.0}, 10.0, 190.0))
    rows = sibc.csv_sector_allocation(MAIN, "2026-06-30", sibc._load_df())
    assert _by(rows, "alloc") == {}
    contrib = _by(rows, "contribution")
    assert set(contrib) == {"A", "B"}
    # rows are stored rounded to 4 dp (compute/common.row) — match the storage
    assert abs(contrib["A"] - 100 * 100.0 / 190.0) < 1e-3


def test_acceleration_is_signed_and_carries_an_aggregate():
    rows = _rows(sibc.csv_sector_acceleration)
    assert _by(rows, "aggregate").get("total") is not None
    assert all(r["unit"] == "pp" for r in rows)


# ── the router: all three regimes ─────────────────────────────────────────────

FOUR = {"Services": 10.0, "Personal Loans": 9.0, "Industry": 7.0, "Agriculture": 4.0}
SPEED = {k: 15.0 + i for i, k in enumerate(FOUR)}
ACCEL = {k: 1.0 - i * 0.3 for i, k in enumerate(FOUR)}


def _alloc(d, net):
    return {k: 100 * v / net for k, v in d.items()}


def test_aligned_regime_reports_where_the_new_units_went():
    net = sum(FOUR.values())
    ins = RI.movement_insight(_alloc(FOUR, net), _alloc(FOUR, net), FOUR,
                              net, net, 1.0, ACCEL, SPEED, "bank credit")
    assert ins["insight_kind"] == "movement_allocation"
    assert "33.3%" in ins["body"]


def test_contested_regime_names_the_dissenters_instead():
    mom = {"Services": 100.0, "Industry": 60.0, "Agriculture": -25.0}
    net, gross = 135.0, 185.0
    ins = RI.movement_insight({}, {k: 100 * v / gross for k, v in mom.items()}, mom,
                              net, gross, net / gross, ACCEL, SPEED, "bank credit")
    assert ins["insight_kind"] == "movement_momentum"
    assert "Agriculture" in ins["title"]
    assert "moved against" in ins["title"]


def test_handover_regime_leads_with_the_transfer_not_the_net():
    mom = {"Public Sector Banks": 204595.0, "Private Sector Banks": -257290.0}
    net, gross = -52695.0, 461885.0
    ins = RI.movement_insight({}, {k: 100 * v / gross for k, v in mom.items()}, mom,
                              net, gross, abs(net) / gross, ACCEL, SPEED, "POS terminals")
    assert ins["insight_kind"] == "movement_momentum"
    assert "shed ground to" in ins["title"]
    assert "transfer between members, not a change in size" in ins["body"]
    # No numeric coherence in published prose — Check 2g cannot ground a derived
    # ratio, and it caught exactly this on the infrastructure card (77.8 = 100 x 0.778).
    assert "%" not in ins["chain"][1]


def test_regime_boundaries_are_exactly_the_documented_thresholds():
    assert RI._regime(0.90) == "aligned"
    assert RI._regime(0.8999) == "contested"
    assert RI._regime(0.50) == "contested"
    assert RI._regime(0.4999) == "handover"


# ── the pairing rule ──────────────────────────────────────────────────────────

def test_a_share_is_never_rendered_without_its_speed_and_acceleration():
    """The rule exists because a falling share of a FASTER-growing flow reads as
    decline — personal loans fell 44.7% -> 30.1% while accelerating."""
    net = sum(FOUR.values())
    ins = RI.movement_insight(_alloc(FOUR, net), _alloc(FOUR, net), FOUR,
                              net, net, 1.0, {}, {}, "bank credit")
    assert ins is None, "no entity had speed+acceleration, so nothing may be quoted"


def test_least_accelerating_sector_is_stated_as_overtaken_not_shrinking():
    net = sum(FOUR.values())
    ins = RI.movement_insight(_alloc(FOUR, net), _alloc(FOUR, net), FOUR,
                              net, net, 1.0, ACCEL, SPEED, "bank credit")
    assert "not a retreat" in ins["body"]


# ── Layer 2: mix state (SYSTEM_MODEL_SPEC §16 Step 2b) ────────────────────────

def test_mix_state_names_where_money_is_going_not_the_biggest_mover():
    """`toward` must be the biggest POSITIVE tilt. argmax|tilt| on the main-sector cut picks
    Personal Loans at -4.9pp — the child money is moving AWAY from — and reporting that as the
    lead inverts the finding this whole family exists to state."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    st = json.loads((root / "rbi_sibc" / "merged" / "system_state_2026-07-31.json").read_text())
    main = st["mix_states"]["sibc-main-momentum"]
    assert main["toward"] == "Services"
    assert main["away_from"] == "Personal Loans"
    assert main["toward_tilt_pp"] > 0
    assert main["mix_state"] == "steered"


def test_mix_states_are_keyed_by_cut_so_both_industry_decompositions_survive():
    """Industry by size (Statement 1) and by type (Statement 2) hang off the SAME entity node.
    Keying by entity would drop one of two genuinely different mixes."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    ms = json.loads((root / "rbi_sibc" / "merged" / "system_state_2026-07-31.json").read_text())["mix_states"]
    size, typ = ms["sibc-ind-size-momentum"], ms["sibc-ind-type-momentum"]
    assert size["entity_urn"] == typ["entity_urn"], "same node — that is the point"
    assert size["decomposition"] != typ["decomposition"]


def test_a_contested_cut_reports_no_destination():
    """Below the aligned threshold there is no honest 'steered toward' — the parts disagree."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    ms = json.loads((root / "rbi_sibc" / "merged" / "system_state_2026-07-31.json").read_text())["mix_states"]
    infra = ms["sibc-infra-sub-momentum"]
    assert infra["mix_state"] == "contested"
    assert infra["toward"] is None and infra["toward_tilt_pp"] is None
