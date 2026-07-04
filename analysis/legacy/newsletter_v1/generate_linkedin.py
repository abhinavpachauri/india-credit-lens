#!/usr/bin/env python3
"""
generate_linkedin.py — LinkedIn post package generator for India Credit Lens.

Reads newsletter_config.json and produces 7 post packages:
  - post_00_anchor   : hero_narrative (release week, no image)
  - post_01..06      : one per signal[], ordered new → correction → confirmed

Each package = post copy (.txt) + paired image (.png, copied from image_url).
Also produces schedule.md — suggested week-by-week posting order.

Usage:
  python3 analysis/newsletter/generate_linkedin.py

Output: analysis/newsletter/output/linkedin/YYYY-MM-DD/
"""

import json
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

NEWSLETTER_DIR = Path(__file__).resolve().parent
CONFIG_PATH    = NEWSLETTER_DIR / "newsletter_config.json"
OUTPUT_BASE    = NEWSLETTER_DIR / "output" / "linkedin"

# Posting cadence: release date + week offsets
SCHEDULE = [
    (0,  "Week 1 — release week"),
    (7,  "Week 2"),
    (14, "Week 3"),
    (21, "Week 4"),
    (28, "Week 5"),
    (35, "Week 6"),
    (42, "Week 7"),
]

TYPE_ORDER = {"new": 0, "correction": 1, "confirmed": 2}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"  ❌  newsletter_config.json not found at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def format_anchor_post(editorial: dict, cta: dict) -> str:
    hero = editorial.get("hero_narrative", "").strip()
    issue_title = ""
    substack_url = cta.get("substack", "indiacreditlens.substack.com")

    # Pull issue title from _meta if available
    tldr = editorial.get("tldr", [])
    context = tldr[0].strip() if tldr else ""

    lines = [
        hero,
        "",
        context if context else "",
        "",
        f"Full breakdown → https://{substack_url}",
    ]
    return "\n".join(l for l in lines if l is not None)


def format_new_post(signal: dict, issue_title: str, substack_url: str) -> str:
    hook    = signal.get("signal", "").strip()
    stat    = signal.get("stat", "").strip()
    body    = signal.get("body", "").strip()
    impl    = signal.get("implication", "").strip()

    # Body: first 2 sentences only for LinkedIn short-form
    sentences = re.split(r'(?<=[.!?])\s+', body)
    context = " ".join(sentences[:2])

    lines = [
        hook,
        "",
        stat,
        "",
        context,
        "",
        impl,
        "",
        f"Full breakdown in '{issue_title}' → https://{substack_url}",
    ]
    return "\n".join(lines)


def format_correction_post(signal: dict, issue_title: str, substack_url: str) -> str:
    hook      = signal.get("signal", "").strip()
    prev_read = signal.get("prev_read", "").strip()
    curr_read = signal.get("curr_read", "").strip()
    impl      = signal.get("implication", "").strip()
    # Correction signals use curr_stat, not stat
    curr_stat = signal.get("curr_stat", signal.get("stat", "")).strip()

    parts = [hook]
    if curr_stat:
        parts += ["", curr_stat]
    parts += [
        "",
        f"Issue #1 read: {prev_read}",
        "",
        f"Updated: {curr_read}",
        "",
        impl,
        "",
        f"Full breakdown in '{issue_title}' → https://{substack_url}",
    ]
    return "\n".join(parts)


def format_confirmed_post(signal: dict, issue_title: str, substack_url: str) -> str:
    hook      = signal.get("signal", "").strip()
    curr_stat = signal.get("curr_stat", signal.get("stat", "")).strip()
    badge     = signal.get("badge", "").strip()
    note      = signal.get("note", "").strip()
    impl      = signal.get("implication", "").strip()
    caveat    = signal.get("caveat", "").strip()

    # Strip HTML tags (note uses <em>)
    note_clean = re.sub(r'<[^>]+>', '', note)
    sentences  = re.split(r'(?<=[.!?])\s+', note_clean)
    context    = " ".join(sentences[:2])

    parts = [hook]
    if curr_stat:
        parts += ["", curr_stat]
    if badge:
        parts += [f"  {badge}"]
    parts += ["", context]
    if impl:
        parts += ["", impl]
    # Caveat: appended before CTA when the signal contains a hypothesis element
    if caveat:
        parts += ["", f"⚠ {caveat}"]
    parts += ["", f"Full breakdown in '{issue_title}' → https://{substack_url}"]
    return "\n".join(parts)


def copy_image(image_url: str, dest: Path) -> bool:
    """Resolve image_url relative to NEWSLETTER_DIR and copy to dest."""
    if not image_url:
        return False
    src = NEWSLETTER_DIR / image_url
    if not src.exists():
        print(f"  ⚠️   Image not found: {src} — skipping")
        return False
    shutil.copy2(src, dest)
    return True


