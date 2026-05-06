#!/usr/bin/env python3
"""
validate_sections.py — India Credit Lens
-----------------------------------------
Validates sections.json before any dashboard or chart generation.

Checks:
  1. Schema         — required top-level fields, required per-section fields
  2. Date           — dataDate is a valid ISO date
  3. Data presence  — absoluteData has ≥3 rows; growthData and fyData are non-empty
  4. Positive values — all absoluteData numeric values are positive
  5. Growth bounds  — growthData values in [-50%, 300%]
  6. Key sectors    — minimum expected sector IDs present
  7. Series match   — seriesNames exactly match keys in every absoluteData row
  8. No nulls       — no null/None values in any data row
  8b. All-null series — any series where ALL rows are null (stale extraction guard)
  8c. YoY coverage  — for every (series, month) where both Year N and Year N-1 exist
                       in absoluteData, a null in either blocks a computable YoY; flagged
                       as WARNING (merged) or ERROR (per-period)
  9. Merged check   — (--merged) all known periods present, no gap >2 months

Usage:
    python3 validate_sections.py rbi_sibc/2026-02-27/sections.json
    python3 validate_sections.py rbi_sibc/merged/sections_merged.json --merged
    python3 validate_sections.py rbi_sibc/2026-02-27/sections.json \\
        --output output/validation/

Exit codes:
    0 = passed (errors=0; warnings are non-blocking)
    1 = failed (one or more critical errors)
"""

import json
import math
import os
import re
import sys
import argparse
from datetime import date, datetime
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────

REQUIRED_SECTION_IDS = {
    "bankCredit",
    "mainSectors",
    "services",
    "personalLoans",
}

REQUIRED_SECTION_FIELDS = ["id", "title", "seriesNames", "absoluteData", "growthData", "fyData"]

GROWTH_MIN = -50.0
GROWTH_MAX = 300.0

# Regex to parse "Jan 2024", "Mar 2025", or "Feb 2024*" (delayed-publication labels).
DATE_LABEL_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\*?$")

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_date_label(label):
    """'Jan 2024' → date(2024,1,1) or None"""
    if not label:
        return None
    m = DATE_LABEL_RE.match(str(label).strip())
    if not m:
        return None
    return date(int(m.group(2)), MONTH_MAP[m.group(1)], 1)


def months_between(d1, d2):
    """Number of months between two date objects (absolute)."""
    return abs((d2.year - d1.year) * 12 + d2.month - d1.month)


# ── Result collector ──────────────────────────────────────────────────────────

class ValidationResult:
    def __init__(self):
        self.errors   = []
        self.warnings = []
        self.info     = []

    def error(self, check, msg):
        self.errors.append({"check": check, "level": "ERROR", "message": msg})

    def warn(self, check, msg):
        self.warnings.append({"check": check, "level": "WARNING", "message": msg})

    def note(self, check, msg):
        self.info.append({"check": check, "level": "INFO", "message": msg})

    @property
    def passed(self):
        return len(self.errors) == 0


# ── Check 1: Top-level schema ─────────────────────────────────────────────────

def check_schema(data, result):
    for field in ["report", "dataDate", "sections"]:
        if field not in data:
            result.error("schema", f"Top-level field missing: '{field}'")

    sections = data.get("sections")
    if not isinstance(sections, list) or len(sections) == 0:
        result.error("schema", "'sections' must be a non-empty array")
        return

    for i, sec in enumerate(sections):
        sid = sec.get("id", f"[{i}]")
        for field in REQUIRED_SECTION_FIELDS:
            if field not in sec:
                result.error("schema", f"Section '{sid}' missing required field: '{field}'")
            elif field in ("absoluteData", "growthData", "fyData") and not isinstance(sec[field], list):
                result.error("schema", f"Section '{sid}'.{field} must be an array")


# ── Check 2: Date validity ────────────────────────────────────────────────────

