#!/usr/bin/env python3
"""
Unit tests for the distribution layer (DISTRIBUTION_SPEC).

The three things worth locking, because each one is a way the layer could go quietly
wrong rather than loudly wrong:

  - the CATEGORY PARTITION covers every compute method and resolves multi-signal cards
    by specificity — an unclassified method silently landing in C1 is how two slots
    start telling the same story (§2, §3)
  - PROXIMITY agrees with the compute layer's own status evaluation, and separates a
    real distance from a momentum knife edge (§6)
  - the TRACEABILITY GATE bites: invented numbers, reworded feed cards, undeclared
    derived numbers, and banned register all fail (§5, §10)

Run: python3 -m pytest analysis/tests/test_distribution.py -q
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from distribution import categories as cats             # noqa: E402
from distribution import distribution_sources as src    # noqa: E402
from distribution import generate_slot as gen           # noqa: E402
from distribution import ledger as ledger_mod           # noqa: E402
from distribution import slot_render                    # noqa: E402
from distribution.validate_distribution import check_slate  # noqa: E402
from signals import proximity                           # noqa: E402


# ── The partition ─────────────────────────────────────────────────────────────

def test_every_compute_method_is_classified():
    """A new compute method must be given a category, not defaulted into one."""
    assert cats.unclassified_methods(src.ns.load_registry()) == []


def test_precedence_picks_the_question_not_the_data():
    """A card citing a rotation signal and a level is a rotation card (§3)."""
    registry = {
        "r": {"compute": {"method": "csv_sector_rotation"}},
        "a": {"compute": {"method": "csv_sector_abs"}},
    }
    assert cats.category_of_signals(["a", "r"], registry) == "C2"
    assert cats.category_of_signals(["a"], registry) == "C1"


def test_divergence_outranks_rotation():
    registry = {
        "d": {"compute": {"method": "csv_pair_divergence"}},
        "r": {"compute": {"method": "csv_category_rotation"}},
    }
    assert cats.category_of_signals(["r", "d"], registry) == "C3"


def test_unknown_signal_yields_no_category():
    assert cats.category_of_signals(["nope"], {}) is None


# ── Proximity (C8, the only net-new compute) ──────────────────────────────────

RULES = [
    {"if": "value > prev_value and value > 0", "then": "strengthening"},
    {"if": "value > 0", "then": "active"},
    {"if": "true", "then": "declining"},
]


def test_eval_status_matches_the_compute_layer():
    """Proximity re-evaluates the same rules on hypothetical values — same answers."""
    from signals.compute.sibc import _eval_status
    for value, prev in ((5.0, 4.0), (3.0, 3.0), (-1.0, 2.0), (0.0, 0.0)):
        assert proximity.eval_status(RULES, value, prev) == _eval_status(RULES, value, prev)


def test_threshold_actually_flips_the_status():
    """The reported threshold is the edge: just past it reads differently."""
    rules = [{"if": "value > 10", "then": "strengthening"}, {"if": "true", "then": "weakening"}]
    dist = proximity._flip_point(rules, 9.0, 9.0, "weakening", span=10.0, direction=1)
    assert dist is not None
    assert proximity.eval_status(rules, 9.0 + dist, 9.0) == "strengthening"
    assert proximity.eval_status(rules, 9.0 + dist * 0.9, 9.0) == "weakening"


def test_typical_move_ignores_flat_periods():
    assert proximity.typical_move([1.0, 1.0, 3.0, 5.0]) == 2.0
    assert proximity.typical_move([2.0, 2.0, 2.0]) is None


def test_knife_edge_and_level_are_told_apart():
    """A momentum rule flips on any downtick; a level has ground to cover. Same
    arithmetic, different stories — the watchlist only wants the second."""
    levels = proximity.ranked(kind="level")
    edges = proximity.ranked(kind="knife_edge")
    assert levels and edges
    assert all(r["moves_away"] >= proximity.KNIFE_EDGE_MOVES for r in levels)
    assert all(r["moves_away"] < proximity.KNIFE_EDGE_MOVES for r in edges)
    assert not {r["signal_id"] for r in levels} & {r["signal_id"] for r in edges}


def test_ranked_is_nearest_first():
    rows = proximity.ranked(limit=10)
    assert rows == sorted(rows, key=lambda r: r["moves_away"])


def test_pp_is_spaced_so_the_extractor_can_read_it():
    """"1.9pp" backtracks to a bare 1 in the number extractor and then grounds to
    nothing; "1.9 pp" reads as 1.9. Same lesson as core.relational_insights._pp."""
    assert proximity._fmt(1.9, "pp") == "1.9 pp"
    assert proximity._fmt(62.1, "pct") == "62.1%"


def test_real_watchlist_sentences_are_never_falsely_rejected():
    """The gate must bite on invention without biting on the truth — a false rejection
    takes down the whole slot, so this is the half that keeps the calendar running."""
    from distribution.validate_distribution import _ungrounded, legit_card_texts, signal_ground_truth
    cards = legit_card_texts()
    for row in proximity.ranked(limit=15):
        legit = signal_ground_truth([row["signal_id"]]) + [
            row["value"], row["threshold_value"], row["distance"],
            row["typical_move"], row["prev_value"]]
        assert _ungrounded(proximity.sentence(row), legit, cards, row["signal_id"]) == []


def test_pair_gap_units_come_from_the_total_row():
    """A pair signal stores pp at total level and pct on its sides — don't mix them."""
    rows = {r["signal_id"]: r for r in proximity.ranked(kind=None)}
    gap = rows.get("atm-fleet-vs-withdrawal-gap")
    if gap:                      # only when that pair is present in the current db
        assert gap["unit"] == "pp"
        assert "pp" in proximity.sentence(gap)


