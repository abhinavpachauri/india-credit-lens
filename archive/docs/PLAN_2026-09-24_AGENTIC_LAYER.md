# Agentic layer: design pass

> Status: DECIDED 2026-09-24; phases 0–2 BUILT the same day. This is the design record; the live plan is `PLAN.md`.
> Question asked: the architecture was written in March. Will it scale to ~22 sources with
> cross-connected insights, and is it time for native agentic workflows?

---

## 1. The answer in one paragraph

The **engine** scales. The manifest gate, compute modules keyed by shape, the registry and the
traceability gates all took a third pipeline (NBFC) without new plumbing. It stays deterministic
code, because its whole value is that an LLM never decides a number. What does not scale is the
**operating knowledge around the engine**: how to ingest, how to source a force, how to add a signal
family, and the failure patterns to check for. Today that lives in one 247 KB append-only notes file
plus three skills written in March that no longer match the code. So the agentic layer is a
**procedure, review and enforcement layer on top of the engine**, not a replacement for any of it.

```
            ┌──────────────────────────────────────────────────────────┐
  PROCEDURE │ skills: ingest-period · model-pass · s4-source · …        │  how work is done
            ├──────────────────────────────────────────────────────────┤
  REVIEW    │ subagents: population · absence · plausibility            │  independent cold eyes
            ├──────────────────────────────────────────────────────────┤
  ENFORCE   │ hooks + reconcile + pre-commit + llm_budget               │  what cannot be skipped
            ╞══════════════════════════════════════════════════════════╡
  ENGINE    │ gate.py · compute/ · registry · signals.db · validators   │  unchanged; deterministic
            └──────────────────────────────────────────────────────────┘
```

**The contract between the layers:** a skill never computes a number and never judges a gate as
"close enough". It runs the engine, and it is finished only when the gate is green. Judgment steps
(sourcing, spine picks, remap approval, paid-run approval) stop and ask the user.

---

## 2. What was measured

| Finding | Evidence |
|---|---|
| **About 75k tokens are loaded before any work starts** | `CLAUDE.local.md` 246,888 bytes (2,965 lines, 59 sections, of which about 50 are dated session logs) + `CLAUDE.md` 46,386 + `MEMORY.md` 10,484 = 304 KB. Most of it is history, not the current state. |
| **All 3 skills are stale** | `add-new-report` runs `analysis/run_evals.py` (retired 2026-06-25) 4 times and writes `subsystems.json` (retired). `merged-analysis` and `per-period-analysis` also produce `subsystems.json`. Last edited before the §4 cutover. |
| **The edit hook reports false failures** | `.claude/settings.json` PostToolUse → `hook_validate.py` → validates `system_model.json` with **`legacy/validate.py`** (the v2 validator). Reproduced today: an edit to the live v4 model prints `❌ FAILED — 371 error(s)`. Every model edit produces this noise, which teaches you to ignore the hook. |
| **The permission allowlist is stale** | 11 of the 12 `python3 analysis/...` entries point at files that no longer exist at that path (`analysis/run_evals.py`, `analysis/validate.py`, `analysis/generate_mermaid.py`, …). |
| **Nothing guards `.claude/`** | `reconcile.py` DOCS covers 15 living docs and none of `.claude/skills`, `.claude/agents` or `settings.json`. This is why the skills rotted without anything failing. It is the check-population pattern again. |
| **Workflows recur without a procedure** | 403 commits since March (58 feat, 46 docs, 36 refactor, 22 fix). The recurring shapes are counted in §3. |

---

## 3. Workflow inventory: what recurs, and where it should live

Recurrence is counted from git history and the session notes.

