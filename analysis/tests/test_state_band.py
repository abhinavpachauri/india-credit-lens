"""The standing state band — sentence grammar, the honest absences, and the gate.

Driven SYNTHETICALLY wherever the logic is the subject, because the interesting branches
are the ones live data does not currently take: SIBC has run coherence 0.99-1.00 in every
observed window, so `contested` and `reallocating` would never once render against it, and
`contracting` needs a negative rate that no SIBC cut has. The live artifacts get their own
separate assertions — that pair is the durable shape (a check that only asserts against this
month's data stops asserting anything the month the data moves).
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "guards"))

from core import state_lines as SL                      # noqa: E402
from core.movement_cards import MovementCut             # noqa: E402
import validate_state_band as VSB                       # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "web" / "public" / "data"


def _db(rows):
    """An in-memory signals table holding exactly `rows`."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE signals (pipeline TEXT, period TEXT, metric_id TEXT, "
                "entity_type TEXT, entity_id TEXT, value REAL, status TEXT)")
    con.executemany("INSERT INTO signals VALUES (?,?,?,?,?,?,?)", rows)
    return con


def _yoy(*vals, sid="p-yoy"):
    """A parent-YoY signal's own series, oldest first."""
    return [("t", f"2026-0{i+1}-30", sid, "aggregate", "total", v, "active")
            for i, v in enumerate(vals)]


# ── speed · Layer 1 ───────────────────────────────────────────────────────────

def test_speed_names_the_pace_from_the_signals_own_last_two_readings():
    con = _db(_yoy(18.0, 20.0))          # +2.0 pp, well past the 0.5 pp band
    line, short, direction, sids = SL.speed_line(con, "t", "2026-02-30", "p-yoy", "Industry credit")
    assert line == "Industry credit growing 20.0% YoY, accelerating."
    assert short == "20.0% YoY · accelerating"
    assert direction == "up" and sids == ["p-yoy"]


def test_speed_says_slowing_and_steady_on_the_other_two_sides_of_the_band():
    slow, _, _, _ = SL.speed_line(_db(_yoy(22.0, 20.0)), "t", "2026-02-30", "p-yoy", "X")
    assert slow == "X growing 20.0% YoY, but slowing."
    # inside the band: a pace that has not meaningfully changed is SAID to be unchanged,
    # never silently rendered as acceleration.
    steady, short, _, _ = SL.speed_line(_db(_yoy(20.2, 20.0)), "t", "2026-02-30", "p-yoy", "X")
    assert steady == "X growing 20.0% YoY, at a steady pace."
    assert short == "20.0% YoY"          # the tile drops a non-finding


def test_a_contraction_is_signed_so_it_traces():
    """The first run of the gate rejected `shrinking 15.8%`: the stored row is -15.83 and the
    unsigned figure traces to nothing. Direction lives in the verb AND in the number."""
    line, short, direction, _ = SL.speed_line(_db(_yoy(-4.0, -15.83)), "t", "2026-02-30",
                                              "p-yoy", "POS terminals")
    assert line == "POS terminals at -15.8% YoY, contracting."
    assert "-15.8%" in short and direction == "down"


def test_no_parent_signal_means_no_speed_line_ever():
    """Priority Sector is a memo lens with no total. An absent input renders nothing —
    it never borrows a neighbour's rate or falls back to a period-wide number."""
    assert SL.speed_line(_db([]), "t", "2026-02-30", None, "Priority sector credit") is None


def test_speed_is_silent_when_the_signal_has_no_row_for_this_period():
    con = _db(_yoy(18.0, 20.0))
    assert SL.speed_line(con, "t", "2026-09-30", "p-yoy", "X") is None


# ── mix · Layer 2 ─────────────────────────────────────────────────────────────

def _alloc_db(alloc, weight, net):
    return _db([("t", "P", "a", "alloc", "Medium", alloc, "active"),
                ("t", "P", "a", "weight", "Medium", weight, "active"),
                ("t", "P", "m", "aggregate", "total", net, "active")])


def test_steered_and_drifting_quote_the_two_stored_rows_not_the_tilt():
    """The tilt is alloc - weight: a subtraction, which traces to nothing. Both operands
    are stored, so the sentence quotes those — checkable, and plainer English."""
    for state, verb in (("steered", "Steered"), ("drifting", "Drifting")):
        line, sids = SL.mix_line(_alloc_db(14.03, 9.18, 798500.0), "t", "P", "a", "m",
                                 {"mix_state": state, "toward": "Medium", "away_from": "Large"})
        assert line == (f"{verb} toward Medium — it took 14.0% of the growth while "
                        f"holding 9.2% of the total. Away from Large.")
        assert "4.85" not in line and "+4.9" not in line
        assert set(sids) == {"a", "m"}


def test_the_noun_follows_the_sign_of_the_stored_net():
    """A coherent cut can be one in which every part is SHRINKING. 'took 14% of the growth'
    would then be the exact inversion of what happened."""
    line, _ = SL.mix_line(_alloc_db(14.03, 9.18, -798500.0), "t", "P", "a", "m",
                          {"mix_state": "drifting", "toward": "Medium", "away_from": "Large"})
    assert "of the contraction while" in line and "of the growth" not in line


