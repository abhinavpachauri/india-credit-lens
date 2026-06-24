#!/usr/bin/env python3
"""
run_inference.py — stratum S4 (LLM inference loop, sourcing-gated)
-----------------------------------------------------------------
COMPOSITION_SPEC.md §8. Detects what the causal model does NOT explain, then asks an
LLM to PROPOSE new channels / force-instances / cross-edges that might. Every proposal
must name the external source that would have to be checked to confirm it. Proposals are
HYPOTHESES — written to analysis/s4_proposals/{period}.json with status 'proposed', they
NEVER auto-enter the model. A human (or a later session) sources + promotes them.

Detection (deterministic):
  1. Unexplained movement — an entity whose live signal is moving but which no force/channel
     points at (no incoming drives/suppresses/amplifies edge and not in any force_instance scope).
  2. Authored-vs-observed mismatch — a force authored 'active' that S3 computes as not firing.
  3. Unconfirmed cross-link — a derived stock↔flow candidate whose both sides are live but which
     is not yet in composition.json.

Usage:  python3 analysis/run_inference.py            # all pipelines, latest period
        python3 analysis/run_inference.py --no-llm   # detection only (no proposals)
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

from core import generate_skeleton as gs

ROOT = gs.ROOT
OUT_DIR = ROOT / "analysis" / "s4_proposals"
DRIVER_EDGES = {"drives", "suppresses", "amplifies"}

SYSTEM = (
    "You are a credit-systems analyst proposing NEW causal explanations for India Credit Lens. "
    "You are given movements in the data that the current model does NOT explain, plus the "
    "mechanisms (channels) the model already has. Propose candidate explanations. CRITICAL: every "
    "proposal MUST name the specific external source (a regulator circular, official report, or "
    "price series) that someone would have to check to confirm it — proposals are hypotheses until "
    "sourced and will NOT be added to the model without that source. Do not propose anything an "
    "existing channel already covers. Be concrete and plain. Return ONLY JSON: "
    '{"proposals":[{"kind":"channel|instance|cross_edge","label":"...","mechanism":"plain '
    'one-sentence how","affects":"which product/entity","required_source":"the exact source to '
    'check","claim_type":"hypothesis"}]}.'
)


def latest_state(cfg):
    files = sorted(cfg["model"].parent.glob("system_state_*.json"))
    return gs.load_json(files[-1]) if files else None


def detect_unexplained(pipeline, cfg):
    model = gs.load_json(cfg["model"])
    state = latest_state(cfg)
    if not state:
        return [], None
    ent = {n.get("urn"): n for n in model["nodes"] if n.get("tier") == "entity"}
    id2urn = {n["id"]: n.get("urn") for n in ent.values()}
    # urns that already have a driver: behavioral-edge target or force_instance scope
    driven = set()
    for e in model["edges"]:
        if e.get("type") in DRIVER_EDGES and e.get("to") in id2urn:
            driven.add(id2urn[e["to"]])
    for fi in model.get("force_instances", []):
        driven.update(fi.get("scope_entities", []))
    unexplained = []
    for urn, st in state["entity_states"].items():
        n = ent.get(urn)
        tags = (n or {}).get("concept_tags") or {}
        # only LEAF entities — aggregates move mechanically from their children, not from a force
        if (st["direction"] != 0 and urn not in driven and st.get("observed", 0) > 0
                and tags.get("product") and n and n.get("structural_role") == "leaf"):
            unexplained.append({"entity": n["label"], "urn": urn, "product": tags["product"],
                                "direction": "rising" if st["direction"] > 0 else "falling"})
    mismatches = state["system_observations"].get("authored_vs_observed_mismatches", [])
    return unexplained[:15], mismatches


def detect_cross():
    cand_f = ROOT / "analysis/cross_source/candidates.json"
    comp_f = ROOT / "analysis/cross_source/composition.json"
    if not cand_f.exists():
        return []
    cand = gs.load_json(cand_f)["candidates"]
    confirmed = {(c["from"], c["to"]) for c in gs.load_json(comp_f).get("cross_edges", [])} if comp_f.exists() else set()
    # focus on the meaningful stock↔flow leads not yet confirmed
    return [{"from": c["from"], "to": c["to"], "shared": c.get("shared"), "rule": c["rule"]}
            for c in cand if c["rule"] == "R1_stock_flow" and (c["from"], c["to"]) not in confirmed][:10]


VERIFY_SYSTEM = (
    "You verify a proposed causal mechanism for India's credit/payments system. USE WEB SEARCH to "
    "find an authoritative PRIMARY source (RBI, NPCI, Ministry of Finance, PIB, Union Budget). Decide "
    "whether a real, citable source actually supports the claimed mechanism — do NOT invent a URL. If "
    "you cannot find a real supporting source, say so. Return ONLY JSON: "
    '{"verified":true/false,"verdict":"supported|not_found|contradicts","url":"","source_title":"",'
    '"excerpt":"a short line quoted from the source","verified_date":"YYYY-MM-DD","note":""}.'
)


MODEL = "claude-sonnet-4-5-20250929"


def _parse_json(text):
    a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b + 1])


def _claude_json(system, payload, web=False, timeout=240):
    """Prefer the Anthropic API (reliable, supports the web_search server tool) when
    ANTHROPIC_API_KEY is set; fall back to the `claude -p` CLI otherwise. The CLI is
    rate-gated on the Pro subscription, so the API path is the default for S4."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        kwargs = dict(model=MODEL, max_tokens=2000, system=system,
                      messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
        if web:
            kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}]
        resp = client.messages.create(**kwargs)
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
        return _parse_json(text)
    # CLI fallback (no web search available this way)
    proc = subprocess.run(["claude", "-p", "--output-format", "text"],
                          input=f"{system}\n\n{'─'*50}\n\n{json.dumps(payload, ensure_ascii=False)}",
                          capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[:200])
    return _parse_json(proc.stdout)