# ── Selection ─────────────────────────────────────────────────────────────────

def _claim(cid, pipeline, where, category="C1"):
    return {"id": cid, "pipeline": pipeline, "where": where, "category": category,
            "title": cid, "body": "", "signal_ids": [cid]}


def test_diversify_spans_pipelines_rather_than_draining_one_feed():
    claims = [_claim(f"s{i}", "sibc", "bankCredit") for i in range(4)] + \
             [_claim("p1", "atm_pos", "cc"), _claim("p2", "atm_pos", "infra")]
    picked = src.diversify(claims, 4)
    assert len({c["pipeline"] for c in picked}) == 2
    assert len(picked) == 4


def test_diversify_keeps_feed_order_inside_a_bucket():
    claims = [_claim("first", "sibc", "x"), _claim("second", "sibc", "x")]
    assert [c["id"] for c in src.diversify(claims, 2)] == ["first", "second"]


def test_prioritise_floats_the_headline_signals():
    claims = [_claim("other", "sibc", "x"), _claim("lead", "sibc", "y")]
    assert src.prioritise(claims, ["lead"])[0]["id"] == "lead"


# ── Vintage (§11.1, §13.2) ────────────────────────────────────────────────────

def test_vintage_states_the_gap_when_the_pipelines_disagree():
    v = {"sibc": {"label": "June 2026"}, "atm_pos": {"label": "May 2026"}, "gap_months": 1}
    s = src.vintage_sentence(v)
    assert "June 2026 credit data" in s and "May 2026 payments data" in s
    assert "1 month ahead" in s


def test_vintage_says_so_when_they_agree():
    v = {"sibc": {"label": "May 2026"}, "atm_pos": {"label": "May 2026"}, "gap_months": 0}
    assert "same data month" in src.vintage_sentence(v)


# ── The gate — negative tests ─────────────────────────────────────────────────

def _live_slate(slot, categories):
    return gen.build_slate(slot, "2026-07-21", categories, False)


def test_live_slots_pass_the_gate():
    for slot, cat in (("1st", ["C1", "C5"]), ("7th", ["C2", "C3"]), ("28th", ["C8"])):
        slate = _live_slate(slot, cat)
        assert slate, f"{slot} produced no slate"
        assert check_slate(slate) == [], f"{slot} failed: {check_slate(slate)}"


