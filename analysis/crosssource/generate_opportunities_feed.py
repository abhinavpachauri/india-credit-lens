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
import sys
from pathlib import Path

# Bootstrap: <repo>/analysis on sys.path so `from core import …` resolves from any cwd now
# that this script lives under crosssource/. Move-safe via .git walk (see core/paths.py).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs  # noqa: E402

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
            "evidence_all": d.get("evidence_all", d.get("evidence", [])),
            "highlight": ref["highlight"] if ref else [],
            "charts": [ref] if ref else [],
        })
    return items


DRIVER_BADGE = {"cross_edge": "Credit ✕ Payments", "construct": "Ecosystem · construct",
                "eco_loop": "Ecosystem · loop", "constraint": "Data check"}
DIR_WORD = {1: "rising", -1: "falling", 0: "flat", None: "unobserved"}
LOOP_SEG_WORD = {"active": "running", "reversed": "running in reverse", "dormant": "idle"}


def _load_eco_model():
    p = ROOT / "analysis" / "cross_source" / "ecosystem_model.json"
    return gs.load_json(p) if p.exists() else {}


def _member_fact(pipe, ent, db_cache):
    """The member's own headline signal value for the basis row: prefer its direct YoY."""
    for sid in ent.get("signal_ids") or []:
        if sid.endswith("-yoy") and (pipe, sid) in db_cache:
            v = db_cache[(pipe, sid)]
            return {"id": sid, "value": v["value"], "unit": v["unit"], "status": v["status"],
                    "display": f"{v['value']:+.1f}% YoY"}
    return None


def _db_latest_values(periods):
    """(pipeline, metric_id) → {value, unit, status} at that pipeline's latest period."""
    con = sqlite3.connect(gs.ANALYSIS / "signals" / "signals.db")
    out = {}
    for pipe, period in periods.items():
        if not period:
            continue
        # total-level rows: atm_pos uses entity_type='total'; sibc uses ('aggregate', 'total')
        for m, v, u, s in con.execute(
                "select metric_id, value, unit, status from signals "
                "where pipeline=? and period=? and (entity_type='total' or entity_id='total')",
                (pipe, period)):
            out[(pipe, m)] = {"value": round(v, 2) if isinstance(v, float) else v, "unit": u, "status": s}
    con.close()
    return out


def _construct_item(p, eco_state, eco_model, eidx, chart_series, db_cache):
    """§23.2/§23.3 — construct-driven item: member charts + deterministic computed basis."""
    urn = p["refs"]["construct"]
    cstate = eco_state.get("construct_states", {}).get(urn, {})
    construct = next((c for c in eco_model.get("constructs", []) if c["urn"] == urn), {})
    b = cstate.get("basis", {})
    d = cstate.get("direction", 0)
    word = "expanding" if d > 0 else "contracting" if d < 0 else "mixed"

    # member rows (measures before proxies) + charts (cap 3) + facts (direct signal values)
    rows, charts, facts = [], [], []
    members = sorted(b.get("members", []), key=lambda m: m.get("role") != "measures")
    for m in members:
        if m["urn"] not in eidx:
            continue
        pipe, ent = eidx[m["urn"]]
        fact = _member_fact(pipe, ent, db_cache)
        if fact:
            facts.append({k: fact[k] for k in ("id", "value", "unit", "status")})
        rows.append({"role": m.get("role"), "label": f"{ent['label']} ({PIPE_LABEL.get(pipe, pipe)})",
                     "direction": m.get("direction"),
                     "value": fact["display"] if fact else DIR_WORD.get(m.get("direction"), "")})
        if len(charts) < 3:
            ref = chart_ref_for_entity(pipe, ent, chart_series, with_caption=True)
            if ref:
                charts.append(ref)

    inputs = ", ".join(f"{r['label'].split(' (')[0]} {r['value'] or DIR_WORD.get(r['direction'], '')}"
                       for r in rows)
    sustained = cstate.get("direction_prev") == d and d != 0
    coverage = (f"{b.get('observed', 0)}/{b.get('total', 0)} measurements observed · "
                + " · ".join(f"{PIPE_LABEL.get(pl, pl)} @ {pd}"
                             for pl, pd in (b.get("pipelines") or {}).items()))
    basis = {
        "headline": f"{construct.get('label', urn)} → {word}",
        "coverage": coverage,
        "members": rows,
        "chain": [
            f"Measured inputs: {inputs}.",
            "Member directions combine — measures and proxies count as-is, contra-indicators "
            f"flipped — giving {'an' if word[0] in 'aeiou' else 'a'} {word} read on "
            f"{b.get('observed', 0)} of {b.get('total', 0)} measurements.",
            construct.get("definition", ""),
            ("Direction sustained across two composed periods → status active."
             if sustained else "Direction is new or flipped this period → status watch."),
        ],
        "facts": facts,
    }
    body = (f"{construct.get('label', 'This measure')} is {word}. It is not one series — it is "
            "credit and payments data read together, and right now most of its measurements are "
            "moving the same way. The computed basis below shows exactly which inputs drive the read.")
    implication = ("Treat this as the combined read across credit and payments — check the basis "
                   "to see which side is doing the work before acting on it.")
    return {"basis": basis, "charts": charts, "body": body, "implication": implication,
            "chain": basis["chain"][:2] + [basis["chain"][3]]}


