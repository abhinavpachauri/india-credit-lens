# India Credit Lens — Root Context

> Single source of truth for session startup. Keep short — detail lives in linked files.
> Strategy & revenue: `STRATEGY_PLANNER.md` | Pipeline detail: `PIPELINE_ARCHITECTURE.md` | System + status: `ARCHITECTURE.md`

---

## What This Is

India Credit Lens (`indiacreditlens.com`) turns Indian regulatory credit reports into
structured, executive-level insights for NBFCs, banks, fintechs, PE/VC funds.

**Differentiator:** Causal model layer — explains *why* credit moved, not just that it moved.
**Model:** Content ladder from free (LinkedIn/Substack) → paid (SaaS + consulting).

---

## Decision Filter

Before any feature, report, content, or technical decision:

1. Does it build expert positioning in the Indian lending ecosystem?
2. Does it attract CPOs, CROs, credit analysts, PE/VC at NBFCs/banks/fintechs?
3. Does it move toward a monetisable asset (consulting, CPO role, or SaaS subscriber)?

No to all three → deprioritise.

---

## Engineering Principle (non-negotiable) — Design for the long term

This platform is **multi-pipeline by design** (SIBC, ATM/POS, future sources) and that count only
grows. Every technical decision must scale to **multiple ingestion types and multiple pipelines** —
never optimise for the single case in front of you.

- **One generic mechanism per pipeline, not per-pipeline one-offs.** Both pipelines run the *same*
  scripts/validators/gates; alignment is by construction, not parallel hand-maintenance.
- **Compute once, ship compact.** Precompute artifacts at ingestion/build time; never make the
  browser parse raw consolidated data or re-derive series client-side.
- **Single source of truth.** No parallel copies that "agree today but could drift" — guard with a
  deterministic freshness/traceability check.
- Given "quick win vs proper fix", **default to the proper fix**; state it as the recommendation.
- Test every design against: *does this still hold at N pipelines / N ingestion types?*

---

## Where things are

Loaded below with every session: **`PLAN.md`** (what we are doing now and next) and
**`DECISIONS.md`** (standing decisions with their reasons). What each component is and its status,
plus the key-files index, are in **`ARCHITECTURE.md`** (read on demand). Pipeline stages are in
`PIPELINE_ARCHITECTURE.md`. How to run a workflow is in its skill (below).

@PLAN.md

@DECISIONS.md

---

## CLI Tools

Use CLI tools for all external service interactions — they are the most context-efficient approach (one line of output vs loading API JSON).

### External services

| Tool | Use for |
|---|---|
| `gh` | PRs, CI status, issues, release notes — never use GitHub web for anything scriptable |
| `vercel` | Domain management, deployment status, env vars |

### Pipeline gates (always use these — never run validators ad-hoc)

