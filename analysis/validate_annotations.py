#!/usr/bin/env python3
"""
validate_annotations.py — India Credit Lens
---------------------------------------------
Pre-generation validator. Runs BEFORE Claude generates system_model.json.

Validates the annotations TypeScript file (e.g. web/lib/reports/rbi_sibc.ts)
to ensure the analysis input is complete and correctly structured before it
is used to generate the system model.

If this passes → safe to run the report_analysis_prompt and generate system_model.json.
If this fails  → fix annotations first. The system model will inherit any errors here.

Checks:
  1. Schema        — each annotation has id, title, body, implication
  2. ID format     — kebab-case, no spaces or special characters
  3. Uniqueness    — no duplicate IDs within or across sections
  4. Coverage      — each section has at least 1 insight, 1 gap, 1 opportunity
  5. Minimums      — system-wide floor counts before a model is worth generating
  6. Body length   — body text is substantive (not placeholder)
  7. Implication   — implication/watch_note present and non-trivial

Usage:
    python3 validate_annotations.py ../web/lib/reports/rbi_sibc.ts
    python3 validate_annotations.py ../web/lib/reports/rbi_sibc.ts --output output/

Exit codes:
    0 = passed
    1 = failed
"""

import re
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import date


# ── Constants ─────────────────────────────────────────────────────────────────

# Minimum annotations required system-wide before the model is worth generating
MIN_TOTAL_INSIGHTS      = 5
MIN_TOTAL_GAPS          = 3
MIN_TOTAL_OPPORTUNITIES = 3
MIN_TOTAL_ANY           = 15   # total annotation count floor

# Per-section minimums
MIN_PER_SECTION_INSIGHTS      = 1
MIN_PER_SECTION_GAPS          = 1
MIN_PER_SECTION_OPPORTUNITIES = 1

# Body text floor — anything shorter is likely a placeholder
MIN_BODY_CHARS      = 80
MIN_IMPLICATION_CHARS = 40

# ID format: lowercase, numbers, hyphens only
ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9\-]+[a-z0-9]$')

# Required fields on every annotation
REQUIRED_FIELDS = ["id", "title", "body"]
# implication is checked separately (could also be "watch_note" for gaps)
IMPLICATION_FIELDS = ["implication"]


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_annotations_file(ts_path):
    """
    Parse a TypeScript annotations file into a structured dict.

    Returns:
        {
          "section_key": {
            "insights":      [{"id": ..., "title": ..., "body": ..., "implication": ...}, ...],
            "gaps":          [...],
            "opportunities": [...],
          },
          ...
        }

    Strategy: regex-based extraction — looks for patterns in the TS source.
    Not a full TS parser; relies on consistent code style in the annotations file.
    """
    with open(ts_path) as f:
        content = f.read()

    sections = {}

    # Find the ANNOTATIONS object block
    ann_match = re.search(
        r'const ANNOTATIONS[^=]*=\s*\{(.+?)\}\s*;?\s*\n(?:export|\/\/|const|function|\Z)',
        content, re.DOTALL
    )
    if not ann_match:
        # Fallback: take everything after ANNOTATIONS = {
        ann_start = content.find("const ANNOTATIONS")
        if ann_start == -1:
            return None, "Could not find ANNOTATIONS object in file"
        ann_content = content[ann_start:]
    else:
        ann_content = ann_match.group(0)

    # Find section keys — look for pattern: sectionName: {
    section_pattern = re.compile(r'\n\s{2}(\w+):\s*\{', re.MULTILINE)
    section_matches = list(section_pattern.finditer(ann_content))

    for i, sec_match in enumerate(section_matches):
        section_key = sec_match.group(1)
        # Slice content for this section (up to next section or end)
        start = sec_match.start()
        end   = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(ann_content)
        sec_content = ann_content[start:end]

        sections[section_key] = {
            "insights":      _extract_annotations(sec_content, "insights"),
            "gaps":          _extract_annotations(sec_content, "gaps"),
            "opportunities": _extract_annotations(sec_content, "opportunities"),
        }

    return sections, None


