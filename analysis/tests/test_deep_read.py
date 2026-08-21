#!/usr/bin/env python3
"""
test_deep_read.py — the 14th-of-month deep read (DISTRIBUTION_SPEC §11.2)
--------------------------------------------------------------------------
Covers the parts that are new or were bugs: the inline diagram drawer, the direction
render (the `up, -2.6%` fix), the spine shortlist + freshness, the bank "why" gate, and
the tightened per-member basis scope — negative-tested, because a gate that has never
rejected anything is not known to reject anything.
"""
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import voice                                               # noqa: E402
from distribution import bank_sourcing, ledger, mermaid, model_graph  # noqa: E402
from distribution import distribution_sources as src                 # noqa: E402
from distribution.issues import deep_read as deep                    # noqa: E402
from distribution.validate_distribution import check_doc, prose_lint, word_number_conflicts  # noqa: E402


# ── Direction render (§11.2-R1) — the live `up, -2.6%` bug, now in the shared voice ──

def test_observed_direction_from_value():
    assert voice.observed_dir("+1.3% YoY") == 1
    assert voice.observed_dir("-2.6% YoY") == -1
    assert voice.observed_dir("rising") == 1
    assert voice.observed_dir("falling") == -1
    # A mixed multi-component value has no single direction — no false "moving against".
    assert voice.observed_dir("atm -1.0% · ecom +5.0% · pos +9.3% YoY") is None


def test_basis_read_flags_moving_against_never_a_contradicting_word():
    """A member observed against its authored polarity is flagged in words — the number is
    shown as-is, never dressed in an 'up' that fights it (§11.2-R1)."""
    doc = []
    basis = {"members": [{"label": "Consumer Durables", "direction": 1,
                          "value": "-2.6% YoY", "signals": ["sibc-pl-consumer-durables-yoy"]}]}
    declared = deep._basis_read(doc, basis)
    line = next(b for b in doc if b["type"] == "p" and "-2.6% YoY" in b.get("text", ""))
    assert "moving against" in line["text"]
    assert " up " not in f" {line['text'].lower()} "        # no word fighting the number
    assert line["signals"] == ["sibc-pl-consumer-durables-yoy"]   # D1 scope holds
    assert declared == ["sibc-pl-consumer-durables-yoy"]


def test_basis_read_agreeing_member_has_no_flag():
    doc = []
    deep._basis_read(doc, {"members": [{"label": "Other PL", "direction": 1,
                                        "value": "+12.5% YoY", "signals": ["sibc-pl-other-yoy"]}]})
    line = next(b for b in doc if "+12.5% YoY" in b.get("text", ""))
    assert "moving against" not in line["text"]


# ── The diagram is the model's own subgraph, drawn by a pure renderer (§11.2-R2) ──

def test_mermaid_render_is_pure_structure():
    code = mermaid.render(
        [{"id": "f", "label": "Zero MDR", "kind": "force"},
         {"id": "q", "label": "UPI QR", "kind": "outcome"},
         {"id": "p", "label": "POS", "kind": "outcome"}],
        [{"from": "f", "to": "q", "label": "drives (+)"},
         {"from": "f", "to": "p", "label": "suppresses", "against": True}])
    assert code.startswith("graph LR")
    assert "-->|drives|" in code                           # a with-arrow (solid, pipe label)
    assert "-. suppresses .->" in code                     # an against-arrow (dotted, inline)
    assert "Zero MDR" in code and "UPI QR" in code


# A model-backed risk spine, addressed by its permanent model node rather than by whichever
# spine happens to be live this period — the invariant is that the model can DRAW it, which does
# not depend on the risk firing in the current opportunities feed.
MODEL_RISK_SPINE = {"id": "risk_infrastructure_bifurcation", "kind": "risk",
                    "item": {"pipeline": "atm_pos"}}


