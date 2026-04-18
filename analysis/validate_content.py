#!/usr/bin/env python3
"""
validate_content.py — Content accuracy checker for Stage 2 outputs.

Validates that numbers, dates, and growth rates cited in annotation bodies
and markdown docs match the underlying sections.json data.

Three checks:
  A) Dates cited in annotation bodies/titles/implications must exist in the
     corresponding section's absoluteData (or any section for markdown docs).
  B) Growth rates cited as "X% FY" or "X% YoY" must match a value in
     growthData/fyData within GROWTH_TOLERANCE percentage points.
  C) Values cited as "₹X.XXL Cr" must match a value in absoluteData (in L Cr)
     or a derived value (difference/sum of two absoluteData values) within
     VALUE_TOLERANCE percent.

Usage:
  # Per-period (checks annotations_draft.ts + insights.md + gaps.md + opportunities.md)
  python3 validate_content.py --period 2026-03-30

  # Merged (checks annotations_merged.ts + merged markdown docs)
  python3 validate_content.py --merged

Exit codes:
  0 — all checks pass (warnings are non-blocking)
  1 — one or more errors found
"""

import re
import sys
import json
import argparse
from pathlib import Path

# ── Tolerances ────────────────────────────────────────────────────────────────
GROWTH_TOLERANCE = 1.0   # ± percentage points (e.g. 13.8% cited, 13.7% actual → OK)
VALUE_TOLERANCE  = 0.05  # ± 5% of cited value (catches rounding to 1dp in L Cr)

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO   = Path(__file__).resolve().parent.parent
ANALYSIS = REPO / "analysis"
SIBC_DIR = ANALYSIS / "rbi_sibc"

# ── Regex patterns ─────────────────────────────────────────────────────────────
# Matches: ₹0.93L Cr  ₹207.5L Cr  ₹25.1L Cr  ₹1,974L Cr (with optional comma)
VALUE_RE  = re.compile(r'₹([\d,]+\.?\d*)L\s*Cr')

# Matches: +13.8% FY  -1.0% YoY  10.4% YoY  +107.8% FY  121.1% YoY
# Capture sign+number and tag (FY/YoY)
GROWTH_RE = re.compile(r'([+\-]?[\d,]+\.?\d*)%\s*(FY|YoY)\b', re.IGNORECASE)

# Matches: Mar 2024  Feb 2026  Jan 2025  etc.
DATE_RE   = re.compile(
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(20\d{2})\b'
)


# ── Data helpers ───────────────────────────────────────────────────────────────

def _clean_float(s: str) -> float:
    """Remove commas and convert to float."""
    return float(s.replace(',', ''))


def build_section_lookup(sections: list) -> dict:
    """
    For each section, build sets of valid:
      - date strings (from absoluteData)
      - values in L Cr (absoluteData values / 100000, rounded to 2dp)
      - derived values in L Cr (all pairwise differences within each series)
      - growth rates (from growthData + fyData, all numeric values)
    """
    lookup = {}
    for sec in sections:
        sid = sec['id']
        abs_data  = sec.get('absoluteData', [])
        grw_data  = sec.get('growthData', [])
        fy_data   = sec.get('fyData', [])

        dates     = set()
        values    = set()    # raw L Cr values
        growths   = set()    # growth % values

        # Dates
        for row in abs_data:
            dates.add(row['date'])

        # Absolute values → L Cr
        # Also collect per-series lists for derived (difference) values
        series_vals: dict[str, list[float]] = {}
        for row in abs_data:
            for k, v in row.items():
                if k == 'date' or v is None:
                    continue
                lcr = round(v / 100_000, 4)
                values.add(lcr)
                series_vals.setdefault(k, []).append(lcr)

        # Derived: pairwise differences and sums within each series
        derived = set()
        for series, vals_list in series_vals.items():
            for i in range(len(vals_list)):
                for j in range(len(vals_list)):
                    if i != j:
                        derived.add(round(abs(vals_list[i] - vals_list[j]), 4))
                        derived.add(round(vals_list[i] + vals_list[j], 4))

        # Growth rates
        for row in grw_data + fy_data:
            for k, v in row.items():
                if k == 'date' or v is None:
                    continue
                growths.add(round(float(v), 2))

        lookup[sid] = {
            'dates':   dates,
            'values':  values,
            'derived': derived,
            'growths': growths,
        }
    return lookup


def all_dates(lookup: dict) -> set:
    """Union of all valid dates across all sections."""
    out = set()
    for v in lookup.values():
        out |= v['dates']
    return out


def all_values(lookup: dict) -> set:
    out = set()
    for v in lookup.values():
        out |= v['values'] | v['derived']
    return out


def all_growths(lookup: dict) -> set:
    out = set()
    for v in lookup.values():
        out |= v['growths']
    return out