def _loop_item(p, eco_state, eco_model, eidx, chart_series):
    """§23.3 — loop-driven item: segment states + endpoint charts."""
    lid = p["refs"]["eco_loop"]
    lstate = eco_state.get("eco_loop_states", {}).get(lid, {})
    loop = next((l for l in eco_model.get("loops", []) if l["id"] == lid), {})
    xstates = {x["id"]: x for x in eco_state.get("cross_edge_states", [])}
    estates = eco_state.get("eco_edge_states", {})
    clabels = {c["urn"]: c.get("label") for c in eco_model.get("constructs", [])}

    def urn_label(u):
        if u in clabels:
            return clabels[u]
        if u in eidx:
            return eidx[u][1]["label"]
        return u

    rows = []
    for ref in loop.get("member_edges", []):
        kind, _, rest = ref.partition(":")
        if kind == "x":
            x = xstates.get(rest, {})
            st = {"aligned": "active", "divergent": "reversed"}.get(x.get("state"), "dormant")
            frm, to = x.get("from"), x.get("to")
        elif kind == "eco":
            e = estates.get(rest, {})
            st, frm, to = e.get("state", "dormant"), e.get("from"), e.get("to")
        else:
            continue
        rows.append({"role": "segment", "label": f"{urn_label(frm)} → {urn_label(to)}",
                     "direction": 1 if st == "active" else -1 if st == "reversed" else 0,
                     "value": LOOP_SEG_WORD.get(st, st)})

    charts = []
    for urn in p["refs"].get("entities", []):
        if urn in eidx and len(charts) < 3:
            pipe, ent = eidx[urn]
            ref = chart_ref_for_entity(pipe, ent, chart_series, with_caption=True)
            if ref:
                charts.append(ref)

    segs = "; ".join(f"{r['label']} — {r['value']}" for r in rows)
    periods_line = " · ".join(f"{PIPE_LABEL.get(pl, pl)} @ {pd}"
                              for pl, pd in (lstate.get("input_periods") or {}).items())
    basis = {
        "headline": f"{loop.get('label', lid)} → {lstate.get('state', 'dormant').replace('_', ' ')}",
        "coverage": f"{lstate.get('live_edges', 0)}/{lstate.get('total_edges', 0)} segments live · {periods_line}",
        "members": rows,
        "chain": [
            f"Segment states: {segs}.",
            "A loop fires only when every segment runs in its expected direction; "
            f"{lstate.get('live_edges', 0)} of {lstate.get('total_edges', 0)} are live, "
            "so the cycle is " + ("running." if lstate.get("state", "").startswith("active")
                                  else "engaged but not aligned — one segment is moving against the cycle."),
            loop.get("description", ""),
        ],
        "facts": [],
    }
    body = ("This is a feedback cycle read across both pipelines: spending, balances, and appetite "
            "feed each other. The basis below shows each segment and whether it is currently "
            "running with the cycle or against it.")
    implication = ("A fully-running cycle compounds; a segment moving against it is the early "
                   "warning that the cycle is turning. Watch the reversed segment.")
    return {"basis": basis, "charts": charts, "body": body, "implication": implication,
            "chain": basis["chain"]}