| Tool | Use for |
|---|---|
| `python3 analysis/core/gate.py --pipeline sibc` | SIBC gate — Stages 0–6 (data integrity + signal + model validation) |
| `python3 analysis/core/gate.py --pipeline atm_pos --xlsx {file}` | ATM/POS gate — Stages 0–3 + L1 signal append + build |
| `python3 analysis/pipelines/sibc/promote_annotations.py` | Stage 7: verified copy annotations_merged.ts → rbi_sibc.ts — never `cp` or manual paste |
| `python3 analysis/pipelines/sibc/detect_format.py` | Stage 0: flag format changes before extraction (SIBC) |
| ~~`python3 analysis/legacy/source_claims.py`~~ | **Legacy** — v2 claim sourcing; superseded by `validate_system_model.py` (sourcing built in). Detached from gate. |
| `python3 analysis/core/generate_skeleton.py --pipeline {sibc\|atm_pos}` | Stage 4-struct: regenerate the deterministic skeleton (preserves behavioral layer + force_instances). Runs inside both gates. |
| `python3 analysis/core/validate_system_model.py --pipeline {name}` | v4.0 model gate — structural + D1/D2/D3 discipline + force sourcing + URN/concept_tags. Replaces legacy checks 4/5/2c. |
| `python3 analysis/core/generate_system_state.py --pipeline {name} --period {date}` | S3: compute dynamic state from `signals.db` → `system_state_{period}.json`. |
| `python3 analysis/core/derive_opportunities.py --pipeline {name} --period {date}` | Derive live opportunity/risk status from S3 driver firing. |
| `python3 analysis/cross/derive_cross_links.py` · `compose_ecosystem.py` · `validate_composition.py` | Cross-system pass (Layer 2b): derive candidates → project ecosystem state → validate cross-edges. |
| `python3 analysis/cross/generate_opportunities_feed.py` then `generate_opportunity_narrative.py` | Presentation: build `opportunities_feed.json`, then add plain-English narrative (post-gate, cached). |
| `python3 analysis/core/generate_signal_history.py append --pipeline {name} --period {date}` | Stage 4: Layer 1 signal compute → writes to signals.db + updates registry |
| `python3 analysis/core/generate_signal_history.py evaluate --pipeline {name} --period {date}` | Stage 5: LLM signal evaluate → evaluations JSON; auto-loads prior period for narrative diff |
| `python3 analysis/core/generate_signal_history.py status` | Print current signal states across all pipelines |
| `python3 analysis/guards/validate_signal_history.py` | Check 2e: signal history integrity — DB rows, registry schema, status sync vs DB |
| `python3 analysis/guards/check_signal_freshness.py [--pipeline {name}]` | Check 2f/5b2: signals.db freshness — recompute every period from the CSV and fail on any drift (value/status/missing/orphan). Deterministic guard; runs in both gates + pre-commit. Fix = re-append **every** period, not just the latest. |
| `python3 analysis/distribution/issues/monthly_issue.py [--shortlist]` | Long-form Post 1 (merged monthly issue, both pipelines) — self-gating; run after the ingestion gate is green |
| `python3 analysis/distribution/issues/deep_read.py` | Long-form Post 2 (L2/L3 deep read) — self-gating; publish mid-cycle |
| `python3 analysis/measure_groundedness.py` | Measure any traceability gate by injection — catch rate + false-rejection rate |

---

## Authoring Rules (non-negotiable)

### Visual outputs
1. **ASCII layout first** — proportions, zones, text hierarchy
2. **Explicit approval** — no code until layout confirmed
3. **Then implement** — translate approved ASCII directly

### SIBC date normalisation (non-negotiable — read before any consolidation)

RBI publishes Statement 1 (Bank Credit / Food Credit / Non-food Credit) as a fortnightly
release — always a Friday, which can fall in the first week of the **following** month.
That publication date must be remapped to the **prior** month-end. Two rules are hard-coded
in `update_web_data.py`; specific edge cases live in `{period}/date_overrides.json`.

| Published on | Maps to | Why |
|---|---|---|
| Apr 1–7 | Mar 31 | Post-FY-end Bank Credit release — Apr 4–5 = March data |
| May 1–7 | Apr 30 | Post-April Bank Credit release — May 2–3 = April data |
| Mar 1–7 | Feb 28/29 | Early-March Bank Credit = February data — captured in `date_overrides.json` for the period |
| Any other date | Last day of same month | Mid-month sector snapshot → month-end |

**The remapping is gated in code, not by habit (2026-08-11).** It used to be a rule in this
document with nothing enforcing it — `update_web_data.py` printed the table and wrote the CSV
regardless. Now `--check` recomputes the remapping and fails if it differs from the approved
record in `analysis/rbi_sibc/date_remap.json`, whether a date MOVED or a raw date appeared that
nobody has classified. It runs as gate stage **1a**, before CSV integrity.

To approve a new or changed remap: review the table, then
`python3 analysis/pipelines/sibc/update_web_data.py --approve` (it asks first). A remap decides
which *month* a number belongs to — get it wrong and the data is misdated rather than broken,
so nothing downstream notices.

