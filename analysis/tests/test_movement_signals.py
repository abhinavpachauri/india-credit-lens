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
    size, typ = ms["sibc-ind-size-momentum"], ms["sibc-industry-type-momentum"]
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


def test_priority_sector_has_a_node_to_belong_to_and_therefore_a_mix_state():
    """PSL entities are reclassification leaves with parent_code null — ten orphans. Without a
    lens node to compose into, a dimension the dashboard renders could carry movement cards but
    no Layer-2 state. `additive: false` because PSL is a lens over the primary tree, not a
    partition of it: its Agriculture is the same rupees as the main cut's."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    model = json.loads((root / "rbi_sibc" / "merged" / "system_model.json").read_text())
    lens = next(n for n in model["nodes"] if n.get("code") == "PSL")
    assert lens["additive"] is False
    assert lens["structural_role"] == "root" and lens["parent_code"] is None
    kids = [e for e in model["edges"]
            if e["type"] == "composes_into" and e["to"] == lens["id"]]
    assert len(kids) == 10
    assert {e.get("decomposition") for e in kids} == {"psl_lens"}, \
        "its own decomposition — the primary roll-up must never sum a lens"

    ms = json.loads((root / "rbi_sibc" / "merged" /
                     "system_state_2026-07-31.json").read_text())["mix_states"]
    assert ms["sibc-psl-momentum"]["entity_urn"].endswith("PSL")
    # The PROPERTY, not the count. This read `len(ms) == 7` until 2026-09-12, when widening
    # coverage to the seven sub-cuts made it 14 — a legitimate change that failed a test while
    # nothing was broken. A characterisation test pins STRUCTURE; only a golden pins values.
    import json as _json
    registry = _json.loads((root.parent / "analysis/signals/registry.json").read_text())["signals"]
    cuts = {sid for sid, sig in registry.items()
            if sig.get("pipeline") == "sibc"
            and sig.get("compute", {}).get("method") == "csv_sector_momentum"}
    missing = cuts - set(ms)
    assert not missing, f"SIBC cuts with no mix state: {sorted(missing)}"


# ── payments movement: the regimes SIBC never renders ─────────────────────────

def test_contested_prose_follows_the_sign_of_the_net():
    """The branch read "grew"/"rose" unconditionally and named the FALLERS as the
    dissenters. Correct for SIBC — credit grows in every window, and every SIBC cut runs
    coherence 0.99-1.00 so the branch never rendered. Payments POS terminals is the first
    real contested window with a negative net: the fleet shrank 1.86M while public banks
    expanded, and the card said "POS terminals rose over the past year"."""
    from core.relational_insights import movement_insight
    momentum = {"Private Sector Banks": -2_003_950, "Public Sector Banks": 146_358,
                "Small Finance Banks": 274, "Foreign Banks": -3_510}
    contribution = {k: 100.0 * v / 2_154_092 for k, v in momentum.items()}
    ins = movement_insight({}, contribution, momentum, net=-1_860_828,
                           gross=2_154_092, coherence=0.864, accel={},
                           speed={}, subject="POS terminals")
    assert "shrank" in ins["title"] and "rose" not in ins["body"]
    assert "fell over the past year" in ins["body"]
    # the dissenters are whoever moved AGAINST the total, so risers when it falls
    assert "Public Sector Banks" in ins["title"]
    assert "Private Sector Banks" not in ins["title"]


def test_a_share_of_gross_movement_is_a_magnitude():
    """Gross ignores direction by construction, so printing a signed share of it read
    "-93.0% of all the movement" — not a quantity anyone can picture."""
    from core.relational_insights import movement_insight
    momentum = {"A": -930.0, "B": 70.0}
    ins = movement_insight({}, {"A": -93.0, "B": 7.0}, momentum, net=-860.0,
                           gross=1000.0, coherence=0.86, accel={}, speed={},
                           subject="terminals")
    assert "-93.0%" not in ins["body"] and "93.0% of all the movement" in ins["body"]


def test_subject_capitalisation_preserves_existing_capitals():
    """`subject.capitalize()` lowercases the rest — "POS terminals" became "Pos terminals"."""
    from core.relational_insights import movement_insight
    ins = movement_insight({}, {"A": -93.0, "B": 7.0}, {"A": -930.0, "B": 70.0},
                           net=-860.0, gross=1000.0, coherence=0.86,
                           accel={}, speed={}, subject="POS terminals")
    assert ins["title"].startswith("POS terminals")


def test_weight_is_emitted_in_every_regime():
    """A category's share of the parent at the START of the window is direction-free and
    always computable. Payments emitted it INSIDE the coherence branch, so it vanished
    exactly when the mix was contested — and Layer 2 reads `tilt = alloc - weight`, so
    payments' two most interesting mixes (debit 0.525, POS 0.864) produced no mix state
    at all. Coherence routes; it does not gate."""
    import sqlite3
    from core.paths import ROOT
    con = sqlite3.connect(ROOT / "analysis/signals/signals.db")
    try:
        for sid in ("cc-category-allocation", "dc-category-allocation",
                    "pos-category-allocation"):
            n = con.execute(
                "SELECT COUNT(*) FROM signals WHERE pipeline='atm_pos' AND period=? "
                "AND metric_id=? AND entity_type='weight'", ("2026-06-30", sid)).fetchone()[0]
            assert n > 0, f"{sid} has no weight rows — contested mixes lose their mix state"
    finally:
        con.close()


def test_every_payments_cut_carries_a_mix_state():
    import json
    from core.paths import ROOT
    state = json.loads((ROOT / "analysis/rbi_atm_pos/merged/system_state_2026-06-30.json").read_text())
    mix = state.get("mix_states") or {}
    assert set(mix) == {"cc-category-momentum", "dc-category-momentum", "pos-category-momentum"}
    assert mix["dc-category-momentum"]["mix_state"] == "contested"


def test_an_ambiguous_reasoning_key_refuses_rather_than_guesses():
    """'{metric_id}:{entity_id}' cannot tell alloc from contribution from weight, and the
    resolver kept whichever row came last — a card citing its contribution was compared
    against a weight and reported STALE. Same class as the proximity.series bug, where a
    signal with several aggregate rows silently returned three values per period."""
    from pipelines.atm_pos.validate_atm_pos_claims import load_db_row_values
    rows = load_db_row_values("2026-06-30")
    assert rows["cc-category-allocation:Private Sector Banks"] is None    # ambiguous
    assert rows["cc-category-momentum:Private Sector Banks"] is not None  # unique


def test_the_movement_family_publishes_once_per_cut_and_not_as_scans():
    """One card per cut — never also as three separate scan cards.

    These signals had no evaluation until Jul 2026 (the family was built after the previous eval
    ran), so the generic annotation path had never seen them. The first eval that covered them
    produced duplicate ids in the same section, cards routed to the wrong dimension (services
    cards under Personal Loans), aggregate ROW NAMES rendered as entities — "gross_movement
    growing fastest at 798,500", "total growing fastest at 84.7%" — and `coherence` quoted in
    published prose, which is barred because no gate can ground it.
    """
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    feed = json.loads((root / "web/public/data/sibc_l1_annotations.json").read_text())

    cards = [(sec, c) for sec, v in feed["sections"].items()
             for c in v["insights"] + v.get("gaps", [])]

    ids = [c["id"] for _, c in cards]
    assert len(ids) == len(set(ids)), \
        f"a signal published twice: {sorted({i for i in ids if ids.count(i) > 1})}"

    # The compute layer's internal row names are not entities and must never reach a reader.
    for sec, c in cards:
        blob = json.dumps(c)
        for leaked in ("gross_movement", "coherence", "net_movement"):
            assert leaked not in blob, f"{c['id']} in {sec} leaks the internal row name {leaked!r}"

    # Every cut that publishes a movement card publishes it in its OWN section.
    from pipelines.sibc.generate_analysis_report import MOVEMENT_CUTS
    section_of = {cut.slug: cut.section for cut in MOVEMENT_CUTS}
    for slug, section in section_of.items():
        placed = [sec for sec, c in cards if c["id"] == f"sibc-{slug}-allocation"]
        assert placed in ([], [section]), \
            f"the {slug} movement card belongs in {section}, found in {placed}"


# ── the coherence threshold's outcome, not the threshold ──────────────────────

def test_no_published_alloc_exceeds_the_bound_coherence_puts_on_it():
    """The live invariant — and note what it is NOT.

    This test used to assert `|alloc| <= 100`, on the reasoning that a share cannot
    exceed the whole. That is false when the denominator is the NET: if one part
    shrinks, another can account for more than the whole net increase. In May 2026
    public banks added 204,595 POS terminals against a net of -55,885 — a share of
    -366%, and perfectly true.

    What IS provable, since a single entity's change cannot exceed the gross:

        |share_i| = |delta_i| / |net| <= gross / |net| = 1 / coherence

    That is also the only justification `coherence_min` has (0.90 -> no share past
    111%, signals/README.md). The old form stayed green only because no window in
    the store then landed between 100% and 111%; when the cut coverage widened it
    failed on 100.003%, where one category took all the growth and two others shrank
    by a rounding whisker.
    """
    import sqlite3
    from core.paths import ROOT
    con = sqlite3.connect(ROOT / "analysis/signals/signals.db")
    try:
        coh = {(pl, per, mid[: -len("-momentum")]): v for pl, per, mid, v in con.execute(
            "SELECT pipeline, period, metric_id, value FROM signals "
            "WHERE entity_type='aggregate' AND entity_id='coherence'")}
        bad, unbounded = [], []
        for pl, mid, per, eid, val in con.execute(
                "SELECT pipeline, metric_id, period, entity_id, value FROM signals "
                "WHERE entity_type='alloc'"):
            c = coh.get((pl, per, mid[: -len("-allocation")]))
            if c is None:
                unbounded.append((mid, per, eid))
            elif c > 0 and abs(val) > 100.0 / c + 0.5:
                bad.append((mid, per, eid, round(val, 1), round(100.0 / c, 1)))
    finally:
        con.close()
    assert not bad, f"allocation shares beyond their bound: {bad[:3]}"
    assert not unbounded, f"allocation shares with no coherence to bound them: {unbounded[:3]}"


def test_the_allocation_guard_rejects_an_impossible_share():
    """Drive the rule synthetically, so fixing the data can never untest the check.

    Three tests in the 2026-08-25 build became assertions that nothing is wrong once
    the defect they described was fixed. The durable shape is this pair: the live
    feed is asserted clean above, and the LOGIC is driven here against rows that will
    never exist in the database.
    """
    def offending(rows, coherence):
        """The rule under test: a share may exceed 100%, but never 100/coherence."""
        return [r for r in rows
                if r["entity_type"] == "alloc" and abs(r["value"]) > 100.0 / coherence + 0.5]

    aligned = [{"entity_type": "alloc", "entity_id": "Services", "value": 33.8},
               {"entity_type": "alloc", "entity_id": "Industry", "value": 66.2}]
    assert offending(aligned, 1.0) == []

    # Mildly contested: one part took MORE than the whole net because another shrank.
    # The old rule rejected this; it is ordinary, and at coherence 0.95 the bound is 105.3%.
    over_a_hundred = [{"entity_type": "alloc", "entity_id": "Private", "value": 104.7}]
    assert offending(over_a_hundred, 0.95) == [], "a share past 100% is legal inside its bound"

    # The whisker case that exposed the old rule: one entity took all of the growth and
    # two others shrank by a rounding amount.
    assert offending([{"entity_type": "alloc", "entity_id": "SFB", "value": 100.003}], 1.0) == []

    # The same 104.7% in a LOW-coherence window breaches its own bound (0.5 -> 200%? no:
    # pick a coherence whose bound is tighter than the value).
    assert len(offending(over_a_hundred, 0.99)) == 1, "a share past its own bound must be rejected"

    # A handover window: -460% is true at coherence 0.12 (bound 833%), and NOT an error.
    handover = [{"entity_type": "alloc", "entity_id": "Private", "value": -460.4},
                {"entity_type": "alloc", "entity_id": "Public", "value": 366.1}]
    assert offending(handover, 0.12) == [], "the handover figures are real, not defects"
    # ...but the same rows in a coherent window are impossible.
    assert len(offending(handover, 1.0)) == 2

    # contribution rows are shares of GROSS, bounded by construction, never in scope
    contribution = [{"entity_type": "contribution", "entity_id": "Private", "value": 93.0}]
    assert offending(contribution, 0.12) == []