def call_llm(payload):
    # one retry — the generation call occasionally returns malformed JSON
    for attempt in range(2):
        try:
            return _claude_json(SYSTEM, payload).get("proposals", [])
        except (json.JSONDecodeError, ValueError):
            if attempt == 1:
                raise
    return []


def verify_proposal(p):
    """Web-verify a proposal's source. Returns the proposal with a `verification` block and a
    `promotable` flag (true only when a real supporting source with a URL + excerpt is found)."""
    try:
        v = _claude_json(VERIFY_SYSTEM, {"label": p.get("label"), "mechanism": p.get("mechanism"),
                                         "affects": p.get("affects"),
                                         "source_to_check": p.get("required_source")}, web=True)
    except Exception as e:
        v = {"verified": False, "verdict": "error", "note": str(e)[:120]}
    p["verification"] = v
    p["promotable"] = bool(v.get("verified") and v.get("verdict") == "supported" and v.get("url"))
    if p["promotable"]:
        p["claim_type"] = "inference"        # now externally sourced
        p["source"] = v.get("source_title", "")
        p["source_url"] = v.get("url", "")
        p["source_excerpt"] = v.get("excerpt", "")
        p["source_verified_date"] = v.get("verified_date", "")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--no-verify", action="store_true", help="skip the web source-verification pass")
    args = ap.parse_args()

    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")["channels"]
    chan_labels = [c["label"] for c in channels]
    period = max(filter(None, (
        Path(f).stem.replace("system_state_", "")
        for f in glob.glob(str(ROOT / "analysis/*/merged/system_state_*.json")))), default="latest")

    gaps, proposals = {"unexplained": {}, "mismatches": {}, "cross": []}, []
    for pipe, cfg in gs.PIPELINES.items():
        unexplained, mismatches = detect_unexplained(pipe, cfg)
        gaps["unexplained"][pipe] = unexplained
        gaps["mismatches"][pipe] = mismatches
        if (unexplained or mismatches) and not args.no_llm:
            try:
                props = call_llm({"pipeline": pipe, "unexplained_movements": unexplained,
                                  "mismatches_to_review": mismatches, "existing_channels": chan_labels})
                for p in props:
                    p["from_pipeline"] = pipe
                proposals += props
            except Exception as e:
                print(f"  ⚠ {pipe}: {e}", file=sys.stderr)

    gaps["cross"] = detect_cross()
    if gaps["cross"] and not args.no_llm:
        try:
            proposals += call_llm({"scope": "cross_system",
                                   "unconfirmed_stock_flow_links": gaps["cross"],
                                   "existing_channels": chan_labels})
        except Exception as e:
            print(f"  ⚠ cross: {e}", file=sys.stderr)

    # web source-verification pass — turns "source needed" into verified/rejected (sourcing gate)
    if proposals and not args.no_llm and not args.no_verify:
        print(f"  verifying {len(proposals)} proposals against primary sources (web)…", file=sys.stderr)
        proposals = [verify_proposal(p) for p in proposals]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "_meta": {"description": "S4 inference proposals — HYPOTHESES, sourcing-gated. NEVER "
                                 "auto-promoted; review + source + promote by hand.",
                  "spec_ref": "analysis/COMPOSITION_SPEC.md §8", "period": period},
        "gaps_detected": gaps,
        "proposals": [{**p, "status": "proposed"} for p in proposals],
    }
    out_path = OUT_DIR / f"{period}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    nun = sum(len(v) for v in gaps["unexplained"].values())
    promotable = [p for p in out["proposals"] if p.get("promotable")]
    print(f"S4 inference @ {period}: {nun} unexplained movements, "
          f"{sum(len(v) for v in gaps['mismatches'].values())} mismatches, "
          f"{len(gaps['cross'])} unconfirmed cross-links")
    print(f"  → {len(out['proposals'])} proposals · {len(promotable)} PROMOTABLE (source verified) · "
          f"{len(out['proposals']) - len(promotable)} stay hypothesis")
    for p in promotable:
        print(f"    ✓ PROMOTABLE [{p['kind']}] {p.get('label','')[:46]}")
        print(f"        source: {p.get('source_url','')}")
    print(f"  wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
