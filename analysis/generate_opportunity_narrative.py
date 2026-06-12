#!/usr/bin/env python3
"""
generate_opportunity_narrative.py — expository narrative step (COMPOSITION_SPEC §12, option 2)
---------------------------------------------------------------------------------------------
Enriches web/public/data/opportunities_feed.json with LLM-written, numbers-grounded copy:
a sharp "For lenders" implication + a body that weaves in the LIVE signal figures from
signals.db. Read-only over the model/state (it does NOT propose causal structure — that's
S4); it only verbalises what S3 already computed. Uses the `claude -p` CLI (Pro, no API
cost), mirroring evaluate.py. Cached by payload hash so re-runs are instant.

Usage:  python3 analysis/generate_opportunity_narrative.py
        python3 analysis/generate_opportunity_narrative.py --no-llm   # skip (keep templated copy)
"""
import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys

import generate_skeleton as gs

ROOT = gs.ROOT
FEED = ROOT / "web" / "public" / "data" / "opportunities_feed.json"
CACHE = gs.ANALYSIS / "signals" / "narrative_cache.json"

SYSTEM = (
    "You explain a lending opportunity to a smart person who is NOT a finance expert. "
    "Use plain, everyday English and short sentences. Include the actual numbers given, and "
    "say what they mean in normal words. Explain WHAT is happening, WHY it is happening, and "
    "WHAT a bank should do — concretely. "
    "BANNED words/phrases (never use): moat, tailwind, headwind, structural, secular, "
    "intermediated, intermediation, bifurcated, disproportionate, durable, leverage, capture, "
    "deploy, land-grab, synergy, accretive, value accretion, deepening, ecosystem, "
    "positioned, optionality, flywheel, secularly, outperformance, re-rating. "
    "If you would use a fancy word, use the simple one instead (e.g. say 'growing fast' not "
    "'structural tailwind'; 'lending through NBFCs' not 'intermediated flow'). No hype, no "
    'preamble. Return ONLY minified JSON: {"body":"2-3 plain sentences with the numbers",'
    '"implication":"one plain sentence saying what the bank should do"}.'
)


def db_signal_values(pipeline, period, metric_ids):
    if not metric_ids:
        return []
    con = sqlite3.connect(gs.ANALYSIS / "signals" / "signals.db")
    q = ("select metric_id,value,unit,status from signals where pipeline=? and period=? "
         f"and metric_id in ({','.join('?' * len(metric_ids))})")
    rows = con.execute(q, (pipeline, period, *metric_ids)).fetchall()
    con.close()
    return [{"id": m, "value": round(v, 2) if isinstance(v, float) else v, "unit": u, "status": s}
            for m, v, u, s in rows]


def entity_signal_ids(models, urns):
    out = []
    for m in models.values():
        for n in m["nodes"]:
            if n.get("tier") == "entity" and n.get("urn") in urns:
                out += n.get("signal_ids") or []
    return out


def load_cache():
    return gs.load_json(CACHE) if CACHE.exists() else {}


def call_claude(payload):
    user = json.dumps(payload, ensure_ascii=False)
    proc = subprocess.run(["claude", "-p", "--output-format", "text"],
                          input=f"{SYSTEM}\n\n{'─'*50}\n\n{user}",
                          capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[:200])
    txt = proc.stdout.strip()
    a, b = txt.find("{"), txt.rfind("}")
    return json.loads(txt[a:b + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    if not FEED.exists():
        print("✗ opportunities_feed.json not found — run generate_opportunities_feed.py first")
        return 1
    feed = gs.load_json(FEED)
    periods = feed["_meta"]["periods"]
    models = {p: gs.load_json(cfg["model"]) for p, cfg in gs.PIPELINES.items()}
    cache = load_cache()
    done = skipped = failed = 0

    def enrich(item, pipeline, refs_entities):
        nonlocal done, skipped, failed
        if item["status"] not in ("active", "watch"):
            return
        period = periods.get(pipeline) if pipeline else max(periods.values())
        metric_ids = list(dict.fromkeys(
            (item.get("evidence") or []) + entity_signal_ids(models, set(refs_entities or []))))
        signals = db_signal_values(pipeline, period, metric_ids) if pipeline else []
        payload = {"title": item["title"], "description": item.get("body", ""),
                   "driver": item.get("driver"), "via": item.get("via"), "signals": signals}
        key = hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
        if key in cache:
            res = cache[key]; skipped += 1
        elif args.no_llm:
            return
        else:
            try:
                res = call_claude(payload); cache[key] = res; done += 1
            except Exception as e:
                print(f"  ⚠ {item['id']}: {e}", file=sys.stderr); failed += 1; return
        if res.get("body"):
            item["body"] = res["body"]
        if res.get("implication"):
            # the card already renders a "For lenders" header — strip any duplicate prefix
            imp = re.sub(r"^\s*for lenders\s*[:\-—]\s*", "", res["implication"], flags=re.I)
            item["implication"] = imp[0].upper() + imp[1:] if imp else imp
        item["narrative"] = True

    for pipe in gs.PIPELINES:
        for item in feed["pipelines"].get(pipe, []):
            if item["tier"] == "opportunity":
                enrich(item, pipe, item.get("refs", {}).get("entities"))
    # cross-system: enrich in place (no pipeline signals, prose polish only)
    for c in feed.get("cross_system", []):
        if c["status"] in ("active", "watch") and not c.get("narrative"):
            payload = {"title": c["title"], "description": c.get("body", ""),
                       "driver": None, "via": None, "signals": []}
            key = hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
            res = cache.get(key)
            if res is None and not args.no_llm:
                try:
                    res = call_claude(payload); cache[key] = res; done += 1
                except Exception as e:
                    print(f"  ⚠ {c['id']}: {e}", file=sys.stderr); failed += 1; res = None
            if res:
                c["body"] = res.get("body", c["body"])
                c["narrative"] = True

    CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))
    FEED.write_text(json.dumps(feed, indent=2, ensure_ascii=False))
    print(f"narrative: {done} generated, {skipped} cached, {failed} failed → {FEED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