When a new XLSX introduces dates not covered by the rules above, ask the user to classify
each raw date before proceeding. Document the decision in `{period}/date_overrides.json`
if it is a semantic correction (early-month = prior-month data); the normalization rule
handles formatting-only cases automatically.

### Analysis outputs
- `annotation_ids` in `system_model.json` must **exactly match** `id` fields in the annotations file. Copy-paste — never retype.
- **Annotation IDs are permanent.** Once an `id` exists in `annotations_merged.ts`, it is never renamed or deleted — even across FOUNDATION rebuilds. UPDATE mode only adds. FOUNDATION mode may restructure, but any removed ID requires explicit justification after `promote_annotations.py --dry-run`.
- **Layer 2a model has two modes; `/model-pass` reads which one from `timeline.json`.** FY-end (March file) = FOUNDATION. All other months = UPDATE. Wrong mode = wrong depth of analysis. Signal evaluation (Stage 5) runs every period regardless of mode.
- Stage 7 always uses `promote_annotations.py` — never manual copy.

### API spend (non-negotiable)

**Never make a paid model call without explicit approval in the current conversation.** Not
"the user approved something similar last session", not "this run is cheap", not "it is part of
the agreed plan". Ask, name the size, wait.

This is enforced in code, because the rule alone kept failing across sessions:
`analysis/core/llm_budget.require_approval` gates every billing path and refuses unless
`ICL_LLM_OK=1` is set **for that invocation**. Consent is per-process by design — "you said yes
last week" is exactly the reasoning that caused the problem. `test_llm_budget.py` asserts the
property over every module, so a new paid call site cannot skip it.

Which work is paid: Stage 5 `evaluate`, S4 proposal generation, S4 `--verify-api` source-hunt,
`generate_opportunity_narrative`. Everything else — computes, gates, validators, the Chrome
sourcing path (`--worklist` / `--resolve`) — costs nothing and needs no approval.

**Prefer the free channel.** Source verification runs through the editor's browser: only 19 of
47 allowlisted hosts are readable by an automated fetch, so the API hunt is opportunistic, not
the default (COMPOSITION_SPEC §8.1).

### Git / deployment
- **Solo project — work directly on `main`. Never create feature branches or worktrees.**
- Never auto-push to GitHub
- Always run `python3 analysis/core/gate.py --pipeline sibc` (includes `npm run build`) before `git push`
- Show results and wait for explicit confirmation

---

## Skills — procedures, loaded on demand (`.claude/skills/`)

| Skill | Use for | Who starts it |
|---|---|---|
| `/ingest-period` | a new XLSX, any pipeline, through the gate to a verified dashboard | user |
| `/model-pass` | the Layer 2a UPDATE (or March FOUNDATION) pass after a current-period ingest | user |
| `/s4-source` | S4 proposals → triage → Chrome sourcing → promote only verified forces | user |
| `/session-close` | end of session: rewrite `CLAUDE.local.md` + `PLAN.md`, log measurements | user |

A skill runs engine commands only and is finished only when its named gate passes. Skills are
guarded by `reconcile.py` Check 6: a skill that names a missing or retired script fails the gate.

Distribution: `python3 analysis/distribution/generate_slot.py --slot {1st|7th|14th|21st|28th}`
(spec `analysis/distribution/DISTRIBUTION_SPEC.md`); long-form in `analysis/distribution/issues/`
(see `analysis/distribution/NEWSLETTER_CONTEXT.md`). Substack is paused.

Use a subagent (`data-inspector`) to explore data files — keeps main context clean.

---

## Compaction Instructions

When compacting, always preserve:
- Current pipeline stage (e.g. "Stage 3, per-period 2026-03-30, evals failing on Check 4")
- Period directory being worked on
- Any unresolved eval errors and which check they came from
- File paths of outputs written this session

## Session state (CLAUDE.local.md)

`CLAUDE.local.md` (git-ignored) holds only where the last session stopped. It is **rewritten, not
appended**, capped at 120 lines by `reconcile.py`; `/session-close` does it. Anything a cloud session
must know goes in `PLAN.md` instead.
