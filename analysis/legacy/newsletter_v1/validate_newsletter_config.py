#!/usr/bin/env python3
"""
validate_newsletter_config.py — Content accuracy gate for newsletter_config.json

This is the newsletter equivalent of validate_content.py (Check 2b for annotations).
It validates that every ₹X.XXL Cr value and X% FY/YoY growth rate cited in
newsletter_config.json editorial fields exactly matches sections_merged.json data.

Why this exists: newsletter_config.json is authored manually from analysis recall.
There is no pipeline gate between authoring the config and running the generators.
This script is that gate — run it before generate_newsletter.py and generate_linkedin.py.

Checks:
  A) Dates cited near a data claim must exist in sections_merged.json — WARNING
  B) Growth rates (X% FY / X% YoY) must match growthData or fyData ± GROWTH_TOLERANCE — ERROR
  C) Values (₹X.XXL Cr) must match absoluteData ± VALUE_TOLERANCE — ERROR

Fields validated:
  editorial.hero_narrative
  editorial.tldr[]
  editorial.system_narrative
  editorial.signals[].stat         ← primary stat line per signal
  editorial.signals[].body         ← 2-3 sentence context
  editorial.signals[].implication  ← one-sentence lender action
  editorial.signals[].note         ← confirmed-type extended copy
  editorial.signals[].curr_stat    ← confirmed-type: current period stat
  editorial.signals[].prev_stat    ← confirmed-type: prior period stat (warnings only)
  editorial.what_to_watch.bullets[]

Tolerances (tighter than validate_content.py — newsletter is published copy):
  GROWTH_TOLERANCE = 0.5  percentage points  (validate_content.py uses 1.0)
  VALUE_TOLERANCE  = 0.02  (±2%)             (validate_content.py uses 5%)

Usage:
  python3 analysis/newsletter/validate_newsletter_config.py
  python3 analysis/newsletter/validate_newsletter_config.py path/to/newsletter_config.json

Exit codes:
  0 — clean (errors = 0)
  1 — one or more errors found
"""

import re
import sys
import json
import argparse
from pathlib import Path

# ── Tolerances (tighter than validate_content.py — newsletter is publishable copy) ─
GROWTH_TOLERANCE = 0.5   # ± percentage points
VALUE_TOLERANCE  = 0.02  # ± 2% of cited value

# ── Paths ──────────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
REPO         = SCRIPT_DIR.parent.parent
SECTIONS_MERGED = REPO / "analysis" / "rbi_sibc" / "merged" / "sections_merged.json"
DEFAULT_CONFIG  = SCRIPT_DIR / "newsletter_config.json"

# ── Regex patterns (same as validate_content.py) ──────────────────────────────────
VALUE_RE  = re.compile(r'₹([\d,]+\.?\d*)L\s*Cr')
GROWTH_RE = re.compile(r'([+\-]?[\d,]+\.?\d*)%\s*(FY|YoY)\b', re.IGNORECASE)
DATE_RE   = re.compile(
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(20\d{2})\b'
)


def _clean_float(s: str) -> float:
    return float(s.replace(',', ''))


# ── Build lookup from sections_merged.json ────────────────────────────────────────

def build_lookup(sections_path: Path) -> tuple[set, set, set]:
    """
    Returns (all_dates, all_values_lcr, all_growths) from sections_merged.json.
    Covers all sections so cross-section references validate correctly.
    """
    with open(sections_path) as f:
        data = json.load(f)

    sections = data.get('sections', [])
    all_dates:   set = set()
    all_values:  set = set()
    all_derived: set = set()
    all_growths: set = set()

    for sec in sections:
        abs_data = sec.get('absoluteData', [])
        grw_data = sec.get('growthData', [])
        fy_data  = sec.get('fyData', [])

        series_vals: dict = {}
        for row in abs_data:
            all_dates.add(row['date'])
            for k, v in row.items():
                if k == 'date' or v is None:
                    continue
                lcr = round(v / 100_000, 4)
                all_values.add(lcr)
                series_vals.setdefault(k, []).append(lcr)

        # Derived: pairwise differences and sums (for incrementals like "FY26 add")
        for _, vals_list in series_vals.items():
            for i in range(len(vals_list)):
                for j in range(len(vals_list)):
                    if i != j:
                        all_derived.add(round(abs(vals_list[i] - vals_list[j]), 4))
                        all_derived.add(round(vals_list[i] + vals_list[j], 4))

        for row in grw_data + fy_data:
            for k, v in row.items():
                if k == 'date' or v is None:
                    continue
                all_growths.add(round(float(v), 2))

    return all_dates, all_values | all_derived, all_growths


