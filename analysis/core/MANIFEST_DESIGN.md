# P3 Design — manifest-driven gate (`pipeline.json` + `core/gate.py`)

> Status: **DESIGN (for review)** — no code yet. This is the §4 P3 target: converge the
> copy-per-pipeline ingestion/gate/insight layer onto **one generic gate runner + a
> per-pipeline manifest**, so adding source #3 is *config + a thin extractor*, not 10
> copied scripts. Design-before-move: P1/P2 (the file relocations) implement toward this.

## The bar this must clear

The litmus test for "acceptable" (the engineering principle): **a new source is added as
`pipelines/{x}/pipeline.json` + a thin `extract.py`, with zero new top-level scripts and
zero edits to `core/` or `gate.py`.** If adding a source forces an `if pipeline == "x"`
anywhere in the generic layer, the design has failed — it just relocated the one-off.

## What actually differs between the two pipelines (the evidence)

Measured, not assumed:

| Concern | SIBC | ATM/POS | Verdict |
|---|---|---|---|
| Extractor | `extract_sibc` 678 ln | `extract_atm_pos` 248 ln | **Genuinely custom** (different XLSX formats) |
| Insight generator | `generate_analysis_report` 329 ln | `generate_atm_pos_insights` 1866 ln | **Genuinely custom** (different insight models — do NOT merge) |
| Traceability validator | `validate_sibc_traceability` 196 ln | `validate_atm_pos_insights` 401 ln | **`extract_numbers`/`matches` DUPLICATED** → extract shared core |
| Analytical layer (skeleton, system_state, opportunities, chart_series, signal_history, freshness, model-validate) | — | — | **Already generic** (`--pipeline`), ~14 modules |
| Section/annotation validators | 5 (sections, annotations_draft, content, basis, web_series) | 1 (`validate_atm_pos`) | SIBC-only (hand-authored annotation path); ATM/POS fully deterministic |

**Conclusion — three buckets, not one engine:**
1. **`core/` engines** (generic, param by `--pipeline`): the analytical layer + freshness/
   history + the *shared* traceability core (`core/traceability.py` = `extract_numbers`,
   `matches`, `ratio_matches`, number-tracing — de-duplicated; already unit-tested).
