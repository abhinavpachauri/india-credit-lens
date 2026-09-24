#!/usr/bin/env python3
"""reconcile Checks 6 + 7 — the agent layer and the always-loaded context.

By 2026-09-24 all three project skills ran scripts retired three months earlier, the edit hook
validated v4 models with the v2 validator, and 11 of 12 allowlisted scripts were gone. None of
it failed anything: the skills lived in a gitignored .claude/ that nothing read, and the doc
check matched scripts by BASENAME — every retired script still exists in legacy/, so
`analysis/run_evals.py` passed. Meanwhile CLAUDE.local.md had grown to 2,965 lines by being
appended to.

Pinned here:
  1. a procedure naming a script at a path it does not live at fails;
  2. a procedure RUNNING a retired script fails, while a doc merely MENTIONING one does not;
  3. the settings allowlist and hook commands are held to the same rule;
  4. CLAUDE.md must import the plan and the decisions, and those stay under their caps;
  5. the live repo passes (so the synthetic checks above are not the only thing asserted).

Run: python3 -m pytest analysis/tests/test_reconcile_agent_layer.py -q
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "architecture"))

import reconcile  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "analysis" / "core").mkdir(parents=True)
    (tmp_path / "analysis" / "legacy").mkdir(parents=True)
    (tmp_path / "analysis" / "core" / "gate.py").write_text("")
    (tmp_path / "analysis" / "legacy" / "run_evals.py").write_text("")
    (tmp_path / ".claude" / "skills" / "demo").mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text("# root\n\n@PLAN.md\n\n@DECISIONS.md\n")
    (tmp_path / "PLAN.md").write_text("# plan\n")
    (tmp_path / "DECISIONS.md").write_text("# decisions\n")
    monkeypatch.setattr(reconcile, "ROOT", tmp_path)
    monkeypatch.setattr(reconcile, "SETTINGS", tmp_path / ".claude" / "settings.json")
    monkeypatch.setattr(reconcile, "DOCS", ["CLAUDE.md"])
    return tmp_path


def _skill(repo, text):
    (repo / ".claude" / "skills" / "demo" / "SKILL.md").write_text(text)


def test_skill_naming_a_moved_script_fails(repo):
    _skill(repo, "python3 analysis/run_evals.py --merged")
    [f] = reconcile.check_agent_layer()
    assert "analysis/run_evals.py" in f and "does not exist" in f


def test_skill_running_a_retired_script_fails_even_though_the_file_exists(repo):
    _skill(repo, "python3 analysis/legacy/run_evals.py")
    [f] = reconcile.check_agent_layer()
    assert "retired" in f


def test_skill_naming_a_live_script_passes(repo):
    _skill(repo, "python3 analysis/core/gate.py --pipeline sibc")
    assert reconcile.check_agent_layer() == []


def test_a_doc_may_mention_a_retired_script(repo):
    (repo / "CLAUDE.md").write_text("@PLAN.md\n@DECISIONS.md\narchived: analysis/legacy/run_evals.py\n")
    assert reconcile.check_agent_layer() == []


def test_settings_allowlist_and_hooks_are_checked(repo):
    reconcile.SETTINGS.write_text(json.dumps({
        "hooks": {"PostToolUse": [{"hooks": [{"command": "python3 analysis/hook_gone.py"}]}]},
        "permissions": {"allow": ["Bash(python3 analysis/validate.py*)"]},
    }))
    found = reconcile.check_agent_layer()
    assert len(found) == 2 and all(".claude/settings.json" in f for f in found)


def test_missing_import_fails(repo):
    (repo / "CLAUDE.md").write_text("@PLAN.md\n")
    assert reconcile.check_context_budget() == ["CLAUDE.md does not import @DECISIONS.md"]


def test_over_cap_fails_and_names_the_cap(repo):
    (repo / "PLAN.md").write_text("x\n" * (reconcile.LINE_CAPS["PLAN.md"] + 1))
    [f] = reconcile.check_context_budget()
    assert f.startswith("PLAN.md:") and "cap is" in f


def test_the_live_repo_passes():
    assert reconcile.check_agent_layer() == []
    assert reconcile.check_context_budget() == []
