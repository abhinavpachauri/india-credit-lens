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
from datetime import date
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

# Bootstrap: <repo>/analysis on sys.path so `from core import …` resolves from any cwd now
# that this script lives under core/. Move-safe via .git walk (see core/paths.py).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs  # noqa: E402

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
    "Name the source as a LADDER, most authoritative first, not a single target: a proposal whose "
    "one named document turns out not to say what you expected should degrade to the next rung, "
    "not die. Rung 1 = the specific primary document; rung 2 = a different document from the same "
    "issuer (bulletin, circular, press release); rung 3 = a reputed report or named financial "
    "press. Two to three rungs. The evidence bar does not move — only where we look. "
    "Return ONLY JSON: "
    '{"proposals":[{"kind":"channel|instance|cross_edge","label":"...","mechanism":"plain '
    'one-sentence how","affects":"which product/entity","required_source":"the exact source to '
    'check","source_ladder":["rung 1","rung 2","rung 3"],"claim_type":"hypothesis"}]}.'
)


from core.source_fetch import fetch_text                                   # noqa: E402
from distribution.bank_sourcing import (                                  # noqa: E402
    MIN_EXCERPT_CHARS, excerpt_on_page, tier_of)


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
    "you cannot find a real supporting source, say so. "
    "TEMPORAL VALIDITY (hard rule): the payload's `eval_period` is the data period this mechanism is "
    "proposed to explain. A time-bound scheme/instrument that has EXPIRED or been SUPERSEDED before "
    "eval_period (e.g. a guarantee scheme that ended, a subsidy window that closed, a definition later "
    "revised) cannot be 'supported' for it — verdict 'expired', and name the currently-in-force "
    "successor instrument in `note` (with its own primary source in `url` if found). Standing "
    "regulations still in force (Master Directions as amended, live mandates) are fine regardless of "
    "issue date. Return ONLY JSON: "
    '{"verified":true/false,"verdict":"supported|expired|not_found|contradicts","url":"","source_title":"",'
    '"excerpt":"a short line quoted from the source","verified_date":"YYYY-MM-DD",'
    '"in_force_at_eval_period":true/false,"note":""}.'
)


MODEL = "claude-sonnet-4-5-20250929"
MAX_RUNGS = 3        # each rung is an LLM call with web search — bounded, not exhaustive


def _parse_json(text):
    a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b + 1])


