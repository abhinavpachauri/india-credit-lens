"""No paid model call without explicit, per-run authorisation.

This is a mechanism rather than a rule because the rule kept failing: the same unapproved spend
recurred across sessions, since a promise lives in a conversation and the code did not know
about it. These tests pin the two properties that matter — every billing path is behind the
guard, and consent is never remembered.
"""
import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.llm_budget import (LLMSpendNotApproved, MAX_RUN_USD, approved,  # noqa: E402
                             estimate_usd, require_approval)


def test_unapproved_runs_refuse_and_say_what_they_would_have_spent(monkeypatch):
    monkeypatch.delenv("ICL_LLM_OK", raising=False)
    with pytest.raises(LLMSpendNotApproved) as e:
        require_approval("S4 source-finding", "up to 105", est_usd=1.26)
    msg = str(e.value)
    assert "up to 105" in msg, "the size is the thing being approved, so it must be shown"
    assert "$1.26" in msg, "and so is the price — size alone does not say cents or tens of dollars"
    assert "Nothing was billed" in msg


def test_approval_is_per_process_and_not_remembered(monkeypatch):
    monkeypatch.setenv("ICL_LLM_OK", "1")
    require_approval("x", 1, est_usd=0.10)
    monkeypatch.delenv("ICL_LLM_OK")
    assert approved() is False
    with pytest.raises(LLMSpendNotApproved):
        require_approval("x", 1, est_usd=0.10)


def test_every_billing_call_site_sits_behind_the_guard():
    """A property over the whole set, not a sample — the failure class this project keeps
    re-learning. Any module that constructs an Anthropic client or creates a message must import
    the guard; legacy/ is archived and out of the live path."""
    offenders = []
    for path in ROOT.rglob("*.py"):
        if "legacy" in path.parts or "tests" in path.parts or "archive" in path.parts:
            continue
        src = path.read_text(errors="ignore")
        bills = "client.messages.create" in src or "anthropic.Anthropic()" in src
        if not bills:
            continue
        # Parse, do not grep. evaluate.py carried its guard import INSIDE the module docstring
        # for months: the text "require_approval" was present, so a substring check passed, while
        # the name was never bound and the guard would have raised NameError instead of refusing.
        # A mention is not an import — so ask the AST whether it is really imported at module
        # level, which is the only form that binds the name for the call site below.
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        imported = any(
            isinstance(n, ast.ImportFrom) and n.module == "core.llm_budget"
            and any(a.name == "require_approval" for a in n.names)
            for n in ast.walk(tree))
        if not imported:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"paid call site with no IMPORTED budget guard: {offenders}"


def test_the_cli_refuses_cleanly_rather_than_crashing():
    env = {k: v for k, v in os.environ.items() if k != "ICL_LLM_OK"}
    r = subprocess.run(
        [sys.executable, str(ROOT / "core" / "run_inference.py"),
         "--verify-only", str(ROOT / "s4_proposals" / "2026-07-31.json")],
        capture_output=True, text=True, env=env, cwd=ROOT.parent)
    assert r.returncode == 1
    assert "not authorised" in r.stderr
    assert "Traceback" not in r.stderr, "a refusal is a decision point, not a crash"


def test_a_run_with_no_cost_estimate_is_refused_even_when_approved(monkeypatch):
    """Approval without an amount is a blank cheque.

    Setting ICL_LLM_OK says "yes to THIS run"; it cannot mean "yes to whatever this costs",
    because the amount is the thing actually being decided. So the missing-estimate refusal sits
    ahead of the approval check rather than behind it.
    """
    monkeypatch.setenv("ICL_LLM_OK", "1")
    with pytest.raises(LLMSpendNotApproved) as e:
        require_approval("Stage 5 signal evaluation", "1 per domain")
    assert "no cost estimate" in str(e.value)
    assert "Nothing was billed" in str(e.value)


def test_every_guarded_call_site_actually_prices_its_run():
    """The guard can only show a price if the caller computed one. A call site that passes no
    est_usd would refuse at runtime — a break discovered during a paid run, which is the worst
    moment. Pinned as a property over all live call sites, not a sample."""
    import re
    offenders = []
    for path in ROOT.rglob("*.py"):
        if {"legacy", "tests", "archive"} & set(path.parts):
            continue
        if path.name == "llm_budget.py":
            continue          # the guard defines the signature; it does not call it
        src = path.read_text(errors="ignore")
        for call in re.findall(r"require_approval\((?:[^()]|\([^()]*\))*\)", src):
            if "est_usd" not in call:
                offenders.append(f"{path.relative_to(ROOT)}: {' '.join(call.split())[:70]}")
    assert offenders == [], f"guarded call site with no cost estimate: {offenders}"


def test_the_estimate_uses_real_prices_and_scales_with_size():
    assert estimate_usd(1_000_000, "claude-sonnet-4-5-20250929") == pytest.approx(5.4, abs=0.01)
    assert estimate_usd(2_000) == pytest.approx(2 * estimate_usd(1_000))
    assert estimate_usd(1_000, "claude-opus-5") > estimate_usd(1_000, "claude-sonnet-5")