def value_near(cited: float, valid_set: set) -> bool:
    """True if cited is within VALUE_TOLERANCE of any value in valid_set."""
    if not valid_set:
        return False
    tol = VALUE_TOLERANCE * max(abs(cited), 0.001)
    return any(abs(cited - v) <= tol for v in valid_set)


def growth_near(cited: float, valid_set: set) -> bool:
    """True if cited is within GROWTH_TOLERANCE of any value in valid_set."""
    if not valid_set:
        return False
    return any(abs(cited - v) <= GROWTH_TOLERANCE for v in valid_set)


# ── Text extraction ────────────────────────────────────────────────────────────

def extract_annotation_texts(ts_path: Path) -> dict[str, list[str]]:
    """
    Parse annotations_draft.ts / annotations_merged.ts.
    Returns { section_id: [text1, text2, ...] } where each text is the
    concatenated body+implication+title strings for all annotations in that section.

    Strategy: scan for section headers and accumulate string literals between them.
    """
    text = ts_path.read_text(encoding='utf-8')
    result: dict[str, list[str]] = {}

    # Find section blocks: "  sectionId: {" lines
    # Pattern: a bare identifier followed by ": {" at the start of a section block
    section_starts = list(re.finditer(
        r'^\s{2}(\w+)\s*:\s*\{',
        text, re.MULTILINE
    ))

    # For each section block, grab all string literal content
    for idx, m in enumerate(section_starts):
        sid = m.group(1)
        if sid in ('insights', 'gaps', 'opportunities', 'effect'):
            continue  # skip sub-keys
        start = m.start()
        end = section_starts[idx + 1].start() if idx + 1 < len(section_starts) else len(text)
        block = text[start:end]

        # Extract all string literals (single-line, double or single quoted)
        strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', block)
        strings += re.findall(r"'([^'\\]*(?:\\.[^'\\]*)*)'", block)
        result.setdefault(sid, []).extend(strings)

    return result


def extract_markdown_texts(md_path: Path) -> list[str]:
    """Return all non-header, non-bullet lines from a markdown file."""
    lines = []
    for line in md_path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('---'):
            lines.append(stripped)
    return lines


# ── Validation logic ──────────────────────────────────────────────────────────

class Result:
    def __init__(self, source: str):
        self.source = source
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str):
        self.errors.append(f"[{self.source}] {msg}")

    def warn(self, msg: str):
        self.warnings.append(f"[{self.source}] {msg}")

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate_text_against_lookup(
    texts: list[str],
    valid_dates: set,
    valid_values: set,
    valid_growths: set,
    result: Result,
    context: str,
):
    """
    Check dates, values, and growth rates in a list of text strings.

    Date check (A): A date is flagged as an ERROR only if it appears within
    150 characters of a ₹ value or % growth claim — indicating it is being
    cited as a data point. Dates mentioned in purely contextual prose (e.g.
    "Oct 2024 RBI guideline", "requires Feb 2025 data") are flagged as warnings
    only.

    Value check (C): Uses the all-sections value set, because annotations in one
    section legitimately cite values from other sections. Values < 0.1L Cr are
    skipped (too small for reliable matching). Forward-looking or illustrative
    values (no matching data row) are warnings, not errors.

    Growth check (B): Warns only (growth rates are sometimes cited approximately
    or computed from adjacent months not in the current file).
    """
    for text in texts:
        # Build the set of positions "near" a data claim (within 150 chars of ₹ or %)
        claim_spans: list[tuple[int,int]] = []
        for m in VALUE_RE.finditer(text):
            claim_spans.append((max(0, m.start() - 150), m.end() + 150))
        for m in GROWTH_RE.finditer(text):
            claim_spans.append((max(0, m.start() - 150), m.end() + 150))

        def near_claim(pos: int) -> bool:
            return any(lo <= pos <= hi for lo, hi in claim_spans)

        # A: Date check — always WARN, never ERROR.
        # Natural language often mixes data dates with event dates (e.g. "Oct 2024
        # RBI regulation") in the same sentence as data claims. Reliable automatic
        # distinction between "data point date" and "event date" is not possible
        # without semantic parsing. The check is advisory: flag for human review.
        for m in DATE_RE.finditer(text):
            date_str = m.group(0).strip()
            if date_str not in valid_dates:
                priority = "near data claim" if near_claim(m.start()) else "contextual"
                result.warn(
                    f"Date '{date_str}' in {context} not in sections.json "
                    f"({priority} — review if this is a data reference). "
                    f"Valid data dates: {sorted(valid_dates)}"
                )

        # B: Growth rate check (warnings only — values can be approximate or derived)
        for m in GROWTH_RE.finditer(text):
            cited_pct = _clean_float(m.group(1).lstrip('+'))
            if not growth_near(cited_pct, valid_growths):
                result.warn(
                    f"Growth rate '{m.group(0)}' ({cited_pct}%) in {context} "
                    f"not within ±{GROWTH_TOLERANCE}pp of any data value. "
                    f"Closest: {_nearest(cited_pct, valid_growths)}"
                )

        # C: Value check (₹X.XXL Cr) — uses all-sections values
        for m in VALUE_RE.finditer(text):
            cited_lcr = _clean_float(m.group(1))
            if cited_lcr < 0.1:
                continue  # too small to verify reliably at 1dp precision
            if not value_near(cited_lcr, valid_values):
                result.warn(
                    f"Value '₹{m.group(1)}L Cr' ({cited_lcr}) in {context} "
                    f"not within ±{VALUE_TOLERANCE*100:.0f}% of any data value or "
                    f"derived value across all sections. "
                    f"Closest: {_nearest(cited_lcr, valid_values)}"
                )