def _nearest(v: float, s: set, n: int = 3) -> list:
    if not s:
        return []
    return sorted(s, key=lambda x: abs(x - v))[:n]


def value_near(cited: float, valid: set) -> bool:
    tol = VALUE_TOLERANCE * max(abs(cited), 0.001)
    return any(abs(cited - v) <= tol for v in valid)


def growth_near(cited: float, valid: set) -> bool:
    return any(abs(cited - v) <= GROWTH_TOLERANCE for v in valid)


# ── Validation of a single text chunk ─────────────────────────────────────────────

class Result:
    def __init__(self):
        self.errors:   list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)


def validate_text(
    text: str,
    label: str,
    all_dates: set,
    all_values: set,
    all_growths: set,
    result: Result,
    prev_stat: bool = False,
):
    """
    Validate a single text string. `prev_stat=True` relaxes errors to warnings
    since prev_stat fields reference prior-period data which may not be the
    current merged view's primary period.
    """
    severity = result.warn if prev_stat else result.error

    # A: Date check — always WARNING (event dates mixed with data dates)
    for m in DATE_RE.finditer(text):
        date_str = m.group(0).strip()
        if date_str not in all_dates:
            result.warn(
                f"{label}: date '{date_str}' not found in sections_merged.json. "
                f"Valid dates: {sorted(all_dates)}"
            )

    # B: Growth rate check — ERROR (warnings for prev_stat)
    for m in GROWTH_RE.finditer(text):
        raw   = m.group(1).lstrip('+')
        cited = _clean_float(raw)
        tag   = m.group(2).upper()
        if not growth_near(cited, all_growths):
            severity(
                f"{label}: growth rate '{m.group(0)}' ({cited}% {tag}) not within "
                f"±{GROWTH_TOLERANCE}pp of any value in sections_merged.json. "
                f"Closest: {_nearest(cited, all_growths)}"
            )

    # C: Value check — ERROR (warnings for prev_stat)
    for m in VALUE_RE.finditer(text):
        cited = _clean_float(m.group(1))
        if cited < 0.1:
            continue  # too small to match reliably at 1dp
        if not value_near(cited, all_values):
            severity(
                f"{label}: value '₹{m.group(1)}L Cr' ({cited}) not within "
                f"±{VALUE_TOLERANCE*100:.0f}% of any value in sections_merged.json. "
                f"Closest: {_nearest(cited, all_values)}"
            )


# ── Extract all text fields from newsletter_config.json ───────────────────────────

def collect_fields(cfg: dict) -> list[tuple[str, str, bool]]:
    """
    Returns list of (label, text, is_prev_stat) tuples.
    is_prev_stat=True relaxes errors to warnings (prior-period references).
    """
    fields: list[tuple[str, str, bool]] = []
    ed = cfg.get('editorial', {})

    def add(label, text, prev=False):
        if text and isinstance(text, str) and text.strip():
            fields.append((label, text, prev))

    # Top-level editorial narrative
    add("hero_narrative",    ed.get('hero_narrative', ''))
    add("system_narrative",  ed.get('system_narrative', ''))
    for i, bullet in enumerate(ed.get('tldr', [])):
        add(f"tldr[{i}]", bullet)

    # Per-signal fields
    for i, sig in enumerate(ed.get('signals', [])):
        sig_type = sig.get('type', 'unknown')
        arc      = sig.get('story_arc', f'signal_{i}')
        prefix   = f"signals[{i}] ({sig_type}: {arc})"

        add(f"{prefix}.stat",         sig.get('stat', ''))
        add(f"{prefix}.body",         sig.get('body', ''))
        add(f"{prefix}.implication",  sig.get('implication', ''))
        add(f"{prefix}.note",         sig.get('note', ''))
        add(f"{prefix}.curr_stat",    sig.get('curr_stat', ''))
        # prev_stat references prior period — relax to warnings
        add(f"{prefix}.prev_stat",    sig.get('prev_stat', ''), prev=True)

    # What to watch
    wtw = ed.get('what_to_watch', {})
    for i, bullet in enumerate(wtw.get('bullets', [])):
        add(f"what_to_watch.bullets[{i}]", bullet)

    return fields