def test_reworded_feed_card_fails():
    """Distribution curates gate-validated prose; it never rewrites it."""
    slate = _live_slate("7th", ["C2", "C3"])
    corrupted = copy.deepcopy(slate)
    corrupted["claims"][0]["body"] += " And the trend is expected to continue."
    failures = check_slate(corrupted)
    assert any("not verbatim" in f for f in failures), failures


def test_invented_number_in_generated_text_fails():
    """Our own words are scoped to the signals the claim declares."""
    slate = _live_slate("28th", ["C8"])
    corrupted = copy.deepcopy(slate)
    corrupted["claims"][0]["body"] = "The gap widened to 47.3pp this month."
    failures = check_slate(corrupted)
    assert any("ungrounded number" in f for f in failures), failures


def test_undeclared_derived_number_fails():
    """A threshold is legitimate only because the claim declares it.

    Built from a synthetic slate rather than a live slot: which watchlist rows survive
    depends on the ledger, and a negative test whose bite depends on this month's
    publishing history is not a test. Same claim twice — the only difference is whether
    the derived numbers were declared.
    """
    row = proximity.ranked(limit=1)[0]
    claim = {
        "id": row["signal_id"], "pipeline": row["pipeline"], "category": "C8",
        "title": row["title"], "body": proximity.sentence(row), "implication": "",
        "signal_ids": [row["signal_id"]], "verbatim": False, "where": None,
        "source": "signals/proximity.py",
        "extra_numbers": [row["value"], row["threshold_value"], row["distance"],
                          row["typical_move"], row["prev_value"]],
    }
    slate = {"slot": "28th", "date": "2026-08-28", "category": "C8",
             "claims": [claim], "vintage": {}, "vintage_sentence": "", "pages": 1}
    assert check_slate(slate) == [], check_slate(slate)

    undeclared = copy.deepcopy(slate)
    undeclared["claims"][0]["extra_numbers"] = []
    assert any("ungrounded number" in f for f in check_slate(undeclared))


def test_banned_register_fails_the_lint():
    problems = slot_render.lint_blurb("Credit is robust and poised to grow.")
    assert any("robust" in p for p in problems)
    assert any("poised to" in p for p in problems)


def test_billion_is_banned_in_favour_of_lakh_crore():
    assert slot_render.lint_blurb("Spending crossed 5 billion.")


def test_sebi_guardrail_survived_the_reply_desk_retirement():
    """The only SEBI control in the codebase used to live in the reply desk. It is a
    compliance rule, not a channel preference, so it outlived the channel."""
    assert slot_render.lint_compliance("Gold financiers look undervalued — accumulate.")
    assert slot_render.lint_compliance("A clear multibagger.")
    assert slot_render.lint_compliance("Investors should buy into this trend.")
    assert slot_render.lint_compliance("Target price implies real upside.")
    assert slot_render.lint_compliance("") == []
    # word-boundary, so ordinary prose is untouched
    assert slot_render.lint_compliance("Buyers of gold jewellery rose.") == []


def test_sebi_guardrail_covers_the_design_prompt_too():
    """A design prompt becomes a public pager, so advice language must not ride out on it."""
    slate = _live_slate("1st", ["C1", "C5"])
    corrupted = copy.deepcopy(slate)
    corrupted["claims"][0]["title"] = "Bank credit looks undervalued at these levels"
    assert any("design prompt" in f or "SEBI" in f for f in check_slate(corrupted))


def test_rhetorical_opener_fails_the_lint():
    assert any("rhetorical" in p for p in slot_render.lint_blurb("What is going on here?\n\nA lot."))


def test_unformatted_number_fails_the_lint():
    assert slot_render.lint_blurb("India has 120454115.0 credit cards.")
    assert slot_render.lint_blurb("Growth held for 12.0 periods.")
    assert not slot_render.lint_blurb("Growth is 0.0% this month.")


def test_lede_skips_an_unpresentable_sentence_instead_of_fixing_it():
    lede = src._lede("Title", "There are 120454115.0 cards. Private banks hold 70.9 percent.")
    assert "120454115.0" not in lede
    assert "70.9 percent" in lede


