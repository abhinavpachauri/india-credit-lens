#!/usr/bin/env python3
"""
validate_web_series.py — Stage 3 guard rail for series name consistency.

Problem this solves
───────────────────
The RBI CSV uses verbose official sector names (e.g. "Non-Banking Financial
Companies (NBFCs)", "Housing (Including Priority Sector Housing)"). The web
dashboard applies label overrides so the chart legend shows short readable
names ("NBFCs", "Housing"). Annotation effects (highlight/dim/dash) must
reference the SHORT chart names — but sections_merged.json seriesNames can
drift if the overrides JSON is not applied during extraction.

Two checks
──────────
Check W1 — sections_merged.json alignment
  For every section, compare the seriesNames in sections_merged.json against
  the true web series names (CSV + overrides). Any mismatch means Check H in
  validate_annotations.py is validating against wrong names.

Check W2 — annotation effect names
  For every annotation effect (highlight/dim/dash), verify each referenced
  name exists in the web series names for that section. This is the definitive
  check — sections_merged.json may still be stale after an extraction, but
  annotations go live immediately via promote_annotations.py.

Usage
─────
  python3 analysis/validate_web_series.py               # uses defaults
  python3 analysis/validate_web_series.py \\
      --csv  web/public/data/rbi_sibc_consolidated.csv \\
      --overrides web/lib/reports/rbi_sibc_label_overrides.json \\
      --merged analysis/rbi_sibc/merged/sections_merged.json \\
      --annotations web/lib/reports/rbi_sibc.ts

Exit codes: 0 = pass, 1 = errors found.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path


# ── Section config — mirrors buildSections() in rbi_sibc.ts ───────────────────
# Each entry describes how the web layer builds that section's labels.
#
# "hardcoded" sections use fixed code→label maps, no CSV lookup needed.
# "parent"    sections derive labels from childrenOf(parent_code, stmt?, psl?).
#
# When adding a new section to the dashboard, add a matching entry here.

SECTION_CONFIG = {
    "bankCredit": {
        "type": "hardcoded",
        "labels": {
            "I": "Bank Credit",
            "II": "Food Credit",
            "III": "Non-food Credit",
        },
    },
    "mainSectors": {
        "type": "hardcoded",
        "labels": {
            "1": "Agriculture",
            "2": "Industry",
            "3": "Services",
            "4": "Personal Loans",
        },
    },
    "industryBySize": {
        "type": "parent",
        "parent": "2",
        "stmt": "Statement 1",
        "psl": False,
    },
    "services": {
        "type": "parent",
        "parent": "3",
        "stmt": None,
        "psl": False,
        "override_key": "services",
    },
    "personalLoans": {
        "type": "parent",
        "parent": "4",
        "stmt": None,
        "psl": False,
        "override_key": "personalLoans",
    },
    "prioritySector": {
        "type": "psl",
        "override_key": "prioritySector",
    },
    "industryByType": {
        "type": "parent",
        "parent": "2",
        "stmt": "Statement 2",
        "psl": False,
    },
}


# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def children_of(
    rows: list[dict],
    parent_code: str,
    stmt = None,
    psl: bool = False,
) -> dict[str, str]:
    """Return {code: sector} for children of parent_code (mirrors childrenOf in data.ts)."""
    result: dict[str, str] = {}
    for r in rows:
        if r.get("parent_code") != parent_code:
            continue
        row_psl = r.get("is_priority_sector_memo", "False").lower() in ("true", "1")
        if row_psl != psl:
            continue
        if stmt and r.get("statement") != stmt:
            continue
        result[r["code"]] = r["sector"]
    return result


def psl_labels(rows: list[dict]) -> dict[str, str]:
    """Return {code: sector} for PSL memo rows."""
    result: dict[str, str] = {}
    for r in rows:
        if r.get("is_priority_sector_memo", "False").lower() in ("true", "1"):
            result[r["code"]] = r["sector"]
    return result


# ── Compute true web series names ─────────────────────────────────────────────

def web_series_names(
    rows: list[dict],
    section_id: str,
    overrides: dict[str, dict[str, str]],
) -> set[str]:
    cfg = SECTION_CONFIG.get(section_id)
    if cfg is None:
        return set()

    if cfg["type"] == "hardcoded":
        return set(cfg["labels"].values())

    if cfg["type"] == "psl":
        labels = psl_labels(rows)
    else:
        labels = children_of(rows, cfg["parent"], cfg.get("stmt"), cfg.get("psl", False))

    # Apply overrides from JSON
    override_key = cfg.get("override_key")
    if override_key and override_key in overrides:
        for code, short_label in overrides[override_key].items():
            if code in labels:
                labels[code] = short_label

    return set(labels.values())


# ── Annotation effect parser ───────────────────────────────────────────────────

def extract_annotation_effects(ts_path: str) -> dict[str, dict[str, list[str]]]:
    """
    Parse rbi_sibc.ts and return {annotation_id: {field: [names]}}.
    Fields: highlight, dim, dash.
    """
    with open(ts_path) as f:
        content = f.read()

    results: dict[str, dict[str, list[str]]] = {}
    current_id = None

    for line in content.split("\n"):
        id_match = re.search(r'\bid:\s*"([^"]+)"', line)
        if id_match:
            current_id = id_match.group(1)

        if current_id and "effect:" in line:
            effects: dict[str, list[str]] = {}
            for field in ("highlight", "dim", "dash"):
                pattern = rf'{field}:\s*\[([^\]]*)\]'
                m = re.search(pattern, line)
                if m:
                    names = re.findall(r'"([^"]+)"', m.group(1))
                    if names:
                        effects[field] = names
            if effects:
                results[current_id] = effects

    return results


def section_of_annotation(ts_path: str) -> dict[str, str]:
    """Return {annotation_id: section_id} by parsing the sections object."""
    with open(ts_path) as f:
        content = f.read()

    ann_to_section: dict[str, str] = {}
    current_section = None

    for line in content.split("\n"):
        # Detect section key  e.g.  "  services: {"  or  "  bankCredit: {"
        sec_match = re.match(r'\s{2}(\w+):\s*\{', line)
        if sec_match and sec_match.group(1) in SECTION_CONFIG:
            current_section = sec_match.group(1)

        id_match = re.search(r'\bid:\s*"([^"]+)"', line)
        if id_match and current_section:
            ann_to_section[id_match.group(1)] = current_section

    return ann_to_section


# ── Validator ─────────────────────────────────────────────────────────────────

def validate(
    csv_path: str,
    overrides_path: str,
    merged_path: str,
    annotations_path: str,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    rows = load_csv(csv_path)

    with open(overrides_path) as f:
        raw = json.load(f)
    # Strip the _comment key before treating as overrides
    overrides = {k: v for k, v in raw.items() if not k.startswith("_")}

    with open(merged_path) as f:
        merged_data = json.load(f)
    merged_names: dict[str, set[str]] = {
        s["id"]: set(s.get("seriesNames", []))
        for s in merged_data.get("sections", [])
    }

    # ── Check W1: sections_merged alignment ──────────────────────────────────
    for sec_id in SECTION_CONFIG:
        web_names = web_series_names(rows, sec_id, overrides)
        mrg_names = merged_names.get(sec_id, set())

        only_web = web_names - mrg_names
        only_mrg = mrg_names - web_names

        if only_web:
            errors.append(
                f"[W1:{sec_id}] In CSV+overrides but missing from sections_merged.json: "
                f"{sorted(only_web)}. "
                f"Re-run generate_merge.py (Check H in validate_annotations.py is validating wrong names)."
            )
        if only_mrg:
            errors.append(
                f"[W1:{sec_id}] In sections_merged.json but not rendered by chart: "
                f"{sorted(only_mrg)}. "
                f"Either add an override to rbi_sibc_label_overrides.json or update sections_merged."
            )

    # ── Check W2: annotation effect names ────────────────────────────────────
    ann_effects = extract_annotation_effects(annotations_path)
    ann_sections = section_of_annotation(annotations_path)

    for ann_id, effects in ann_effects.items():
        sec_id = ann_sections.get(ann_id)
        if sec_id is None:
            warnings.append(f"[W2:{ann_id}] Could not determine section — skipping effect check.")
            continue

        web_names = web_series_names(rows, sec_id, overrides)

        for field, names in effects.items():
            for name in names:
                if name not in web_names:
                    errors.append(
                        f"[W2:{sec_id}.{ann_id}] effect.{field} references '{name}' "
                        f"which is not in the chart's series names. "
                        f"Available: {sorted(web_names)}."
                    )

    return errors, warnings


# ── Output ────────────────────────────────────────────────────────────────────

def main():
    repo = Path(__file__).parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv",         default=str(repo / "web/public/data/rbi_sibc_consolidated.csv"))
    parser.add_argument("--overrides",   default=str(repo / "web/lib/reports/rbi_sibc_label_overrides.json"))
    parser.add_argument("--merged",      default=str(repo / "analysis/rbi_sibc/merged/sections_merged.json"))
    parser.add_argument("--annotations", default=str(repo / "web/lib/reports/rbi_sibc.ts"))
    args = parser.parse_args()

    errors, warnings = validate(args.csv, args.overrides, args.merged, args.annotations)

    w = 64
    print(f"\n{'═' * w}")
    print(f"  India Credit Lens — Web Series Name Validation")
    print(f"  Checks: W1 (sections_merged alignment)  W2 (annotation effects)")
    print(f"{'═' * w}")

    if errors:
        print(f"\n  ❌  ERRORS ({len(errors)}) — fix before pushing\n")
        for e in errors:
            print(f"     {e}")

    if warnings:
        print(f"\n  ⚠️   WARNINGS ({len(warnings)})\n")
        for wn in warnings:
            print(f"     {wn}")

    if not errors and not warnings:
        print(f"\n  ✅  PASSED — all chart series names are consistent")
    elif not errors:
        print(f"\n  ✅  PASSED (with warnings)")
    else:
        print(f"\n  ❌  FAILED — {len(errors)} error(s) must be resolved")

    print(f"{'═' * w}\n")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