def _claude_json(system, payload, web=False, timeout=240, max_tokens=2000):
    """Prefer the Anthropic API (reliable, supports the web_search server tool) when
    ANTHROPIC_API_KEY is set; fall back to the `claude -p` CLI otherwise. The CLI is
    rate-gated on the Pro subscription, so the API path is the default for S4.

    `max_tokens` is a parameter because the proposal call emits a list and the verify call
    emits one object. Adding `source_ladder` to the proposal schema pushed the list past a
    hardcoded 2000 and every domain came back as truncated JSON — three parse warnings, zero
    proposals, and the run still wrote its empty result over a good file."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system,
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
            return _claude_json(SYSTEM, payload, max_tokens=8000).get("proposals", [])
        except (json.JSONDecodeError, ValueError):
            if attempt == 1:
                raise
    return []


def check_source(url, excerpt, page_text=None):
    """Is the claimed excerpt actually on the page at the claimed URL, on an allowed host?

    `page_text` lets the caller supply text obtained some other way — in practice the editor's
    logged-in Chrome. That is not a workaround: measured across all 47 allowlisted hosts, only
    19 are readable by an automated fetch, and every masthead this project has actually sourced
    from (Business Standard above all) refuses one. The trust anchor is identical either way —
    the excerpt must be literally on the page — so the channel the text came through changes
    nothing about how hard the claim is checked.

    Until 2026-08-19 S4 asked this of nobody. It took the model's word for both the URL and
    the quote — the prompt says "do NOT invent a URL", which is an instruction, not a check —
    while `bank_sourcing.excerpt_on_page`, the trust anchor that makes the bank-claims store
    trustworthy, sat one import away and unused. The allowlist was not consulted either, so a
    force could be sourced to any site on the internet.

    Returns (ok, verdict, tier). Verdicts are recorded whether they pass or fail: a rejection
    is evidence about the world and the reason the same dead search stops being re-run.
    """
    if not url:
        return False, "no_url", None
    tier = tier_of(url)
    if tier is None:
        return False, "off_allowlist", None
    if not excerpt or len(excerpt.strip()) < MIN_EXCERPT_CHARS:
        return False, "no_excerpt", tier
    text, fetch_verdict = (page_text, "ok") if page_text else fetch_text(url)
    if text is None:
        return False, fetch_verdict, tier          # blocked | unreachable | empty | no_pdf_tool
    if not excerpt_on_page(excerpt, text):
        return False, "excerpt_not_on_page", tier
    return True, "excerpt_verified", tier


def verify_proposal(p, eval_period=None):
    """Web-verify a proposal's source, then CHECK what came back.

    `promotable` now requires all of: the model reports a supporting source; the host is on the
    tiered allowlist; the page is actually retrievable; the claimed excerpt is literally on it;
    and the instrument is in force at eval_period (an expired scheme cannot explain a current
    movement — verdict 'expired' carries the in-force successor in its note instead).

    Every attempt is appended to `attempts[]` whatever the outcome, so a negative result is
    retained rather than discarded and re-paid for next period.
    """
    # R3 — a ladder, not one named target. The large-corporate force died because the FSR
    # release it named turned out to be about stability rather than large-corporate credit,
    # and there was no rung below "the exact document I asked for". Capped, because each rung
    # is an LLM call with web search.
    ladder = [r for r in ([p.get("required_source")] + list(p.get("source_ladder") or []))
              if r][:MAX_RUNGS]
    v, checked = {"verified": False, "verdict": "not_found", "note": "no source named"}, False
    if not ladder:
        # Record it. "Nothing to check" is itself a finding about the proposal — a hypothesis
        # that names no source can never be promoted, and silently leaving no trace is exactly
        # the discard R4 exists to stop.
        p.setdefault("attempts", []).append({
            "rung": 0, "target": None, "url": "", "tier": None,
            "verdict": "no_source_named", "llm_verdict": None,
            "date": date.today().isoformat(), "note": "proposal named no source to check",
        })
    for rung, target in enumerate(ladder, 1):
        try:
            v = _claude_json(VERIFY_SYSTEM, {"label": p.get("label"), "mechanism": p.get("mechanism"),
                                             "affects": p.get("affects"),
                                             "eval_period": eval_period,
                                             "source_to_check": target}, web=True)
        except Exception as e:
            v = {"verified": False, "verdict": "error", "note": str(e)[:120]}

        url, excerpt = v.get("url", ""), v.get("excerpt", "")
        # An infrastructure failure is NOT a negative result. A 400 from the API, a timeout, a
        # rate limit — none of them are evidence that no source exists, and recording them as
        # `no_url` alongside genuine dead ends poisons the very record R4 exists to build. On
        # 2026-08-19 an exhausted API balance produced 93 such attempts; read as sourcing
        # verdicts they would have said "the LLM cannot find URLs", which is not what happened.
        if v.get("verdict") == "error":
            checked, check_verdict, tier = False, "check_error", None
        else:
            checked, check_verdict, tier = check_source(url, excerpt)
        v["source_check"], v["tier"], v["rung"] = check_verdict, tier, rung
        attempt = {
            "rung": rung, "target": target, "url": url, "tier": tier,
            "verdict": check_verdict, "llm_verdict": v.get("verdict"),
            "date": date.today().isoformat(), "note": (v.get("note") or "")[:200],
            # Retryable = we never actually learned anything. Settled = we did, good or bad.
            "retryable": check_verdict == "check_error",
        }
        # A failed retry is the SAME non-event as the one before it. Appending each one turns
        # the record into a log of an outage rather than a record of what we learned about the
        # world — so a repeated check_error on the same rung updates in place with a count.
        prior = p.setdefault("attempts", [])
        same = next((a for a in prior if a.get("retryable") and a.get("rung") == rung
                     and a.get("target") == target), None)
        if same and check_verdict == "check_error":
            same.update(attempt)
            same["retries"] = same.get("retries", 1) + 1
        else:
            prior.append(attempt)
        if check_verdict == "check_error":
            break                                    # stop burning rungs on a broken channel
        if checked and v.get("verdict") == "supported":
            break                                    # first rung that actually holds up

    p["verification"] = v
    p["promotable"] = bool(v.get("verified") and v.get("verdict") == "supported"
                           and v.get("in_force_at_eval_period", True) and checked)
    if p["promotable"]:
        p["claim_type"] = "inference"        # now externally sourced AND excerpt-verified
        p["source"] = v.get("source_title", "")
        p["source_url"] = url
        p["source_excerpt"] = excerpt
        p["source_verified_date"] = v.get("verified_date", "")
    return p


def worklist(path):
    """Proposals the automated path could not settle — the handoff to a Chrome session.

    A blocked host is not a dead end, it is a queue. Printing it is what turns `attempts[]`
    from a record into something a person can act on in one pass.
    """
    doc = json.loads(Path(path).read_text())
    out = []
    for i, p in enumerate(doc.get("proposals", [])):
        if p.get("promotable"):
            continue
        last = (p.get("attempts") or [{}])[-1]
        if last.get("verdict") in ("excerpt_verified",):
            continue
        out.append((i, last.get("verdict", "unverified"), last.get("url", ""),
                    last.get("target") or p.get("required_source", ""), p.get("label", "")))
    return out


def cmd_resolve(args):
    """Record a Chrome-sourced verification against the SAME excerpt check as the crawler."""
    path = Path(args.file)
    doc = json.loads(path.read_text())
    p = doc["proposals"][args.index]
    page = Path(args.page_file).read_text(errors="ignore")
    # A browser hands over rendered HTML; reduce it the same way the fetcher does so the
    # substring check behaves identically whichever channel supplied the text.
    from core.source_fetch import html_to_text
    text = html_to_text(page) if "<" in page[:400] else page
    ok, verdict, tier = check_source(args.url, args.excerpt, page_text=text)
    p.setdefault("attempts", []).append({
        "rung": "chrome", "target": p.get("required_source"), "url": args.url, "tier": tier,
        "verdict": verdict, "llm_verdict": None, "date": date.today().isoformat(),
        "note": "verified via editor browser (host refuses automated reads)",
    })
    if ok:
        p["promotable"] = True
        p["claim_type"] = "inference"
        p["source_url"], p["source_excerpt"] = args.url, args.excerpt
        p["source_verified_date"] = date.today().isoformat()
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(("✓ verified + recorded: " if ok else "✗ not recorded: ") + verdict)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--verify-api", action="store_true",
                    help="also run the API web-search source hunt (costs credit; only rung-1 "
                         "official hosts pay off — see COMPOSITION_SPEC §8.1 census)")
    ap.add_argument("--no-verify", action="store_true",
                    help="(default behaviour; kept so existing runbooks do not break)")
    ap.add_argument("--verify-only", metavar="FILE", dest="verify_file",
                    help="verify the proposals already in FILE — no regeneration")
    ap.add_argument("--worklist", metavar="FILE", help="print the proposals a Chrome session must settle")
    ap.add_argument("--resolve", metavar="FILE", dest="file", help="record a Chrome-sourced verification")
    ap.add_argument("--index", type=int, help="proposal index (with --resolve)")
    ap.add_argument("--url"); ap.add_argument("--excerpt"); ap.add_argument("--page-file")
    args = ap.parse_args()

    channels = gs.load_json(ROOT / "analysis/ontology/channels.json")["channels"]
    chan_labels = [c["label"] for c in channels]
    period = max(filter(None, (
        Path(f).stem.replace("system_state_", "")
        for f in glob.glob(str(ROOT / "analysis/*/merged/system_state_*.json")))), default="latest")

    if args.verify_file:
        # Generation and verification are separable because they fail differently and cost
        # differently. Re-running the whole command to verify would discard a good proposal set
        # and pay for it again — and the proposals are the part a human has already read.
        path = Path(args.verify_file)
        doc = json.loads(path.read_text())
        ps = doc.get("proposals", [])
        def settled(p):
            """Already told us something — don't pay for it twice. An attempt that only ever
            hit a broken channel is not settled, which is what makes a resumed run cheap."""
            att = p.get("attempts") or []
            return bool(att) and not all(a.get("retryable") for a in att)

        todo = [p for p in ps if not settled(p)]
        print(f"verifying {len(todo)} of {len(ps)} proposals in {path.name} "
              f"({len(ps) - len(todo)} already settled) — API web-search hunt, costs credit. "
              f"For the browser path use --worklist then --resolve.", file=sys.stderr)
        period = doc.get("_meta", {}).get("period")
        doc["proposals"] = [verify_proposal(p, eval_period=period) if p in todo else p
                            for p in ps]
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
        ok = [p for p in doc["proposals"] if p.get("promotable")]
        print(f"  → {len(ok)} promotable of {len(ps)}")
        return 0

    if args.worklist:
        rows = worklist(args.worklist)
        print(f"{len(rows)} proposal(s) need the editor's browser:\n")
        for i, verdict, url, target, label in rows:
            print(f"  [{i:>2}] {verdict:20} {label[:58]}")
            print(f"       target: {target[:90]}")
            if url:
                print(f"       url:    {url}")
        return 0
    if args.file:
        return cmd_resolve(args)

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
    # Source-finding is OPT-IN, not the default. Generation needs a model — there is no page to
    # read, it is invention. Source-finding is reading pages, and measured across all 47
    # allowlisted hosts only 19 are readable by an automated fetch; every masthead this project
    # has actually sourced from refuses one. So the browser is the channel, `--worklist` and
    # `--resolve` are the path, and the API hunt is an opportunistic extra for rung-1 official
    # targets. Defaulting it ON spent credit re-measuring something already known.
    if proposals and not args.no_llm and args.verify_api:
        print(f"  verifying {len(proposals)} proposals against primary sources (web)…", file=sys.stderr)
        proposals = [verify_proposal(p, eval_period=period) for p in proposals]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "_meta": {"description": "S4 inference proposals — HYPOTHESES, sourcing-gated. NEVER "
                                 "auto-promoted; review + source + promote by hand.",
                  "spec_ref": "analysis/COMPOSITION_SPEC.md §8", "period": period},
        "gaps_detected": gaps,
        "proposals": [{**p, "status": "proposed"} for p in proposals],
    }
    out_path = OUT_DIR / f"{period}.json"
    # A run that produced nothing must not overwrite a file that has something. The
    # source_ladder schema change truncated every domain's JSON on 2026-08-19; the run printed
    # three parse warnings, carried on, and wrote 0 proposals over 36 good ones. Warnings that
    # do not stop the write are the same class of bug as a rule that raises and is ignored.
    if not proposals and out_path.exists():
        try:
            prior = len(json.loads(out_path.read_text()).get("proposals", []))
        except Exception:
            prior = 0
        if prior:
            print(f"✗ generated 0 proposals but {out_path.name} already holds {prior} — refusing "
                  f"to overwrite. Check the parse warnings above.", file=sys.stderr)
            return 1
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
