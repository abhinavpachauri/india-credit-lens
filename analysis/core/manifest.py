#!/usr/bin/env python3
"""
core/manifest.py — the pipeline manifest, read once and understood in one place
------------------------------------------------------------------------------
A pipeline declares its gate as data (`pipelines/{id}/pipeline.json`). Two callers need
to understand that data:

  * `core/gate.py`      — runs every stage, in order, and reports a verdict.
  * `guards/check_derived_fresh.py` — re-runs only the stages that *regenerate committed
                          artifacts*, then checks nothing drifted.

Before this module the second caller kept its own hand-written copy of both lists — which
script to run, and which artifacts to watch. That copy silently fell behind: the dashboard
`planes` sidecars were added to it, but `sibc_l1_annotations.json` and `atm_pos_insights.json`
— the two largest artifacts the gate writes — never were, so nothing guarded their freshness.

The fix is structural rather than a longer list. A stage that writes committed artifacts
declares them itself:

    { "id": "insights", "pipeline": "insights", "derived": ["web/public/data/…json"] }

`derived` means two things at once, which is the point: *this stage regenerates those paths*,
and *those paths must be fresh at commit time*. Add a pipeline, declare its stages once, and
both the gate and the freshness guard learn about it together. Nothing here inspects a
pipeline id.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from core.paths import ROOT, ANALYSIS

# Logical core-engine name → (script relative to ANALYSIS, default args, cwd).
# The manifests name engines logically; this is the only place those names meet a path,
# so relocating an engine is a one-line change here.
CORE_MAP = {
    "validate_timeline":        ("core/validate_timeline.py", ["--path", "$TIMELINE"], "ANALYSIS"),
    "validate_signal_history":  ("guards/validate_signal_history.py", [], "ROOT"),
    "check_signal_freshness":   ("guards/check_signal_freshness.py", ["--pipeline", "$ID"], "ROOT"),
    "skeleton":                 ("core/generate_skeleton.py", ["--pipeline", "$ID"], "ROOT"),
    "validate_system_model":    ("core/validate_system_model.py", ["--pipeline", "$ID"], "ANALYSIS"),
    "system_state":             ("core/generate_system_state.py", ["--pipeline", "$ID", "--period", "$LATEST"], "ROOT"),
    "derive_opportunities":     ("core/derive_opportunities.py", ["--pipeline", "$ID", "--period", "$LATEST"], "ROOT"),
    "validate_composition":     ("cross/validate_composition.py", [], "ROOT"),
    "compose_ecosystem":        ("cross/compose_ecosystem.py", [], "ROOT"),
    "derive_cross_links":       ("cross/derive_cross_links.py", [], "ROOT"),
    "opportunities_feed":       ("cross/generate_opportunities_feed.py", [], "ROOT"),
    "opportunity_traceability": ("core/validate_opportunity_traceability.py", ["--strict"], "ROOT"),
    "chart_series":             ("core/generate_chart_series.py", ["--pipeline", "$ID"], "ROOT"),
    "stamp_planes":             ("signals/stamp_planes.py", ["--pipeline", "$ID"], "ROOT"),
    "card_cuts":                ("guards/validate_card_cuts.py", ["--pipeline", "$ID", "--strict"], "ROOT"),
    "card_prose":               ("guards/validate_card_prose.py", ["--pipeline", "$ID", "--strict"], "ROOT"),
    "architecture_discover":    ("architecture/discover.py", ["--quiet"], "ROOT"),
    "architecture_render":      ("architecture/render.py", [], "ROOT"),
    "reconcile":                ("architecture/reconcile.py", ["--strict"], "ROOT"),
}

PIPELINE_IDS = ("sibc", "atm_pos")


def load(pipeline: str) -> dict:
    """The manifest for one pipeline."""
    return json.loads((ANALYSIS / "pipelines" / pipeline / "pipeline.json").read_text())


def subst(args, vars_):
    """Replace every $VAR in an argument list. Manifests are data, so they carry
    placeholders rather than resolved paths."""
    out = []
    for a in args:
        for k, v in vars_.items():
            a = a.replace(k, str(v))
        out.append(a)
    return out


def resolve(stage, manifest, vars_, flags=None):
    """Return (cmd_list, cwd) for a script-backed stage, or (None, None) for a builtin.

    A stage may carry mode-variant args: `args_merged` is used in merged mode (when present),
    else `args`. This lets one manifest entry serve both the merged and per-period gates
    (e.g. SIBC sections: merged validates sections_merged.json --merged; per-period validates
    {period}/sections.json) without the gate inspecting the pipeline id.
    """
    flags = flags or {}
    raw_args = stage["args_merged"] if (flags.get("merged") and "args_merged" in stage) \
        else stage.get("args", [])
    extra = subst(raw_args, vars_)
    if "core" in stage:
        script, dargs, cwdname = CORE_MAP[stage["core"]]
        cwd = ANALYSIS if cwdname == "ANALYSIS" else ROOT
        return [sys.executable, str(ANALYSIS / script)] + subst(dargs, vars_) + extra, cwd
    if "pipeline" in stage:
        script = manifest["modules"][stage["pipeline"]]
        return [sys.executable, str(ANALYSIS / script)] + extra, ROOT
    return None, None  # builtin


def path(pipeline: str, key: str) -> Path:
    """A declared path for a pipeline, absolute.

    The manifest has always carried these — `consolidated_csv`, `timeline`, `system_model` — and
    almost nobody read them. Six live modules hardcoded the consolidated CSV instead, which meant
    the declaration was decorative and moving the file was a six-file edit. Read it from here and
    the manifest becomes the single place a path is decided.
    """
    return ROOT / load(pipeline)["paths"][key]


def consolidated_csv(pipeline: str) -> Path:
    """The pipeline's consolidated CSV — the source every Layer-1 signal is computed from."""
    return path(pipeline, "consolidated_csv")


def regenerating_stages(manifest) -> list[dict]:
    """The stages that rewrite committed artifacts — those declaring `derived`.

    Manifest order is preserved because it is dependency order: a skeleton precedes the
    state computed from it, which precedes the opportunities derived from that.
    """
    return [s for s in manifest["gate"] if s.get("derived")]


def derived_globs(pipeline: str | None = None) -> list[str]:
    """Every committed artifact declared by a stage, across all pipelines (or one).

    Repo-relative globs, de-duplicated with order preserved — the cross-source artifacts
    are declared by both pipelines because both regenerate them.
    """
    seen: dict[str, None] = {}
    for pid in ([pipeline] if pipeline else PIPELINE_IDS):
        for stage in regenerating_stages(load(pid)):
            for g in stage["derived"]:
                seen.setdefault(g, None)
    return list(seen)
