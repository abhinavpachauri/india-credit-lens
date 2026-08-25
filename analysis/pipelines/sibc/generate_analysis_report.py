#!/usr/bin/env python3
"""
Stage 5.5 — Generate L1 annotation JSON from LLM evaluation output.

Reads:  analysis/signals/evaluations/sibc/{period}.json
        analysis/signals/registry.json
Writes: web/public/data/sibc_l1_annotations.json

The output is keyed by UI section (bankCredit, mainSectors, etc.) and contains
annotation-shaped objects derived from the computed signal evaluations.
These are merged with L2/L3 authored annotations in the UI at build time.

Signal → section routing is done by domain + signal prefix rules below.
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

# Add <repo>/analysis to sys.path (location-independent) so signals.* / core.* resolve
# regardless of where this module lives (it moved to pipelines/sibc/ in the §4 cutover).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from signals.query import signal_numbers, scan_distribution, _signal_type   # noqa: E402
from core.relational_insights import (                                       # noqa: E402
    rotation_insight, divergence_insight, rotation_distribution,
    movement_insight, entity_roles, _subject as relational_subject)
from core.paths import ROOT as REPO
from core.cuts import sibc_cut, sibc_sections, chart_label   # noqa: E402
ANAL  = REPO / "analysis"
SIG   = ANAL / "signals"
EVALS = SIG / "evaluations"
REG   = SIG / "registry.json"
OUT   = REPO / "web" / "public" / "data" / "sibc_l1_annotations.json"

# ── Signal → UI section routing ───────────────────────────────────────────────
# Default: domain maps to section. Overrides handle cases where one domain
# spans multiple UI sections (sector_mix→services, industry→industryByType).

DOMAIN_SECTION: dict[str, str] = {
    "credit_headline": "bankCredit",
    "sector_mix":      "mainSectors",
    "industry":        "industryBySize",
    "retail":          "personalLoans",
    "psl":             "prioritySector",
}

# Signals that belong to a different section than their domain default
SIGNAL_SECTION_OVERRIDE: dict[str, str] = {
    # relational signals describe the sub-sector mix, not the size partition
    "sibc-industry-rotation":     "industryByType",
    "sibc-industry-divergence":   "industryByType",
    "sibc-services-rotation":     "services",
    "sibc-services-divergence":   "services",

    # sector_mix signals that describe services sub-sectors → services section
    "sibc-services-yoy-scan":     "services",
    "sibc-services-share-scan":   "services",
    "sibc-trade-sub-yoy-scan":    "services",
    "sibc-trade-sub-share-scan":  "services",
    "sibc-nbfc-sub-yoy-scan":     "services",
    "sibc-nbfc-sub-share-scan":   "services",
    "sibc-sectors-positive-yoy-count": "mainSectors",

    # industry signals that describe sub-sector types → industryByType section
    "sibc-industry-type-yoy-scan":         "industryByType",
    "sibc-industry-type-share-scan":       "industryByType",
    "sibc-engineering-sub-yoy-scan":       "industryByType",
    "sibc-engineering-sub-share-scan":     "industryByType",
    "sibc-infra-sub-yoy-scan":             "industryByType",
    "sibc-infra-sub-share-scan":           "industryByType",
    "sibc-chemicals-sub-yoy-scan":         "industryByType",
    "sibc-chemicals-sub-share-scan":       "industryByType",
    "sibc-basic-metal-sub-yoy-scan":       "industryByType",
    "sibc-basic-metal-sub-share-scan":     "industryByType",
    "sibc-textiles-sub-yoy-scan":          "industryByType",
    "sibc-textiles-sub-share-scan":        "industryByType",
    "sibc-food-processing-sub-yoy-scan":   "industryByType",
    "sibc-food-processing-sub-share-scan": "industryByType",
}

# ── Signal method → preferredMode ─────────────────────────────────────────────

def preferred_mode(method: str) -> str:
    """Which chart view best represents this signal when its insight is active.
    'share' means the Distribution tab (% share); the others are Trend-tab modes.
    The card switches BOTH tab and mode to this — so a share insight shows the
    distribution, and a streak/yoy insight shows the YoY line it describes."""
    if "share" in method:                         # share + share-scan → distribution
        return "share"
    if "abs" in method or "delta" in method:      # levels / FY add → absolute
        return "absolute"
    # streak tracks a YoY/growth condition over time → show the YoY line, not the level.
    # yoy / acceleration / ratio / breadth / yoy-scan → YoY too.
    return "yoy"

# ── Signal → insight type ─────────────────────────────────────────────────────

def insight_type(obs: str, inf: str) -> str:
    """
    Signals about contraction/decline/structural gaps → 'gap'.
    Everything else → 'insight'.
    Simple heuristic from the observation and inference text.
    """
    text = (obs + " " + inf).lower()
    gap_words = ["contracted", "contraction", "declining", "missing", "opaque",
                 "not captured", "double-counted", "cannot", "no breakdown"]
    if any(w in text for w in gap_words):
        return "gap"
    return "insight"

# ── Title derivation ──────────────────────────────────────────────────────────

def derive_title(eval_entry: dict) -> str:
    """
    Use LLM-generated title if present (prompt v1.5+).
    Otherwise synthesise from observation: take first sentence (split on '. '
    not '.'), truncate to 90 chars at word boundary.
    """
    import re
    if eval_entry.get("title"):
        return eval_entry["title"].strip()
    obs = eval_entry.get("observation", "").strip()
    # Split on period+space to avoid splitting on decimal points (₹213.6)
    sentences = re.split(r"\.\s+", obs)
    first = sentences[0].rstrip(".")
    if len(first) <= 90:
        return first
    # Truncate at last word boundary before 90 chars
    truncated = first[:90].rsplit(" ", 1)[0]
    return truncated + "…"

# ── Traceability: data points the insight rests on (basis.facts) ──────────────

def _fmt_val(v, unit: str) -> str:
    if unit == "pct":     return f"{v:.1f}%"
    if unit == "pp":      return f"{v:.1f}pp"
    if unit == "lcr_cr":  return f"{v:,.1f}L Cr"
    if unit == "ratio":   return f"{v:.1f}x"
    if unit == "periods": return f"{int(v)} periods"
    return f"{v:,.1f}"


def data_facts(facts: dict, src_ref: dict) -> list[str]:
    """Readable list of the computed data points this insight rests on — the
    traceability anchors (basis.facts in the shared schema)."""
    u = facts.get("unit") or ""
    out: list[str] = []
    if facts.get("value") is not None:
        out.append(f"Current: {_fmt_val(facts['value'], u)}")
    if facts.get("prior") is not None:
        out.append(f"Prior period: {_fmt_val(facts['prior'], u)}")
    for label, v in (facts.get("components") or {}).items():
        nice = label.replace("fy_yoy:", "FY YoY @ ")
        out.append(f"{nice}: {_fmt_val(v, 'pct')}")
    rng = facts.get("range") or {}
    if rng.get("min") is not None and rng.get("max") is not None:
        line = f"Range: {_fmt_val(rng['min'], u)} – {_fmt_val(rng['max'], u)}"
        if rng.get("count"):                 # scans have no period count — omit, never print "?"
            line += f" over {rng['count']} periods"
        out.append(line)
    sf = src_ref.get("source_file", "")
    if sf:
        out.append(f"Source: {sf} ({src_ref.get('method', '')})")
    return out


# ── Deterministic scan insights (every number from the distribution) ──────────
# Scan signals summarise a distribution — a mechanical task the LLM does badly
# (it rounds, groups, and invents middle-entity figures). We generate their
# body/chain/implication directly from the ranked distribution so every number
# is grounded by construction and Check 2g hard-enforces them.

def _short(name: str) -> str:
    name = re.split(r"\s*\(", name)[0]
    name = re.split(r"\s+including\b", name)[0]
    name = re.split(r"\s+other than\b", name)[0]
    return name.strip()


def _is_residual(name: str) -> bool:
    """RBI's catch-all 'Others' bucket — the sub-sectors it does not break out. It is a residual,
    not a sector, so it must never headline a leaderboard ('Others is the biggest slice of X'). When
    it is large, the real signal is a classification gap, not a composition read."""
    return _short(name).strip().lower() in {"others", "other"}


def _scan_fmt(v: float, unit: str) -> str:
    return f"{v:.1f}%" if unit == "pct" else f"{v:,.0f}"


def deterministic_scan_insight(dist: list[tuple], unit: str, kind: str = "yoy",
                               share_of: str | None = None) -> tuple[str, str, list[str], str]:
    """Return (title, body, chain, implication) for a scan distribution —
    fully grounded in the ranked entity values.

    `kind` is DECLARED by the registry spec (compute.method: *_scan_share →
    "share", *_scan_yoy → "yoy") — never inferred from the values. The old
    any-negative heuristic misread every all-positive growth scan as a share
    distribution and summed growth rates into "top three hold X% of the total".
    `share_of` is the spec's label for the share denominator (compute.share_of),
    so share cards can say what the percentages are shares OF."""
    n  = len(dist)
    fv = lambda v: _scan_fmt(v, unit)
    spread = dist[0][1] - dist[-1][1] if n >= 2 else 0.0
    gap = f"{spread:.1f} percentage points"
    L0, Lv0 = _short(dist[0][0]), fv(dist[0][1])
    W0, Wv0 = _short(dist[-1][0]), fv(dist[-1][1])

    if kind == "share":
        of = f"of {share_of}" if share_of else "of the parent category"
        residual = next((d for d in dist if _is_residual(d[0])), None)
        named = [d for d in dist if not _is_residual(d[0])]
        if residual and named:
            # RBI's 'Others' residual is in the mix — never headline it as a sector. Lead with the
            # biggest NAMED sub-sector; the residual's size is the classification-coverage story.
            rv = fv(residual[1])
            nL0, nLv0 = _short(named[0][0]), fv(named[0][1])
            if len(named) == 1:
                title = f"RBI breaks out only {nL0} {of} — the rest is unclassified"
                body = (f"{nL0} is the one named sub-sector RBI reports {of}, at {nLv0}. The remaining "
                        f"{rv} sits in an unclassified 'Others' residual — these are size shares, not "
                        f"growth rates.")
                chain = [
                    f"{nL0} is the only broken-out sub-sector at {nLv0} {of}.",
                    f"The residual 'Others' holds {rv} {of} — RBI names nothing else.",
                    "A lone named block beside a large residual is a coverage gap, not a mix.",
                ]
                implication = (f"Only {nL0} is visible {of}; most of the category is an unclassified "
                               "block. Read it as data coverage, not composition.")
            else:
                nW0, nWv0 = _short(named[-1][0]), fv(named[-1][1])
                title = f"{nL0} leads the named {share_of or 'sub-sectors'} at {nLv0}"
                body = (f"Among the sub-sectors RBI actually breaks out, {nL0} holds the largest share "
                        f"{of} at {nLv0}, {_short(named[1][0])} {fv(named[1][1])}; {nW0} is the smallest "
                        f"at {nWv0}. A further {rv} is the unclassified 'Others' residual — these are "
                        f"size shares, not growth rates.")
                chain = [
                    f"{nL0} is the largest named block at {nLv0} {of}.",
                    f"{nW0} is the smallest named block at {nWv0}.",
                    f"RBI leaves {rv} {of} in an unclassified 'Others' residual.",
                ]
                implication = (f"Composition among the classified sub-sectors: {nL0} carries the most "
                               f"weight. But {rv} is unclassified — read the named mix with that caveat.")
            return title, body, chain, implication
        top3 = sum(v for _, v, _ in dist[:3])
        if n == 2:
            # two break-outs: a comparison, not a leaderboard (no "top three",
            # no duplicate listing of the same entity as runner-up AND lowest)
            close = dist[-1][1] >= 0.75 * dist[0][1]
            title = f"{L0} holds {Lv0} {of}; {W0} {Wv0}"
            full = top3 >= 97          # the two break-outs ARE the whole parent
            coverage = (f"Together the two break-outs cover {fv(top3)} {of} — the full category."
                        if full else
                        f"Together the two break-outs cover {fv(top3)} {of}; the rest "
                        f"is not sub-classified in the RBI statement.")
            body = (f"RBI breaks {share_of or 'this category'} into two sub-categories. "
                    f"{L0} holds {Lv0} and {W0} {Wv0} — these are size shares, not growth "
                    f"rates. " + coverage)
            chain = [
                f"{L0} is the larger break-out at {Lv0} {of}.",
                f"{W0} holds {Wv0} — a {gap} gap between the only two break-outs.",
                (f"Together they cover {fv(top3)} {of} — the full category."
                 if full else
                 f"Together they cover {fv(top3)} {of}; RBI does not sub-classify the rest."),
            ]
            implication = (
                "Read this as size mix, not momentum: "
                + (f"the two blocks are close in size — a move in either shifts {share_of or 'the mix'}. "
                   if close else
                   f"{L0} is clearly the bigger block. ")
                + "Check the matching growth scan before positioning.")
        else:
            title = f"{L0} is the biggest slice {of} at {Lv0}"
            body = (f"{L0} holds the largest share {of} at {Lv0}, "
                    f"{_short(dist[1][0])} {fv(dist[1][1])}; {W0} is the smallest at {Wv0}. "
                    f"These are size shares, not growth rates. "
                    f"Top three hold {fv(top3)} {of}, spread {gap}.")
            chain = [
                f"{L0} is the largest block at {Lv0} {of}.",
                f"{W0} is the smallest at {Wv0} — a {gap} spread across {n} sub-categories.",
                f"The top three hold {fv(top3)} {of} — "
                f"{'concentrated' if top3 > 60 else 'dispersed'} mix.",
            ]
            implication = (
                f"Composition, not momentum: {L0} carries the most weight {of}. "
                + ("Concentration means the big blocks drive the category — watch them first."
                   if top3 > 60 else
                   "A dispersed mix — no single block decides the category."))
        return title, body, chain, implication

    # kind == "yoy" — growth rates; NEVER sum them into a "share of total"
    residual = next((d for d in dist if _is_residual(d[0])), None)
    named = [d for d in dist if not _is_residual(d[0])]
    # Only reframe when the residual would otherwise headline (it is the fastest mover, or it is one of
    # only two break-outs). A named sub-sector already leading needs no help.
    if residual and named and (_is_residual(dist[0][0]) or len(named) == 1):
        rv = fv(residual[1])
        if len(named) == 1:
            # a two-way split of one named sub-sector vs the residual — lead with the named one.
            nL0, nLv0 = _short(named[0][0]), fv(named[0][1])
            sub = f"sub-sector of {share_of}" if share_of else "sub-sector"
            title = f"{nL0} is RBI's only named {sub} — grew {nLv0} YoY"
            body = (f"{nL0} is the only sub-sector RBI breaks out {('of ' + share_of) if share_of else ''}, "
                    f"and it grew {nLv0} year-on-year. The unclassified 'Others' residual grew {rv} — a "
                    f"black-box mover, not a sector signal.")
            chain = [
                f"{nL0} is the only named sub-sector, at {nLv0} YoY.",
                f"The 'Others' residual grew {rv} — RBI names nothing else here.",
                "One named block beside a large residual is a coverage gap, not a mix.",
            ]
            implication = (f"Only {nL0}'s momentum is legible; the rest is an unclassified block. Read "
                           "it as coverage, not a sector call.")
        else:
            # >=2 named, but the residual is the fastest — lead with the fastest NAMED sub-sector.
            L0, Lv0 = _short(named[0][0]), fv(named[0][1])
            W0, Wv0 = _short(named[-1][0]), fv(named[-1][1])
            title = f"{L0} is the fastest-growing named {share_of or 'sub-sector'} at {Lv0}"
            body = (f"Among the sub-sectors RBI names, {L0} leads YoY growth at {Lv0}, {W0} slowest at "
                    f"{Wv0}. The unclassified 'Others' residual grew {rv}.")
            chain = [
                f"{L0} is the fastest named block at {Lv0} YoY.",
                f"{W0} is the slowest named block at {Wv0}.",
                f"The 'Others' residual grew {rv} — a black-box mover, not a sector signal.",
            ]
            implication = (f"Momentum among the classified sub-sectors: {L0} is pulling ahead. The "
                           "'Others' residual moved too, but it is unclassified — don't read a sector into it.")
        return title, body, chain, implication
    n_pos = sum(1 for _, v, _ in dist if v > 0)
    if n == 2:
        title = f"{L0} growing at {Lv0} YoY; {W0} at {Wv0}"
        body = (f"{L0} grew {Lv0} year-on-year against {W0} at {Wv0} — "
                f"a {gap} growth gap between the two sub-categories RBI breaks out.")
        direction = ("Both are growing — the gap is about pace, not direction."
                     if n_pos == 2 else
                     "One is growing while the other contracts — a direction split, not just pace."
                     if n_pos == 1 else
                     "Both are contracting.")
        chain = [
            f"{L0} is the faster of the two at {Lv0} YoY.",
            f"{W0} is at {Wv0} — {gap} behind.",
            direction,
        ]
    else:
        title = f"{L0} growing fastest at {Lv0}; {W0} slowest at {Wv0}"
        body = (f"{L0} leads YoY growth at {Lv0}, {_short(dist[1][0])} at {fv(dist[1][1])}; "
                f"{W0} is slowest at {Wv0}. "
                f"{n_pos} of {n} categories growing, spread {gap}.")
        chain = [
            f"{L0} is the standout at {Lv0} YoY.",
            f"{W0} is the weakest at {Wv0} — a spread of {gap} across {n} categories.",
            f"{n_pos} of {n} categories are growing — "
            f"{'broad-based' if n_pos > n / 2 else 'concentrated'} momentum.",
        ]
    implication = (
        f"Lenders can lean into {L0} ({Lv0}) and monitor {W0} ({Wv0}). "
        + ("Broad participation supports diversified deployment."
           if n_pos > n / 2 else
           "Narrow leadership argues for selective positioning."))
    return title, body, chain, implication


# ── Main ──────────────────────────────────────────────────────────────────────

# Movement cuts: one card per dashboard dimension. Each names the section it belongs to, the
# speed signal that satisfies the pairing rule, and the noun the prose adds to ("...of all new
# {subject}"). Adding a cut is a row here plus its registry entries — no new code.
MOVEMENT_CUTS = [
    # slug,        section,           speed signal,                    subject
    ("main",       "mainSectors",     "sibc-main-yoy-scan",            "bank credit"),
    ("ind-type",   "industryByType",  "sibc-industry-type-yoy-scan",   "industry credit"),
    ("ind-size",   "industryBySize",  "sibc-ind-size-yoy-scan",        "industry credit"),
    ("svcs",       "services",        "sibc-services-yoy-scan",        "services credit"),
    ("pl",         "personalLoans",   "sibc-pl-yoy-scan",              "personal loans"),
    ("psl",        "prioritySector",  "sibc-psl-yoy-scan",             "priority sector credit"),
    ("infra-sub",  "industryByType",  "sibc-infra-sub-yoy-scan",       "infrastructure credit"),
]

def movement_annotations(conn, period: str, registry: dict, sections: dict) -> list[tuple[str, dict]]:
    """One movement card per cut — where the new credit went, how fast, speeding up or not.

    Deliberately built OUTSIDE the evaluation loop. The movement family's prose is deterministic
    by design (signals/README.md), so making a card conditional on an LLM evaluation having run
    would be backwards, and would silently drop it in any period evaluated before these signals
    existed.

    Three registry signals plus a speed scan, ONE card per cut. Emitting them separately would
    say one thing three times on a dashboard that already renders too many.
    """
    def rows(metric_id: str, entity_type: str) -> dict:
        return {e: v for e, v in conn.execute(
            "SELECT entity_id, value FROM signals WHERE pipeline='sibc' AND period=? "
            "AND metric_id=? AND entity_type=?", (period, metric_id, entity_type))}

    out: list[tuple[str, dict]] = []
    for slug, section, speed_sid, subject in MOVEMENT_CUTS:
        mom_sid, acc_sid, alloc_sid = (f"sibc-{slug}-momentum", f"sibc-{slug}-acceleration",
                                       f"sibc-{slug}-allocation")
        et = (registry.get(mom_sid, {}).get("compute", {}) or {}).get("entity_type")
        if not et:
            continue
        momentum = rows(mom_sid, et)
        if not momentum:
            continue
        agg     = rows(mom_sid, "aggregate")
        alloc   = rows(alloc_sid, "alloc")
        contrib = rows(alloc_sid, "contribution")
        accel   = rows(acc_sid, et)
        speed_et = (registry.get(speed_sid, {}).get("compute", {}) or {}).get("entity_type", et)
        speed   = rows(speed_sid, speed_et)

        ins = movement_insight(alloc, contrib, momentum, agg.get("total"),
                               agg.get("gross_movement"), agg.get("coherence"),
                               accel, speed, subject)
        if ins is None:
            continue

        # The chart's vocabulary, looked up — never the compute layer's. signals.db
        # carries the CSV's full RBI names ("Non-Banking Financial Companies (NBFCs)")
        # while the chart draws the override ("NBFCs"), and a hand-kept map covering
        # only the main cut left the services and personal-loan cards highlighting a
        # series that does not exist. A lead the chart cannot draw at all — an
        # infrastructure sub-type, say — falls back to the cut's parent, which it can,
        # until §15.6 lets the chart render the sub-cut itself.
        lead = max(alloc or momentum, key=(alloc or momentum).get)
        cut  = sibc_cut(registry.get(alloc_sid, {}).get("compute", {}))
        highlight = (chart_label(sections, section, lead)
                     or chart_label(sections, section, cut.parent_code or ""))
        facts = signal_numbers(conn, alloc_sid, registry.get(alloc_sid, {}), "sibc", period)
        out.append((section, {
            "id":            alloc_sid,
            "layer":         1,
            "title":         ins["title"],
            "body":          ins["body"],
            "implication":   ins["implication"],
            "preferredMode": "yoy",
            "effect":        {"highlight": [highlight] if highlight else [],
                              "cut": cut.as_json()},
            "claim_type":    "data",
            "insight_kind":  ins["insight_kind"],
            # Declared reads — the card quotes allocation next to speed and acceleration, so
            # Check 2g scopes to exactly these signals rather than falling back to period-wide.
            "sourceSignals": [alloc_sid, mom_sid, acc_sid, speed_sid],
            "basis": {
                "facts":      data_facts(facts, {}),
                "inferences": ins["chain"],
            },
        }))
    return out


def main(period: str | None = None) -> int:
    with open(REG) as f:
        registry = json.load(f)["signals"]

    conn = sqlite3.connect(f"file:{SIG / 'signals.db'}?mode=ro", uri=True)

    # Find latest SIBC evaluation if period not specified
    eval_dir = EVALS / "sibc"
    if period:
        eval_path = eval_dir / f"{period}.json"
    else:
        files = sorted(eval_dir.glob("*.json"))
        if not files:
            print("ERROR: no SIBC evaluation files found")
            return 1
        eval_path = files[-1]
        period = eval_path.stem

    print(f"Reading evaluation: {eval_path}")
    with open(eval_path) as f:
        ev = json.load(f)

    # Flatten all evaluated signals: signal_id → {observation, direction, inference}
    eval_signals: dict[str, dict] = {}
    for domain, dd in ev["domains"].items():
        for sid, se in dd.get("signals", {}).items():
            eval_signals[sid] = {**se, "_domain": domain}

    # Group signals by UI section
    all_sections: list[str] = [
        "bankCredit", "mainSectors", "industryBySize",
        "services", "personalLoans", "prioritySector", "industryByType",
    ]
    sections_out: dict[str, dict] = {s: {"insights": [], "gaps": [], "opportunities": []} for s in all_sections}

    # What each section's chart actually draws, and what it calls each series
    # (core.cuts, shared with the gate that checks this). Resolved once.
    sections = sibc_sections()

    for sid, se in eval_signals.items():
        reg_sig = registry.get(sid)
        if not reg_sig or reg_sig.get("layer") != 1:
            continue


        domain  = se["_domain"]
        section = SIGNAL_SECTION_OVERRIDE.get(sid) or DOMAIN_SECTION.get(domain)
        if not section or section not in sections_out:
            continue

        method       = reg_sig.get("compute", {}).get("method", "")
        cut          = sibc_cut(reg_sig.get("compute", {}))
        # DERIVED, never the registry's hand-typed `chart_series` (§15.4). Typing it
        # by hand produced highlights that render nothing: 'Education Loans' where the
        # chart draws 'Education', 'Power' where the chart has no such series at all.
        # A card about a sub-cut still highlights its parent — the only thing this
        # chart can draw — and now DECLARES the cut it is really about, so the gap is
        # visible to the gate instead of silent until §15.6 closes it.
        named        = (cut.codes if cut.shape in ("level", "pair")
                        else (cut.parent_code or "",))
        chart_series = [l for l in (chart_label(sections, section, c) for c in named) if l]
        facts        = signal_numbers(conn, sid, reg_sig, "sibc", period)
        stype        = _signal_type(reg_sig)
        insight_kind = None

        # Shared schema: basis.facts = traceable data points (the numbers this
        # rests on), basis.inferences = the reasoning chain rendered by the card.
        if stype in ("rotation", "divergence"):
            # Relational signals: deterministic prose is the product
            # (signals/README.md) — never the LLM-eval branch. No rows for the
            # period (window unavailable / nothing diverges) → no card.
            if stype == "rotation":
                dist, mass_val = rotation_distribution(conn, sid, "sibc", period)
                rel = rotation_insight(dist, mass_val, entity_roles("sibc"),
                                       relational_subject(reg_sig))
            else:
                dist = scan_distribution(conn, sid, "sibc", period)
                rel = divergence_insight(dist, relational_subject(reg_sig))
            if rel is None:
                continue
            title, body, chain, inf = (rel["title"], rel["body"],
                                       rel["chain"], rel["implication"])
            insight_kind = rel["insight_kind"]
            itype = "insight"
        elif stype == "scan" and (dist := scan_distribution(conn, sid, "sibc", period)):
            # Scan distributions are generated deterministically (grounded by
            # construction), not from the LLM narrative. Semantics come from the
            # SPEC: *_scan_share → size shares (with the spec's share_of label),
            # *_scan_yoy → growth rates. Never inferred from the values.
            comp = reg_sig.get("compute", {})
            scan_kind = "share" if "share" in comp.get("method", "") else "yoy"
            title, body, chain, inf = deterministic_scan_insight(
                dist, facts.get("unit") or "pct",
                kind=scan_kind, share_of=comp.get("share_of"))
            itype = "insight"
        else:
            obs   = se.get("observation", "")
            dir_  = se.get("direction",   "")
            inf   = se.get("inference",   "")
            chain = se.get("chain") or []
            title = derive_title(se)
            body  = " ".join(filter(None, [obs, dir_]))
            itype = insight_type(obs, inf)
        annotation = {
            "id":            sid,
            "layer":         1,
            "title":         title,
            "body":          body,
            "implication":   inf,
            "preferredMode": preferred_mode(method),
            "effect":        {**({"highlight": chart_series} if chart_series else {}),
                              "cut": cut.as_json()},
            "claim_type":    "data",
            "basis":         {
                "facts":      data_facts(facts, se.get("source_ref", {})),
                "inferences": chain,
            },
        }
        if insight_kind:
            annotation["insight_kind"] = insight_kind

        sections_out[section][itype + "s"].append(annotation)

    for section, card in movement_annotations(conn, period, registry, sections):
        if section in sections_out:
            sections_out[section]["insights"].append(card)

    output = {
        "pipeline":     "sibc",
        "period":       period,
        "generated_at": ev.get("evaluated_at", ""),
        "sections":     sections_out,
    }

    with open(OUT, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Summary
    total = sum(
        len(v["insights"]) + len(v["gaps"])
        for v in sections_out.values()
    )
    print(f"Written: {OUT}")
    print(f"Period:  {period}")
    print(f"Total L1 annotations: {total}")
    for sec, data in sections_out.items():
        n = len(data["insights"]) + len(data["gaps"])
        if n:
            print(f"  {sec:<20} {n} ({len(data['insights'])} insights, {len(data['gaps'])} gaps)")
    return 0


if __name__ == "__main__":
    period_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(period_arg))