| # | Workflow | Recurrence | Lives today | Mechanism |
|---|---|---|---|---|
| W1 | **Ingest a period** (either pipeline) | monthly × 2–3 pipelines; May, Jun, Jul cycles, plus 2 backfills | runbook at the bottom of CLAUDE.local, stale skill | **skill** `ingest-period` |
| W2 | **L2a model pass** (UPDATE, or FOUNDATION in March) | every current-period ingest (standing rule) | memory `feedback_l2a_s4…`, stale `merged-analysis` | **skill** `model-pass` |
| W3 | **S4 sourcing via Chrome** (worklist → triage → search → resolve `--in-force`) | every ingest; 6+ sessions (Aug 23 – Sep 10) | ritual scattered over 5 session logs | **skill** `s4-source` |
| W4 | **Add a signal family / compute method** | ~10 (rotation, divergence, pair, movement ×3, scan_abs, share-of-credit, bank_scan_share, cadence) | re-derived each time | **skill** `add-signal-family` |
| W5 | **Onboard a new source** | 3 so far; ~19 to come | ARCHITECTURE §"Adding a pipeline" + PLAN_NBFC | **skill** `onboard-source` |
| W6 | **Measure a gate** (inject, catch rate, false rejection, log to ai_pm_register) | ~15 measurements; 4 probe bugs from missing controls | CLAUDE.md standing rule + habit | **skill** `measure-gate` |
| W7 | **Dashboard change** (ASCII → approval → build → verify at 1440/375 + gate) | ~20 UI commits | CLAUDE.md authoring rule | **skill** `dashboard-change` |
| W8 | **Close a session** (state, handoff, ai_pm log, memory) | every session | appended to CLAUDE.local by hand | **skill** `session-close` + restructure (§6) |
| W9 | **"Is this check covering the right set?"** | 5+ incidents (MOVEMENT_CUTS, SIBC_CUTS, freshness reading its own DB, 2e B6, the payments reachability test) | caught by luck or by you | **subagent** `population-auditor` |
| W10 | **"Can a failure look like a legitimate null?"** | 10+ incidents (S4 outage as `no_url`, empty ingest reporting success, refusal as a cache hit, …) | memory `feedback_failure_that_looks…` | **subagent** `absence-auditor` |
| W11 | **"Could that number be true?"** | ₹219 lakh crore unit bug, "₹137 of every ₹100", POS −15.8% was ICICI | caught by reading output | **subagent** `plausibility-auditor` |
| W12 | **Paid-run approval** (estimate, ask, `ICL_LLM_OK=1`, $5 cap) | every evaluate / S4 / narrative run | enforced in code (`llm_budget`) | **stays in code.** Skills call it; nothing new is needed |
| W13 | **Distribution slot / issue** | monthly while live; Substack paused | DISTRIBUTION_SPEC | **skill** `distribution-run`, deferred until distribution resumes |

Not proposed: refactor-with-golden (6 uses, but already well captured by the characterisation-test
pattern in the code), and a Vercel deploy skill (the plugin already ships one).

---

## 4. Skills catalogue

Every skill uses the same shape, so a skill is reviewable and testable:

```
---
name, description (when to trigger)
disable-model-invocation: true    ← for any skill that ingests, spends, sources or commits
---
Inputs          what the user supplies (xlsx path, pipeline id, period)
Preconditions   commands that must pass before starting (git clean, disk space, gate green)
Steps           engine commands only; every judgment step is marked  ⏸ ASK
Done when       a named gate result, not a feeling
Traps           the specific failure history of this workflow (short, linked to memory)
Record          what to write to STATE / ai_pm_register at the end
```

| Skill | Invocation | Replaces | Done when |
|---|---|---|---|
| `ingest-period` | user only: `/ingest-period {pipeline} {xlsx}` | `add-new-report`, the runbooks in CLAUDE.local | `gate.py --pipeline {p} --merged` passes all stages incl. build; dashboard verified in preview |
| `model-pass` | user only | `merged-analysis`, `per-period-analysis` | `validate_system_model` PASS; S3 + opportunities regenerated; mode (UPDATE/FOUNDATION) read from `timeline.is_fy_end`, never assumed |
| `s4-source` | user only | ritual in session logs | every proposal is `promoted`, `triaged` with a verdict, or recorded in `attempts[]`; `audit_force_sources` NOT ON PAGE = 0 |
| `add-signal-family` | model may suggest; user runs | nothing | spec entry in `signals/README` → registry → reconcile Check 5 → backfill **every** period → freshness green → a test that drives **every** branch (including the ones live data never reaches) → `categories.py` classified |
| `onboard-source` | user only | ARCHITECTURE §"Adding a pipeline" | manifest + skeleton profile + registry + sidecars; press-release ground truth gates the extractor; both existing gates still green (no-op proof) |
| `measure-gate` | model-invocable | the standing rule in CLAUDE.md | catch **and** false-rejection measured by enumerating (not sampling), with one known-good and one known-bad control run through the harness first; entry appended to `ai_pm_register` |
| `dashboard-change` | model-invocable | CLAUDE.md authoring rule | ASCII approved → tsc + build → preview at 1440 + 375, console clean, no horizontal scroll → gate |
| `session-close` | user only: `/session-close` | hand-appending to CLAUDE.local | STATE rewritten (not appended), journal entry written, ai_pm measurements logged, memory updated |