2. **`pipelines/{id}/` modules** (custom, conform to a contract): `extract.py`,
   `detect_format.py`, `consolidate.py`, `insights.py`, `insights_validate.py` (a thin
   adapter that supplies the pipeline's schema/ground-truth and calls `core.traceability`),
   plus any pipeline-only validators. `profile.md`, date rules, data dir live here too.
3. **The gate**: ONE `core/gate.py` that executes a manifest-declared, ordered stage list.

The discipline that prevents leakage: **the manifest says WHAT runs in WHAT order; the
custom logic lives in `pipelines/{id}/` modules; the shared logic lives in `core/` param'd
by id. No `if pipeline ==` ever appears in `core/`.**

## `pipeline.json` schema

```jsonc
{
  "id": "sibc",
  "name": "RBI SIBC — Bank Credit",
  "paths": {                          // all repo-relative; resolved via core.paths.ROOT
    "data_dir":         "analysis/rbi_sibc",
    "consolidated_csv": "web/public/data/rbi_sibc_consolidated.csv",
    "timeline":         "analysis/rbi_sibc/timeline.json",
    "skeleton_profile": "analysis/rbi_sibc/skeleton_profile.json",
    "system_model":     "analysis/rbi_sibc/merged/system_model.json"
  },
  "schema": {                         // lets generic stages read the CSV without knowing the pipeline
    "date_column":   "date",
    "value_column":  "outstanding_cr",
    "entity_columns": ["code", "parent_code"]
  },
  "gate": [                           // ORDERED stage list — this IS the gate sequence
    { "id": "tests",       "label": "unit tests",          "run": "core.pytest" },
    { "id": "consolidate", "label": "consolidate CSV",     "run": "pipeline.consolidate" },
    { "id": "skeleton",    "label": "system model",        "run": "core.skeleton",
      "requires": ["consolidate"] },
    { "id": "freshness",   "label": "signal freshness",    "run": "core.check_signal_freshness" },
    { "id": "traceability","label": "insight traceability","run": "pipeline.insights_validate",
      "requires": ["insights"] },
    { "id": "build",       "label": "tsc + next build",    "run": "core.web_build",
      "skip_if": "--skip-build" }
    /* … full sequence below … */
  ]
}
```

### Stage object

| field | meaning |
|---|---|
| `id` | unique within the manifest; targets for `requires` |
| `label` | summary-table label |
| `run` | `"core.<engine>"` (generic module) · `"pipeline.<module>"` (per-pipeline) · `"core.<builtin>"` (pytest/web_build/csv_integrity) |
| `args` | optional extra args; supports `$ID`, `$LATEST` (latest signals.db period), `$PERIOD` |
| `requires` | upstream stage ids; if any **failed**, this stage is **SKIPPED** (not failed) |
| `skip_if` | a runtime flag (`--skip-build`) or condition that skips the stage |
| `note` | optional substring/regex to pull the summary line (default: last non-empty line) |

**`requires` unifies the two gates' divergent failure policies** without two code paths:
- SIBC today "runs every check, reports all" → its checks are mostly independent (few
  `requires`), so all run.
- ATM/POS today "short-circuits insight stages on upstream failure" → declare
  `requires: [extract, consolidate]` on the insight stages; they auto-skip. Same engine.

`core.gate` runs the list in order, executes each `run` target (subprocess for module
targets; builtin for pytest/web_build/csv_integrity), substitutes `$VARS`, applies
`requires`/`skip_if`, collects `(label, passed|None, note)`, prints the existing summary
table, exits non-zero if any stage failed. It is the ONLY orchestration code.

## Both gates expressed in the model (proof it holds for both today)

```
SIBC gate sequence            run target                       requires
  tests                       core.pytest
  timeline                    core.validate_timeline
  consolidate                 pipeline.consolidate
  sections                    pipeline.validate_sections       [consolidate]
  csv_integrity               core.csv_integrity               [consolidate]
  annotations_draft           pipeline.validate_annotations
  content                     pipeline.validate_content
  annotation_basis            pipeline.validate_annotation_basis
  signal_history              core.validate_signal_history
  freshness                   core.check_signal_freshness
  traceability                pipeline.insights_validate       [insights]
  insights                    pipeline.insights                [freshness]
  annotations_live            pipeline.validate_annotations_live
  web_series                  pipeline.validate_web_series
  system_model                core.validate_system_model       [skeleton]
  skeleton                    core.skeleton                    [consolidate]
  system_state                core.system_state                [system_model]
  opportunities               core.derive_opportunities        [system_state]
  ecosystem                   core.compose_ecosystem
  feed                        core.opportunities_feed          [opportunities]
  opp_traceability            core.validate_opportunity_traceability [opportunities]
  build                       core.web_build                   skip_if --skip-build

ATM/POS gate sequence         run target                       requires
  tests                       core.pytest
  format_detect               pipeline.detect_format
  extract                     pipeline.extract                 [format_detect]
  validate_data               pipeline.validate_data           [extract]
  consolidate                 pipeline.consolidate             [validate_data]
  signal_history              core.validate_signal_history     [consolidate]
  freshness                   core.check_signal_freshness      [consolidate]
  skeleton                    core.skeleton                    [consolidate]
  system_model                core.validate_system_model       [skeleton]
  system_state                core.system_state                [system_model]
  opportunities               core.derive_opportunities        [system_state]
  opp_traceability            core.validate_opportunity_traceability [opportunities]
  signals_payload             pipeline.signals_payload         [consolidate]
  chart_series                core.chart_series                [consolidate]
  insights                    pipeline.insights                [signals_payload]
  insights_validate           pipeline.insights_validate       [insights]
  claims_validate             pipeline.claims_validate         [insights]
  csv_integrity               core.csv_integrity
  build                       core.web_build                   skip_if --skip-build
```

Both draw from the **same runner vocabulary** (`core.*` + `pipeline.*`); only the manifest's
list and `requires` differ. No engine inspects the pipeline id.

## Source-#3 pressure test (the acceptance proof)

To add "UPI transactions": author `pipelines/upi/pipeline.json` (paths + schema + a `gate`
list reusing `core.*` stages, pointing custom stages at `pipelines/upi/extract.py`,
`insights.py`, a thin `insights_validate.py` over `core.traceability`). Run
`python3 analysis/core/gate.py --pipeline upi`. **Zero new top-level scripts; zero edits to
`core/` or `gate.py`.** → litmus test passes. A genuinely novel *kind* of stage = a new
reusable `core/` engine or a `pipelines/upi/` module — localized, never an `if`-branch.

## Open design decisions (need a call before implementing)

1. **`requires` = skip-on-upstream-failure** as the single failure model (vs SIBC's
   run-all). Recommend yes — it's a superset and removes the two-policy split.
2. **Insight generators stay fully custom** (`pipelines/{id}/insights.py`), NOT a shared
   engine (1866 vs 329 ln, different models). Recommend yes — forcing a merge would breed
   internal branches. Only the *traceability number-core* is shared.
3. **Build/CSV-integrity/pytest as `core` builtins** in `gate.py` vs separate modules.
   Recommend builtins (they're tiny and pipeline-agnostic).
4. **Implementation order:** build `core/gate.py` + both manifests and prove byte-identical
   summaries against the current gates FIRST (on the current flat layout), THEN do the P1/P2
   file moves — so the convergence is verified before relocation. (Inverts the handoff's
   P1→P3 order; safer because gate parity is checked on a known-good tree.) **DONE 2026-06-23
   (commit 232fe40): gate.py + both manifests built, verdict parity verified on both gates.**

## P1/P2 file-move execution map (coupling verified 2026-06-23 — for the fresh session)

The moves are a COORDINATED CLUSTER, not isolated files. Verified surface:

- **Import hub:** `generate_skeleton` is imported `as gs` by **11 modules**: compose_ecosystem,
  derive_cross_links, validate_composition, generate_opportunities_feed,
  generate_opportunity_narrative, generate_system_state, derive_opportunities,
  validate_system_model, run_inference, plus the two one-time helpers build_behavioral_layer
  and migrate_forces_to_instances. Moving it ⇒ rewrite all 11 `import generate_skeleton`
  sites (→ `from core import generate_skeleton as gs`; KEEP the filename to avoid rename churn).
  **DONE — P1 batch 1, commit 6c6ca3c.**
- **All other generic engines are subprocess-only (imported_by=0)** → moving them is pure
  path-string updates. `check_signal_freshness` also imports `signals.db` + `signals.compute.engine`
  (those stay under signals/, unaffected).
- **Subprocess path-refs live in exactly:** `core/gate.py` (CORE_MAP — 11 entries),
  `run_evals.py`, `run_atm_pos_evals.py`, `check_derived_fresh.py`, `git_hooks/pre-commit`,
  `generate_merge.py`, `hook_validate.py`.
- **sys.path note:** every moved script must carry the P0 bootstrap (adds `<repo>/analysis`
  to sys.path) so `from core import …` / `from crosssource import …` resolve as namespace
  packages from any depth. Verify each mover has it before moving.

**Target dirs:** core/ ← generate_skeleton, validate_system_model, generate_system_state,
derive_opportunities, generate_chart_series, generate_signal_history, run_inference.
guards/ ← check_signal_freshness, validate_signal_history, check_derived_fresh.
crosssource/ ← derive_cross_links, compose_ecosystem, validate_composition,
generate_opportunities_feed, generate_opportunity_narrative.

**Batch plan (verify the full matrix — both legacy gates + gate.py both pipelines +
check_derived_fresh + reconcile + build + 74 tests — and commit after EACH):**
1. ✅ **DONE (6c6ca3c)** — `generate_skeleton` → core/ + rewrote 11 import sites + 4 path-refs. (Highest coupling; done first, alone.)
2. ✅ **DONE (20c05e2)** — moved the 4 gate-internal core/ engines (validate_system_model,
   generate_system_state, derive_opportunities, generate_chart_series) + repointed CORE_MAP +
   run_evals/run_atm_pos_evals/check_derived_fresh + fixed test_system_state import.
   ⚠ **STILL TODO (2b, deferred):** `generate_signal_history` + `run_inference` are
   USER-INVOKED CLI tools — moving them changes documented `append`/`evaluate` commands +
   4 error-hint strings (check_signal_freshness, validate_signal_history,
   generate_atm_pos_insights, compute_atm_pos_signals) + the per-period command lists in
   CLAUDE.md/CLAUDE.local.md/PIPELINE_ARCHITECTURE.md/rbi_atm_pos/CLAUDE.md. Do as a
   doc-coordinated move (fold into step 7's doc sweep), not a pure path-string repoint.
3. ✅ **DONE (bcb292f)** — guards/ (check_signal_freshness, validate_signal_history,
   check_derived_fresh) + crosssource/ (derive_cross_links, compose_ecosystem,
   validate_composition, generate_opportunities_feed, generate_opportunity_narrative).
   Rewrote the two __file__.parent path roots → .git-walk; bootstrap-injected the rest;
   repointed CORE_MAP + run_evals + run_atm_pos_evals + check_derived_fresh orchestration +
   the pre-commit symlink; updated 2 `generated_by` provenance strings. NB: the architecture
   discoverer SCAN_DIRS does NOT yet scan core/guards/crosssource — adding them may surface
   new "undocumented module" drift, so it's deferred to step 7's doc sweep (reconcile --strict
   is green today because those dirs are simply out of scan scope).
4. Achieve full-mode parity (SIBC per-period, ATM/POS xlsx-ingest), then retire run_evals /
   run_atm_pos_evals (point any callers at gate.py).
5. Behavior-merge the two diverged `extract_numbers` → core/traceability.py (SIBC strips
   FY/ISO/quarter; ATM/POS handles B/M/K/x/% suffixes + REL_TOL 0.005 vs 0.02 — write
   ATM/POS traceability tests FIRST, then a parameterized superset).
6. pipelines/{id}/ for the per-pipeline modules + update each manifest's `modules` map.
7. legacy/ the retired scripts; update docs (CLAUDE.md, PIPELINE_ARCHITECTURE.md, per-period
   command lists) + add core/ to the architecture discoverer SCAN_DIRS.
```
```