def build_schedule(signals: list, release_date: date, issue_title: str) -> str:
    """Generate a suggested posting schedule in markdown."""
    ordered = sorted(signals, key=lambda s: TYPE_ORDER.get(s["type"], 99))
    # Anchor + 6 signals = 7 posts, 7 weeks
    entries = [{"label": "Anchor post", "type": "anchor", "signal": ""}]
    for s in ordered:
        entries.append({
            "label": s.get("story_arc", s.get("signal", "")[:50]),
            "type": s["type"],
            "signal": s.get("signal", "")[:80],
        })

    lines = [
        f"# LinkedIn Posting Schedule — {issue_title}",
        f"Release date: {release_date}",
        f"Cadence: 1 post/week (adjust to 2/week from week 2 if engagement warrants)",
        "",
        "| Week | Date | Type | Post |",
        "|---|---|---|---|",
    ]
    for i, (entry, (offset, week_label)) in enumerate(zip(entries, SCHEDULE)):
        post_date = release_date + timedelta(days=offset)
        post_label = entry["signal"] or entry["label"]
        lines.append(
            f"| {week_label} | {post_date} | {entry['type']} | {post_label} |"
        )

    lines += [
        "",
        "## Notes",
        "- **Anchor post** (week 1): no image — standalone context-setting post",
        "- **New signals** (weeks 1–2): highest relevance to the just-published issue",
        "- **Correction** (week 2–3): contrarian framing drives engagement; pair with the newsletter link",
        "- **Confirmed signals** (weeks 3–7): credibility arc — 'we called this last issue'",
        "- Set `_meta.current_issue_url` in newsletter_config.json before generating — links to the specific issue, not the main page",
    ]
    return "\n".join(lines)


def main():
    config   = load_config()
    meta     = config.get("_meta", {})
    editorial = config.get("editorial", {})
    cta      = config.get("branding", {})
    signals  = editorial.get("signals", [])

    issue_title  = editorial.get("issue_title", "Latest Issue")
    published    = meta.get("published", date.today().isoformat())

    # Prefer the specific issue URL; fall back to main Substack page
    current_issue_url = meta.get("current_issue_url", "").strip()
    substack_base     = cta.get("substack", "indiacreditlens.substack.com")
    substack_url      = current_issue_url if current_issue_url else substack_base

    if not current_issue_url:
        print("  ⚠️   current_issue_url not set in _meta — CTA will link to main Substack page.")
        print("       Add it once Issue #2 is published: _meta.current_issue_url")

    try:
        release_date = date.fromisoformat(published)
    except ValueError:
        release_date = date.today()

    today     = date.today().isoformat()
    out_dir   = OUTPUT_BASE / today
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating LinkedIn posts for '{issue_title}'")
    print(f"Output: {out_dir.relative_to(NEWSLETTER_DIR.parent.parent)}\n")

    # ── Post 00: Anchor ───────────────────────────────────────────────────────
    anchor_text = format_anchor_post(editorial, cta)
    (out_dir / "post_00_anchor.txt").write_text(anchor_text, encoding="utf-8")
    print("  ✓ post_00_anchor   (no image — release week)")

    # ── Posts 01–06: Signals, ordered new → correction → confirmed ────────────
    ordered_signals = sorted(signals, key=lambda s: TYPE_ORDER.get(s["type"], 99))

    for i, signal in enumerate(ordered_signals, start=1):
        sig_type  = signal.get("type", "new")
        story_arc = signal.get("story_arc", f"signal_{i}")
        slug      = re.sub(r'[^a-z0-9]+', '_', story_arc.lower()).strip('_')[:30]
        base_name = f"post_{i:02d}_{sig_type}"

        # Format post copy
        if sig_type == "new":
            text = format_new_post(signal, issue_title, substack_url)
        elif sig_type == "correction":
            text = format_correction_post(signal, issue_title, substack_url)
        else:
            text = format_confirmed_post(signal, issue_title, substack_url)

        (out_dir / f"{base_name}.txt").write_text(text, encoding="utf-8")

        # Copy paired image
        image_url  = signal.get("image_url", "")
        image_dest = out_dir / f"{base_name}.png"
        has_image  = copy_image(image_url, image_dest)
        image_note = f"+ {Path(image_url).name}" if has_image else "(no image)"

        print(f"  ✓ {base_name}  {image_note}")

    # ── schedule.md ───────────────────────────────────────────────────────────
    schedule_text = build_schedule(signals, release_date, issue_title)
    (out_dir / "schedule.md").write_text(schedule_text, encoding="utf-8")
    print(f"  ✓ schedule.md")

    print(f"\n✅  {len(ordered_signals) + 1} post packages ready")
    print(f"   {out_dir.relative_to(NEWSLETTER_DIR.parent.parent)}/")
    print(f"\nNext: review post copy, replace Substack URL, schedule per schedule.md")


if __name__ == "__main__":
    main()