def test_a_run_above_the_ceiling_refuses_even_when_approved(monkeypatch):
    """The editor set a hard upper limit on any one run. Approval says "yes to this run"; it
    cannot mean "yes at any price", so the ceiling sits ahead of the approval check too."""
    monkeypatch.setenv("ICL_LLM_OK", "1")
    require_approval("small", 1, est_usd=MAX_RUN_USD - 0.01)          # under: proceeds
    with pytest.raises(LLMSpendNotApproved) as e:
        require_approval("huge", 9999, est_usd=MAX_RUN_USD + 0.01)
    assert "ceiling" in str(e.value) and "Nothing was billed" in str(e.value)


def test_the_ceiling_cannot_be_lifted_by_an_environment_variable(monkeypatch):
    """A limit you can raise from the shell is a suggestion. Raising it must be an edit to the
    module, reviewed like any other change."""
    monkeypatch.setenv("ICL_LLM_OK", "1")
    for var in ("MAX_RUN_USD", "ICL_MAX_RUN_USD", "ICL_LLM_MAX_USD"):
        monkeypatch.setenv(var, "1000")
    with pytest.raises(LLMSpendNotApproved):
        require_approval("huge", 1, est_usd=MAX_RUN_USD + 1)


# ── The CLI path (found live, Aug 2026 ingest, 2026-10-02) ────────────────────
# `claude -p` bills the subscription, not the API, and the property test above only looked for
# SDK calls, so evaluate's CLI path called the model with no approval while every test was green.
# Two halves: an INVENTORY of every module that shells out to `claude -p` (so a new one fails
# until it is driven below), and a BEHAVIOURAL check that each one refuses before any process
# starts when the run is not approved.

CLI_SITES = {"signals/evaluate.py", "core/run_inference.py", "cross/generate_opportunity_narrative.py"}


def _invokes_claude_cli(src: str) -> bool:
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.List) and len(n.elts) >= 2 and all(isinstance(e, ast.Constant) for e in n.elts[:2]):
            if [e.value for e in n.elts[:2]] == ["claude", "-p"]:
                return True
    return False


def test_every_module_that_shells_out_to_claude_is_driven_below():
    found = set()
    for path in ROOT.rglob("*.py"):
        if {"legacy", "tests", "archive"} & set(path.parts):
            continue
        if _invokes_claude_cli(path.read_text(errors="ignore")):
            found.add(str(path.relative_to(ROOT)))
    reachers = {"cross/generate_opportunity_narrative.py"}      # reuses evaluate._call_llm
    assert found | reachers == CLI_SITES, (
        f"`claude -p` call sites changed: {sorted(found)}. Add each to CLI_SITES and drive it below.")


def _no_subprocess(monkeypatch, module):
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(
        AssertionError(f"a process started before the guard: {a[0] if a else k}")))
    return calls


def test_evaluate_cli_path_refuses_before_calling_the_model(monkeypatch):
    from signals import evaluate as ev
    monkeypatch.delenv("ICL_LLM_OK", raising=False)
    monkeypatch.setattr(ev, "USE_CLI", True)
    monkeypatch.setitem(ev._EST, "usd", 0.10)
    _no_subprocess(monkeypatch, ev)
    with pytest.raises(LLMSpendNotApproved):
        ev._call_llm("system", "user")


def test_the_narrative_step_refuses_through_the_shared_path(monkeypatch):
    from signals import evaluate as ev
    from cross import generate_opportunity_narrative as gon
    monkeypatch.delenv("ICL_LLM_OK", raising=False)
    monkeypatch.setattr(ev, "USE_CLI", True)
    _no_subprocess(monkeypatch, ev)
    with pytest.raises(LLMSpendNotApproved):
        gon.call_claude({"x": 1})


def test_s4_generation_refuses_before_calling_the_model(monkeypatch):
    from core import run_inference as ri
    monkeypatch.delenv("ICL_LLM_OK", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _no_subprocess(monkeypatch, ri)
    with pytest.raises(LLMSpendNotApproved):
        ri.call_llm({"x": 1})


def test_every_claude_cli_call_pins_the_model():
    """Without --model the CLI uses the machine's default; on 2026-10-02 that was a retired model
    and every Stage 5 call failed. Each `claude -p` call names its model."""
    unpinned = []
    for path in ROOT.rglob("*.py"):
        if {"legacy", "tests", "archive"} & set(path.parts):
            continue
        for n in ast.walk(ast.parse(path.read_text(errors="ignore"))):
            if isinstance(n, ast.List) and len(n.elts) >= 2 and all(isinstance(e, ast.Constant) for e in n.elts[:2]) \
                    and [e.value for e in n.elts[:2]] == ["claude", "-p"]:
                if not any(isinstance(e, ast.Constant) and e.value == "--model" for e in n.elts):
                    unpinned.append(f"{path.relative_to(ROOT)}:{n.lineno}")
    assert not unpinned, f"`claude -p` without --model: {unpinned}"


def test_the_pinned_model_is_priced():
    from core.llm_budget import DEFAULT_MODEL, PRICING
    assert DEFAULT_MODEL in PRICING
