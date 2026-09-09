#!/usr/bin/env python3
"""
audit_force_sources.py — does a force's excerpt actually appear on the page it cites?
────────────────────────────────────────────────────────────────────────────────────
`excerpt_on_page` is the trust anchor of this whole sourcing programme: an LLM can
propose a plausible URL and a plausible quote, and only a real page containing the
literal quote passes. It was built 2026-07-29 and wired into every path that has
sourced anything SINCE.

Nothing ever pointed it at the forces authored BEFORE it. Measured 2026-09-09 over
all 18 force instances in both models, 11 excerpts did not appear on their cited
page — and every one of those forces carried `claim_type: inference`, meaning the
model treated it as sourced. The seven that passed were, without exception, the
ones sourced after the anchor existed.

That is the check-population failure again: the guard existed, worked, and was
never aimed at the existing store. `validate_system_model` checks that sourcing is
PRESENT; it cannot check that sourcing is TRUE, because that needs the network.

Not a gate stage, deliberately
──────────────────────────────
This needs live fetches, so it cannot run inside an offline gate and must never
become a build dependency on someone else's uptime. Run it after an authoring pass,
the way `measure_groundedness.py` is run.

A FETCH FAILURE IS NOT A BAD EXCERPT
────────────────────────────────────
Reported as separate outcomes, always. On 2026-09-09 a probe bug made every host
look blocked, and that false reading was written into a spec and a commit message
before a control caught it. An unreachable page tells you nothing about the quote;
saying otherwise is how a verification tool starts manufacturing verdicts.

Usage:  python3 analysis/guards/audit_force_sources.py [--strict] [--pipeline sibc]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core.source_fetch import fetch_text                      # noqa: E402
from distribution.bank_sourcing import excerpt_on_page, tier_of  # noqa: E402

MODELS = {
    "sibc":    "analysis/rbi_sibc/merged/system_model.json",
    "atm_pos": "analysis/rbi_atm_pos/merged/system_model.json",
}

VERIFIES, NOT_ON_PAGE, UNREACHABLE, NO_SOURCE = (
    "verifies", "NOT ON PAGE", "unreachable", "no source")


def audit_force(f: dict) -> tuple[str, str]:
    """(outcome, detail) for one force instance. Never conflates the outcomes."""
    url, excerpt = f.get("source_url"), f.get("source_excerpt")
    if not url or not excerpt:
        return NO_SOURCE, "no source_url or source_excerpt"
    text, verdict = fetch_text(url)
    if verdict != "ok" or not text:
        # Says nothing about the excerpt. Reported apart from a real failure.
        return UNREACHABLE, f"fetch {verdict}"
    if excerpt_on_page(excerpt, text):
        return VERIFIES, f"tier={tier_of(url)}"
    return NOT_ON_PAGE, f"page {len(text)} chars, tier={tier_of(url)}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pipeline", choices=sorted(MODELS))
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any excerpt is NOT ON PAGE (unreachable never fails)")
    args = ap.parse_args()

    pipelines = [args.pipeline] if args.pipeline else sorted(MODELS)
    counts: dict[str, int] = {}
    failures = []

    for pipe in pipelines:
        model = json.loads((ROOT / MODELS[pipe]).read_text())
        print(f"\n{pipe}")
        for f in model.get("force_instances", []):
            outcome, detail = audit_force(f)
            counts[outcome] = counts.get(outcome, 0) + 1
            mark = "✓" if outcome == VERIFIES else ("·" if outcome == UNREACHABLE else "✗")
            print(f"  {mark} {outcome:12} {f['id']:40} {f.get('claim_type','?'):10} {detail}")
            if outcome == NOT_ON_PAGE:
                failures.append((pipe, f["id"], f.get("claim_type")))

    total = sum(counts.values())
    print(f"\n{total} force instance(s): " +
          ", ".join(f"{n} {k}" for k, n in sorted(counts.items())))
    if failures:
        print("\nExcerpts that do not appear on their cited page:")
        for pipe, fid, claim in failures:
            flag = "  ← claims to be sourced" if claim == "inference" else ""
            print(f"  {pipe:8} {fid:40} claim_type={claim}{flag}")
    if counts.get(UNREACHABLE):
        print(f"\n{counts[UNREACHABLE]} page(s) unreachable — that is a verdict about the "
              f"NETWORK, not about the excerpt. Re-run before drawing any conclusion.")

    return 1 if (args.strict and failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
