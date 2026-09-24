---
name: session-close
description: Close a working session — rewrite CLAUDE.local.md to current state, update PLAN.md and DECISIONS.md in place, log measurements, and run reconcile. Use when the user says to close, wrap up or hand off a session.
disable-model-invocation: true
---

# Close a session

**Done when:** `python3 analysis/architecture/reconcile.py --strict` passes. That run includes
the line caps on `PLAN.md` (120), `DECISIONS.md` (150) and `CLAUDE.local.md` (120), and checks
that every script path named in them exists.

The rule: **rewrite, never append.** git log is the history; commit messages carry the narrative.

## 1. `CLAUDE.local.md`: where this session stopped (≤ 120 lines, overwrite it)

- What is uncommitted or unpushed, and why.
- The exact next step, with the command.
- Anything half-done that a fresh session would otherwise redo or break.

Nothing else. No history, no "what we learned". Those belong in commit messages, `DECISIONS.md`
or a skill.

## 2. `PLAN.md`: edit in place

- **Delete** finished items (git has them). Mark in-flight items with their state.
- Add new next steps and open debts in priority order.
- Anything a cloud session must know goes here, not in `CLAUDE.local.md` (which is not committed).

## 3. `DECISIONS.md`: only if a decision was made

- A standing rule the user decided or confirmed, with **why** and a **revisit trigger**.
- If an existing entry changed, **edit that entry**; never add a second one that contradicts it.
- A status report is not a decision.

## 4. Procedure changes go into the skill

If a skill was wrong or incomplete this session (a missing step, a new trap), fix
`.claude/skills/{name}/SKILL.md` now, while the reason is fresh.

## 5. Measurements

If the session produced a number measuring the active AI PM topic (catch rate, false-rejection
rate, scope tightness), append it to `analysis/distribution/ai_pm_register.json`
`topics[].measurements[]` with a value AND a source file.

## 6. Verify and ⏸ commit

```bash
python3 analysis/architecture/reconcile.py --strict
git status --short
```
⏸ Commit only if the user asked for it. Never push without an explicit yes; before any push the
SIBC gate must pass including the build.