def test_chosen_spine_diagram_comes_from_the_model():
    """The #8 diagram is a real signed subgraph the model holds — not a synthesised triangle."""
    sub = model_graph.subgraph_for(MODEL_RISK_SPINE)
    assert sub and len(sub["nodes"]) >= 4          # force + QR + POS + risk, at least
    assert any(n["kind"] == "force" for n in sub["nodes"])
    assert any(e.get("against") for e in sub["edges"])     # the suppressed side is signed


def test_trivial_subgraph_is_suppressed():
    assert model_graph.trivial({"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{}]})
    assert model_graph.subgraph_for({"kind": "opportunity", "id": "nope",
                                     "item": {"pipeline": "sibc"}}) is None


def test_mermaid_dotted_edge_carries_its_label_inline_not_a_pipe():
    """The live parse error: a dashed arrow with a pipe label (`-. x .->|y|`) is invalid
    mermaid. A dotted edge must carry its text INSIDE the dots; only solid edges take a pipe."""
    code = mermaid.render(
        [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}],
        [{"from": "a", "to": "b", "label": "suppresses", "against": True},
         {"from": "a", "to": "c", "label": "drives"}])
    assert ".->|" not in code                         # the exact defect that broke rendering
    assert "-. suppresses .->" in code                # dotted → label inline
    assert "-->|drives|" in code                      # solid → label in a pipe


def test_chosen_spine_mermaid_labels_are_parser_safe():
    """Node labels must carry no character that breaks the mermaid grammar even inside quotes
    (parens/colons/slashes/pipes) — the reason #8's force + risk labels are softened."""
    import re as _re
    code = mermaid.render(*[model_graph.subgraph_for(MODEL_RISK_SPINE)[k] for k in ("nodes", "edges")])
    assert ".->|" not in code
    for m in _re.finditer(r'"([^"]*)"', code):
        assert not _re.search(r"[()/:|{}\[\]]", m.group(1)), m.group(1)


def test_mermaid_block_is_out_of_number_scope():
    """A diagram carries structure only; check_doc treats a mermaid block like a chart."""
    doc = [{"type": "mermaid", "code": mermaid.render([{"id": "a", "label": "A"}], [])}]
    assert check_doc(doc, [], label="t") == []


# ── Spine shortlist + freshness ───────────────────────────────────────────────

def test_spine_candidates_ranked_and_diagram_flagged():
    cands = src.spine_candidates()
    assert cands, "the composed model should offer at least one spine"
    scores = [c["score"] for c in cands]
    assert scores == sorted(scores, reverse=True)
    for c in cands:
        # The diagram flag now tracks what the MODEL can draw (§11.2-R2), not the spine kind.
        assert c["diagram"] == (model_graph.subgraph_for(c) is not None)
        assert "?" in c["question"]               # every candidate is phrased as a question
    # A risk earns a diagram from its model subgraph — the point of the R2 change. Asserted on the
    # permanent model node so the invariant holds in any period, whether or not it is live now.
    assert model_graph.subgraph_for(MODEL_RISK_SPINE) is not None


def test_recent_spine_kind_is_downranked(tmp_path, monkeypatch):
    """A spine KIND run last month sinks below an equally-weighted fresh one."""
    from datetime import date
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "led.json")
    last_month = date.today().replace(day=1)
    prev = (last_month.replace(year=last_month.year - (last_month.month == 1),
                               month=12 if last_month.month == 1 else last_month.month - 1))
    ledger.record_spines(["eco_loop"], when=prev.isoformat())
    recent = ledger.recent_spine_kinds()
    assert recent.get("eco_loop") == 1


# ── Bank "why" gate — never auto-trusted ──────────────────────────────────────

def test_unverified_bank_why_never_publishes(tmp_path, monkeypatch):
    monkeypatch.setattr(bank_sourcing, "STORE", tmp_path / "bs.json")
    bank_sourcing.save({"bank_claims": [
        {"bank": "SBM Bank India", "why": "a plausible story",
         "url": "https://example.com/x", "excerpt": "x" * 50, "status": "draft"}],
        "corroborations": []})
    assert bank_sourcing.sourced_why("SBM Bank India") is None   # status != verified


