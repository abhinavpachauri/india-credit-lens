---
name: onboard-source
description: Take a new data source (an RBI release, a MoSPI dataset, any official statistic) from "we should add this" to a gated pipeline whose numbers reach the dashboard. Use when the user asks to add, onboard or probe a new source or pipeline.
disable-model-invocation: true
---

# Onboard a source

Written 2026-10-05 from the two real onboardings: **NBFC** (a primary pipeline: own signals, own
page; `archive/docs/PLAN_2026-09-16_NBFC.md`) and **MoSPI** (a reference pipeline: no signals or
page of its own, joined to credit through a concordance; signals/README "MoSPI", COMPOSITION_SPEC
§24, DASHBOARD_SPEC §21). What a new pipeline inherits for free is in ARCHITECTURE.md
§"Adding a pipeline"; this skill is the order to do it in.

**Done when:** the new pipeline's gate (`python3 analysis/core/gate.py --pipeline {p}`) and every
dependent pipeline's gate pass, `python3 analysis/architecture/reconcile.py` shows no hard drift,
and each gate change made on the way has a measured catch rate in `ai_pm_register.json`.

The order matters: each step's check is what makes the next step's numbers trustworthy. Stop at
every ⏸ for the user. **A phase is a commit**; do not start the next with the last uncommitted.

## 0. Decide whether, and what kind (⏸ user)

- Run the Decision Filter (CLAUDE.md). Then place it in the source order (DECISIONS.md "Sources
  and roadmap"); a source jumping the queue is the user's call, recorded there.
- **Primary or reference?** Primary = its own signals, model and page (SIBC, payments, NBFC).
  Reference = it explains another pipeline's numbers and has no page (MoSPI). Most non-credit
  statistics are reference. The manifest declares `kind`, and loops pick pipelines by capability
  (`signal_pipelines()`, `model_pipelines()`), never by id.
- **Write the spec before any code**: what one release contains, the cadence of each VALUE
  (DECISIONS: cadence = how often the value can change), the release lag, what it does NOT
  measure. Then run the three reviewers (`/review-change`) on the spec. On MoSPI they changed
  output to a trailing year and found a 3.2-vs-14.83 unit error, before a line of code.

## 1. Probe the source as it really is

Read the source; never assume it. Every one of these was found by probing, not by the docs:
- **Find the publisher's own inventory first.** MoSPI's eSankhyiki catalogue
  (`api.mospi.gov.in/api/esankhyiki/cms/golden-sheet/list?product=…`) held the official IIP
  weights and the CPI annexes as Excel; we built on a transcription and hand-read PDFs before
  anyone looked. RBI: DBIE is the portal, the release page is the source.
- **Silent wrong answers.** MoSPI's WPI served the 2011-12 series with status 200 unless an
  undocumented `base_year` was passed; the IIP base changed to 2022-23 without the spec saying
  so. Check the BASE and the UNIT of what comes back, not just the status.
- **Free ground truth.** If the source prints its own growth rate (NBFC YoY columns, MoSPI's
  printed IIP growth), our computed value will be checked against it (stage 1c). Find it now.
- **Revisions.** Does a later release change earlier values? Provisional/final flags? This
  decides snapshot vs increment saving and whether it can be scheduled (MoSPI: by hand until two
  clean cycles, DECISIONS).
- Record findings in the spec's "as built" section as you go, not afterwards.

## 2. Manifest, fetch, saved releases

- `analysis/pipelines/{p}/pipeline.json`: `kind`, `order` (after everything it `depends_on`),
  paths, cadence and `expected_lag_days` per dataset, `period_key`. `test_manifest.py` holds kind
  and capabilities to each other.
- **Save every release as published**, never only the consolidated result; an unchanged fetch
  writes nothing. Releases merge in publication order, never fetch order.
- **A fetch contract that fails loudly.** Anything other than the expected shape raises
  (exactly one workbook, a declared field present, a page that is not the menu). Example: in Oct
  2026 MoSPI's list endpoint stopped filling `file_type`; the fetch failed instead of picking
  nothing (`analysis/pipelines/mospi/fetch.py`, `the_workbook`).
- **The release calendar**: a period past `period + lag + grace` and still missing fails the gate
  as overdue. An outage must never look like "not released yet".
- Hand-read sources (PDFs) get a reader that orders by layout and raises on anything else; the
  CPI press release changed layout three times in eight releases. Prefer the publisher's Excel.

## 3. Consolidate and gate the data

```bash
python3 analysis/core/gate.py --pipeline {p}
```
Stages to have before going on: integrity (one base, no gaps, unique keys, every declared field
present), the release calendar, and the printed-growth check (`analysis/pipelines/mospi/validate_published_growth.py`,
`analysis/pipelines/nbfc/validate_published_yoy.py` are the two examples). Measure the printed-growth
check by injection (a one-period shift on every series) before trusting it.

⏸ Show the user the first consolidated numbers next to the publisher's own headline.

## 4. The join (reference sources, or any cross-pipeline link)

- **One concordance file per (credit pipeline, reference pipeline)**:
  `analysis/ontology/concordance/{credit}__{reference}.json`. NBFC ↔ MoSPI is a file, not code.
- **Match = exact, or built from exact parts.** A broader shared group is `absent: shared_group`,
  not a match. Unmatched parts carry a STATIC reason from `core/absence.py`; never invent a match
  to raise coverage.
- **Weights cite an official table** (`sources` + `assign`). Verify them by rebuilding the
  published aggregate: MoSPI's own IIP weights rebuild manufacturing to 0.046 pt over 41 months;
  the transcription we first used missed by ~1 pt.
- **Which cuts must be covered** is declared by the credit pipeline's manifest
  (`reference_cuts.{reference}`: include / exclude with a `why`).
- `python3 analysis/cross/validate_concordance.py` runs in BOTH gates: a renamed credit code
  breaks the join as surely as a MoSPI change.
- ⏸ Every judgment (a proxy deflator, a mapping choice) is listed as an open decision in PLAN
  and absent until the user decides.

## 5. Signals

- New methods dispatch only from `METHODS`; a registry entry naming a method that is not there
  raises. Errors that mean "outage" re-raise through the engine's catch-all (`ParentNotFound`,
  `ReferenceMissing` in `signals/compute/real_economy.py`).