def check_date(data, result):
    raw = data.get("dataDate")
    if not raw:
        return  # already caught by schema
    try:
        datetime.strptime(str(raw), "%Y-%m-%d")
        result.note("date", f"dataDate '{raw}' is a valid ISO date")
    except ValueError:
        result.error("date", f"dataDate '{raw}' is not a valid ISO date (expected YYYY-MM-DD)")


# ── Check 3: Data presence ────────────────────────────────────────────────────

def check_data_presence(data, result):
    for sec in data.get("sections", []):
        sid = sec.get("id", "?")

        abs_data = sec.get("absoluteData", [])
        if len(abs_data) < 3:
            result.error(
                "data_presence",
                f"Section '{sid}'.absoluteData has only {len(abs_data)} rows — "
                "need ≥3 (at minimum 2 historical + 1 current).",
            )

        if not sec.get("growthData"):
            result.warn("data_presence", f"Section '{sid}'.growthData is empty")

        if not sec.get("fyData"):
            result.warn("data_presence", f"Section '{sid}'.fyData is empty")


# ── Check 4: Positive values ──────────────────────────────────────────────────

def check_positive_values(data, result):
    for sec in data.get("sections", []):
        sid = sec.get("id", "?")
        for row in sec.get("absoluteData", []):
            for key, val in row.items():
                if key == "date":
                    continue
                if isinstance(val, (int, float)) and val < 0:
                    result.error(
                        "positive_values",
                        f"Section '{sid}'.absoluteData[date={row.get('date')}] "
                        f"has negative value for '{key}': {val}",
                    )


# ── Check 5: Growth bounds ────────────────────────────────────────────────────

def check_growth_bounds(data, result):
    for sec in data.get("sections", []):
        sid = sec.get("id", "?")
        for row in sec.get("growthData", []):
            for key, val in row.items():
                if key == "date":
                    continue
                if not isinstance(val, (int, float)):
                    continue
                if val < GROWTH_MIN:
                    result.warn(
                        "growth_bounds",
                        f"Section '{sid}'.growthData[date={row.get('date')}] "
                        f"'{key}' = {val}% is below {GROWTH_MIN}% — verify not a series break.",
                    )
                if val > GROWTH_MAX:
                    result.warn(
                        "growth_bounds",
                        f"Section '{sid}'.growthData[date={row.get('date')}] "
                        f"'{key}' = {val}% exceeds {GROWTH_MAX}% — verify not a base-effect artifact.",
                    )


# ── Check 6: Key sectors present ─────────────────────────────────────────────

def check_key_sectors(data, result):
    present = {sec.get("id") for sec in data.get("sections", [])}
    for required in sorted(REQUIRED_SECTION_IDS):
        if required not in present:
            result.error(
                "key_sectors",
                f"Required section '{required}' is missing from sections array.",
            )
    result.note("key_sectors", f"Sections present: {sorted(present)}")


# ── Check 7: Series names match data keys ─────────────────────────────────────

def check_series_match(data, result):
    for sec in data.get("sections", []):
        sid = sec.get("id", "?")
        series = set(sec.get("seriesNames", []))
        abs_data = sec.get("absoluteData", [])
        if not abs_data:
            continue

        # All rows must have exactly the declared seriesNames as keys (besides "date")
        for row in abs_data:
            row_keys = {k for k in row if k != "date"}
            extra   = row_keys - series
            missing = series - row_keys
            if extra:
                result.warn(
                    "series_match",
                    f"Section '{sid}' absoluteData row date={row.get('date')} "
                    f"has undeclared keys: {sorted(extra)}",
                )
            if missing:
                result.error(
                    "series_match",
                    f"Section '{sid}' absoluteData row date={row.get('date')} "
                    f"missing declared seriesNames: {sorted(missing)}",
                )


# ── Check 8: No nulls ─────────────────────────────────────────────────────────

