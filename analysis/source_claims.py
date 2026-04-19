#!/usr/bin/env python3
"""
source_claims.py — India Credit Lens  (Stage 6b)
--------------------------------------------------
Attempts to find credible, publicly-accessible sources for hypothesis and
inference nodes in a system_model.json file using Claude with web search.

For each driver/opportunity/pressure/gap node that is:
  - missing claim_type, OR
  - claim_type = "hypothesis", OR
  - claim_type = "inference" with no source

...the script:
  1. Formulates a targeted search query from the node label + description
  2. Calls Claude (claude-3-5-sonnet) with web_search tool
  3. Extracts the most credible source found (URL + citation text)
  4. If a credible source is found:
       → upgrades claim_type to "inference"
       → populates source, source_url, source_verified_date
  5. If not found: marks claim_type = "hypothesis", logs reason

Writes updated system_model.json in-place (backs up original as .bak).

Source hierarchy (most to least authoritative):
  1. rbi.org.in  — circulars, press releases, annual reports, DBIE
  2. pib.gov.in  — government scheme announcements
  3. mospi.gov.in — MOSPI / NSO macro data
  4. mnre.gov.in, cea.nic.in — energy sector data
  5. siam.in, vahan.parivahan.gov.in — auto / EV data
  6. ibef.org, care ratings, crisil — industry research (secondary)

Usage:
    python3 source_claims.py                                    # merged model
    python3 source_claims.py rbi_sibc/2026-03-30/system_model.json
    python3 source_claims.py --dry-run                          # show what would run, don't update

Requirements:
    pip install anthropic
    ANTHROPIC_API_KEY env var set
"""

import json
import os
import sys
import copy
import argparse
from pathlib import Path
from datetime import date

try:
    import anthropic
except ImportError:
    print("❌  anthropic package not found — run: pip install anthropic", file=sys.stderr)
    sys.exit(1)

TIERS_TO_SOURCE = {"driver", "opportunity", "pressure", "gap"}
TODAY = str(date.today())

# ── Source credibility hierarchy ──────────────────────────────────────────────
# Used in the prompt to guide Claude's source selection
CREDIBLE_SOURCES = """
Credibility hierarchy (prefer in this order):
1. rbi.org.in — RBI circulars, press releases, monetary policy, annual reports, DBIE data
2. pib.gov.in — Press Information Bureau: government scheme announcements, PLI, PMAY, budget
3. mospi.gov.in / data.gov.in — official Indian macro statistics
4. mnre.gov.in, cea.nic.in — Ministry of New & Renewable Energy, Central Electricity Authority
5. siam.in — Society of Indian Automobile Manufacturers (EV/auto sales data)
6. vahan.parivahan.gov.in — VAHAN vehicle registration data
7. ibef.org, care ratings, crisil, icra — industry research (secondary, acceptable if primary unavailable)

Do NOT use: news articles, Wikipedia, blog posts, LinkedIn, Twitter, or paywalled sources.
A source is only valid if it contains a specific verifiable data point that directly supports the claim.
"""


def build_search_query(node: dict) -> str:
    """Generate a targeted search query from node label + description."""
    label = node.get("label", "")
    desc  = node.get("description", "")[:300]
    tier  = node.get("tier", "")

    # Extract the core factual claim from the description
    # Strip forward-looking language — search for what's verifiable
    query = f"India {label} site:rbi.org.in OR site:pib.gov.in OR site:mospi.gov.in"
    return query


def build_source_prompt(node: dict) -> str:
    """Build the Claude prompt for sourcing a specific node."""
    label = node.get("label", "")
    desc  = node.get("description", "")
    tier  = node.get("tier", "")

    return f"""You are a research assistant for India Credit Lens, a financial analytics platform.

I need you to find a credible, publicly accessible source for this claim about Indian bank credit:

CLAIM LABEL: {label}
CLAIM DESCRIPTION: {desc}
CLAIM TYPE: {tier} node in a causal model of Indian bank credit

{CREDIBLE_SOURCES}

TASK:
1. Search for the most authoritative source that directly supports this claim
2. The source must contain a specific verifiable data point (not just general topic)
3. Prefer official Indian government or RBI sources
4. Return ONLY a JSON object in this exact format:

{{
  "found": true | false,
  "claim_type": "inference" | "hypothesis",
  "source": "Exact document name, circular number, or dataset name with date",
  "source_url": "Full URL — must be publicly accessible",
  "source_excerpt": "The specific sentence or data point from the source that supports the claim (max 150 chars)",
  "confidence": "high" | "medium" | "low",
  "rationale": "Why this source supports or does not support the claim (max 100 chars)"
}}

If no credible source is found, set found=false, claim_type="hypothesis", source="", source_url="".
Do not fabricate URLs or citations. If uncertain, say so in rationale."""


