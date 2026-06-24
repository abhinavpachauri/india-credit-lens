#!/usr/bin/env python3
"""
core/gate.py — the ONE manifest-driven gate runner (replaces run_evals + run_atm_pos_evals)
------------------------------------------------------------------------------------------
Reads a per-pipeline manifest (pipelines/{id}/pipeline.json) and executes its declared,
ordered stage list. Each stage targets a generic `core.*` engine, a per-pipeline
`pipeline.*` module, or a `builtin` (pytest/web_build/csv_integrity). The manifest is the
ONLY place the gate sequence is declared; this file holds no pipeline-specific logic and
never inspects the pipeline id (see analysis/core/MANIFEST_DESIGN.md).

Status: P3 increment 1 — runs alongside the legacy gates for parity verification before the
P1/P2 file moves. CORE_MAP resolves logical names to the CURRENT (pre-move) script paths;
at move-time only CORE_MAP + each manifest's `modules` map change.

Usage:
    python3 analysis/core/gate.py --pipeline sibc --merged --skip-build
    python3 analysis/core/gate.py --pipeline atm_pos --period 2026-04-30
"""
import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT, ANALYSIS  # noqa: E402

WEB = ROOT / "web"
DB = ANALYSIS / "signals" / "signals.db"

GREEN, RED, YELLOW, BOLD, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[0m"

# Logical core-engine name → (script relative to ANALYSIS, default args, cwd).
# $VARS are substituted at run time. Pre-move these point at analysis/*.py; post-move
# this single map repoints to core/*.py — the manifests stay unchanged.
CORE_MAP = {
    "validate_timeline":        ("validate_timeline.py", ["--path", "$TIMELINE"], "ANALYSIS"),
    "validate_signal_history":  ("validate_signal_history.py", [], "ROOT"),
    "check_signal_freshness":   ("check_signal_freshness.py", ["--pipeline", "$ID"], "ROOT"),
    "skeleton":                 ("core/generate_skeleton.py", ["--pipeline", "$ID"], "ROOT"),
    "validate_system_model":    ("core/validate_system_model.py", ["--pipeline", "$ID"], "ANALYSIS"),
    "system_state":             ("core/generate_system_state.py", ["--pipeline", "$ID", "--period", "$LATEST"], "ROOT"),
    "derive_opportunities":     ("core/derive_opportunities.py", ["--pipeline", "$ID", "--period", "$LATEST"], "ROOT"),
    "compose_ecosystem":        ("compose_ecosystem.py", [], "ROOT"),
    "opportunities_feed":       ("generate_opportunities_feed.py", [], "ROOT"),
    "opportunity_traceability": ("validate_opportunity_traceability.py", ["--strict"], "ROOT"),
    "chart_series":             ("core/generate_chart_series.py", ["--pipeline", "$ID"], "ROOT"),
}


def latest_period(pipeline):
    if not DB.exists():
        return None
    con = sqlite3.connect(DB)
    row = con.execute("select max(period) from signals where pipeline=?", (pipeline,)).fetchone()
    con.close()
    return row[0] if row else None


def subst(args, vars_):
    out = []
    for a in args:
        for k, v in vars_.items():
            a = a.replace(k, str(v))
        out.append(a)
    return out


def run_cmd(cmd, cwd):
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
        return p.returncode == 0, p.stdout, p.stderr
    except FileNotFoundError as e:
        return False, "", f"Command not found: {e}"


def note_from(out, err, hint):
    text = (out + "\n" + err)
    if hint:
        for ln in text.splitlines():
            if hint in ln:
                return ln.strip().lstrip("✓✗⚠ ").strip()[:60]
    # Real content lines only — drop blanks and box-drawing separator banners.
    def _content(ln):
        s = ln.strip()
        return s and not all(c in "═─-=•· " for c in s)
    lines = [ln.strip() for ln in text.splitlines() if _content(ln)]
    # Prefer an explicit pass/summary line if present.
    for ln in reversed(lines):
        if any(t in ln for t in ("PASS", "PASSED", "✅", "passed", "wrote", "→")):
            return ln.lstrip("✓✗⚠ ").strip()[:60]
    return (lines[-1][:60] if lines else "")


# ── builtins ──────────────────────────────────────────────────────────────────

def builtin_pytest(manifest, vars_, flags):
    return run_cmd([sys.executable, "-m", "pytest", str(ANALYSIS / "tests"), "-q"], ROOT)


def builtin_web_build(manifest, vars_, flags):
    ok, o, e = run_cmd(["npx", "tsc", "--noEmit"], WEB)
    if not ok:
        return ok, o, e
    return run_cmd(["npm", "run", "build"], WEB)


def builtin_csv_integrity(manifest, vars_, flags):
    """Generic: CSV exists, non-empty, no duplicate periods on the schema date column."""
    import pandas as pd
    csv = ROOT / manifest["paths"]["consolidated_csv"]
    if not csv.exists():
        return False, "", f"missing {csv}"
    df = pd.read_csv(csv)
    col = manifest["schema"]["date_column"]
    dups = df[col].value_counts()
    nrows = len(df)
    return True, f"{nrows} rows, {df[col].nunique()} periods", ""


BUILTINS = {"pytest": builtin_pytest, "web_build": builtin_web_build,
            "csv_integrity": builtin_csv_integrity}


# ── stage resolution + execution ────────────────────────────────────────────────

def resolve(stage, manifest, vars_):
    """Return (cmd_list, cwd) for a script-backed stage, or (None, None) for builtins."""
    extra = subst(stage.get("args", []), vars_)
    if "core" in stage:
        script, dargs, cwdname = CORE_MAP[stage["core"]]
        cwd = ANALYSIS if cwdname == "ANALYSIS" else ROOT
        return [sys.executable, str(ANALYSIS / script)] + subst(dargs, vars_) + extra, cwd
    if "pipeline" in stage:
        script = manifest["modules"][stage["pipeline"]]
        return [sys.executable, str(ANALYSIS / script)] + extra, ROOT
    return None, None  # builtin


def should_skip(stage, flags, vars_, failed, stop):
    if stop:                       # global on_fail:stop — an earlier stage failed
        return "skipped (upstream failure)"
    cond = stage.get("skip_if")
    if cond == "merged" and flags.get("merged"):
        return "skipped (merged)"
    if cond == "revalidate" and flags.get("revalidate"):
        return "skipped (revalidate — period already extracted)"
    if cond == "--skip-build" and flags.get("skip_build"):
        return "skipped (--skip-build)"
    if cond and cond.startswith("missing:"):
        path = subst([cond[len("missing:"):]], vars_)[0]
        if not (ROOT / path).exists():
            return "skipped (file absent)"
    for req in stage.get("requires", []):
        if req in failed:
            return f"skipped (requires {req})"
    return None


def main():
    ap = argparse.ArgumentParser(description="Manifest-driven pipeline gate")
    ap.add_argument("--pipeline", required=True)
    ap.add_argument("--period")
    ap.add_argument("--merged", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    manifest = json.loads((ANALYSIS / "pipelines" / args.pipeline / "pipeline.json").read_text())
    flags = {"merged": args.merged, "skip_build": args.skip_build,
             "revalidate": bool(args.period)}
    latest = args.period or latest_period(args.pipeline)
    vars_ = {"$ID": args.pipeline, "$LATEST": latest or ""}
    # Every manifest path key becomes a $VAR (e.g. "sections_merged" → $SECTIONS_MERGED).
    for key, rel in manifest["paths"].items():
        vars_["$" + key.upper()] = str(ROOT / rel)

    print(f"\n  Gate: {manifest['name']}  (pipeline={args.pipeline}, "
          f"merged={args.merged}, period={latest})\n")

    stop_on_fail = manifest.get("on_fail") == "stop"
    results, failed = [], set()
    for stage in manifest["gate"]:
        sid, label = stage["id"], stage["label"]
        skip = should_skip(stage, flags, vars_, failed, stop_on_fail and bool(failed))
        if skip:
            results.append((label, None, skip))
            continue
        if "builtin" in stage:
            passed, out, err = BUILTINS[stage["builtin"]](manifest, vars_, flags)
        else:
            cmd, cwd = resolve(stage, manifest, vars_)
            passed, out, err = run_cmd(cmd, cwd)
        if not passed:
            failed.add(sid)
            print(out)
            print(err, file=sys.stderr)
        results.append((label, passed, note_from(out, err, stage.get("note", ""))))

    # summary
    print("\n" + "═" * 72)
    print(f"  {BOLD}Gate Summary — {manifest['name']}{RESET}")
    print("═" * 72)
    print(f"  {'Stage':<42} {'Status':<9} Notes")
    print("  " + "-" * 68)
    any_fail = False
    for label, passed, note in results:
        if passed is True:
            st = f"{GREEN}PASS{RESET}   "
        elif passed is None:
            st = f"{YELLOW}SKIP{RESET}   "
        else:
            st = f"{RED}FAIL{RESET}   "
            any_fail = True
        print(f"  {label:<42} {st}  {note}")
    print("═" * 72)
    if any_fail:
        print(f"  {RED}{BOLD}❌  ONE OR MORE STAGES FAILED{RESET}")
        return 1
    print(f"  {GREEN}{BOLD}✅  ALL STAGES PASSED{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