def check_no_nulls(data, result, merged=False):
    """
    For per-period files: null values are errors — all series should be populated.
    For merged files: null values are warnings — some series (Gold Loans, Housing,
    NBFCs, Tourism) only appear in March SIBC files and are legitimately null in
    January rows of the merged dataset.
    """
    for sec in data.get("sections", []):
        sid = sec.get("id", "?")
        for array_name in ("absoluteData", "growthData", "fyData"):
            for row in sec.get(array_name, []):
                for key, val in row.items():
                    if key == "date":
                        continue
                    if val is None:
                        msg = (
                            f"Section '{sid}'.{array_name}[date={row.get('date')}] "
                            f"key '{key}' is null."
                        )
                        if merged:
                            result.warn("no_nulls", msg + " (expected for series absent in January SIBC files)")
                        else:
                            result.error("no_nulls", msg)


# ── Check 9: Merged continuity ────────────────────────────────────────────────

def check_merged_continuity(data, result):
    """Only run when --merged is passed. Checks that all absoluteData date labels
    form a roughly continuous sequence with no gap > 12 months. RBI SIBC files are
    semi-annual (January and March only), so gaps of up to 10 months between
    consecutive data points are normal and expected."""
    for sec in data.get("sections", []):
        sid = sec.get("id", "?")
        abs_data = sec.get("absoluteData", [])
        dates = []
        for row in abs_data:
            d = parse_date_label(row.get("date"))
            if d:
                dates.append(d)

        if len(dates) < 2:
            result.warn(
                "merged_continuity",
                f"Section '{sid}' has fewer than 2 parseable date labels — cannot check continuity.",
            )
            continue

        dates_sorted = sorted(dates)
        for i in range(1, len(dates_sorted)):
            gap = months_between(dates_sorted[i - 1], dates_sorted[i])
            if gap > 12:
                result.error(
                    "merged_continuity",
                    f"Section '{sid}' has a {gap}-month gap between "
                    f"'{dates_sorted[i-1].strftime('%b %Y')}' and "
                    f"'{dates_sorted[i].strftime('%b %Y')}' — "
                    "merged series should have no gap > 12 months.",
                )

        result.note(
            "merged_continuity",
            f"Section '{sid}': {len(dates_sorted)} date points from "
            f"{dates_sorted[0].strftime('%b %Y')} to {dates_sorted[-1].strftime('%b %Y')}",
        )


# ── Check 8b: All-null series detection (stale extraction guard) ──────────────

def check_all_null_series(data, result, merged=False):
    """
    Fires when an entire series is null across ALL absoluteData rows.
    This catches the case where extract_sibc.py was run with an older parser
    that could not read certain rows — every value comes back None rather than
    a number.  A partial null (some rows null, some populated) is handled by
    check_no_nulls; this check is specifically for the all-null symptom.

    Per-period: ERROR — the extraction is definitively broken for that series.
    Merged:     WARNING — a series absent from ALL periods is suspicious but may
                be a newly added series not yet present in older SIBC files.
    """
    import math

    for sec in data.get("sections", []):
        sid = sec.get("id", "?")
        abs_data = sec.get("absoluteData", [])
        if not abs_data:
            continue

        series_names = sec.get("seriesNames", [])
        for series in series_names:
            values = [row.get(series) for row in abs_data]
            # A value counts as "missing" if it is None or NaN
            missing = [
                v for v in values
                if v is None or (isinstance(v, float) and math.isnan(v))
            ]
            if len(missing) == len(values):
                msg = (
                    f"Section '{sid}' series '{series}' is null/NaN across ALL "
                    f"{len(values)} absoluteData rows — likely a stale extraction "
                    f"(re-run extract_sibc.py with the current parser)."
                )
                if merged:
                    result.warn("all_null_series", msg)
                else:
                    result.error("all_null_series", msg)
            elif len(missing) > len(values) * 0.5:
                result.warn(
                    "all_null_series",
                    f"Section '{sid}' series '{series}' has {len(missing)}/{len(values)} "
                    f"null/NaN absoluteData rows — verify parser is reading all columns.",
                )


