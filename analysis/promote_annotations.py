#!/usr/bin/env python3
"""
promote_annotations.py — India Credit Lens
--------------------------------------------
Automated Stage 8 copy: promotes annotations_merged.ts → web/lib/reports/rbi_sibc.ts.

What it does:
  1. Reads annotations_merged.ts from the merged period directory
  2. Extracts the ANNOTATIONS block (export const ANNOTATIONS = { ... })
  3. Replaces the ANNOTATIONS block in web/lib/reports/rbi_sibc.ts
  4. Verifies the annotation IDs in the live file match those in the source
  5. Prints a diff summary (IDs added, removed, unchanged)
  6. Exits 0 on success, 1 on any verification failure

Does NOT:
  - Run tsc or npm run build (call run_evals.py for that)
  - Commit or push to git

Usage:
    python3 analysis/promote_annotations.py
    python3 analysis/promote_annotations.py --dry-run     # preview only, no file write
    python3 analysis/promote_annotations.py --force       # skip ID diff prompt

Exit codes:
    0 = promotion succeeded and verified
    1 = error (source not found, extraction failed, ID mismatch)
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
ANALYSIS    = REPO_ROOT / "analysis"
MERGED_DIR  = ANALYSIS / "rbi_sibc" / "merged"
SOURCE_FILE = MERGED_DIR / "annotations_merged.ts"
TARGET_FILE = REPO_ROOT / "web" / "lib" / "reports" / "rbi_sibc.ts"

# ── Regex to locate the ANNOTATIONS block ────────────────────────────────────

ANNOTATIONS_RE = re.compile(
    r'^export const ANNOTATIONS.*?^\};',
    re.MULTILINE | re.DOTALL
)

ID_RE = re.compile(r'\bid:\s*["\']([a-z0-9][a-z0-9-]*)["\']')


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_annotations_block(text: str, label: str) -> str:
    """Extract the ANNOTATIONS export block. Exits on failure."""
    m = ANNOTATIONS_RE.search(text)
    if not m:
        print(f"  ❌ Could not find 'export const ANNOTATIONS' block in {label}", file=sys.stderr)
        sys.exit(1)
    return m.group(0)


def extract_ids(text: str) -> list[str]:
    """Return all annotation id values found in text, in order."""
    return ID_RE.findall(text)


def print_diff(source_ids: list[str], target_ids: list[str]):
    """Print a human-readable summary of annotation ID changes."""
    source_set = set(source_ids)
    target_set = set(target_ids)
    added   = source_set - target_set
    removed = target_set - source_set
    kept    = source_set & target_set

    print(f"\n  ℹ️   ANNOTATION DIFF")
    print(f"     Source (annotations_merged.ts) : {len(source_ids)} annotations")
    print(f"     Target (rbi_sibc.ts, current)  : {len(target_ids)} annotations")
    print(f"     Unchanged : {len(kept)}")

    if added:
        print(f"     Added ({len(added)}):")
        for a in sorted(added):
            print(f"       + {a}")
    if removed:
        print(f"     Removed ({len(removed)}):")
        for r in sorted(removed):
            print(f"       - {r}")
    if not added and not removed:
        print(f"     (annotation set is identical — only bodies/titles may differ)")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Promote annotations_merged.ts → web/lib/reports/rbi_sibc.ts"
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview the diff without writing any files")
    ap.add_argument("--force",   action="store_true",
                    help="Skip confirmation prompt when IDs change")
    args = ap.parse_args()

    print(f"\n  India Credit Lens — Promote Annotations (Stage 8)")
    print(f"  Source : {SOURCE_FILE.relative_to(REPO_ROOT)}")
    print(f"  Target : {TARGET_FILE.relative_to(REPO_ROOT)}")

    # ── Read source ───────────────────────────────────────────────────────────
    if not SOURCE_FILE.exists():
        print(f"\n  ❌ Source file not found: {SOURCE_FILE}", file=sys.stderr)
        print(f"     Run Stage 6 (Claude merged analysis) first.", file=sys.stderr)
        sys.exit(1)

    source_text = SOURCE_FILE.read_text()
    new_block   = extract_annotations_block(source_text, "annotations_merged.ts")
    source_ids  = extract_ids(new_block)

    if not source_ids:
        print(f"\n  ❌ No annotation IDs found in source — is the file complete?", file=sys.stderr)
        sys.exit(1)

    # ── Read target ───────────────────────────────────────────────────────────
    if not TARGET_FILE.exists():
        print(f"\n  ❌ Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    target_text  = TARGET_FILE.read_text()
    old_block    = extract_annotations_block(target_text, "rbi_sibc.ts")
    target_ids   = extract_ids(old_block)

    # ── Diff ──────────────────────────────────────────────────────────────────
    print_diff(source_ids, target_ids)

    if args.dry_run:
        print(f"  🔍 DRY RUN — no files written.")
        print(f"     Re-run without --dry-run to apply.\n")
        return

    # ── Confirm if IDs changed and not --force ────────────────────────────────
    source_set = set(source_ids)
    target_set = set(target_ids)
    ids_changed = source_set != target_set
    if ids_changed and not args.force:
        answer = input("  Annotation IDs will change. Proceed? [y/N]: ").strip().lower()
        if answer != "y":
            print(f"  Aborted — no files written.")
            sys.exit(0)

    # ── Replace ANNOTATIONS block in target ───────────────────────────────────
    new_target = ANNOTATIONS_RE.sub(new_block, target_text, count=1)

    if new_target == target_text:
        print(f"  ⚠️  No changes detected in rbi_sibc.ts (content may already be up to date).")
    else:
        TARGET_FILE.write_text(new_target)
        print(f"  ✅ Wrote {TARGET_FILE.relative_to(REPO_ROOT)}")

    # ── Verify: re-read and compare IDs ──────────────────────────────────────
    written_text   = TARGET_FILE.read_text()
    written_block  = extract_annotations_block(written_text, "rbi_sibc.ts (after write)")
    written_ids    = extract_ids(written_block)

    source_set  = set(source_ids)
    written_set = set(written_ids)

    if source_set != written_set:
        missing = source_set - written_set
        extra   = written_set - source_set
        print(f"\n  ❌ VERIFICATION FAILED — ID mismatch after write!", file=sys.stderr)
        if missing:
            print(f"     Missing from rbi_sibc.ts: {sorted(missing)}", file=sys.stderr)
        if extra:
            print(f"     Extra in rbi_sibc.ts:     {sorted(extra)}", file=sys.stderr)
        sys.exit(1)

    print(f"  ✅ Verification passed — {len(written_ids)} annotation IDs match source")
    print(f"\n  Next steps:")
    print(f"     python3 analysis/run_evals.py --period merged --merged")
    print(f"     (or omit --skip-build to also run tsc + npm run build)\n")


if __name__ == "__main__":
    main()