def test_contested_and_reallocating_name_no_destination_and_quote_no_number():
    for state, cue in (("contested", "opposite directions"), ("reallocating", "very nearly cancel")):
        line, sids = SL.mix_line(_db([]), "t", "P", "a", "m", {"mix_state": state})
        assert cue in line
        assert not any(ch.isdigit() for ch in line)   # no coherence figure, ever
        assert sids == []


def test_no_mix_state_means_no_mix_line():
    assert SL.mix_line(_db([]), "t", "P", "a", "m", {}) is None


# ── the band ──────────────────────────────────────────────────────────────────

def test_a_cut_with_neither_speed_nor_mix_produces_no_block():
    """An empty band is worse than no band."""
    cut = MovementCut("x", "dimA", "x-yoy-scan", "things")
    assert SL.blocks(_db([]), "t", "P", [cut], "p-", {}) == []


def test_two_cuts_on_one_dimension_both_survive_keyed_by_cut():
    """Industry carries a by-size and a by-type decomposition off the same node. Keying the
    band by dimension alone would silently drop one."""
    rows = []
    for slug in ("one", "two"):
        rows += [("t", "P", f"p-{slug}-allocation", "alloc",     "Medium", 14.0, "active"),
                 ("t", "P", f"p-{slug}-allocation", "weight",    "Medium",  9.0, "active"),
                 ("t", "P", f"p-{slug}-momentum",   "aggregate", "total",   1.0, "active")]
    cuts = [MovementCut("one", "dimA", "s1", "things"),
            MovementCut("two", "dimA", "s2", "things")]
    mix = {f"p-{s}-momentum": {"mix_state": "drifting", "toward": "Medium", "away_from": "Large"}
           for s in ("one", "two")}
    out = SL.blocks(_db(rows), "t", "P", cuts, "p-", mix)
    assert [b.cut for b in out] == ["one", "two"]
    assert all(b.dimension == "dimA" for b in out)


def test_a_section_keyed_prefix_map_resolves_per_cut():
    """Payments names its three cuts cc-/dc-/pos-, all with the slug "category". A single
    prefix string would resolve all three to the same signals."""
    rows = [("t", "P", "cc-category-momentum", "aggregate", "total", 1.0, "active"),
            ("t", "P", "cc-category-allocation", "alloc",  "SFB", 10.7, "active"),
            ("t", "P", "cc-category-allocation", "weight", "SFB",  1.0, "active")]
    cuts = [MovementCut("category", "cc", "s", "credit cards")]
    out = SL.blocks(_db(rows), "t", "P", cuts, {"cc": "cc-"},
                    {"cc-category-momentum": {"mix_state": "steered", "toward": "SFB",
                                              "away_from": "Foreign Banks"}})
    assert len(out) == 1 and "10.7%" in out[0].mix


# ── the gate ──────────────────────────────────────────────────────────────────

def test_gate_rejects_a_number_that_is_not_in_the_blocks_own_rows():
    """Synthetic, so it keeps asserting after the live figures move. The attack is the one
    period-wide scope cannot see: a plausible value that exists nowhere in this block."""
    con = _db([("t", "P", "p-yoy", "aggregate", "total", 20.0, "active")])
    reg = {"p-yoy": {}}
    block = {"source_signals": ["p-yoy"], "toward_entity": None}
    cands = VSB.candidates(con, reg, "t", "P", block)
    from core.traceability import DISTRIBUTION as POL, matches
    assert matches(20.0, cands, POL)
    assert not matches(21.7, cands, POL)


def test_gate_scopes_to_the_named_entity_not_the_signals_history():
    """At history width four of twenty-three near-miss injections survived by landing on the
    signal's OWN past readings. The band never quotes history."""
    rows = [("t", f"2026-0{i}-30", "a", "alloc", "Medium", v, "active")
            for i, v in enumerate([11.9, 12.4, 14.0], start=1)]
    con = _db(rows)
    cands = VSB.candidates(con, {"a": {}}, "t", "2026-03-30",
                           {"source_signals": ["a"], "toward_entity": "Medium"})
    assert cands == [14.0]          # this period only — not 11.9, not 12.4


def test_live_sidecars_are_clean_on_both_pipelines():
    """Separate from the logic tests above, deliberately: a check that only asserts the live
    feed is clean stops asserting anything the moment someone fixes the defect it found."""
    for pipeline in ("sibc", "atm_pos"):
        assert VSB.validate(pipeline) == []


def test_no_published_sentence_carries_a_coherence_figure():
    """Decision #4, as a property over everything the band actually ships. Coherence lives in
    a state file rather than signals.db, so no gate can ground it — invented values have
    passed before. The regime WORD carries the meaning."""
    for pipeline in ("sibc", "atm_pos"):
        doc = json.loads((DATA / f"{pipeline}_state.json").read_text())
        for blocks in doc["dimensions"].values():
            for b in blocks:
                for field in ("speed", "speed_short", "mix"):
                    text = (b.get(field) or "").lower()
                    assert "coherence" not in text, f"{pipeline}/{b['cut']}.{field}"
                if b["mix_state"] in ("contested", "reallocating"):
                    assert not any(c.isdigit() for c in b["mix"])
