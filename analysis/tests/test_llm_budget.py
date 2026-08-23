"""No paid model call without explicit, per-run authorisation.

This is a mechanism rather than a rule because the rule kept failing: the same unapproved spend
recurred across sessions, since a promise lives in a conversation and the code did not know
about it. These tests pin the two properties that matter — every billing path is behind the
guard, and consent is never remembered.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.llm_budget import LLMSpendNotApproved, approved, require_approval  # noqa: E402


def test_unapproved_runs_refuse_and_say_what_they_would_have_spent(monkeypatch):
    monkeypatch.delenv("ICL_LLM_OK", raising=False)
    with pytest.raises(LLMSpendNotApproved) as e:
        require_approval("S4 source-finding", "up to 105")
    msg = str(e.value)
    assert "up to 105" in msg, "the size is the thing being approved, so it must be shown"
    assert "Nothing was billed" in msg


def test_approval_is_per_process_and_not_remembered(monkeypatch):
    monkeypatch.setenv("ICL_LLM_OK", "1")
    require_approval("x", 1)
    monkeypatch.delenv("ICL_LLM_OK")
    assert approved() is False
    with pytest.raises(LLMSpendNotApproved):
        require_approval("x", 1)


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
        if bills and "require_approval" not in src:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"paid call site with no budget guard: {offenders}"


def test_the_cli_refuses_cleanly_rather_than_crashing():
    env = {k: v for k, v in os.environ.items() if k != "ICL_LLM_OK"}
    r = subprocess.run(
        [sys.executable, str(ROOT / "core" / "run_inference.py"),
         "--verify-only", str(ROOT / "s4_proposals" / "2026-07-31.json")],
        capture_output=True, text=True, env=env, cwd=ROOT.parent)
    assert r.returncode == 1
    assert "not authorised" in r.stderr
    assert "Traceback" not in r.stderr, "a refusal is a decision point, not a crash"