**Retire:** `per-period-analysis` (Stage 2 LLM authoring of per-period annotations). Nothing in the
live chain consumes its output since L1 annotations became generated. Retirement agreed (§8, Q3).

---

## 5. Reviewer subagents

These are cold, read-only reviewers. Each answers **one question** about a diff or a named check.
They start without the session's assumptions, and that is the point: every incident in W9–W11 was
missed by a session that had already convinced itself.

| Agent | The one question | Reads | Returns |
|---|---|---|---|
| `population-auditor` | "What set does this check iterate, where does that set come from, and can it come from the thing being checked or from a hand-written list sitting beside a derived one?" | the diff + the check's source | the population's source, whether it is derived or hand-kept, and any sibling set it should match |
| `absence-auditor` | "On each error path, does the output differ from a legitimate empty result?" | the diff | the paths where failure and null are indistinguishable, with the exact line |
| `plausibility-auditor` | "Could each published number be true?" (magnitude vs the book, share > 100% of a net, one entity dominating an aggregate) | rendered sidecars + signals.db | the numbers that fail a sanity band, with the reason |
| `data-inspector` (existing) | refresh its file list for v4; keep it | | |

A **`review-change`** skill (user-invoked, run before a commit) fans out to the three auditors in
parallel over `git diff` and merges their findings. Reviewers never edit files.

---

## 6. Knowledge restructure: the largest single win

**Rule (user, 2026-09-24): anything dated goes stale.** So there is **no journal** and **no dated
plans**. Each kind of knowledge gets exactly one home, and that home is either rewritten or
guarded, never appended to forever.

| Kind | New home | Lifetime rule | Loaded every session? |
|---|---|---|---|
| **Plan**: what we are doing and what is next | **one `PLAN.md`**, rewritten in place | finished items are deleted from it (git keeps them); the four dated `PLAN_*.md` + `REVIEW_2026-08-11.md` move to `archive/docs/` once harvested | pointer only |
| **State**: where the last session stopped | `CLAUDE.local.md`, **rewritten** each session, hard cap ~100 lines | overwritten, never appended | yes |
| **Decisions**: standing rules with a why | `DECISIONS.md` (committed) | each entry names a **revisit trigger**; an entry whose trigger has fired is re-decided or deleted | no; linked from CLAUDE.md and the skills |
| **Procedure**: how a workflow is run | the **skill** that owns it | guarded by reconcile (§7) | only when invoked |
| **History**: what happened | **git log** | commit messages here are already written as narrative ("seven tables were computed for nobody…"), so no second copy is kept | no |

**The one-time harvest.** Today's `CLAUDE.local.md` is gitignored, so it has no history behind it.
Before it is rewritten:
1. Extract only the **still-true standing decisions** into `DECISIONS.md`. The about 50 dated logs
   are not 50 decisions; most are status reports whose value was used up by the next session. The
   user reviews the extracted list, since that is the judgment step.
2. Extract **still-open items** into `PLAN.md`.
3. Freeze the rest once as `archive/session_notes_until_2026-09-24.md`, which is never loaded and
   never appended. This is a safety net, because the file is not in git; it is not a journal.

`CLAUDE.md` gets the same treatment. The 60-line "Current Platform State" table moves to
ARCHITECTURE.md (where it describes the system) and CLAUDE.md keeps the rules plus pointers.

**How they are always in front of a session (user asked, 2026-09-24).** `CLAUDE.md` is loaded
automatically in every session, including cloud sessions, because it is committed. It **imports**
both files with Claude Code's `@` syntax (`@PLAN.md`, `@DECISIONS.md`), so their text is loaded
too, not just linked. A plain link would depend on a session choosing to open the file.
Importing is only affordable because both files are **capped**: `PLAN.md` ≤ ~120 lines and
`DECISIONS.md` ≤ ~150 lines (about 3 lines per decision). `reconcile.py` fails the gate if either
file exceeds its cap or if either import target is missing. The cap is what stops them turning back
into the 247 KB file.

