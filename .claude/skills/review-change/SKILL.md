---
name: review-change
description: Run the three independent reviewers (population, absence, plausibility) over the current change or a commit range, verify what they find, and report. Use before committing a change to a guard, a compute method, a formatter, an ingestion step or anything that publishes numbers.
disable-model-invocation: true
---

# Review a change with cold eyes

Three reviewer agents, each asking **one** question about the change, each starting without this
session's assumptions. That is the point: every defect they target was missed by a session that
had already convinced itself (`DECISIONS.md` → "A check's population…", "Make the unknown case
loud").

| Agent | The question |
|---|---|
| `population-auditor` | what set does each check iterate, and where does that set come from? |
| `absence-auditor` | can a failure produce the same output as a legitimate empty, zero, cached or OK result? |
| `plausibility-auditor` | could each published number be true (units, part vs whole, shares, signs)? |

**Inputs:** nothing (review the working tree against `HEAD`), or a commit range (`abc123..HEAD`).
**Done when:** every finding is verified by reading the code, and either fixed, or reported to the
user with the reason it stands.

## 1. Prepare the change (free, deterministic)

```bash
git diff HEAD > {scratchpad}/review.diff            # or: git diff {range} > …
git diff HEAD --name-only                           # the files in scope
```
Choose which reviewers apply. Run all three when unsure; they are cheap next to a missed defect.
- `population-auditor`: any guard, validator, test, gate stage, or code that iterates a collection.
- `absence-auditor`: any code with error handling, fallbacks, caches, retries, skips or success output.
- `plausibility-auditor`: any change to compute, units, formatting, sidecars or rendered text. Also run
  it after an ingest, on the new sidecars in `web/public/data/`.

## 2. Launch them in parallel, read-only

Give each agent: the diff path, the changed files, one or two neutral sentences on what the code
does, and **no hint of what might be wrong.** A reviewer told where to look is no longer a cold
check. The agents must not edit anything.

## 3. Verify before reporting

For every finding, open the file and line yourself and confirm it. Classify each one:
- **confirmed**: the scenario is real → fix it, or report it with a failing case;
- **by design**: the behaviour is intended and documented (e.g. a legitimately hand-written
  declaration) → say why in one line;
- **not reproducible**: drop it, and say so.

A reviewer's `NO FINDINGS` is a result, not a formality: report which reviewers came back clean.

## 4. Report

One table: reviewer · finding · file:line · verdict (confirmed / by design / not reproducible) ·
action. Findings the user must decide go last, with the decision named.

## Known limits (measured 2026-09-26, see `PLAN.md` phase 3)

- **Not fully cold.** Subagents load this project's `CLAUDE.md`, which imports `PLAN.md` and
  `DECISIONS.md`. A reviewer therefore knows every lesson written there, which helps on real work
  and invalidates it as a blind test: two of four acceptance catches were discounted for exactly
  this reason. A truly cold review runs outside the repo (`claude -p` from a scratch directory).
- They are one more pair of eyes, not a gate, and they miss things. Nothing here replaces a test
  that pins the fix.
- Their first real outing found a live defect: the freshness check still hand-listed two of three
  pipelines, so a deleted NBFC month passed as "fresh" (fixed 2026-09-26, negative-tested).
