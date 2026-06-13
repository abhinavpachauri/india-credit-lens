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


PIPE_LABEL = {"sibc": "Credit", "atm_pos": "Payments"}


def load_chart_series_index():
    """registry signal_id -> chart_series[] (the exact chart series names to highlight)."""
    reg = gs.load_json(gs.ANALYSIS / "signals" / "registry.json")
    return {sid: s.get("chart_series") or []
            for sid, s in reg["signals"].items()}


def _entity_index(models):
    idx = {}
    for pipe, m in models.items():
        for n in m["nodes"]:
            if n.get("tier") == "entity" and n.get("urn"):
                idx[n["urn"]] = (pipe, n)
    return idx


def chart_ref_for_entity(pipe, e, chart_series, with_caption=False):
    """Resolve an entity to a chart spec: {pipeline, section, highlight, caption}."""
    if pipe == "sibc":
        section_id = sibc_section_for(e["code"], e.get("statement"))
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
        section_id = g[0] if g else None
        highlight = ["Total"]
    if not section_id:
        return None
    ref = {"pipeline": pipe, "section": section_id, "highlight": highlight}
    if with_caption:
        ref["caption"] = f"{e['label']} ({PIPE_LABEL.get(pipe, pipe)})"
    return ref


def build_pipeline_items(pipeline, channels, models, chart_series):
    period = latest_period(pipeline)
    cfg = gs.PIPELINES[pipeline]
    model = models[pipeline]
    feed_path = cfg["model"].parent / f"opportunities_{period}.json"
    if not feed_path.exists():
        return []
    derived = {i["id"]: i for i in gs.load_json(feed_path)["items"]}
    opp_nodes = {n["id"]: n for n in model["nodes"] if n.get("tier") in ("opportunity", "risk")}
    fi = {f["id"]: f for f in model.get("force_instances", [])}
    ent = {n["urn"]: n for n in model["nodes"] if n.get("tier") == "entity"}

    items = []
    for oid, d in derived.items():
        n = opp_nodes.get(oid)
        if not n:
            continue
        refs = d.get("refs", {})
        inst = fi.get((refs.get("instances") or [None])[0])
        chan = next((c for c in channels if c["id"] in (refs.get("channels") or [])), None)
        e = ent.get((refs.get("entities") or [None])[0])
        ref = chart_ref_for_entity(pipeline, e, chart_series) if e else None
        sec = SIBC_SECTION_META.get(ref["section"], ("", "")) if (ref and pipeline == "sibc") \
            else (ATM_GROUP.get((e.get("concept_tags") or {}).get("product"), (None, "", ""))[1:]
                  if e and pipeline == "atm_pos" else ("", ""))
        # deterministic fallback causal chain (the narrative step rewrites this in plain English)
        chain = []
        if chan:
            chain.append(chan.get("mechanism", chan["label"]))
        if inst:
            chain.append(f"This is being driven by {inst['label']}.")
        items.append({
            "id": oid, "pipeline": pipeline, "scope": "pipeline",
            "tier": n["tier"], "status": d["status"], "authored_status": d.get("authored_status"),
            "section": {"id": ref["section"] if ref else None, "title": sec[0], "icon": sec[1]},
            "title": n["label"], "body": n.get("description", ""),
            # plain fallback so "For lenders" is never empty if the narrative LLM call fails;
            # the narrative step overrides this with sharper, numbers-grounded copy.
            "implication": "Move on this while the trend is still running in your favour.",
            "chain": chain,
            # internal context for the narrative step — not rendered on the card
            "_driver": inst["label"] if inst else None, "_via": chan["label"] if chan else None,
            "evidence": d.get("evidence", []),
            "highlight": ref["highlight"] if ref else [],
            "charts": [ref] if ref else [],
        })
    return items


def build_cross_system(models, chart_series):
    states = sorted((ROOT / "analysis" / "cross_source").glob("ecosystem_state_*.json"))
    if not states:
        return []
    eco = gs.load_json(states[-1])
    eidx = _entity_index(models)
    out = []
    for p in eco.get("cross_source_opportunities", []):
        e = next((x for x in eco["cross_edge_states"] if x["id"] == p["refs"]["cross_edge"]), {})
        charts = []
        for urn in (e.get("from"), e.get("to")):
            if urn in eidx:
                pipe, ent = eidx[urn]
                ref = chart_ref_for_entity(pipe, ent, chart_series, with_caption=True)
                if ref:
                    charts.append(ref)
        # plain-English deterministic fallbacks (narrative step overrides with numbers).
        # These avoid jargon ("flow/stock/law") in case the LLM call fails.
        lead = charts[0]["caption"] if len(charts) == 2 else "the leading side"
        lag = charts[1]["caption"] if len(charts) == 2 else "the lagging side"
        chain = [
            f"The early signal is on the leading side: {lead}.",
            "What happens there tends to show up on the other side a little later.",
            f"So expect the other side to follow: {lag}.",
        ]
        body = (f"{lead} is the early signal; {lag} usually follows it a few months later. "
                "Reading the two together gives an early view of where the slower side is heading.")
        implication = "Use the leading side to plan ahead for the lagging side, before it shows up there."
        out.append({
            "id": p["id"], "scope": "cross_source", "tier": "opportunity",
            "status": p["status"], "title": p.get("label") or p.get("title", ""),
            "body": body, "implication": implication, "chain": chain,
            "badge": "Credit ✕ Payments", "charts": charts,
        })
    return out


def main():
    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")["channels"]
    chart_series = load_chart_series_index()
    models = {p: gs.load_json(cfg["model"]) for p, cfg in gs.PIPELINES.items()}
    bundle = {
        "_meta": {"spec_ref": "analysis/COMPOSITION_SPEC.md §12",
                  "generated_by": "analysis/generate_opportunities_feed.py",
                  "periods": {p: latest_period(p) for p in gs.PIPELINES}},
        "cross_system": build_cross_system(models, chart_series),
        "pipelines": {p: build_pipeline_items(p, channels, models, chart_series) for p in gs.PIPELINES},
    }
    # Preserve existing narrative across regeneration (so the gate's feed rebuild does not
    # revert to templated copy). Carry forward body/implication/chain for items that were
    # already narrated; new/changed items stay templated until generate_opportunity_narrative
    # runs again (cached → fast). Same preserve-on-regen pattern as the skeleton.
    if OUT.exists():
        try:
            prev = gs.load_json(OUT)
            narrated = {}
            for it in prev.get("cross_system", []) + [x for v in prev.get("pipelines", {}).values() for x in v]:
                if it.get("narrative"):
                    narrated[it["id"]] = {k: it.get(k) for k in ("body", "implication", "chain")}
            for it in bundle["cross_system"] + [x for v in bundle["pipelines"].values() for x in v]:
                if it["id"] in narrated:
                    it.update(narrated[it["id"]])
                    it["narrative"] = True
        except Exception:
            pass

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
