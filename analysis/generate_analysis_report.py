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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from signals.query import signal_numbers, scan_distribution, _signal_type   # noqa: E402

REPO  = Path(__file__).resolve().parent.parent
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
        out.append(f"Range: {_fmt_val(rng['min'], u)} – {_fmt_val(rng['max'], u)} "
                   f"over {rng.get('count', '?')} periods")
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


def _scan_fmt(v: float, unit: str) -> str:
    return f"{v:.1f}%" if unit == "pct" else f"{v:,.0f}"


def deterministic_scan_insight(dist: list[tuple], unit: str) -> tuple[str, str, list[str], str]:
    """Return (title, body, chain, implication) for a scan distribution —
    fully grounded in the ranked entity values."""
    n  = len(dist)
    fv = lambda v: _scan_fmt(v, unit)
    leaders  = dist[:2]
    laggard  = dist[-1]
    spread   = dist[0][1] - dist[-1][1] if n >= 2 else 0.0
    n_pos    = sum(1 for _, v, _ in dist if v > 0)
    signed   = any(v < 0 for _, v, _ in dist)        # yoy-type (growth) vs share-type
    top3     = sum(v for _, v, _ in dist[:3])

    L0, Lv0 = _short(leaders[0][0]), fv(leaders[0][1])
    W0, Wv0 = _short(laggard[0]),    fv(laggard[1])

    title = f"{L0} leads at {Lv0}; {W0} lowest at {Wv0}"

    parts = [f"{L0} leads at {Lv0}"]
    if n > 1:
        parts.append(f"{_short(leaders[1][0])} at {fv(leaders[1][1])}")
    body = ", ".join(parts) + f"; {W0} is lowest at {Wv0}. "
    body += (f"{n_pos} of {n} categories positive, spread {fv(spread)}."
             if signed else
             f"Top three hold {fv(top3)} of the total, spread {fv(spread)}.")

    chain = [
        f"{L0} is the standout at {Lv0}.",
        f"{W0} is the weakest at {Wv0} — a spread of {fv(spread)} across {n} categories.",
        (f"{n_pos} of {n} categories are growing — "
         f"{'broad-based' if n_pos > n / 2 else 'concentrated'} momentum."
         if signed else
         f"The top three hold {fv(top3)} of the total — "
         f"{'concentrated' if top3 > 60 else 'dispersed'} mix."),
    ]
    implication = (
        f"Lenders can lean into {L0} ({Lv0}) and monitor {W0} ({Wv0}). "
        + ("Broad participation supports diversified deployment."
           if (signed and n_pos > n / 2) else
           "Narrow leadership argues for selective positioning.")
    )
    return title, body, chain, implication


# ── Main ──────────────────────────────────────────────────────────────────────

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

    for sid, se in eval_signals.items():
        reg_sig = registry.get(sid)
        if not reg_sig or reg_sig.get("layer") != 1:
            continue

        domain  = se["_domain"]
        section = SIGNAL_SECTION_OVERRIDE.get(sid) or DOMAIN_SECTION.get(domain)
        if not section or section not in sections_out:
            continue

        method       = reg_sig.get("compute", {}).get("method", "")
        chart_series = reg_sig.get("chart_series", [])
        facts        = signal_numbers(conn, sid, reg_sig, "sibc", period)

        # Shared schema: basis.facts = traceable data points (the numbers this
        # rests on), basis.inferences = the reasoning chain rendered by the card.
        if _signal_type(reg_sig) == "scan" and (dist := scan_distribution(conn, sid, "sibc", period)):
            # Scan distributions are generated deterministically (grounded by
            # construction), not from the LLM narrative.
            title, body, chain, inf = deterministic_scan_insight(dist, facts.get("unit") or "pct")
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
            "effect":        {"highlight": chart_series} if chart_series else {},
            "claim_type":    "data",
            "basis":         {
                "facts":      data_facts(facts, se.get("source_ref", {})),
                "inferences": chain,
            },
        }

        sections_out[section][itype + "s"].append(annotation)

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