# ── Check 8c: YoY growth coverage ────────────────────────────────────────────

def check_yoy_coverage(data, result, merged=False):
    """
    Check 8c: For every (series, month-name) pair where absoluteData contains
    entries for both Year N and Year N-1, flag any null value that makes the
    YoY growth uncomputable.

    This catches the subtle failure mode where a later SIBC file drops historical
    rows as NaN — the dates are present in absoluteData but the values are null,
    silently producing missing entries in growthData.

    Severity: ERROR for per-period files; WARNING for merged files (some nulls are
    expected for series absent in January SIBC files, e.g. Gold Loans).
    """
    for sec in data.get("sections", []):
        sid = sec.get("id", "?")
        abs_data = sec.get("absoluteData", [])
        series_names = sec.get("seriesNames", [])
        if not abs_data or not series_names:
            continue

        # Build map: display-label → {series: value}
        val_map: dict[str, dict] = {}
        for row in abs_data:
            lbl = row.get("date", "")
            if lbl:
                val_map[lbl] = {k: v for k, v in row.items() if k != "date"}

        # Parse each label to extract (month_name, year) — e.g. "Jan 2025" → ("Jan", 2025)
        MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        parsed: dict[str, tuple[str, int]] = {}  # label → (month_abbr, year)
        for lbl in val_map:
            parts = lbl.split()
            if len(parts) == 2 and parts[0] in MONTHS:
                try:
                    # Strip trailing '*' (Pattern A relabelled dates e.g. "Feb 2025*")
                    parsed[lbl] = (parts[0], int(parts[1].rstrip("*")))
                except ValueError:
                    pass

        # For each label, check if the same month in prior year exists.
        # Check both plain ("Feb 2025") and relabelled ("Feb 2025*") variants —
        # Pattern A relabelled dates carry an asterisk but are semantically equivalent.
        for lbl, (month, year) in parsed.items():
            prior_plain = f"{month} {year - 1}"
            prior_star  = f"{month} {year - 1}*"
            prior_lbl = prior_plain if prior_plain in val_map else (prior_star if prior_star in val_map else None)
            if prior_lbl is None:
                continue  # No prior-year entry — YoY simply not computable, not a data error

            for sn in series_names:
                curr_val = val_map[lbl].get(sn)
                prev_val = val_map[prior_lbl].get(sn)

                curr_null = curr_val is None or (isinstance(curr_val, float) and math.isnan(curr_val))
                prev_null = prev_val is None or (isinstance(prev_val, float) and math.isnan(prev_val))

                if curr_null or prev_null:
                    null_side = []
                    if prev_null:
                        null_side.append(f"{prior_lbl} (prior-year)")
                    if curr_null:
                        null_side.append(f"{lbl} (current)")
                    msg = (
                        f"Section '{sid}' series '{sn}': YoY growth for {lbl} is uncomputable — "
                        f"null absoluteData value at {' and '.join(null_side)}."
                    )
                    if merged:
                        result.warn("yoy_coverage", msg)
                    else:
                        result.error("yoy_coverage", msg)


# ── Check 2c: dateOverrides consistency ──────────────────────────────────────

def check_date_overrides(data: dict, result) -> None:
    """Check 2c: dateOverrides entries are consistent with absoluteData."""
    overrides = data.get("dateOverrides", [])
    if not overrides:
        return  # No overrides — nothing to validate

    sections = {s["id"]: s for s in data.get("sections", [])}

    for rec in overrides:
        orig    = rec.get("original_iso", "")
        relabel = rec.get("relabelled_iso", "")
        disp    = rec.get("relabelled_display", "")
        stmt    = rec.get("statement", "")

        # Validate ISO date format
        for field, val in [("original_iso", orig), ("relabelled_iso", relabel)]:
            if not val:
                result.error("date_overrides", f"dateOverrides: missing '{field}'")
                continue
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                result.error(
                    "date_overrides",
                    f"dateOverrides: {field}={val!r} is not a valid YYYY-MM-DD date"
                )

        # Check that the relabelled display label appears in at least one section's absoluteData
        if disp:
            found = any(
                any(row.get("date") == disp for row in sec.get("absoluteData", []))
                for sec in sections.values()
            )
            if not found:
                result.warn(
                    "date_overrides",
                    f"dateOverrides: relabelled_display={disp!r} not found in any section's absoluteData "
                    f"(may be expected if section uses different statement)"
                )


