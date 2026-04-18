#!/usr/bin/env python3
"""
hook_validate.py — India Credit Lens
--------------------------------------
PostToolUse hook: runs lightweight validation immediately after Claude writes
or edits a pipeline file, catching errors before they reach the eval gate.

Called by Claude Code hooks. Receives tool data on stdin as JSON:
  {"tool_name": "Write"|"Edit", "tool_input": {"file_path": "..."}, ...}

Runs the appropriate validator based on file type:
  annotations_*.ts or rbi_sibc.ts  → validate_annotations.py
  system_model.json                 → validate.py (structure only, no annotation cross-check)
  timeline.json                     → validate_timeline.py
  sections.json / sections_*.json   → validate_sections.py

Prints a one-line summary. Exits 0 on pass, 1 on error (Claude Code will surface this).
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS  = REPO_ROOT / "analysis"


def run(cmd, cwd=None):
    proc = subprocess.run(
        cmd, cwd=str(cwd or REPO_ROOT),
        capture_output=True, text=True
    )
    return proc.returncode, proc.stdout + proc.stderr


def one_liner(output: str) -> str:
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    for line in reversed(lines):
        if any(kw in line for kw in ["PASSED", "FAILED", "ERROR", "error", "✅", "❌"]):
            return line[:80]
    return lines[-1][:80] if lines else "(no output)"


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)  # Not a JSON event — ignore

    tool_name  = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    p = Path(file_path)
    name = p.name
    returncode = 0

    # ── Dispatch by file type ─────────────────────────────────────────────────

    if name.endswith(".ts") and ("annotation" in name or name == "rbi_sibc.ts"):
        if p.exists():
            rc, out = run([sys.executable, str(ANALYSIS / "validate_annotations.py"), str(p)])
            print(f"[hook:annotations] {one_liner(out)}")
            returncode = rc

    elif name == "system_model.json" and p.exists():
        # Structure-only check (no annotation cross-check — annotations may not exist yet)
        rc, out = run([sys.executable, str(ANALYSIS / "validate.py"), str(p)])
        print(f"[hook:system_model] {one_liner(out)}")
        returncode = rc

    elif name == "timeline.json" and p.exists():
        rc, out = run([sys.executable, str(ANALYSIS / "validate_timeline.py"), "--path", str(p)])
        print(f"[hook:timeline] {one_liner(out)}")
        returncode = rc

    elif (name == "sections.json" or name == "sections_merged.json") and p.exists():
        cmd = [sys.executable, str(ANALYSIS / "validate_sections.py"), str(p)]
        if name == "sections_merged.json":
            cmd.append("--merged")
        rc, out = run(cmd)
        print(f"[hook:sections] {one_liner(out)}")
        returncode = rc

    else:
        sys.exit(0)  # File type not covered — skip silently

    sys.exit(returncode)


if __name__ == "__main__":
    main()
