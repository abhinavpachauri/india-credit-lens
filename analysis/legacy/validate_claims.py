#!/usr/bin/env python3
"""
validate_claims.py — India Credit Lens  (Check 2c)
----------------------------------------------------
Validates claim_type + source fields on all driver, opportunity, pressure,
and gap nodes in a system_model.json file.

Rules:
  FAIL  — any driver/opportunity/pressure/gap node missing claim_type
  FAIL  — any "inference" node with empty or missing source
  FAIL  — any "inference" node whose source is literally "SIBC data"
  WARN  — any "hypothesis" node (allowed, does not fail — sourcing pipeline
           will attempt to find a source; newsletter flags it visually)
  PASS  — "data" nodes (no source required)
  SKIP  — sector nodes (data by definition, no claim_type needed)

Usage:
    python3 validate_claims.py analysis/rbi_sibc/merged/system_model.json
    python3 validate_claims.py analysis/rbi_sibc/2026-03-30/system_model.json

Exit codes:
    0 = all rules passed (warnings OK)
    1 = one or more FAIL rules triggered
"""

import json
import sys
from pathlib import Path

TIERS_REQUIRING_CLAIM_TYPE = {"driver", "opportunity", "pressure", "gap"}
ANSI_GREEN  = "\033[32m"
ANSI_RED    = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_RESET  = "\033[0m"
ANSI_BOLD   = "\033[1m"


def validate_claims(model_path: str) -> bool:
    path = Path(model_path)
    if not path.exists():
        print(f"{ANSI_RED}❌  File not found: {path}{ANSI_RESET}", file=sys.stderr)
        return False

    with open(path) as f:
        model = json.load(f)

    nodes = [n for n in model.get("nodes", []) if "_comment" not in n and "id" in n]

    failures   = []
    warnings   = []
    ok_count   = 0
    skip_count = 0

    for node in nodes:
        tier = node.get("tier", "")
        nid  = node.get("id", "?")
        label = node.get("label", "?")

        if tier not in TIERS_REQUIRING_CLAIM_TYPE:
            skip_count += 1
            continue

        claim_type = node.get("claim_type")
        source     = node.get("source", "")

        # Missing claim_type — hard fail
        if not claim_type:
            failures.append((nid, label, tier, "missing claim_type"))
            continue

        if claim_type == "data":
            ok_count += 1

        elif claim_type == "inference":
            if not source or str(source).strip() == "":
                failures.append((nid, label, tier,
                    'claim_type="inference" but source is empty'))
            elif source.strip().lower() == "sibc data":
                failures.append((nid, label, tier,
                    'claim_type="inference" but source is "SIBC data" — '
                    'inference requires an external source'))
            else:
                ok_count += 1

        elif claim_type == "hypothesis":
            # Warnings only — hypothesis is allowed, sourcing pipeline will try to resolve
            source_note = f'source="{source}"' if source else "no source yet"
            warnings.append((nid, label, tier,
                f'claim_type="hypothesis" ({source_note}) — will be flagged in newsletter'))

        else:
            failures.append((nid, label, tier,
                f'unknown claim_type="{claim_type}" — must be data|inference|hypothesis'))

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n  Check 2c — claim sourcing: {path.parent.name}/{path.name}")
    print(f"  {'─' * 60}")
    print(f"  Nodes checked : {len(nodes)}")
    print(f"  Skipped       : {skip_count} (sector nodes — data by definition)")
    print(f"  Passed        : {ok_count}")
    print(f"  Warnings      : {len(warnings)} (hypothesis — allowed)")
    print(f"  Failures      : {len(failures)}")
    print()

    if warnings:
        print(f"  {ANSI_YELLOW}◈  HYPOTHESES (not blocking — sourcing pipeline will attempt resolution):{ANSI_RESET}")
        for nid, label, tier, msg in warnings:
            print(f"     [{tier}] {nid}")
            print(f"       label : {label}")
            print(f"       note  : {msg}")
        print()

    if failures:
        print(f"  {ANSI_RED}✗  FAILURES:{ANSI_RESET}")
        for nid, label, tier, msg in failures:
            print(f"     [{tier}] {nid}")
            print(f"       label : {label}")
            print(f"       error : {msg}")
        print()
        print(f"  {ANSI_RED}{ANSI_BOLD}FAILED — {len(failures)} node(s) violate claim sourcing rules{ANSI_RESET}")
        print(f"  Fix: add claim_type + source to each node listed above.")
        print(f"  Run source_claims.py to auto-source hypothesis nodes.\n")
        return False

    if warnings:
        print(f"  {ANSI_GREEN}✅  PASSED{ANSI_RESET} — {ok_count} nodes clean, "
              f"{len(warnings)} hypothesis node(s) flagged for sourcing pipeline")
    else:
        print(f"  {ANSI_GREEN}✅  PASSED{ANSI_RESET} — all {ok_count} nodes have valid claim_type + source")
    print()
    return True


def main():
    if len(sys.argv) < 2:
        # Default: merged system model
        default = Path(__file__).resolve().parent / "rbi_sibc" / "merged" / "system_model.json"
        model_path = str(default)
    else:
        model_path = sys.argv[1]

    ok = validate_claims(model_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