- **Every row holds this period's value or a reason code, never an earlier period's value.** A
  quarterly value stores at quarter-ends only. Per-period reasons are a closed list in
  `core/absence.py`; adding one is a user decision (e.g. `reference_history_gap`, 2026-10-03).
- Pin the main formula with a unit test using the spec's own worked example.
- Append **every** declared period, then check:
```bash
python3 analysis/core/generate_signal_history.py append --pipeline {p} --period {period}   # each period
python3 analysis/guards/check_signal_freshness.py --pipeline {p}
```
  If the store gains fields (`reason`, `operands`), freshness must compare them and must count
  rows per part, or a part that emits nothing on both sides passes.

## 6. On the dashboard

- **ASCII layout first, with the live numbers, and approval** (CLAUDE.md). `x.x%` placeholders hide
  the readings that need explaining (petroleum −17.1% real was a 38.5% fuel-price jump).
- A table column is declared once in `analysis/core/table_columns.py`, then
  `python3 analysis/core/table_columns.py --write` regenerates `web/lib/table_columns.ts`.
- Cells are rendered in Python (`analysis/signals/stamp_table.py`); an empty cell is "—" with a
  reason and a sentence, and a column a cut can never fill is not drawn.
- Extend `analysis/guards/validate_cut_table.py` for the new cells and measure it by injection.
- Check the page in the preview at 1440 and 375: console clean, no page-level horizontal scroll.

## 7. Primary pipelines only: the model

A primary source also gets a deterministic skeleton and a FOUNDATION pass when there is enough
history (`python3 analysis/core/generate_skeleton.py --pipeline {p}`,
`python3 analysis/core/validate_system_model.py --pipeline {p}`). NBFC deferred its behavioral
layer until Layer 1 was reviewed; that is the default.

## Traps (each one happened)

- **A failure that returns the same value as a legitimate empty passes every gate.** Twelve
  payments signals once computed nothing and freshness stayed green because both sides were
  empty. Every new check states its population and where it comes from (DECISIONS).
- **A test that reads the live CSV** turns into a test of nothing when the data moves on ("IIP Aug
  absent" until MoSPI published it). Pin the state the test is about.
- **A tolerance built for prose is not a check for a stored value.** The table gate's ±0.5% let 6
  of 57 moved cells pass; cells compare exactly.
- **Measure before you gate, by enumeration.** Every gate change on MoSPI was injected over its
  whole population (2,440 rows, 368 groups, 857 cells), with a known-good control at 0 false.
  Long harnesses: one recompute saved to disk, then mutate in memory, then the real function.
- **Count what the new pipeline touched that was not its own** at the end (PLAN asks for it after
  NBFC); that number decides how generic the next one can be.

## Record

`/session-close`: the spec's "as built" notes, PLAN (phases ✅, open decisions), DECISIONS for any
user ruling, and the register entries. If this skill was wrong anywhere, fix it HERE in the same
session.
