#!/usr/bin/env python3
"""
relational_insights.py — deterministic insight builders for the relational
signal methods (rotation_insight + divergence_insight).

Spec: analysis/signals/README.md — "Relational signal methods". Deterministic
prose is the product: the copy must be publishable with zero LLM calls (quality
bar: pipelines/sibc/generate_analysis_report.deterministic_scan_insight).

The real-world line comes from the majority economic_role of the top gainers /
losers, resolved from the system model's concept_tags (COMPOSITION_SPEC §4).
Roles are grouping labels, so the insight may make COMPOSITION reads ("the mix
is shifting toward energy & logistics capex") but never lead/lag transmission
claims — those are channels (COMPOSITION_SPEC §2a) and enter via S2a/S4 only.
Mixed or missing roles → the honest fallback ("no single theme").

Numbers policy: every figure in the prose is a signal row value (Δshare_pp per
entity, or the aggregate rotation-mass row); counts of periods/months are
written in words ("a year") so the copy stays traceable to signals.db alone.

Usage (review render — reads signals.db, writes nothing):
    python3 analysis/core/relational_insights.py --pipeline sibc  --period 2026-06-30
    python3 analysis/core/relational_insights.py --pipeline atm_pos --period 2026-05-31
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import residuals
from core.paths import ROOT as REPO  # noqa: E402

SIG = REPO / "analysis" / "signals"
MODEL_PATH = {
    "sibc":    REPO / "analysis" / "rbi_sibc"    / "merged" / "system_model.json",
    "atm_pos": REPO / "analysis" / "rbi_atm_pos" / "merged" / "system_model.json",
}

# Human phrasing for the economic_role vocabulary (COMPOSITION_SPEC §4).
ROLE_LABELS = {
    "energy_logistics_capex":   "energy & logistics capex",
    "capital_goods":            "capital goods",
    "industrial_inputs":        "industrial inputs",
    "construction_real_estate": "construction & real estate",
    "agri_inputs":              "agriculture",
    "trade_channel":            "trade & distribution",
    "consumer_traditional":     "traditional consumer sectors",
    "consumer_mobility":        "mobility",
    "consumer_durables":        "consumer durables",
    "consumer_finance":         "consumer finance",
    "financial_intermediation": "financial intermediation",
    "digital_payment_rails":    "digital payment rails",
    "cash_infrastructure":      "cash infrastructure",
}


def entity_roles(pipeline: str) -> dict[str, str]:
    """label → economic_role, resolved from the system model's concept_tags.
    The model is the single source of role truth (regenerated with the skeleton
    from skeleton_profile.json) — never re-declare roles here."""
    model = json.loads(MODEL_PATH[pipeline].read_text())
    out = {}
    for n in model["nodes"]:
        if n.get("tier") != "entity":
            continue
        role = (n.get("concept_tags") or {}).get("economic_role")
        if role:
            out[n["label"]] = role
    return out


def rotation_distribution(conn: sqlite3.Connection, sid: str, pipeline: str,
                          period: str) -> tuple[list[tuple], float | None]:
    """([(entity_id, Δshare_pp, status)] ranked desc, rotation_mass)."""
    rows = [(r[0], r[1], r[2]) for r in conn.execute(
        "SELECT entity_id, value, status FROM signals "
        "WHERE pipeline=? AND period=? AND metric_id=? "
        "AND value IS NOT NULL AND entity_type != 'aggregate' "
        "ORDER BY value DESC", (pipeline, period, sid)).fetchall()]
    mass = conn.execute(
        "SELECT value FROM signals "
        "WHERE pipeline=? AND period=? AND metric_id=? "
        "AND entity_type='aggregate' AND entity_id='total'",
        (pipeline, period, sid)).fetchone()
    return rows, (mass[0] if mass else None)


def _short(name: str) -> str:
    """Trim parenthetical qualifiers from RBI sector names for prose."""
    cut = name.split("(")[0].strip().rstrip(",")
    return cut if cut else name


def _majority_role(movers: list[tuple[str, float]],
                   roles: dict[str, str]) -> str | None:
    """Majority economic_role among the MATERIAL movers (|Δ| ≥ 0.15pp — the
    same threshold the status rules use for strengthening/weakening), so a
    +0.04pp bystander cannot outvote a +3.4pp shift. None when the tagged
    material movers split (mixed roles → honest fallback) or none are tagged."""
    tagged = [roles[e] for e, v in movers if abs(v) >= 0.15 and e in roles]
    if not tagged:
        return None
    role, count = Counter(tagged).most_common(1)[0]
    return role if count * 2 > len(tagged) else None


def _pp(v: float) -> str:
    # Signed, with a space before the unit: the traceability extractors parse
    # "3.21 pp" as 3.21 but backtrack glued "3.21pp" to a bare "3" — and the
    # sign must match the stored row value, so "below"-style prose still
    # carries the signed figure.
    return f"{v:+.2f} pp"


def rotation_insight(dist: list[tuple], mass: float | None,
                     roles: dict[str, str], subject: str) -> dict | None:
    """Deterministic rotation insight from a ranked Δshare distribution.

    dist    — [(entity_id, Δshare_pp, status)] sorted desc (no aggregate row)
    mass    — the aggregate rotation-mass row's value (Σ|Δ|/2, pp)
    roles   — label → economic_role (from entity_roles)
    subject — what the shares are shares OF ("industry credit", "credit cards
              by bank category") — the registry share_of / metric label

    Returns {title, body, chain, implication, insight_kind} or None when the
    distribution is empty (window not yet available → insight suppressed).
    """
    if not dist:
        return None

    # Movers below display precision (±0.01pp) are noise in prose — drop them.
    gainers = [(e, v) for e, v, _ in dist if v >= 0.01][:3]
    losers  = [(e, v) for e, v, _ in dist[::-1] if v <= -0.01][:3]   # worst first
    mass_v  = mass if mass is not None else sum(abs(v) for _, v, _ in dist) / 2

    # Honest edge: a mix that barely moved is the finding, not a failure.
    if mass_v < 0.5:
        title = f"{subject.capitalize()} mix steady — only {mass_v:.2f} pp changed hands in a year"
        body = (f"Compared with the same month a year ago, the {subject} mix is "
                f"essentially unchanged: {mass_v:.2f} pp of share moved between "
                f"segments in total. No segment gained or lost meaningful ground.")
        chain = [
            f"Each segment's share of {subject} is compared with the same month a year earlier.",
            f"Rotation mass — the share that changed hands — is {mass_v:.2f} pp, "
            f"below the half-point mark that would signal a real shift.",
        ]
        implication = ("A stable mix is information too: whatever is driving "
                       f"headline growth in {subject}, it is not a reallocation "
                       "between segments. Watch for the first month this breaks.")
        return {"title": title, "body": body, "chain": chain,
                "implication": implication, "insight_kind": "rotation"}

    role_g = _majority_role(gainers, roles)
    role_l = _majority_role(losers, roles)

    if not gainers:
        return None   # a mix that only sheds share has no rotation story to lead with

    # Entities with no economic_role at all (e.g. bank categories — a lender
    # mix, not an economic one) get NO theme sentence: claiming "no economic
    # theme" about a set that is not role-tagged would be a category error.
    has_roles = any(e in roles for e, _, _ in dist)

    # A remainder must not headline. "The mix is rotating toward Other Personal Loans"
    # asserts a destination, and RBI does not say what is in that bucket — the honest
    # headline is the biggest block that IS named. No card leads with one this period;
    # the guard is here because nothing stopped next period's from doing so.
    named_gainers = [g for g in gainers if not residuals.is_catch_all(g[0])]
    head = named_gainers[0] if named_gainers else gainers[0]
    L0, Lv0 = _short(head[0]), head[1]
    theme = None
    if role_g:
        toward = ROLE_LABELS[role_g]
        if role_l and role_l != role_g:
            theme = (f"The gains concentrate in {toward}, the cessions in "
                     f"{ROLE_LABELS[role_l]} — the mix is tilting toward {toward}.")
        else:
            theme = f"The gains concentrate in {toward} — the mix is tilting toward {toward}."
    elif role_l:
        theme = (f"The cessions concentrate in {ROLE_LABELS[role_l]}; "
                 f"the gains span several parts of the economy.")
    elif has_roles:
        theme = ("No single economic theme unites the movers — the rotation is "
                 "broad-based rather than a story about one part of the economy.")

    title = (f"{subject[0].upper()}{subject[1:]} mix rotating toward {L0} "
             f"({_pp(Lv0)} share in a year)")

    # Entity names carry commas ("Petroleum, Coal Products…") — separate with
    # semicolons so the list stays readable.
    # A remainder is named, never silently listed as a peer. RBI does not break
    # "Other Personal Loans" or "Other Services" down, so a share it gains or sheds
    # is as much a reclassification as a lending decision — the reader is owed that
    # once, inline, rather than left to infer it from the word "Other".
    def _entity(e: str) -> str:
        n = _short(e)
        return f"{n} (not broken down)" if residuals.is_catch_all(e) else n

    gain_str = "; ".join(f"{_entity(e)} {_pp(v)}" for e, v in gainers)
    lose_str = "; ".join(f"{_entity(e)} {_pp(v)}" for e, v in losers)
    body_parts = [
        f"Compared with the same month a year ago, the biggest share gains in "
        f"{subject} came from {gain_str}."
    ]
    if losers:
        body_parts.append(f"The ground came from {lose_str}.")
    body_parts.append(f"In all, {mass_v:.2f} pp of the mix changed hands."
                      + (f" {theme}" if theme else ""))
    body = " ".join(body_parts)

    chain = [
        f"Each segment's share of {subject} is compared with the same month a "
        f"year earlier — the change is in percentage points of the mix.",
        f"Top gainer: {L0} at {_pp(Lv0)}."
        + (f" Biggest cession: {_short(losers[0][0])} at {_pp(losers[0][1])}."
           if losers else ""),
        f"Rotation mass — the share that changed hands — is {mass_v:.2f} pp.",
    ]
    if theme:
        chain.append(theme)

    if role_g:
        watch = (f"The tilt toward {ROLE_LABELS[role_g]} is the line to watch — "
                 f"confirm it holds next month before treating it as a trend.")
    elif has_roles:
        watch = ("With no single theme behind the movers, treat each segment's "
                 "shift on its own terms rather than as one story.")
    else:
        watch = (f"Watch whether {L0} holds its gains next month before "
                 "reading the shift as a trend.")
    implication = ("This is a composition read: it says where the mix is "
                   "shifting, not why and not what happens next. " + watch)

    return {"title": title, "body": body, "chain": chain,
            "implication": implication, "insight_kind": "rotation"}


def divergence_insight(dist: list[tuple], subject: str, member_noun: str = "segment",
                       parent_is_per_entity: bool = False) -> dict | None:
    """Deterministic divergence insight from the flagged-entity rows.

    dist    — [(entity_id, gap_pp, status)] — value = child_yoy − parent_yoy;
              a positive gap means growing while the parent declines, negative
              the reverse (opposite signs are guaranteed by the flag rule)
    subject — what is being measured ("personal loans", "credit cards")
    member_noun — "segment" (sector trees) or "bank" (bank vs its category)
    parent_is_per_entity — True when each entity contradicts its OWN parent
              (bank vs bank_category) rather than one shared parent

    Number policy: only the gap values (this signal's own rows) appear as
    numerals — the underlying child/parent growth rates belong to other
    signals and are described in words. No rows → None (nothing diverges —
    the insight is suppressed, per spec).
    """
    if not dist:
        return None

    parent = "its category" if parent_is_per_entity else f"the {subject} trend"
    up   = [(e, v) for e, v, _ in dist if v > 0]            # growing vs declining parent
    down = [(e, v) for e, v, _ in sorted(dist, key=lambda r: r[1]) if v < 0]
    lead_e, lead_v = max(dist, key=lambda r: abs(r[1]))[:2]
    Llead = _short(lead_e)

    def _list(pairs):
        return "; ".join(f"{_short(e)} {_pp(v)}" for e, v in pairs[:3])

    if len(dist) == 1:
        side = "above" if lead_v > 0 else "below"
        move = ("growing while the rest declines" if lead_v > 0
                else "contracting while the rest grows")
        title = f"{Llead} is moving against {subject} ({_pp(lead_v)} vs the pace)"
        body = (f"Most {member_noun}s move with their family; a divergence flag "
                f"means one is moving against it. {Llead} is {move} — running "
                f"{_pp(lead_v)} versus {parent}'s year-on-year pace, and it "
                f"is the only {member_noun} flagged this month.")
        chain = [
            f"Each {member_noun}'s year-on-year growth is compared with "
            f"{parent}'s; a flag needs opposite directions and a material gap.",
            f"{Llead} is {_pp(lead_v)} versus {parent} — {move}.",
            f"No other {member_noun} currently contradicts {parent}.",
        ]
    else:
        title = (f"{member_noun.capitalize()}s moving against the pack on "
                 f"{subject} — widest gap {Llead} at {_pp(lead_v)}")
        parts = [f"While {subject} overall moves one way, these {member_noun}s "
                 f"are moving the other."]
        if up:
            parts.append(f"Growing against a declining trend: {_list(up)} "
                         f"versus {parent}'s pace.")
        if down:
            parts.append(f"Declining against a growing trend: {_list(down)}.")
        parts.append(f"{len(dist)} {member_noun}s are flagged in all.")
        body = " ".join(parts)
        chain = [
            f"Each {member_noun}'s year-on-year growth is compared with "
            f"{parent}'s; a flag needs opposite directions and a material gap.",
            f"Widest gap: {Llead} at {_pp(lead_v)} versus {parent}.",
            f"{len(dist)} {member_noun}s currently contradict their trend "
            f"({len(up)} above, {len(down)} below).",
        ]

    implication = (
        f"A {member_noun} moving against its family is an early divergence "
        "read, not a verdict: check whether it is a base effect, a "
        "reclassification, or a genuine shift before acting on it. The gap "
        "closing or widening next month is the signal to watch.")

    return {"title": title, "body": body, "chain": chain,
            "implication": implication, "insight_kind": "divergence_hierarchy"}


# ── movement: where the new units went, and how fast ──────────────────────────

ALIGNED_MIN   = 0.90   # sentence-selector, never a publish gate (signals/README.md)
CONTESTED_MIN = 0.50


def _regime(coherence: float) -> str:
    """Which sentence about this window is true — the router, not a gate.

    Nothing is suppressed at low coherence; the story changes. The two lowest-coherence
    windows in the observed data are a POS-deployment handover and an e-commerce
    consolidation — the best material the layer produces, not the worst."""
    if coherence >= ALIGNED_MIN:
        return "aligned"
    return "contested" if coherence >= CONTESTED_MIN else "handover"


def _pct(v: float) -> str:
    return f"{v:.1f}%"


def _speed_clause(name: str, speed: dict, accel: dict) -> str | None:
    """The pairing rule, enforced structurally rather than by review.

    An allocation figure alone reads as decline when a sector's share of new credit
    falls: personal loans went 44.7% -> 30.1% while GROWING 15.8% YoY and accelerating.
    So a share is never rendered without its own speed and acceleration — and when
    either is missing the caller must drop the entity from prose, not print a bare share.
    """
    sp, ac = speed.get(name), accel.get(name)
    if sp is None or ac is None:
        return None
    moving = "accelerating" if ac > 0.05 else ("slowing" if ac < -0.05 else "steady")
    return f"growing {_pct(sp)} a year and {moving} ({_pp(ac)})"


def movement_insight(alloc: dict, contribution: dict, momentum: dict,
                     net: float | None, gross: float | None, coherence: float | None,
                     accel: dict, speed: dict, subject: str) -> dict | None:
    """Deterministic movement insight — where the new units went, routed by coherence.

    alloc/contribution/momentum/accel/speed — {entity: value} from signals.db rows
    subject — what is being added to ("bank credit")

    Returns {title, body, chain, implication, insight_kind} or None when the annual
    window is not yet available.
    """
    if not momentum or coherence is None or not gross:
        return None
    regime = _regime(coherence)
    ranked = sorted(momentum.items(), key=lambda kv: kv[1], reverse=True)
    risers = [(e, v) for e, v in ranked if v > 0]
    fallers = [(e, v) for e, v in ranked if v < 0][::-1]      # most negative first

    if regime == "aligned" and alloc:
        top = sorted(alloc.items(), key=lambda kv: kv[1], reverse=True)
        lead, lead_v = top[0]
        # Pairing rule: only entities carrying BOTH speed and acceleration reach prose.
        quotable = [(e, v) for e, v in top if _speed_clause(e, speed, accel)]
        if not quotable:
            return None
        lead, lead_v = quotable[0]
        least = min(quotable, key=lambda kv: accel[kv[0]])

        title = (f"{_short(lead)} took {_pct(lead_v)} of all new {subject} in the past year")
        parts = [
            f"Of the {subject} added over the past twelve months, {_short(lead)} took "
            f"{_pct(lead_v)} — the largest share of the new money — {_speed_clause(lead, speed, accel)}."
        ]
        if len(quotable) > 1:
            # A remainder is labelled where it appears. "Other Personal Loans 24.8%"
            # in a list of destinations reads as a choice lenders made; RBI does not
            # break that bucket down, so part of it is reclassification.
            rest = "; ".join(
                f"{_short(e)}{' (not broken down)' if residuals.is_catch_all(e) else ''} {_pct(v)}"
                for e, v in quotable[1:])
            parts.append(f"The rest went to {rest}.")
        # The correction that earns this whole family: least-accelerating is not shrinking.
        if least[0] != lead:
            parts.append(
                f"{_cap(_short(least[0]))} took {_pct(least[1])} while {_speed_clause(least[0], speed, accel)} "
                f"— a smaller slice of a faster-growing total, not a retreat."
            )
        body = " ".join(parts)
        chain = [
            f"Every sector's {subject} is compared with the same month a year earlier, "
            f"and each one's share of the total increase is taken.",
            f"{_short(lead)} accounts for {_pct(lead_v)} of the increase.",
            f"All sectors moved the same way this window, so the shares of the net "
            f"increase are bounded and sum to a hundred.",
        ]
        implication = (
            "Shares of new lending move far faster than shares of the book, so this is the "
            "earlier read of the two. It says where the money went, not why — and a falling "
            "share alongside rising growth means the others grew faster, not that this one shrank."
        )
        return {"title": title, "body": body, "chain": chain,
                "implication": implication, "insight_kind": "movement_allocation"}

    if regime == "contested" and risers and fallers:
        # "Moved against it" is relative to where the TOTAL went, and the total can fall.
        # This branch read "grew"/"rose" unconditionally and named the fallers as the
        # dissenters — correct for SIBC, where credit grows in every window and every cut
        # runs coherence 0.99-1.00 so the branch never rendered. Payments POS terminals is
        # the first real contested window with a NEGATIVE net: the fleet shrank by 1.86M
        # while public banks expanded, and the card said "POS terminals rose over the past
        # year". The dissenters are whoever moved the other way from the total.
        fell = (net or 0) < 0
        movers = risers if fell else fallers
        lead, _lv = (fallers if fell else risers)[0]
        dissent = [_short(e) for e, _ in movers[:2]]
        lead_share = contribution.get(lead)
        verb, past = ("shrank", "fell") if fell else ("grew", "rose")
        against = "expanded" if fell else "contracted"
        rest = "contracted" if fell else "expanded"
        title = (f"{_cap(subject)} {verb}, but {' and '.join(dissent)} moved against it")
        body = (
            f"{_cap(subject)} {past} over the past year, but not everywhere: "
            f"{' and '.join(dissent)} {against} while the rest {rest}. "
            # Gross movement ignores direction by construction, so a share OF it is a
            # magnitude. Printed signed, it read "-93.0% of all the movement", which is
            # not a quantity anyone can picture; the direction is already in the sentence.
            + (f"{_short(lead)} accounts for {_pct(abs(lead_share))} of all the movement "
               "in the period. " if lead_share is not None else "")
            + "Because parts moved in opposite directions, much of the movement cancels out "
              "and the net figure understates how much actually shifted."
        )
        chain = [
            "Each sector's change over the year is measured, then compared with the total "
            "movement ignoring direction.",
            # No numeric coherence in published prose: it is a ratio derived from the movement
            # rows, not a stored value, so Check 2g cannot ground it — the same rule applied to
            # the cross-system cards. The regime word carries the meaning; the shares below are
            # real stored rows and do the quantitative work.
            "Coherence — the net change divided by the total movement ignoring direction — "
            "measures whether the parts agree.",
            "Below one, some sectors are cancelling others out, so shares of the NET change "
            "would overstate; shares of total movement are reported instead.",
        ]
        implication = (
            f"A {'shrinking' if fell else 'growing'} total with members moving the other way is a "
            f"different claim from broad {'decline' if fell else 'growth'}. "
            "Read the members, not the headline."
        )
        return {"title": title, "body": body, "chain": chain,
                "implication": implication, "insight_kind": "movement_momentum"}

    if risers and fallers:
        up, _ = risers[0]
        dn, _ = fallers[0]
        up_c, dn_c = contribution.get(up), contribution.get(dn)
        title = f"{_short(dn)} shed ground to {_short(up)} — the net barely moved"
        body = (
            f"{_cap(subject)} shows almost no net change over the year, but a great deal "
            f"happened underneath it: {_short(up)} expanded while {_short(dn)} contracted by a "
            f"similar amount. "
            + (f"{_short(up)} accounts for {_pct(up_c)} of the total movement and {_short(dn)} "
               f"for {_pct(dn_c)}. " if up_c is not None and dn_c is not None else "")
            + "Almost none of that movement survives into the net figure — this period is a "
              "transfer between members, not a change in size."
        )
        chain = [
            "Each sector's change over the year is measured, then compared with the total "
            "movement ignoring direction.",
            "Coherence — the net change divided by the total movement ignoring direction — is "
            "near zero here, meaning gains and losses very nearly cancel.",
            "At this level a share of the NET change is not meaningful, so the reading is the "
            "transfer between members.",
        ]
        implication = (
            "The headline number is the least informative part of this period. The reallocation "
            "between members is the finding."
        )
        return {"title": title, "body": body, "chain": chain,
                "implication": implication, "insight_kind": "movement_momentum"}
    return None


def _cap(s: str) -> str:
    return f"{s[0].upper()}{s[1:]}" if s else s


def pair_divergence_insight(gap: float | None, status: str | None,
                            a_label: str, b_label: str,
                            yoy_a: float | None = None,
                            yoy_b: float | None = None,
                            flagged: list[tuple] | None = None) -> dict | None:
    """Deterministic insight for a declared co-movement pair (metric axis).

    gap      — the aggregate row's value: yoy_a − yoy_b (pp, signed;
               positive = side A running ahead of side B)
    status   — that row's status ('strengthening' | 'weakening' | 'stable')
    a_label / b_label — the registry-declared names of the two sides
    yoy_a / yoy_b — each side's own growth rate (the pair_side component rows).
               The gap alone cannot distinguish "both grew, A faster" from
               "both shrank, B faster" from "A grew while B fell" — three
               different stories with the same arithmetic, so direction is read
               from these rather than assumed.
    flagged  — bank-level rows [(bank, gap_pp, status)] when the pair also has
               a bank-level signal; the named banks are where the total gap
               lives

    A pair only earns a card when the two sides have come apart: a 'stable'
    gap means they are still moving together, which is the null result, not a
    finding. Number policy: the gap is the only figure stated — the side rates
    inform the wording but are described in words, so nothing in the prose
    depends on a reader parsing two rates and a difference.
    """
    if gap is None or status == "stable":
        return None

    ahead, behind = (a_label, b_label) if gap > 0 else (b_label, a_label)

    # Direction of each side, when known. "Ahead" means the higher growth rate,
    # which in a shrinking pair means shrinking more slowly — never call that
    # growth.
    if yoy_a is not None and yoy_b is not None and max(yoy_a, yoy_b) <= 0:
        shape = "both_shrinking"
    elif yoy_a is not None and yoy_b is not None and min(yoy_a, yoy_b) < 0:
        shape = "split"
    elif yoy_a is not None and yoy_b is not None:
        shape = "both_growing"
    else:
        shape = "unknown"

    # Past-tense verbs throughout: the side labels are authored noun phrases of
    # mixed grammatical number ("debit cards in force" / "cash withdrawn at
    # ATMs"), and grew/fell/shrank agree with both — so one template stays
    # grammatical without the registry having to declare number.
    if shape == "both_shrinking":
        title = (f"{_cap(behind)} shrank faster than {ahead} "
                 f"({_pp(gap)} apart over a year)")
        move  = f"Both shrank over the year, {behind} the faster of the two."
    elif shape == "split":
        title = (f"{_cap(ahead)} grew while {behind} fell "
                 f"({_pp(gap)} apart over a year)")
        move  = f"{_cap(ahead)} grew over the year; {behind} fell."
    elif shape == "both_growing":
        title = (f"{_cap(ahead)} grew faster than {behind} "
                 f"({_pp(gap)} apart over a year)")
        move  = f"Both grew over the year, {ahead} the faster of the two."
    else:
        title = f"{_cap(ahead)} outpaced {behind} ({_pp(gap)} apart over a year)"
        move  = f"{_cap(ahead)} outpaced {behind} over the year."

    body_parts = [
        f"{_cap(a_label)} and {b_label} normally move together — they are two "
        f"readings of the same activity. Over the past year they have come "
        f"apart. {move} Measured as {a_label} minus {b_label}, the two "
        f"year-on-year rates are {_pp(gap)} apart.",
    ]
    chain = [
        f"{_cap(a_label)} and {b_label} are a declared pair: each side's growth "
        f"is measured against the same month a year earlier.",
        f"{move}",
        f"The gap between the two rates — {a_label} minus {b_label} — is "
        f"{_pp(gap)}, wide enough to count as a divergence rather than "
        f"ordinary drift.",
    ]

    if flagged:
        names = "; ".join(f"{_short(e)} {_pp(v)}" for e, v, _ in flagged[:3])
        body_parts.append(
            f"At the bank level the gap is concentrated, not general: "
            f"{len(flagged)} {'bank' if len(flagged) == 1 else 'banks'} are "
            f"flagged — {names}.")
        chain.append(f"{len(flagged)} {'bank' if len(flagged) == 1 else 'banks'} "
                     f"show the same split on their own books, the widest at "
                     f"{_pp(flagged[0][1])}.")

    implication = (
        f"A gap between {a_label} and {b_label} is a question, not a conclusion: "
        "the two sides can part company because behaviour changed, because one "
        "side has a base effect, or because reporting shifted. Watch whether the "
        "gap closes next month — a pair that stays apart for several months is "
        "telling you the relationship itself has changed.")

    return {"title": title, "body": " ".join(body_parts), "chain": chain,
            "implication": implication, "insight_kind": "divergence_pair"}


# ── review render (reads signals.db; writes nothing) ─────────────────────────

def _rotation_signals(registry: dict, pipeline: str) -> list[tuple[str, dict]]:
    return [(sid, s) for sid, s in registry["signals"].items()
            if s["pipeline"] == pipeline
            and s.get("compute", {}).get("method", "").endswith("_rotation")]


METRIC_LABELS = {
    "credit_cards":  "credit cards",
    "debit_cards":   "debit cards",
    "pos_terminals": "POS terminals",
    "upi_qr":        "UPI QR codes",
    "atms":          "ATMs",
}


def _subject(sig: dict) -> str:
    """The registry-declared subject of a relational signal: explicit
    compute.subject (divergence), else share_of (SIBC rotation), else the
    humanised metric label (ATM/POS rotation)."""
    comp = sig.get("compute", {})
    if comp.get("subject"):
        return comp["subject"]
    if comp.get("share_of"):
        return comp["share_of"]
    metric = comp.get("metric", "the mix")
    return METRIC_LABELS.get(metric, metric.replace("_", " "))


def main() -> int:
    ap = argparse.ArgumentParser(description="Render rotation insights for review.")
    ap.add_argument("--pipeline", choices=["sibc", "atm_pos"], required=True)
    ap.add_argument("--period", required=True, help="signals.db period (YYYY-MM-DD)")
    args = ap.parse_args()

    registry = json.loads((SIG / "registry.json").read_text())
    roles = entity_roles(args.pipeline)
    conn = sqlite3.connect(f"file:{SIG / 'signals.db'}?mode=ro", uri=True)

    for sid, sig in _rotation_signals(registry, args.pipeline):
        dist, mass = rotation_distribution(conn, sid, args.pipeline, args.period)
        ins = rotation_insight(dist, mass, roles, _subject(sig))
        print(f"═══ {sid} ═══")
        if ins is None:
            print("  (no rows for this period — window not available)\n")
            continue
        print(f"  TITLE: {ins['title']}")
        print(f"  BODY : {ins['body']}")
        for i, step in enumerate(ins["chain"], 1):
            print(f"  CHAIN {i}. {step}")
        print(f"  IMPL : {ins['implication']}\n")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