def test_lede_falls_back_to_the_title_alone():
    assert src._lede("Title", "All 120454115.0 of them.") == "Title"


# ── The closed design prompt (§5.1) ───────────────────────────────────────────

def test_design_prompt_supplies_numbers_machine_readably():
    slate = _live_slate("7th", ["C2", "C3"])
    prompt = slot_render.design_prompt(slate)
    block = prompt.split("```json", 1)[1].split("```", 1)[0]
    supplied = json.loads(block)["supplied_numbers"]
    assert supplied and all({"value", "claim", "signals"} <= set(s) for s in supplied)


def test_design_prompt_forbids_deriving_new_figures():
    prompt = slot_render.design_prompt(_live_slate("1st", ["C1", "C5"]))
    assert "Invent nothing" in prompt
    assert "Do **not** compute new figures" in prompt
    assert "Do not look anything up" in prompt


def test_design_prompt_carries_the_vintage():
    prompt = slot_render.design_prompt(_live_slate("1st", ["C1", "C5"]))
    assert "Data vintage:" in prompt
    assert "2026" in prompt


# ── The ledger (§7) ───────────────────────────────────────────────────────────

def test_ledger_flags_a_signal_reused_inside_the_window(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger_mod, "LEDGER", tmp_path / "ledger.json")
    ledger_mod.record("7th", "C2", [{"id": "x", "signal_ids": ["sibc-services-rotation"]}],
                      {}, [], when="2026-08-07")
    hits = ledger_mod.overlaps(["sibc-services-rotation"], when="2026-08-14", slot="14th")
    assert hits and hits[0][0] == "sibc-services-rotation"
    assert ledger_mod.verify() == []          # one entry cannot overlap itself


def test_ledger_allows_reuse_outside_the_window(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger_mod, "LEDGER", tmp_path / "ledger.json")
    ledger_mod.record("7th", "C2", [{"id": "x", "signal_ids": ["s1"]}], {}, [],
                      when="2026-06-07")
    assert ledger_mod.overlaps(["s1"], when="2026-08-07", slot="7th") == []


def test_ledger_rerun_replaces_rather_than_duplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger_mod, "LEDGER", tmp_path / "ledger.json")
    for _ in range(3):
        ledger_mod.record("7th", "C2", [{"id": "x", "signal_ids": ["s1"]}], {}, [],
                          when="2026-08-07")
    assert len(ledger_mod.entries()) == 1


def test_ledger_verify_catches_a_real_overlap(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger_mod, "LEDGER", tmp_path / "ledger.json")
    ledger_mod.record("7th", "C2", [{"id": "x", "signal_ids": ["s1"]}], {}, [],
                      when="2026-08-07")
    ledger_mod.record("14th", "C6", [{"id": "y", "signal_ids": ["s1"]}], {}, [],
                      when="2026-08-14")
    assert len(ledger_mod.verify()) == 1


def test_skips_are_recorded_not_forgotten(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger_mod, "LEDGER", tmp_path / "ledger.json")
    ledger_mod.record_skip("21st", "C10", "C9", "both empty", when="2026-08-21")
    assert ledger_mod.load()["skips"][0]["reason"] == "both empty"


# ── Corrections (C9) read our own record ──────────────────────────────────────

def test_correction_appears_when_a_published_signal_has_since_flipped():
    registry = src.ns.load_registry()
    sid = next(s for s, v in registry.items()
               if v.get("layer") == 1 and v.get("current_status") not in (None, "retired"))
    entry = {"date": "2026-06-01", "signal_ids": [sid],
             "statuses": {sid: "declining_forever"}}
    out = src.corrections([entry])
    assert any(c["id"] == sid for c in out)


def test_no_correction_when_the_read_still_holds():
    registry = src.ns.load_registry()
    sid = next(s for s, v in registry.items()
               if v.get("layer") == 1 and v.get("current_status") not in (None, "retired"))
    entry = {"date": "2026-06-01", "signal_ids": [sid],
             "statuses": {sid: registry[sid]["current_status"]}}
    assert not any(c["id"] == sid and "we published" in c["body"]
                   for c in src.corrections([entry]))