# ── Orchestrator ──────────────────────────────────────────────────────────────

def validate(sections_path, merged=False):
    with open(sections_path) as f:
        data = json.load(f)

    result = ValidationResult()

    checks = [
        ("Schema",          lambda d, r: check_schema(d, r)),
        ("Date",            lambda d, r: check_date(d, r)),
        ("Data presence",   lambda d, r: check_data_presence(d, r)),
        ("Positive values", lambda d, r: check_positive_values(d, r)),
        ("Growth bounds",   lambda d, r: check_growth_bounds(d, r)),
        ("Key sectors",     lambda d, r: check_key_sectors(d, r)),
        ("Series match",    lambda d, r: check_series_match(d, r)),
        ("No nulls",        lambda d, r: check_no_nulls(d, r, merged=merged)),
        ("All-null series", lambda d, r: check_all_null_series(d, r, merged=merged)),
        ("YoY coverage",    lambda d, r: check_yoy_coverage(d, r, merged=merged)),
        ("Date overrides",  lambda d, r: check_date_overrides(d, r)),
    ]

    if merged:
        checks.append(("Merged continuity", lambda d, r: check_merged_continuity(d, r)))

    for name, fn in checks:
        fn(data, result)

    return result, data


# ── Output ────────────────────────────────────────────────────────────────────

def print_report(result, sections_path):
    w = 64
    print(f"\n{'═' * w}")
    print(f"  India Credit Lens — Sections Validation Report")
    print(f"  File : {sections_path}")
    print(f"{'═' * w}")

    if result.errors:
        print(f"\n  ❌  ERRORS ({len(result.errors)}) — generation blocked\n")
        for e in result.errors:
            print(f"     [{e['check']}] {e['message']}")

    if result.warnings:
        print(f"\n  ⚠️   WARNINGS ({len(result.warnings)})\n")
        for w_ in result.warnings:
            print(f"     [{w_['check']}] {w_['message']}")

    if result.info:
        print(f"\n  ℹ️   INFO\n")
        for i in result.info:
            print(f"     {i['message']}")

    print(f"\n{'═' * w}")
    if result.passed:
        print(f"  ✅  PASSED — {len(result.warnings)} warning(s)")
    else:
        print(f"  ❌  FAILED — {len(result.errors)} error(s) must be resolved")
    print(f"{'═' * w}\n")


def write_report(result, sections_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "validation_sections.json")
    payload = {
        "passed":        result.passed,
        "sections_path": str(sections_path),
        "generated":     str(date.today()),
        "summary": {
            "errors":   len(result.errors),
            "warnings": len(result.warnings),
            "info":     len(result.info),
        },
        "errors":   result.errors,
        "warnings": result.warnings,
        "info":     result.info,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate sections.json")
    parser.add_argument("sections", help="Path to sections.json")
    parser.add_argument("--merged", action="store_true",
                        help="Enable merged-continuity check (for sections_merged.json)")
    parser.add_argument("--output", help="Directory to write validation_sections.json")
    args = parser.parse_args()

    result, _ = validate(args.sections, merged=args.merged)
    print_report(result, args.sections)

    if args.output:
        out = write_report(result, args.sections, args.output)
        print(f"  Report written: {out}\n")

    sys.exit(0 if result.passed else 1)
