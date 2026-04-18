#!/usr/bin/env python3
"""
newsletter_delta_brief.py — India Credit Lens
----------------------------------------------
Reads the previous period's per-period analytical outputs (insights, gaps,
opportunities) and the current merged outputs, then writes a structured
delta brief to newsletter_delta_brief.md.

The brief is the editorial input for newsletter_config.json:
  - WHAT HELD    — signals from prev period confirmed in merged
  - WHAT CHANGED — signals where the read materially updated
  - WHAT'S NEW   — signals only visible with the full merged series

Usage:
    python3 newsletter_delta_brief.py
    python3 newsletter_delta_brief.py --prev 2026-02-27

Output:
    analysis/newsletter/newsletter_delta_brief.md
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import date

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ANALYSIS  = REPO_ROOT / "analysis"
NL_DIR    = Path(__file__).resolve().parent


def latest_prev_period(timeline_path: Path) -> str | None:
    """Return the second-to-last period dataDate from timeline.json."""
    with open(timeline_path) as f:
        tl = json.load(f)
    periods = tl.get("periods", [])
    if len(periods) < 2:
        return None
    return periods[-2]["dataDate"]


def read_md(path: Path) -> str:
    """Read a markdown file, return content or empty string."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return f"[NOT FOUND: {path}]"


def section_block(title: str, content: str) -> str:
    bar = "─" * 72
    return f"\n{bar}\n## {title}\n{bar}\n\n{content}\n"


def main():
    ap = argparse.ArgumentParser(
        description="Generate delta brief comparing prev period to merged outputs"
    )
    ap.add_argument(
        "--prev",
        default=None,
        help="Previous period dataDate (YYYY-MM-DD). Defaults to second-to-last in timeline.json",
    )
    args = ap.parse_args()

    timeline_path = ANALYSIS / "rbi_sibc" / "timeline.json"
    if not timeline_path.exists():
        print(f"ERROR: timeline.json not found: {timeline_path}", file=sys.stderr)
        sys.exit(1)

    with open(timeline_path) as f:
        tl = json.load(f)

    periods = tl.get("periods", [])
    if len(periods) < 2:
        print("ERROR: Need at least 2 periods in timeline.json to generate a delta.", file=sys.stderr)
        sys.exit(1)

    prev_date = args.prev or periods[-2]["dataDate"]
    curr_date = periods[-1]["dataDate"]
    prev_period = next((p["period"] for p in periods if p["dataDate"] == prev_date), prev_date)
    curr_period = periods[-1]["period"]

    prev_dir   = ANALYSIS / "rbi_sibc" / prev_date
    merged_dir = ANALYSIS / "rbi_sibc" / "merged"

    for d, label in [(prev_dir, f"prev period ({prev_date})"), (merged_dir, "merged")]:
        if not d.exists():
            print(f"ERROR: directory not found for {label}: {d}", file=sys.stderr)
            sys.exit(1)

    print(f"\n  Delta brief: {prev_period} → {curr_period} (merged)")
    print(f"  Prev dir  : {prev_dir}")
    print(f"  Merged dir: {merged_dir}")

    # ── Read all six source files ──────────────────────────────────────────────

    prev_insights = read_md(prev_dir / "insights.md")
    prev_gaps     = read_md(prev_dir / "gaps.md")
    prev_opps     = read_md(prev_dir / "opportunities.md")

    mrg_insights  = read_md(merged_dir / "insights.md")
    mrg_gaps      = read_md(merged_dir / "gaps.md")
    mrg_opps      = read_md(merged_dir / "opportunities.md")

    # ── Build brief ───────────────────────────────────────────────────────────

    brief_lines = [
        f"# Newsletter Delta Brief — Issue #2",
        f"**Previous period:** {prev_period} ({prev_date})",
        f"**Current period:**  {curr_period} (merged, all periods)",
        f"**Generated:**       {date.today()}",
        "",
        "> This brief compares what was said in Issue #1 (based on the",
        "> Jan 2026 per-period analysis) against what the merged view now shows.",
        "> Use it to fill newsletter_config.json editorial fields.",
        "",
        "---",
        "",
        "## HOW TO USE THIS",
        "",
        "1. Read PREV and MERGED side by side for each section below",
        "2. Classify each signal as HELD / CHANGED / NEW",
        "3. Write those classifications into newsletter_config.json:",
        "   - `what_held`  → signals confirmed with no material change",
        "   - `what_changed` → signals where the read materially updated",
        "   - `what_new`  → signals only visible with the full merged series",
        "",
        "---",
    ]

    # ── PREV PERIOD: insights, gaps, opportunities ─────────────────────────────

    brief_lines.append(
        section_block(
            f"PREV PERIOD INSIGHTS — {prev_period} ({prev_date})",
            prev_insights,
        )
    )
    brief_lines.append(
        section_block(
            f"PREV PERIOD GAPS — {prev_period} ({prev_date})",
            prev_gaps,
        )
    )
    brief_lines.append(
        section_block(
            f"PREV PERIOD OPPORTUNITIES — {prev_period} ({prev_date})",
            prev_opps,
        )
    )

    # ── MERGED: insights, gaps, opportunities ─────────────────────────────────

    brief_lines.append(
        section_block(
            "MERGED INSIGHTS — full series (all ingested periods)",
            mrg_insights,
        )
    )
    brief_lines.append(
        section_block(
            "MERGED GAPS — full series",
            mrg_gaps,
        )
    )
    brief_lines.append(
        section_block(
            "MERGED OPPORTUNITIES — full series",
            mrg_opps,
        )
    )

    # ── Guidance footer ───────────────────────────────────────────────────────

    brief_lines.append(
        "\n---\n\n"
        "## CLASSIFICATION GUIDE\n\n"
        "**HELD** — appears in both prev and merged with same directional read.\n"
        "  Signal confirmed. Note if the stat got stronger or weaker.\n\n"
        "**CHANGED** — appears in both, but the merged view materially updates the read.\n"
        "  New data point changes the interpretation (e.g. uncertain → confirmed,\n"
        "  accelerating → decelerating, or a gap is now explained).\n\n"
        "**NEW** — appears only in merged, not in prev per-period outputs.\n"
        "  Only visible because the full multi-period series is now available.\n"
        "  These are the most analytically valuable for the delta newsletter.\n\n"
        "**DROPPED** — appeared in prev, absent from merged.\n"
        "  Either resolved, reclassified, or superseded by a clearer signal.\n\n"
        "---\n\n"
        "*Fill newsletter_config.json editorial fields once classification is complete.*\n"
    )

    brief = "\n".join(brief_lines)
    out_path = NL_DIR / "newsletter_delta_brief.md"
    out_path.write_text(brief, encoding="utf-8")

    print(f"\n  ✅ Delta brief written: {out_path}")
    print(f"     Sections: prev (insights + gaps + opps) | merged (insights + gaps + opps)")
    print(f"     Next: review the brief and fill newsletter_config.json editorial fields\n")


if __name__ == "__main__":
    main()