def _extract_annotations(section_content, lens_type):
    """Extract all annotation objects from a section's lens array."""
    # Find the lens array: insights: [ ... ]
    pattern = re.compile(
        rf'{lens_type}:\s*\[(.+?)(?:\n\s{{4}}\],|\n\s{{4}}\])',
        re.DOTALL
    )
    m = pattern.search(section_content)
    if not m:
        return []

    array_content = m.group(1)

    # Extract each annotation object — look for id: "..." as the anchor
    annotations = []
    for id_match in re.finditer(r'id:\s*"([^"]+)"', array_content):
        ann_id = id_match.group(1)

        # Slice context around this id to extract other fields
        start = id_match.start()
        # Find the next id or end of array
        next_id = re.search(r'id:\s*"', array_content[start + 1:])
        end = start + 1 + next_id.start() if next_id else len(array_content)
        obj_content = array_content[start:end]

        ann = {"id": ann_id}

        # Extract title
        t = re.search(r'title:\s*"((?:[^"\\]|\\.)+)"', obj_content)
        if t:
            ann["title"] = t.group(1)

        # Extract body (may be multi-line string concatenation)
        b = re.search(r'body:\s*"((?:[^"\\]|\\.)*)"', obj_content)
        if b:
            ann["body"] = b.group(1)
        else:
            # Multi-line: "..." + "..." — concatenate
            body_start = obj_content.find("body:")
            if body_start != -1:
                body_seg = obj_content[body_start:body_start + 800]
                parts = re.findall(r'"((?:[^"\\]|\\.)*)"', body_seg)
                ann["body"] = " ".join(parts[:6]) if parts else ""

        # Extract implication
        imp = re.search(r'implication:\s*"((?:[^"\\]|\\.)*)"', obj_content)
        if imp:
            ann["implication"] = imp.group(1)
        else:
            # Multi-line implication
            imp_start = obj_content.find("implication:")
            if imp_start != -1:
                imp_seg = obj_content[imp_start:imp_start + 600]
                parts = re.findall(r'"((?:[^"\\]|\\.)*)"', imp_seg)
                ann["implication"] = " ".join(parts[:4]) if parts else ""

        # Extract effect fields: highlight, dim, dash
        for field in ("highlight", "dim", "dash"):
            pattern_ef = re.compile(
                rf'{field}:\s*\[([^\]]*)\]'
            )
            m_ef = pattern_ef.search(obj_content)
            if m_ef:
                names = re.findall(r'"([^"]+)"', m_ef.group(1))
                ann[f"effect_{field}"] = names

        # Extract hidden flag
        if re.search(r'hidden:\s*true', obj_content):
            ann["hidden"] = True

        annotations.append(ann)

    return annotations


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


# ── Check 1: Schema ───────────────────────────────────────────────────────────

def check_schema(sections, result):
    for section, lenses in sections.items():
        for lens, items in lenses.items():
            for ann in items:
                for field in REQUIRED_FIELDS:
                    if field not in ann or not ann[field]:
                        result.error(
                            "schema",
                            f"[{section}.{lens}] '{ann.get('id','?')}' is missing or empty field: '{field}'",
                        )
                # implication check (slightly relaxed — warn not error)
                has_imp = ann.get("implication") and len(ann["implication"].strip()) > 0
                if not has_imp:
                    result.warn(
                        "schema",
                        f"[{section}.{lens}] '{ann.get('id','?')}' has no implication/watch_note — "
                        "every annotation should tell the reader what to do with the information.",
                    )


# ── Check 2: ID format ────────────────────────────────────────────────────────

def check_id_format(sections, result):
    for section, lenses in sections.items():
        for lens, items in lenses.items():
            for ann in items:
                aid = ann.get("id", "")
                if not ID_PATTERN.match(aid):
                    result.error(
                        "id_format",
                        f"[{section}.{lens}] ID '{aid}' is not valid kebab-case. "
                        "Use lowercase letters, numbers, and hyphens only. "
                        "Must start and end with alphanumeric.",
                    )


# ── Check 3: Uniqueness ───────────────────────────────────────────────────────

def check_uniqueness(sections, result):
    seen    = {}  # id → first location
    all_ids = []

    for section, lenses in sections.items():
        for lens, items in lenses.items():
            for ann in items:
                aid = ann.get("id", "")
                if not aid:
                    continue
                location = f"{section}.{lens}"
                if aid in seen:
                    result.error(
                        "uniqueness",
                        f"Duplicate annotation ID '{aid}' — "
                        f"first seen in [{seen[aid]}], repeated in [{location}]. "
                        "IDs must be globally unique across all sections and lenses.",
                    )
                else:
                    seen[aid] = location
                all_ids.append(aid)

    result.note("uniqueness", f"{len(all_ids)} annotation IDs checked, {len(seen)} unique")


# ── Check 4: Per-section coverage ────────────────────────────────────────────