**Target: about 75k → under 20k tokens always loaded.**

## 7. Enforcement: keeping this layer from rotting like the last one

1. **`reconcile.py` covers `.claude/`.** Add `.claude/skills/*/SKILL.md` and `.claude/agents/*.md`
   to DOCS, and add a check that every `command` in `settings.json` hooks and every allowlisted
   `python3 analysis/...` path exists. On the first run this **fails on today's three stale skills
   and the stale allowlist**. That failure is intended, because it forces the rewrite rather than
   leaving it to memory.
2. **Fix the edit hook**: `system_model.json` → `core/validate_system_model.py`. This makes the hook
   honest again (0 false errors instead of 371).
3. **A skill's "Done when" must name a real gate stage.** Reconcile checks that the named command
   exists. This is cheap, and it stops a skill claiming a finish line the engine no longer has.
4. `llm_budget`, pre-commit freshness and the gates stay exactly as they are. Skills sit on top of
   them and cannot bypass them.

---

## 8. Decisions needed from you

| # | Question | My recommendation |
|---|---|---|
| Q1 | **Agreed**: commit `DECISIONS.md`. Should a trimmed STATE be committed too? This makes cloud and phone sessions viable (see the earlier cloud discussion). | **Commit `DECISIONS.md`**, since decisions are project knowledge. Keep STATE private in `CLAUDE.local.md` unless you want cloud sessions. |
| Q2 | Journal? | **Dropped** (user): git log is the history; one living `PLAN.md` replaces the dated plans (§6). |
| Q3 | Retire `per-period-analysis`? | **Agreed** (user): retire. |
| Q4 | **Agreed.** Which skills may Claude invoke on its own? | Only `measure-gate`, `dashboard-change` and `add-signal-family`. Anything that ingests, spends, sources or commits stays user-only. |

**Answers (user, 2026-09-24):** all four settled, as recorded in the table above. Context for Q3:
`per-period-analysis` last ran on 2026-05-02 (March 2026 data) and has not run for the five
periods since. The dashboard's 96 SIBC cards are generated every ingestion (signals → Stage 5
eval → Stage 5.5 → Check 2g). The 26 hand-written annotations in `rbi_sibc.ts` come from
`merged-analysis`, were last changed 2026-06-12, and nothing refreshes them; `model-pass` decides
whether to refresh them at FY-end FOUNDATION or retire them.

---

## 9. Build order

| Phase | Work | Size | Proves |
|---|---|---|---|
| **0** | Fix the hook, clean the allowlist, extend reconcile to `.claude/` (it will fail on the 3 skills, which is expected) | ~1 hour | the rot is now detected |
| **1** | Knowledge restructure (§6) | 1 session | always-loaded context under 20k; nothing lost (line accounting) |
| **2** | `ingest-period` + `model-pass` + `s4-source`; delete the 3 stale skills | 1 session | **used on August SIBC data (release ~30 Sep)**: a full cycle from skills with no re-derivation |
| **3** | The three auditors + `review-change` | 1 session | run against 2–3 past incident commits (e.g. `b906b1e`'s MOVEMENT_CUTS, the freshness-population fix); the auditors must find them cold |
| **4** | `onboard-source`, `add-signal-family`, `measure-gate`, `dashboard-change`, `session-close` | as each workflow next recurs | each skill is written while doing the real task, not in the abstract |

Phase 3's test deserves stress: **a reviewer earns its place only if it finds a known historical
defect without being told where it is.** That is the same enumerate-and-measure standard as every
other gate here, and it is loggable against AI PM topic #1.

## 10. Deliberately not doing

- **No multi-agent framework or orchestrator service.** The pipeline is sequential and gated;
  Claude Code + skills + `gate.py` already is the orchestrator.
- **No LLM in the compute path**, including "just to classify" steps. `planes.py` and
  `categories.py` stay deterministic and measured.
- **No plugin packaging yet.** It is worth doing only if the layer is reused outside this repo.
- **No big-bang rewrite.** Phases 0–2 pay off at the next ingestion. The rest arrives when its
  workflow next recurs.
