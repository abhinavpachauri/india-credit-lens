#!/usr/bin/env python3
"""
Stage 5.5 (ATM/POS) — Refresh L1 insight content from LLM evaluation output.

Reads:  analysis/signals/evaluations/atm_pos/{period}.json
        web/public/data/atm_pos_insights.json
Writes: web/public/data/atm_pos_insights.json  (in-place, L1 entries only)

For L1 insights: replaces title/body/implication from computed signal evaluations.
All other fields (effect, group, cut, type, exploreAction, sourceSignals, layer)
are preserved exactly — they are manually curated chart-wiring metadata.

L2 insights are untouched.
"""

import json
import re
import sys
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO
ANAL      = REPO / "analysis"
EVALS     = ANAL / "signals" / "evaluations"
INSIGHTS  = REPO / "web" / "public" / "data" / "atm_pos_insights.json"

# ── Insight → evaluation signal mapping ──────────────────────────────────────
# Maps each ATM/POS L1 insight id → registry signal id(s) in the evaluation JSON.
# Order matters: first signal's title is used as the insight title.

INSIGHT_SIGNAL_MAP: dict[str, list[str]] = {
    "cc-ecom-vs-pos-share":      ["cc-ecom-val-share", "cc-pos-val-share"],
    "cc-cards-streak":            ["cc-outstanding-abs"],
    "cc-txn-surge":               ["cc-pos-val-abs", "cc-ecom-val-abs", "cc-atm-val-abs"],
    "cc-category-share-shift":    ["cc-pos-val-share", "cc-ecom-val-share", "cc-atm-val-share"],
    "cc-top5-concentration":      ["cc-bank-scan"],
    "dc-atm-share-structural":    ["dc-atm-val-share"],
    "dc-pos-cash-decline":        ["dc-atm-val-share", "dc-pos-val-share"],
    "dc-ecom-share":              ["dc-ecom-val-share"],
    "dc-cards-streak":            ["dc-outstanding-abs"],
    "dc-psb-dominance":           ["dc-psb-share", "dc-private-share"],
    "dc-top-bank-leader":         ["dc-bank-scan"],
    "infra-qr-per-pos":           ["upi-qr-per-pos"],
    "infra-pos-streak":           ["pos-terminals-pos-streak"],
    "infra-upi-vs-bharat-qr":     ["bharat-qr-abs", "upi-qr-abs"],
    "infra-top-bank-pos":         ["pos-bank-scan"],
    "gap-bharat-qr-contraction":  ["bharat-qr-abs"],
    "gap-pos-concentration":      ["pos-bank-scan"],
    # gap-atm-offsite-decline: no signals yet (needs prior-year CSV) — stays authored
}


def derive_title(eval_entry: dict) -> str:
    """Use LLM title if present (prompt v1.5+), else derive from first sentence of obs."""
    if eval_entry.get("title"):
        return eval_entry["title"].strip()
    obs = eval_entry.get("observation", "").strip()
    sentences = re.split(r"\.\s+", obs)
    first = sentences[0].rstrip(".")
    if len(first) <= 90:
        return first
    return first[:90].rsplit(" ", 1)[0] + "…"


def compose_body(signal_entries: list[dict]) -> str:
    parts = []
    for se in signal_entries:
        obs  = se.get("observation", "").strip()
        dir_ = se.get("direction",   "").strip()
        if obs or dir_:
            parts.append(" ".join(filter(None, [obs, dir_])))
    return " ".join(parts)


def compose_implication(signal_entries: list[dict]) -> str:
    parts = [se.get("inference", "").strip() for se in signal_entries if se.get("inference")]
    return " ".join(parts)


def main(period: str | None = None) -> int:
    # Find latest ATM/POS evaluation
    eval_dir = EVALS / "atm_pos"
    if period:
        eval_path = eval_dir / f"{period}.json"
    else:
        files = sorted(eval_dir.glob("*.json"))
        if not files:
            print("ERROR: no ATM/POS evaluation files found")
            return 1
        eval_path = files[-1]
        period = eval_path.stem

    print(f"Reading evaluation: {eval_path}")
    with open(eval_path) as f:
        ev = json.load(f)

    # Flatten all evaluated signals
    eval_signals: dict[str, dict] = {}
    for domain, dd in ev["domains"].items():
        for sid, se in dd.get("signals", {}).items():
            eval_signals[sid] = se

    # Load existing insights
    with open(INSIGHTS) as f:
        insights: list[dict] = json.load(f)

    updated = 0
    skipped = 0

    for insight in insights:
        if insight.get("layer") != 1:
            continue  # L2 stays authored

        iid = insight["id"]
        signal_ids = INSIGHT_SIGNAL_MAP.get(iid)

        if not signal_ids:
            print(f"  SKIP {iid} — no signal mapping (stays authored)")
            skipped += 1
            continue

        # Collect evaluation entries for mapped signals
        entries = [eval_signals[s] for s in signal_ids if s in eval_signals]
        if not entries:
            print(f"  SKIP {iid} — no eval output for signals {signal_ids}")
            skipped += 1
            continue

        # Update content fields only — preserve all metadata
        insight["title"]      = derive_title(entries[0])
        insight["body"]       = compose_body(entries)
        insight["implication"] = compose_implication(entries)
        insight["period"]     = period

        # Update reasoning chain from inference if available
        chain = [e.get("inference", "") for e in entries if e.get("inference")]
        if chain:
            existing = insight.get("reasoning") or {}
            insight["reasoning"] = {**existing, "chain": chain}

        updated += 1

    # Write back
    with open(INSIGHTS, "w") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nUpdated {updated} L1 insights, skipped {skipped}")
    print(f"Written: {INSIGHTS}")
    return 0


if __name__ == "__main__":
    period_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(period_arg))