def test_verified_but_incomplete_entry_fails_the_store_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(bank_sourcing, "STORE", tmp_path / "bs.json")
    bank_sourcing.save({"bank_claims": [
        {"bank": "Citi Bank", "why": "reason", "url": "", "excerpt": "x" * 50,
         "status": "verified"}], "corroborations": []})   # missing url
    fails = bank_sourcing.validate_store()
    assert fails and any("url" in f for f in fails)


def test_default_store_is_empty_and_clean():
    """Shipped store publishes nothing and passes its own gate — honest fallback state."""
    assert bank_sourcing.validate_store() == []


# ── Tiered S4a sourcing gate (§11.2-R3) — the Part 2 mechanism ─────────────────

def test_source_tiers_resolve_by_host():
    assert bank_sourcing.tier_of("https://www.pib.gov.in/x") == "official"
    assert bank_sourcing.tier_of("https://www.crisil.com/x") == "report"
    assert bank_sourcing.tier_of("https://www.business-standard.com/x") == "press"
    assert bank_sourcing.tier_of("https://randomblog.example/x") is None
    # 2026-08-02 additions: the four RBI-licensed bureaus are all reachable now (CIBIL/CRIF were
    # already in; Equifax + Experian complete the set), plus policy ministries and press mastheads.
    assert bank_sourcing.tier_of("https://www.equifax.co.in/x") == "report"
    assert bank_sourcing.tier_of("https://experian.in/x") == "report"
    assert bank_sourcing.tier_of("https://indiaratings.co.in/x") == "report"
    assert bank_sourcing.tier_of("https://www.meity.gov.in/x") == "official"
    assert bank_sourcing.tier_of("https://www.ndtvprofit.com/x") == "press"
    # an off-list host is still rejected — the list stays controlled, not a judgment call.
    assert bank_sourcing.tier_of("https://medium.com/@someone/post") is None


def test_every_allowlisted_host_resolves_to_its_own_tier():
    """Property over the WHOLE list, not a hand-picked sample.

    The spot-check above passed for a year while `worldline.com` was rejected by its own
    allowlist (the `lstrip("www.")` bug). Hand-written cases select for the hosts the author
    already suspects — the same failure class as the newsletter gate that measured 0% catch
    against nine hand-written negatives. Enumerate the set instead."""
    for tier, hosts in bank_sourcing.ALLOWLIST.items():
        for host in hosts:
            for url in (f"https://{host}/x", f"https://www.{host}/x"):
                got = bank_sourcing.tier_of(url)
                assert got is not None, f"{host} is allowlisted but tier_of({url}) is None"
                assert bank_sourcing.ALLOWLIST[got] is not None
                assert host in bank_sourcing.ALLOWLIST[got], f"{url} resolved to wrong tier {got}"


def test_excerpt_must_literally_appear_on_the_page():
    page = "Zero MDR removes the merchant revenue incentive to maintain POS terminal infrastructure."
    assert bank_sourcing.excerpt_on_page("removes the merchant revenue incentive to maintain POS", page)
    assert not bank_sourcing.excerpt_on_page("banks are deploying far more POS terminals now", page)


def test_gated_writer_refuses_unverifiable_and_off_allowlist(tmp_path, monkeypatch):
    monkeypatch.setattr(bank_sourcing, "STORE", tmp_path / "bs.json")
    page = "Zero MDR removes the merchant revenue incentive to maintain POS terminal infrastructure."
    base = {"bank": "X", "dimension": "POS terminals", "why": "policy squeeze",
            "verified_date": "2026-07-29"}
    # a fabricated excerpt not on the page → refused, never written
    ok, probs = bank_sourcing.add_bank_claim(
        {**base, "url": "https://www.business-standard.com/a",
         "excerpt": "a quote that is nowhere on the actual page at all"}, page_text=page)
    assert not ok and any("verified" in p for p in probs)
    # a real excerpt but an off-allowlist host → refused
    ok2, _ = bank_sourcing.add_bank_claim(
        {**base, "url": "https://randomblog.example/a",
         "excerpt": "removes the merchant revenue incentive to maintain POS terminal"},
        page_text=page)
    assert not ok2
    # a real excerpt on an allowlisted host → written and verified
    ok3, probs3 = bank_sourcing.add_bank_claim(
        {**base, "url": "https://www.business-standard.com/a",
         "excerpt": "removes the merchant revenue incentive to maintain POS terminal"},
        page_text=page)
    assert ok3 and probs3 == []
    assert bank_sourcing.sourced_why("X", "POS terminals")["tier"] == "press"


