#!/usr/bin/env python3
"""
generate_opportunities_feed.py — Stage 5.8 (presentation)
---------------------------------------------------------
Assembles the UI-consumable opportunities bundle from the derived feeds + authored
prose, per COMPOSITION_SPEC §12. Output: web/public/data/opportunities_feed.json.
No LLM — every string is authored (opportunity.description / channel.mechanism /
force_instance.label); only status + evidence come from S3.

Usage:  python3 analysis/generate_opportunities_feed.py
"""
import json
import sqlite3
from pathlib import Path

import generate_skeleton as gs

ROOT = gs.ROOT
OUT = ROOT / "web" / "public" / "data" / "opportunities_feed.json"

# code → SIBC section (for chart reuse on the page); None → no chart
SIBC_SECTION = {"I": "bankCredit", "II": "bankCredit", "III": "bankCredit",
                "1": "mainSectors", "2": "mainSectors", "3": "mainSectors", "4": "mainSectors"}
SIBC_SECTION_META = {
    "bankCredit": ("Bank Credit", "🏦"), "mainSectors": ("Main Sectors", "📊"),
    "industryBySize": ("Industry by Size", "🏭"), "services": ("Services", "🛎️"),
    "personalLoans": ("Personal Loans", "💳"), "prioritySector": ("Priority Sector", "⭐"),
    "industryByType": ("Industry by Type", "🔩"),
}


def sibc_section_for(code, statement):
    if statement == "Statement 2":
        return "industryByType"
    if code in SIBC_SECTION:
        return SIBC_SECTION[code]
    if code.startswith("2."):
        return "industryBySize"
    if code.startswith("3."):
        return "services"
    if code.startswith("4."):
        return "personalLoans"
    if code in list("i ii iii iv v vi vii viii ix x".split()):
        return "prioritySector"
    return "mainSectors"


def latest_period(pipeline):
    con = sqlite3.connect(gs.ANALYSIS / "signals" / "signals.db")
    row = con.execute("select max(period) from signals where pipeline=?", (pipeline,)).fetchone()
    con.close()
    return row[0] if row else None


ATM_GROUP = {"credit_card": ("cc", "Credit Cards", "💳"),
             "debit_card": ("dc", "Debit Cards", "🏧"),
             "pos_acceptance": ("infra", "Infrastructure", "🏗️"),
             "qr_acceptance": ("infra", "Infrastructure", "🏗️"),
             "atm_cash": ("infra", "Infrastructure", "🏗️"),
             "micro_atm_cash": ("infra", "Infrastructure", "🏗️")}


def load_chart_series_index():
    """registry signal_id -> chart_series[] (the exact chart series names to highlight)."""
    reg = gs.load_json(gs.ANALYSIS / "signals" / "registry.json")
    return {sid: s.get("chart_series") or []
            for sid, s in reg["signals"].items()}


def build_pipeline_items(pipeline, channels):
    period = latest_period(pipeline)
    cfg = gs.PIPELINES[pipeline]
    model = gs.load_json(cfg["model"])
    feed_path = cfg["model"].parent / f"opportunities_{period}.json"
    if not feed_path.exists():
        return []
    derived = {i["id"]: i for i in gs.load_json(feed_path)["items"]}
    opp_nodes = {n["id"]: n for n in model["nodes"] if n.get("tier") in ("opportunity", "risk")}
    fi = {f["id"]: f for f in model.get("force_instances", [])}
    ent = {n["urn"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    chart_series = load_chart_series_index()

    items = []
    for oid, d in derived.items():
        n = opp_nodes.get(oid)
        if not n:
            continue
        refs = d.get("refs", {})
        inst = fi.get((refs.get("instances") or [None])[0])
        chan = next((c for c in channels if c["id"] in (refs.get("channels") or [])), None)
        driver = inst["label"] if inst else None
        via = chan["label"] if chan else None
        # section (for chart) from the first anchored entity
        section_id, sec_title, sec_icon, highlight = None, "", "", []
        anchor = (refs.get("entities") or [None])[0]
        e = ent.get(anchor)
        if e:
            if pipeline == "sibc":
                section_id = sibc_section_for(e["code"], e.get("statement"))
                sec_title, sec_icon = SIBC_SECTION_META.get(section_id, ("", ""))
                # highlight = chart series of the anchored entity's L1 signals; prefer the
                # entity-specific single-series signals (a yoy/abs/share on THIS entity) over
                # broad scan/count signals that list every sibling series.
                singles, union = [], []
                for sid in e.get("signal_ids") or []:
                    cs = chart_series.get(sid, [])
                    for x in cs:
                        if x not in union:
                            union.append(x)
                    if len(cs) == 1 and cs[0] not in singles:
                        singles.append(cs[0])
                highlight = singles or union
            else:
                g = ATM_GROUP.get((e.get("concept_tags") or {}).get("product"))
                if g:
                    section_id, sec_title, sec_icon = g
                    highlight = ["Total"]   # payments slice highlights the headline total
        chain = []
        if chan:
            chain.append(chan.get("mechanism", chan["label"]))
        if inst:
            chain.append(f"Triggered by {inst['label']}"
                         + (f" — {inst.get('source','')[:80]}" if inst.get("source") else ""))
        if d.get("evidence"):
            chain.append("Live signals confirming: " + ", ".join(d["evidence"]))
        items.append({
            "id": oid, "pipeline": pipeline, "scope": "pipeline",
            "tier": n["tier"], "status": d["status"], "authored_status": d.get("authored_status"),
            "section": {"id": section_id, "title": sec_title, "icon": sec_icon},
            "title": n["label"], "body": n.get("description", ""),
            "implication": (f"Lenders aligned to {via} capture this first." if via else None),
            "chain": chain, "driver": driver, "via": via,
            "evidence": d.get("evidence", []),
            "highlight": highlight,
        })
    return items


def build_cross_system():
    states = sorted((ROOT / "analysis" / "cross_source").glob("ecosystem_state_*.json"))
    if not states:
        return []
    eco = gs.load_json(states[-1])
    out = []
    for p in eco.get("cross_source_opportunities", []):
        e = next((x for x in eco["cross_edge_states"] if x["id"] == p["refs"]["cross_edge"]), {})
        out.append({
            "id": p["id"], "status": p["status"], "title": p["label"],
            "body": p.get("mechanism", ""),
            "basis": f"{e.get('from','')} (f={e.get('from_direction')}) → "
                     f"{e.get('to','')} (t={e.get('to_direction')})",
            "link": p["refs"]["cross_edge"], "badge": "Credit ✕ Payments",
        })
    return out


def main():
    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")["channels"]
    bundle = {
        "_meta": {"spec_ref": "analysis/COMPOSITION_SPEC.md §12",
                  "generated_by": "analysis/generate_opportunities_feed.py",
                  "periods": {p: latest_period(p) for p in gs.PIPELINES}},
        "cross_system": build_cross_system(),
        "pipelines": {p: build_pipeline_items(p, channels) for p in gs.PIPELINES},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, indent=2, ensure_ascii=False))
    n = sum(len(v) for v in bundle["pipelines"].values())
    print(f"opportunities_feed.json: {n} pipeline items + {len(bundle['cross_system'])} cross-system")
    for pipe, items in bundle["pipelines"].items():
        from collections import Counter
        print(f"  {pipe}: {dict(Counter(i['status'] for i in items))}")
    print(f"  → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