# ── Image URL validation ──────────────────────────────────────────────────────────

def validate_images(cfg: dict, config_path: Path, result: Result) -> int:
    """
    Check D: image_url fields — ERROR if missing or pointing to a non-existent file.

    Rules:
      D1. Every signal must have a non-empty image_url (anchor post has no image by design,
          but the 6 signals each need one for LinkedIn posts).
      D2. The referenced file must exist on disk (resolved relative to config_path's directory).
      D3. WARNING if the image file is older than sections_merged.json (possible stale render).

    Returns count of signals checked.
    """
    newsletter_dir = config_path.parent
    signals = cfg.get('editorial', {}).get('signals', [])
    n = 0

    for i, sig in enumerate(signals):
        sig_type = sig.get('type', 'unknown')
        arc      = sig.get('story_arc', f'signal_{i}')
        prefix   = f"signals[{i}] ({sig_type}: {arc})"
        url      = sig.get('image_url', '').strip()
        n += 1

        # D1: image_url must be set
        if not url:
            result.error(
                f"{prefix}: image_url is empty — run generate_images.py then assign "
                f"the path before running generate_linkedin.py"
            )
            continue

        # D2: file must exist
        img_path = newsletter_dir / url
        if not img_path.exists():
            result.error(
                f"{prefix}: image_url '{url}' → file not found at {img_path}. "
                f"Run generate_images.py or check the path."
            )
            continue

        # D3: freshness — warn if image is older than sections_merged.json
        if SECTIONS_MERGED.exists():
            img_mtime      = img_path.stat().st_mtime
            sections_mtime = SECTIONS_MERGED.stat().st_mtime
            if img_mtime < sections_mtime:
                result.warn(
                    f"{prefix}: image '{img_path.name}' is older than sections_merged.json. "
                    f"Re-run generate_images.py to refresh from the latest Mermaid output."
                )

    return n


# ── Main ──────────────────────────────────────────────────────────────────────────

def run(config_path: Path, sections_path: Path) -> bool:
    print(f"\n  India Credit Lens — Newsletter Config Validator")
    print(f"  Config  : {config_path.name}")
    print(f"  Sections: {sections_path.name}")
    print()

    if not config_path.exists():
        print(f"  ❌  Config not found: {config_path}")
        return False
    if not sections_path.exists():
        print(f"  ❌  sections_merged.json not found: {sections_path}")
        return False

    with open(config_path) as f:
        cfg = json.load(f)

    meta = cfg.get('_meta', {})
    print(f"  Period  : {meta.get('period', '?')} | Issue #{meta.get('issue_number', '?')}")
    print()

    all_dates, all_values, all_growths = build_lookup(sections_path)
    fields = collect_fields(cfg)

    result = Result()
    for label, text, is_prev in fields:
        validate_text(text, label, all_dates, all_values, all_growths, result, prev_stat=is_prev)

    # Check D: image_url presence and file existence
    n_images = validate_images(cfg, config_path, result)

    # ── Report ────────────────────────────────────────────────────────────────────
    print(f"  Fields checked : {len(fields)}")
    print(f"  Images checked : {n_images} signal(s)")
    print()

    if result.errors:
        print(f"  ❌  ERRORS ({len(result.errors)}) — fix before running generators")
        for e in result.errors:
            print(f"     {e}")
        print()
    if result.warnings:
        print(f"  ⚠️   WARNINGS ({len(result.warnings)}) — review but non-blocking")
        for w in result.warnings:
            print(f"     {w}")
        print()

    if not result.errors and not result.warnings:
        print("  ✅  All checks passed — 0 errors, 0 warnings")
    elif not result.errors:
        print(f"  ✅  Passed — 0 errors, {len(result.warnings)} warning(s)")
    else:
        print(f"  ❌  FAILED — {len(result.errors)} error(s) must be fixed before publishing")

    return len(result.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate newsletter_config.json numbers against sections_merged.json"
    )
    parser.add_argument(
        'config', nargs='?', default=str(DEFAULT_CONFIG),
        help=f"Path to newsletter_config.json (default: {DEFAULT_CONFIG})"
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    ok = run(config_path, SECTIONS_MERGED)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