def source_node(client: anthropic.Anthropic, node: dict, dry_run: bool = False) -> dict:
    """
    Attempt to source a single node. Returns updated node dict.
    """
    nid   = node.get("id", "?")
    label = node.get("label", "")
    tier  = node.get("tier", "")

    print(f"  [{tier}] {nid}")
    print(f"    label : {label[:70]}")

    if dry_run:
        print(f"    → DRY RUN — skipping API call")
        return node

    prompt = build_source_prompt(node)

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text content from response
        result_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        # Parse JSON from response
        import re
        json_match = re.search(r'\{[^{}]*"found"[^{}]*\}', result_text, re.DOTALL)
        if not json_match:
            print(f"    ⚠  Could not parse JSON response — keeping as hypothesis")
            node = copy.deepcopy(node)
            node["claim_type"]           = "hypothesis"
            node["source"]               = ""
            node["source_url"]           = ""
            node["source_verified_date"] = TODAY
            node["source_rationale"]     = "Auto-sourcing failed to parse response"
            return node

        result = json.loads(json_match.group())
        found       = result.get("found", False)
        claim_type  = result.get("claim_type", "hypothesis")
        source      = result.get("source", "")
        source_url  = result.get("source_url", "")
        excerpt     = result.get("source_excerpt", "")
        confidence  = result.get("confidence", "low")
        rationale   = result.get("rationale", "")

        node = copy.deepcopy(node)
        node["claim_type"]           = claim_type
        node["source"]               = source
        node["source_url"]           = source_url
        node["source_verified_date"] = TODAY

        if excerpt:
            node["source_excerpt"] = excerpt
        if rationale:
            node["source_rationale"] = rationale

        if found and claim_type == "inference":
            print(f"    ✓  Upgraded to inference")
            print(f"       source: {source[:80]}")
            if source_url:
                print(f"       url   : {source_url[:80]}")
        else:
            print(f"    ◈  Remains hypothesis — {rationale[:70]}")

    except anthropic.APIError as e:
        print(f"    ✗  API error: {e} — keeping as hypothesis")
        node = copy.deepcopy(node)
        node["claim_type"]           = "hypothesis"
        node["source"]               = ""
        node["source_url"]           = ""
        node["source_verified_date"] = TODAY
        node["source_rationale"]     = f"API error during sourcing: {str(e)[:80]}"

    return node


def needs_sourcing(node: dict) -> bool:
    """Return True if this node needs a sourcing attempt."""
    tier       = node.get("tier", "")
    claim_type = node.get("claim_type")
    source     = node.get("source", "")

    if tier not in TIERS_TO_SOURCE:
        return False
    if "_comment" in node:
        return False

    # Missing claim_type → needs sourcing
    if not claim_type:
        return True
    # Hypothesis with no source → try to source
    if claim_type == "hypothesis" and not source:
        return True
    # Inference with no source → try to source
    if claim_type == "inference" and not source:
        return True
    # Data → no sourcing needed
    if claim_type == "data":
        return False

    return False


def main():
    ap = argparse.ArgumentParser(description="Stage 6b: Auto-source hypothesis nodes in system_model.json")
    ap.add_argument("model_path", nargs="?",
                    default=str(Path(__file__).parent / "rbi_sibc" / "merged" / "system_model.json"),
                    help="Path to system_model.json (default: merged)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be sourced without calling the API")
    ap.add_argument("--force", action="store_true",
                    help="Re-source nodes that already have a source (useful for re-verification)")
    args = ap.parse_args()

    model_path = Path(args.model_path).resolve()
    if not model_path.exists():
        print(f"❌  File not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("❌  ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    with open(model_path) as f:
        model = json.load(f)

    nodes = model.get("nodes", [])
    to_source = [n for n in nodes if "_comment" not in n and "id" in n and
                 (needs_sourcing(n) or (args.force and n.get("tier") in TIERS_TO_SOURCE))]

    print(f"\n  Stage 6b — source_claims.py")
    print(f"  Model : {model_path.parent.name}/{model_path.name}")
    print(f"  Total nodes  : {len(nodes)}")
    print(f"  Needs sourcing: {len(to_source)}")
    if args.dry_run:
        print(f"  DRY RUN — no API calls will be made")
    print()

    if not to_source:
        print("  ✓  No nodes need sourcing — all claim_type + source fields present")
        sys.exit(0)

    # ── Source each node ──────────────────────────────────────────────────────
    updated_nodes = []
    sourced_count    = 0
    hypothesis_count = 0

    for node in nodes:
        if "_comment" in node or "id" not in node:
            updated_nodes.append(node)
            continue

        nid = node.get("id", "?")
        needs = needs_sourcing(node) or (args.force and node.get("tier") in TIERS_TO_SOURCE)

        if not needs:
            updated_nodes.append(node)
            continue

        updated = source_node(client, node, dry_run=args.dry_run)
        updated_nodes.append(updated)

        ct = updated.get("claim_type", "")
        if ct == "inference" and updated.get("source"):
            sourced_count += 1
        elif ct == "hypothesis":
            hypothesis_count += 1

    # ── Write updated model ───────────────────────────────────────────────────
    if not args.dry_run:
        # Backup original
        backup_path = model_path.with_suffix(".json.bak")
        import shutil
        shutil.copy2(model_path, backup_path)
        print(f"\n  Backup: {backup_path.name}")

        model["nodes"] = updated_nodes
        with open(model_path, "w") as f:
            json.dump(model, f, indent=2, ensure_ascii=False)
        print(f"  Updated: {model_path.name}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n  {'─' * 60}")
    print(f"  Sourcing complete")
    print(f"  Upgraded to inference : {sourced_count}")
    print(f"  Remain hypothesis     : {hypothesis_count}")
    print()

    if hypothesis_count > 0:
        print(f"  ◈  Hypothesis nodes will be flagged in the newsletter")
        print(f"     Run validate_claims.py to see the full list")
    print()


if __name__ == "__main__":
    main()
