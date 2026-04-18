#!/usr/bin/env python3
"""
validate_timeline.py — India Credit Lens
------------------------------------------
Validates analysis/rbi_sibc/timeline.json for schema correctness,
chronological ordering, and path existence.

Run:
    python3 analysis/validate_timeline.py                    # default path
    python3 analysis/validate_timeline.py --path path/to/timeline.json

Exit codes:
    0 = valid
    1 = one or more errors
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS  = REPO_ROOT / "analysis"

# ── Result collector ──────────────────────────────────────────────────────────

class Result:
    def __init__(self):
        self.errors   = []
        self.warnings = []
        self.notes    = []

    def error(self, code, msg):
        self.errors.append(f"[{code}] {msg}")

    def warn(self, code, msg):
        self.warnings.append(f"[{code}] {msg}")

    def note(self, code, msg):
        self.notes.append(f"[{code}] {msg}")

    def passed(self):
        return len(self.errors) == 0

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_iso_date(s):
    """Return True if s matches YYYY-MM-DD."""
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def parse_iso(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


# ── Checks ────────────────────────────────────────────────────────────────────

def check_schema(data, result):
    """Top-level required fields."""
    required = ["report_id", "report_name", "periods"]
    for f in required:
        if f not in data:
            result.error("schema", f"Missing required top-level field: '{f}'")

    if not isinstance(data.get("periods"), list):
        result.error("schema", "'periods' must be an array")

    if "merged" in data and not isinstance(data["merged"], dict):
        result.error("schema", "'merged' must be an object if present")


def check_period_fields(data, result):
    """Each period entry must have required fields with correct types."""
    required_fields = {
        "period":           str,
        "dataDate":         str,
        "total_credit_lcr": (int, float),
        "paths":            dict,
    }
    optional_numeric = ["yoy_growth_pct", "fy_growth_pct"]
    required_paths   = ["sections", "system_model", "subsystems",
                        "annotations_draft", "annotations_live"]

    for i, entry in enumerate(data.get("periods", [])):
        loc = f"periods[{i}]"

        for field, expected_type in required_fields.items():
            val = entry.get(field)
            if val is None:
                result.error("period_fields", f"{loc}: missing required field '{field}'")
                continue
            if not isinstance(val, expected_type):
                result.error("period_fields",
                    f"{loc}: '{field}' must be {expected_type.__name__ if not isinstance(expected_type, tuple) else '/'.join(t.__name__ for t in expected_type)}, "
                    f"got {type(val).__name__}")

        for field in optional_numeric:
            val = entry.get(field)
            if val is not None and not isinstance(val, (int, float)):
                result.error("period_fields",
                    f"{loc}: '{field}' must be a number or null, got {type(val).__name__}")

        paths = entry.get("paths", {})
        for pf in required_paths:
            if pf not in paths:
                result.warn("period_fields",
                    f"{loc}: paths missing recommended key '{pf}'")


def check_dates(data, result):
    """dataDate must be a valid ISO date."""
    for i, entry in enumerate(data.get("periods", [])):
        dd = entry.get("dataDate", "")
        if not is_iso_date(dd):
            result.error("dates",
                f"periods[{i}]: 'dataDate' is not a valid YYYY-MM-DD date: '{dd}'")
        subsystem_count = entry.get("subsystem_count")
        if subsystem_count is not None and not isinstance(subsystem_count, int):
            result.warn("dates",
                f"periods[{i}]: 'subsystem_count' should be an int, got {type(subsystem_count).__name__}")


def check_order(data, result):
    """Periods must be in strictly ascending chronological order by dataDate."""
    dates = []
    for i, entry in enumerate(data.get("periods", [])):
        d = parse_iso(entry.get("dataDate", ""))
        if d:
            dates.append((i, d, entry.get("dataDate")))

    for j in range(1, len(dates)):
        i_prev, d_prev, s_prev = dates[j - 1]
        i_curr, d_curr, s_curr = dates[j]
        if d_curr <= d_prev:
            result.error("order",
                f"periods[{i_curr}] dataDate '{s_curr}' is not after "
                f"periods[{i_prev}] dataDate '{s_prev}' — periods must be in ascending order")


def check_duplicates(data, result):
    """No two periods may share the same dataDate."""
    seen = {}
    for i, entry in enumerate(data.get("periods", [])):
        dd = entry.get("dataDate")
        if dd in seen:
            result.error("duplicates",
                f"periods[{i}]: duplicate dataDate '{dd}' — also at periods[{seen[dd]}]")
        else:
            seen[dd] = i


def check_paths(data, timeline_path, result):
    """
    All paths in each period's 'paths' dict must resolve to existing files,
    relative to ANALYSIS dir. 'mermaid_output' and 'annotations_live' are
    allowed to be directories or paths that may not exist yet (they are outputs).
    """
    OPTIONAL_PATHS = {"mermaid_output", "annotations_live"}

    for i, entry in enumerate(data.get("periods", [])):
        dd = entry.get("dataDate", f"entry_{i}")
        for key, rel_path in entry.get("paths", {}).items():
            if key in OPTIONAL_PATHS:
                continue
            full_path = ANALYSIS / rel_path
            if not full_path.exists():
                result.error("paths",
                    f"periods[dataDate={dd}]: paths.{key} → '{rel_path}' does not exist")

    # Merged paths
    merged = data.get("merged", {})
    for key, rel_path in merged.items():
        full_path = ANALYSIS / rel_path
        if not full_path.exists():
            result.warn("paths",
                f"merged.{key} → '{rel_path}' does not exist (may not be generated yet)")


def check_merged_section(data, result):
    """merged field is optional but if present must have a 'sections' key."""
    merged = data.get("merged")
    if merged is None:
        result.note("merged", "No 'merged' section in timeline.json — add one after first merge")
        return
    if "sections" not in merged:
        result.warn("merged", "'merged' object is missing the 'sections' key")


# ── Print helpers ─────────────────────────────────────────────────────────────

def print_report(result, timeline_path, data):
    w = 64
    print(f"\n{'═' * w}")
    print(f"  India Credit Lens — Timeline Validation")
    print(f"  File: {timeline_path}")
    print(f"{'═' * w}\n")

    periods = data.get("periods", []) if isinstance(data, dict) else []
    if periods:
        print(f"  ℹ️   PERIODS ({len(periods)})")
        for entry in periods:
            dd = entry.get("dataDate", "?")
            p  = entry.get("period", "?")
            cr = entry.get("total_credit_lcr", "?")
            print(f"     {dd}  →  {p}  (₹{cr}L Cr)")
        print()

    if result.errors:
        print(f"  ❌  ERRORS ({len(result.errors)}) — pipeline blocked\n")
        for e in result.errors:
            print(f"     {e}")
        print()

    if result.warnings:
        print(f"  ⚠️   WARNINGS ({len(result.warnings)})\n")
        for w_ in result.warnings:
            print(f"     {w_}")
        print()

    if result.notes:
        print(f"  ℹ️   NOTES\n")
        for n in result.notes:
            print(f"     {n}")
        print()

    print(f"{'═' * w}")
    if result.passed():
        warn_str = f" — {len(result.warnings)} warning(s)" if result.warnings else ""
        print(f"  ✅  PASSED{warn_str}")
    else:
        print(f"  ❌  FAILED — {len(result.errors)} error(s) must be resolved")
    print(f"{'═' * w}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def validate(timeline_path):
    result = Result()

    if not Path(timeline_path).exists():
        result.error("file", f"timeline.json not found: {timeline_path}")
        print_report(result, timeline_path, {})
        return result

    try:
        with open(timeline_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.error("json", f"Invalid JSON: {e}")
        print_report(result, timeline_path, {})
        return result

    check_schema(data, result)
    check_period_fields(data, result)
    check_dates(data, result)
    check_order(data, result)
    check_duplicates(data, result)
    check_paths(data, timeline_path, result)
    check_merged_section(data, result)

    print_report(result, timeline_path, data)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Validate timeline.json")
    ap.add_argument("--path", default=str(ANALYSIS / "rbi_sibc" / "timeline.json"),
                    help="Path to timeline.json (default: analysis/rbi_sibc/timeline.json)")
    args = ap.parse_args()

    result = validate(args.path)
    sys.exit(0 if result.passed() else 1)