def _constraint_item(p, eco_state, eco_model, models, chart_series):
    """§23.1 — violated data check: a risk card with the computed residual."""
    cid = p["refs"]["constraint"]
    cstate = eco_state.get("constraint_states", {}).get(cid, {})
    cx = next((c for c in eco_model.get("constraints", []) if c["id"] == cid), {})
    lo, hi = (cx.get("tolerance", {}).get("value") or [None, None])[:2]
    charts = []
    sid_owner = {}
    for pipe, m in models.items():
        for n in m["nodes"]:
            for s in n.get("signal_ids") or []:
                sid_owner[s] = (pipe, n)
    for op in cx.get("operands", []):
        owner = sid_owner.get(op.get("signal_id"))
        if owner and len(charts) < 3:
            ref = chart_ref_for_entity(owner[0], owner[1], chart_series, with_caption=True)
            if ref:
                charts.append(ref)
    basis = {
        "headline": f"{cx.get('label', cid)} → violated",
        "coverage": f"computed value {cstate.get('value')} vs corridor [{lo}, {hi}]",
        "members": [],
        "chain": [cx.get("relation", ""),
                  f"Computed value {cstate.get('value')} falls outside the plausibility corridor "
                  f"[{lo}, {hi}] — this is a data problem to fix, not an economic event."],
        "facts": [],
    }
    body = ("Two independent sources that must reconcile no longer do. Until the source data is "
            "fixed, read any insight touching these series with caution.")
    return {"basis": basis, "charts": charts, "body": body,
            "implication": "Fix the data before trusting downstream insights on these series.",
            "chain": basis["chain"]}


def build_cross_system(models, chart_series):
    states = sorted((ROOT / "analysis" / "cross_source").glob("ecosystem_state_*.json"))
    if not states:
        return []
    eco_state = gs.load_json(states[-1])
    eco_model = _load_eco_model()
    eidx = _entity_index(models)
    db_cache = _db_latest_values(eco_state.get("_meta", {}).get("pipeline_periods", {}))
    out = []
    for p in eco_state.get("cross_source_opportunities", []):
        kind = (p.get("driver") or {}).get("kind", "cross_edge")

        if kind == "construct":
            built = _construct_item(p, eco_state, eco_model, eidx, chart_series, db_cache)
        elif kind == "eco_loop":
            built = _loop_item(p, eco_state, eco_model, eidx, chart_series)
        elif kind == "constraint":
            built = _constraint_item(p, eco_state, eco_model, models, chart_series)
        else:
            # cross-edge items — the v1.0 path, unchanged
            e = next((x for x in eco_state["cross_edge_states"] if x["id"] == p["refs"]["cross_edge"]), {})
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
            built = {
                "charts": charts, "basis": None,
                "chain": [
                    f"The early signal is on the leading side: {lead}.",
                    "What happens there tends to show up on the other side a little later.",
                    f"So expect the other side to follow: {lag}.",
                ],
                "body": (f"{lead} is the early signal; {lag} usually follows it a few months later. "
                         "Reading the two together gives an early view of where the slower side is heading."),
                "implication": "Use the leading side to plan ahead for the lagging side, before it shows up there.",
            }

        item = {
            "id": p["id"], "scope": "cross_source", "tier": p.get("tier", "opportunity"),
            "status": p["status"], "title": p.get("label") or p.get("title", ""),
            "body": built["body"], "implication": built["implication"], "chain": built["chain"],
            "badge": DRIVER_BADGE.get(kind, "Cross-system"), "driver": p.get("driver"),
            "charts": built["charts"],
            "evidence": p.get("evidence", []), "evidence_all": p.get("evidence_all", []),
        }
        if built.get("basis"):
            item["basis"] = built["basis"]
        out.append(item)
    return out


def main():
    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")["channels"]
    chart_series = load_chart_series_index()
    models = {p: gs.load_json(cfg["model"]) for p, cfg in gs.PIPELINES.items()}
    bundle = {
        "_meta": {"spec_ref": "analysis/COMPOSITION_SPEC.md §12",
                  "generated_by": "analysis/crosssource/generate_opportunities_feed.py",
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