def test_declared_tier_must_match_the_host_tier(tmp_path, monkeypatch):
    monkeypatch.setattr(bank_sourcing, "STORE", tmp_path / "bs.json")
    # a press host declared as 'official' is a lie the gate catches
    probs = bank_sourcing.validate_entry(
        {"url": "https://www.business-standard.com/a", "tier": "official",
         "excerpt": "x" * 50, "verified_date": "2026-07-29",
         "excerpt_verified": True, "status": "verified"})
    assert any("tier" in p for p in probs)


# ── Part A helpers scope their own signals ────────────────────────────────────

def test_bank_divergence_rows_scope_to_the_divergence_signal():
    p = src.latest_period("atm_pos")
    for d in src.bank_divergence(p):
        assert d["signals"] == [d["signal"]]
        assert d["signal"].endswith("-bank-divergence")


# ── The whole issue gates green, every spine kind ─────────────────────────────

def test_each_spine_kind_builds_and_gates_green():
    cands = src.spine_candidates()
    by_kind = {}
    for i, c in enumerate(cands, 1):
        by_kind.setdefault(c["kind"], i)
    for kind, idx in by_kind.items():
        doc, period, declared, kinds = deep.build_doc(spine_picks=[idx])
        assert check_doc(doc, declared, label=f"deep[{kind}]") == [], kind
        assert word_number_conflicts(doc)[0] == [], kind
        assert prose_lint(doc)[0] == [], kind
        assert kinds == [kind]


def test_published_shape_is_nested_not_flat():
    """The §11.2 shape: h1 masthead, the spine question stated ONCE, h3 sub-sections nested
    under their h2 parents (spine 'Bank angle'; Part A 'Who's rotating'/'Who's diverging')."""
    doc, _, _, _ = deep.build_doc(spine_picks=None)
    assert doc[0]["type"] == "h1" and doc[0]["text"].startswith("The deep read")
    h2 = [b["text"] for b in doc if b["type"] == "h2"]
    h3 = [b["text"] for b in doc if b["type"] == "h3"]
    assert "Why this question now" in h2
    assert "Banks this month" in h2
    assert "Bank angle" in h3                      # nested under the spine, not h2
    # The question is not printed as its own heading twice (the old h1==h2 duplication).
    assert h2.count("Why this question now") == 1
    # A card carries no dashboard-label title in the deep read (heading names the subject).
    assert all(not b.get("title") for b in doc if b["type"] == "card")


def test_tightened_basis_scope_catches_a_planted_number():
    """Negative test: a fabricated figure planted into a numeric basis line, scoped to that
    line's own member signal, must be rejected. If it passes, the D1 tightening is theatre."""
    cands = src.spine_candidates()
    idx = next((i for i, c in enumerate(cands, 1) if c["kind"] == "construct"), None)
    assert idx, "expected a construct spine to test numeric basis scoping"
    doc, period, declared, _ = deep.build_doc(spine_picks=[idx])
    planted = None
    for b in doc:
        if b["type"] == "p" and b.get("signals") and "%" in (b.get("text") or ""):
            b["text"] += " and by a fabricated 91.7% this month."
            planted = b
            break
    assert planted is not None, "the construct spine should have a numeric, member-scoped line"
    assert check_doc(doc, declared, label="neg"), "planted number should have been caught"