def check_coverage(sections, result):
    for section, lenses in sections.items():
        n_insights      = len(lenses.get("insights", []))
        n_gaps          = len(lenses.get("gaps", []))
        n_opportunities = len(lenses.get("opportunities", []))

        if n_insights < MIN_PER_SECTION_INSIGHTS:
            result.error(
                "coverage",
                f"Section '{section}' has {n_insights} insight(s) — "
                f"minimum {MIN_PER_SECTION_INSIGHTS} required.",
            )
        if n_gaps < MIN_PER_SECTION_GAPS:
            result.error(
                "coverage",
                f"Section '{section}' has {n_gaps} gap(s) — "
                f"minimum {MIN_PER_SECTION_GAPS} required.",
            )
        if n_opportunities < MIN_PER_SECTION_OPPORTUNITIES:
            result.error(
                "coverage",
                f"Section '{section}' has {n_opportunities} opportunit(ies) — "
                f"minimum {MIN_PER_SECTION_OPPORTUNITIES} required.",
            )

        result.note(
            "coverage",
            f"Section '{section}': {n_insights} insights, {n_gaps} gaps, {n_opportunities} opportunities",
        )


# ── Check 5: System-wide minimums ────────────────────────────────────────────

def check_minimums(sections, result):
    total_insights      = sum(len(v.get("insights",      [])) for v in sections.values())
    total_gaps          = sum(len(v.get("gaps",          [])) for v in sections.values())
    total_opportunities = sum(len(v.get("opportunities", [])) for v in sections.values())
    total_all           = total_insights + total_gaps + total_opportunities

    result.note("minimums", f"Total: {total_insights} insights, {total_gaps} gaps, "
                            f"{total_opportunities} opportunities = {total_all} annotations")

    if total_insights < MIN_TOTAL_INSIGHTS:
        result.error("minimums",
            f"Only {total_insights} insights system-wide — minimum {MIN_TOTAL_INSIGHTS}. "
            "Not enough to build a meaningful system model.")

    if total_gaps < MIN_TOTAL_GAPS:
        result.error("minimums",
            f"Only {total_gaps} gaps system-wide — minimum {MIN_TOTAL_GAPS}. "
            "The system model requires explicit data limitation modelling.")

    if total_opportunities < MIN_TOTAL_OPPORTUNITIES:
        result.error("minimums",
            f"Only {total_opportunities} opportunities system-wide — minimum {MIN_TOTAL_OPPORTUNITIES}. "
            "The system model requires actionable lender opportunities.")

    if total_all < MIN_TOTAL_ANY:
        result.error("minimums",
            f"Only {total_all} total annotations — minimum {MIN_TOTAL_ANY}. "
            "More analysis depth is needed before generating the system model.")


# ── Check 6: Body length ──────────────────────────────────────────────────────

PIPELINE_LANGUAGE = [
    "statement 1", "statement 2", "statement 3", "statement 4", "statement 5",
    "statement 6", "statement 7", "statement 8",
    "table 1", "table 2", "table 3",
    "appendix", "annex",
]

def check_body_length(sections, result):
    for section, lenses in sections.items():
        for lens, items in lenses.items():
            for ann in items:
                body = ann.get("body", "")
                if len(body) < MIN_BODY_CHARS:
                    result.warn(
                        "body_length",
                        f"[{section}.{lens}] '{ann['id']}' body is {len(body)} chars — "
                        f"minimum {MIN_BODY_CHARS}. May be a placeholder or incomplete analysis.",
                    )

                imp = ann.get("implication", "")
                if imp and len(imp) < MIN_IMPLICATION_CHARS:
                    result.warn(
                        "body_length",
                        f"[{section}.{lens}] '{ann['id']}' implication is {len(imp)} chars — "
                        f"minimum {MIN_IMPLICATION_CHARS}. Too brief to be actionable.",
                    )

                # Check for internal pipeline/methodology language in user-facing text
                combined = (body + " " + imp).lower()
                found_lang = [t for t in PIPELINE_LANGUAGE if t in combined]
                if found_lang:
                    result.error(
                        "pipeline_language",
                        f"[{section}.{lens}] '{ann['id']}' contains internal pipeline/methodology "
                        f"language: {found_lang}. Replace with reader-facing descriptions.",
                    )


# ── Check G: effect.highlight present on insights + opportunities ─────────────

def check_effect_highlight_present(sections, result):
    """Every non-hidden insight and opportunity must declare effect.highlight."""
    for section, lenses in sections.items():
        for lens_type in ("insights", "opportunities"):
            for ann in lenses.get(lens_type, []):
                if ann.get("hidden"):
                    continue
                if not ann.get("effect_highlight"):
                    result.error(
                        "effect_highlight",
                        f"[{section}.{lens_type}] '{ann.get('id','?')}' has no effect.highlight. "
                        "Every insight and opportunity must declare which series tells the story — "
                        "this controls Y-axis scaling and chart focus on the dashboard.",
                    )


