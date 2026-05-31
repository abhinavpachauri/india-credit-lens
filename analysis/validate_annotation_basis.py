#!/usr/bin/env python3
"""
Check 2d — Annotation basis completeness.

Rules:
  • Every annotation with claim_type "inference" or "hypothesis" MUST have
    a non-empty basis.inferences array.
  • Every annotation with claim_type "data" MUST have a non-empty basis.facts array.
  • Annotations without claim_type default to "inference" (strictest rule).

Exit 0 = all pass.  Exit 1 = failures found.
"""

import re
import sys
from pathlib import Path

ROOT       = Path(__file__).parent.parent
MERGED_TS  = ROOT / "analysis/rbi_sibc/merged/annotations_merged.ts"
LIVE_TS    = ROOT / "web/lib/reports/rbi_sibc.ts"


def parse_annotations(path: Path) -> list[dict]:
    """
    Lightweight parser — extracts id, claim_type, basis from a TypeScript
    annotations array without a full TS parser.
    """
    text = path.read_text()

    # Split on annotation object boundaries: look for { id: "..." blocks
    blocks = re.split(r'(?=\n\s*\{\s*\n\s*id:)', text)

    results = []
    for block in blocks:
        id_m = re.search(r'id:\s*["\']([^"\']+)["\']', block)
        if not id_m:
            continue
        ann_id = id_m.group(1)

        ct_m = re.search(r'claim_type:\s*["\']([^"\']+)["\']', block)
        claim_type = ct_m.group(1) if ct_m else "inference"

        has_basis = bool(re.search(r'\bbasis\s*:', block))

        # Extract inferences array content
        inf_m = re.search(r'inferences\s*:\s*\[([^\]]*)\]', block, re.DOTALL)
        inferences = []
        if inf_m:
            raw = inf_m.group(1).strip()
            if raw:
                inferences = [s.strip().strip('"\'') for s in re.split(r',\s*(?=["\'])', raw) if s.strip().strip('"\'')]

        # Extract facts array content
        facts_m = re.search(r'facts\s*:\s*\[([^\]]*)\]', block, re.DOTALL)
        facts = []
        if facts_m:
            raw = facts_m.group(1).strip()
            if raw:
                facts = [s.strip().strip('"\'') for s in re.split(r',\s*(?=["\'])', raw) if s.strip().strip('"\'')]

        results.append({
            "id":         ann_id,
            "claim_type": claim_type,
            "has_basis":  has_basis,
            "inferences": inferences,
            "facts":      facts,
        })

    return results


def validate(path: Path, label: str) -> list[str]:
    annotations = parse_annotations(path)
    if not annotations:
        return [f"[{label}] No annotations found — check parser"]

    errors = []
    for ann in annotations:
        aid       = ann["id"]
        ct        = ann["claim_type"]
        has_basis = ann["has_basis"]

        if not has_basis:
            errors.append(f"  [{aid}] claim_type={ct!r} — basis block missing entirely")
            continue

        if ct in ("inference", "hypothesis"):
            if not ann["inferences"]:
                errors.append(f"  [{aid}] claim_type={ct!r} — basis.inferences is empty")
        elif ct == "data":
            if not ann["facts"]:
                errors.append(f"  [{aid}] claim_type={ct!r} — basis.facts is empty")

    return errors


def main() -> int:
    targets = [
        (MERGED_TS, "annotations_merged.ts"),
        (LIVE_TS,   "rbi_sibc.ts (live)"),
    ]

    overall_ok = True
    for path, label in targets:
        if not path.exists():
            print(f"  SKIP  {label} — file not found")
            continue

        errors = validate(path, label)
        annotations = parse_annotations(path)
        total = len(annotations)

        if errors:
            print(f"\n  FAIL  {label} ({total} annotations, {len(errors)} error(s)):")
            for e in errors:
                print(e)
            overall_ok = False
        else:
            print(f"  PASS  {label} — {total} annotations all have basis ({sum(1 for a in annotations if a['claim_type'] == 'data')} data, {sum(1 for a in annotations if a['claim_type'] in ('inference','hypothesis'))} inference/hypothesis)")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