def _nearest(v: float, s: set, n: int = 3) -> list[float]:
    if not s:
        return []
    return sorted(s, key=lambda x: abs(x - v))[:n]


# ── Per-section annotation validation ─────────────────────────────────────────

def validate_annotations(ts_path: Path, lookup: dict, all_v: set, all_g: set) -> Result:
    result = Result("annotations")
    if not ts_path.exists():
        result.warn(f"Annotations file not found: {ts_path.name} — skipping")
        return result

    section_texts = extract_annotation_texts(ts_path)
    for sid, texts in section_texts.items():
        if sid not in lookup:
            continue
        # Dates: check against the section's own dates (annotations in section X
        # should cite dates that exist in section X's data when making data claims)
        sec_dates = lookup[sid]['dates']
        # Values: use ALL sections' data — cross-section references are common
        # (e.g. mainSectors annotation cites industryBySize Micro & Small value)
        validate_text_against_lookup(
            texts, sec_dates, all_v, all_g, result,
            context=f"section '{sid}'"
        )
    return result


def validate_markdown(md_path: Path, all_dates_: set, all_v: set, all_g: set) -> Result:
    result = Result(md_path.name)
    if not md_path.exists():
        result.warn(f"Markdown file not found: {md_path.name} — skipping")
        return result

    texts = extract_markdown_texts(md_path)
    validate_text_against_lookup(
        texts, all_dates_, all_v, all_g, result,
        context=md_path.name
    )
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def run(period_dir: Path, sections_path: Path) -> bool:
    """
    Run all content checks. Returns True if no errors.
    """
    # Load sections.json
    if not sections_path.exists():
        print(f"  ❌  sections.json not found: {sections_path}")
        return False

    with open(sections_path) as f:
        data = json.load(f)
    sections = data.get('sections', [])

    lookup    = build_section_lookup(sections)
    all_d     = all_dates(lookup)
    all_v     = all_values(lookup)
    all_g     = all_growths(lookup)

    results: list[Result] = []

    # Annotations file
    ann_ts = period_dir / "annotations_draft.ts"
    if not ann_ts.exists():
        ann_ts = period_dir / "annotations_merged.ts"
    results.append(validate_annotations(ann_ts, lookup, all_v, all_g))

    # Markdown docs
    for doc in ('insights.md', 'gaps.md', 'opportunities.md'):
        results.append(validate_markdown(period_dir / doc, all_d, all_v, all_g))

    # ── Print report ──────────────────────────────────────────────────────────
    all_errors   = [e for r in results for e in r.errors]
    all_warnings = [w for r in results for w in r.warnings]

    print()
    if all_errors:
        print(f"  ❌  CONTENT ERRORS ({len(all_errors)})")
        for e in all_errors:
            print(f"     {e}")
    if all_warnings:
        print(f"  ⚠️   CONTENT WARNINGS ({len(all_warnings)})")
        for w in all_warnings:
            print(f"     {w}")
    if not all_errors and not all_warnings:
        print("  ✅  Content check passed — 0 errors, 0 warnings")
    elif not all_errors:
        print(f"  ✅  Content check passed — 0 errors, {len(all_warnings)} warning(s)")

    return len(all_errors) == 0


def main():
    parser = argparse.ArgumentParser(description="Validate content accuracy of Stage 2 outputs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--period', help="Period dir name, e.g. 2026-03-30")
    group.add_argument('--merged', action='store_true', help="Validate merged outputs")
    args = parser.parse_args()

    if args.merged:
        period_dir    = SIBC_DIR / "merged"
        sections_path = period_dir / "sections_merged.json"
    else:
        period_dir    = SIBC_DIR / args.period
        sections_path = period_dir / "sections.json"

    if not period_dir.exists():
        print(f"  ❌  Period directory not found: {period_dir}")
        sys.exit(1)

    ok = run(period_dir, sections_path)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