# ── Check H: series names in effect arrays must exist in section ──────────────

def check_effect_series_names(sections, result, section_series_map):
    """Names in effect.highlight/dim/dash must be valid seriesNames for that section."""
    for section, lenses in sections.items():
        valid_names = set(section_series_map.get(section, []))
        if not valid_names:
            continue  # no series data for this section — skip
        for lens_type in ("insights", "gaps", "opportunities"):
            for ann in lenses.get(lens_type, []):
                for field in ("effect_highlight", "effect_dim", "effect_dash"):
                    for name in ann.get(field, []):
                        if name not in valid_names:
                            result.error(
                                "effect_series_names",
                                f"[{section}.{lens_type}] '{ann.get('id','?')}' has "
                                f"effect.{field.replace('effect_','')} contains '{name}' "
                                f"which is not in this section's seriesNames: {sorted(valid_names)}.",
                            )


# ── Orchestrator ──────────────────────────────────────────────────────────────

def _load_section_series_map(sections_json_path):
    """Load seriesNames per section from sections_merged.json."""
    import json as _json
    try:
        with open(sections_json_path) as f:
            data = _json.load(f)
    except Exception:
        return {}
    series_map = {}
    for item in (data if isinstance(data, list) else []):
        key = item.get("key") or item.get("id") or item.get("section")
        names = item.get("seriesNames", [])
        if key and names:
            series_map[key] = names
    return series_map


def validate(ts_path, sections_json_path=None):
    sections, parse_error = parse_annotations_file(ts_path)

    result = ValidationResult()

    if parse_error or sections is None:
        result.error("parse", f"Could not parse annotations file: {parse_error}")
        return result, {}

    if not sections:
        result.error("parse", "No sections found in annotations file — check file structure")
        return result, sections

    checks = [
        ("Schema",           check_schema),
        ("ID format",        check_id_format),
        ("Uniqueness",       check_uniqueness),
        ("Section coverage", check_coverage),
        ("System minimums",  check_minimums),
        ("Body length",      check_body_length),
        ("Effect highlight", check_effect_highlight_present),
    ]

    for name, fn in checks:
        fn(sections, result)

    if sections_json_path:
        series_map = _load_section_series_map(sections_json_path)
        check_effect_series_names(sections, result, series_map)

    return result, sections


# ── Output ────────────────────────────────────────────────────────────────────

def print_report(result, ts_path, sections):
    w = 64
    total = sum(
        len(v.get(l, []))
        for v in sections.values()
        for l in ("insights", "gaps", "opportunities")
    ) if sections else 0

    print(f"\n{'═' * w}")
    print(f"  India Credit Lens — Pre-Generation Validation")
    print(f"  File    : {ts_path}")
    print(f"  Sections: {len(sections)}   Annotations: {total}")
    print(f"{'═' * w}")

    if result.errors:
        print(f"\n  ❌  ERRORS ({len(result.errors)}) — fix before generating system_model.json\n")
        for e in result.errors:
            print(f"     [{e['check']}] {e['message']}")

    if result.warnings:
        print(f"\n  ⚠️   WARNINGS ({len(result.warnings)})\n")
        for w_ in result.warnings:
            print(f"     [{w_['check']}] {w_['message']}")

    if result.info:
        print(f"\n  ℹ️   COVERAGE SUMMARY\n")
        for i in result.info:
            print(f"     {i['message']}")

    print(f"\n{'═' * w}")
    if result.passed:
        print(f"  ✅  PASSED — annotations are ready for system model generation")
        print(f"  →  Run report_analysis_prompt.md with Claude to generate system_model.json")
        print(f"  →  Then run: python3 generate_mermaid.py [path]/system_model.json")
    else:
        print(f"  ❌  FAILED — {len(result.errors)} error(s) must be resolved first")
    print(f"{'═' * w}\n")


def write_report(result, ts_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "pre_generation_validation_report.json")
    payload = {
        "passed":    result.passed,
        "file_path": str(ts_path),
        "generated": str(date.today()),
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
    parser = argparse.ArgumentParser(
        description="Pre-generation validator — run before generating system_model.json"
    )
    parser.add_argument("annotations", help="Path to the TypeScript annotations file")
    parser.add_argument("--output",    help="Directory to write validation report JSON")
    parser.add_argument("--sections",  help="Path to sections_merged.json for Check H (series name validation)")
    args = parser.parse_args()

    result, sections = validate(args.annotations, sections_json_path=args.sections)
    print_report(result, args.annotations, sections)

    if args.output:
        out = write_report(result, args.annotations, args.output)
        print(f"  Report written: {out}\n")

    sys.exit(0 if result.passed else 1)
