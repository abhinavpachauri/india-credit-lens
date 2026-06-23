# Handoff — `analysis/` restructure for scalability (design; execute in a fresh session)

**Decision (2026-06-23):** the folder structure should mirror the architecture and scale to N pipelines.
Design + prove it on the **2 existing pipelines now**; when **source #3** arrives it just slots in as config
and *validates* the design (don't co-change structure + add a source). Everything is git-committed/recoverable.
**Do NOT execute in a low-context session** — this is a 49-file move with path surgery; run it fresh, verify at
each step, commit in small batches.

---

## The real problem (not just folders)

`analysis/` is 49 standalone scripts in one flat pile. Half the architecture is already **generic /
pipeline-parameterized** (`generate_skeleton --pipeline`, `system_state`, `derive_opportunities`,
`chart_series`, `signal_history`, `run_inference`, `signals/compute/`). The **ingestion + gate layer is
copy-per-pipeline** (`extract_sibc`/`extract_atm_pos`, `run_evals`/`run_atm_pos_evals`,
`validate_sibc_traceability`/`validate_atm_pos_insights`, `generate_analysis_report`/`generate_atm_pos_analysis_report`).
That copy-per-pipeline pattern is exactly what the engineering principle (CLAUDE.md) says to avoid — at N
sources it grows linearly. **The fix is two-layer: (1) folder layout that reflects generic-vs-custom, and
(2) converge the per-pipeline one-offs onto a generic gate runner + per-pipeline config/manifest.**

## Irreducibly-custom vs generic (the key design call)

- **Stays custom, per pipeline** (the ~10% that genuinely differs by source): the **extractor** (raw XLSX
  format parsing), `skeleton_profile.md`, date-normalization rules, section/insight definitions, the data dir.
- **Becomes generic** (one engine, config-driven): the **gate runner**, the traceability/freshness
  validators, consolidation pattern, signals-payload build, insights framework, plus everything already
  generic (model engine, chart series, signal compute dispatch).
- A **pipeline manifest** (`pipelines/{name}/pipeline.json`) declares: extractor module, csv path, date
  column, category/entity columns, which stages run, gate sequence. Adding a pipeline = manifest + a thin
  extractor, **not** 10 copied scripts.

## Target structure

```
analysis/
  core/          # generic, pipeline-parameterized engines + the generic gate runner
                 #   gate.py (replaces run_evals/run_atm_pos_evals — reads pipeline manifest)
                 #   skeleton.py · system_model_validate.py · system_state.py · opportunities.py
                 #   chart_series.py · signal_history.py · inference.py · traceability.py · consolidate.py
                 #   paths.py  ← single source of ROOT/ANALYSIS (fixes the depth hazard, see below)
  pipelines/
    sibc/        pipeline.json · extract.py · detect_format.py · merge.py · profile.md
                 validators specific to sibc (sections/annotations/content/claims/timeline/web_series/
                 sibc_traceability) · analysis_report.py · promote_annotations.py · backfill_basis.py
                 timeline.json · merged/ · periods/
    atm_pos/     pipeline.json · extract.py · detect_format.py · consolidate.py · profile.md
                 validate_data.py · signals_payload.py (compute_atm_pos_signals) · insights.py
                 insights_validate.py · claims_validate.py · timeline.json · merged/
  signals/       registry.json · signals.db · compute/ · evaluations/ · prompts/ · query.py · evaluate.py · db.py   (mostly unchanged)
  crosssource/   derive_cross_links · compose_ecosystem · validate_composition · opportunities_feed · opportunity_narrative · catalog.json · composition.json
  ontology/      concepts.json · channels.json   (unchanged)
  guards/        check_signal_freshness · check_derived_fresh · validate_signal_history · git_hooks/
  content/       newsletter/ (incl. LinkedIn)   (rename or keep `newsletter/`)
  legacy/        validate.py · generate_mermaid · source_claims · build_behavioral_layer · migrate_forces_to_instances
```

(Per-pipeline scripts still exist where genuinely custom — but they're grouped, and the generic stages live
once in `core/`. The gate runner is ONE file driven by each pipeline's manifest.)

## Mechanical surface (small + enumerable — verified 2026-06-23)

1. **Path-depth hazard (do FIRST).** ~12 scripts hardcode `ROOT = Path(__file__).resolve().parent.parent`
   (assumes `analysis/x.py`). Any move into a subfolder breaks this. **Fix:** add `analysis/core/paths.py`
   exporting `ROOT`/`ANALYSIS` (resolved by walking up to the repo marker, e.g. `.git`), and have every moved
   script import from it instead of recomputing. Grep: `grep -rn "parent.parent\|ANALYSIS = " analysis/`.
2. **35 subprocess `.py` path-refs in exactly 4 files:** `run_evals.py`, `run_atm_pos_evals.py`,
   `check_derived_fresh.py`, `git_hooks/pre-commit`. Update each to the new path (or, better, the new
   `core/gate.py` replaces the two run_*_evals).
3. **Module imports (low):** `import generate_skeleton` (×11 → becomes `from core import skeleton` or keep a
   shim), `from signals.* ` (×5, unaffected if `signals/` stays), `from validate_sibc_traceability` (×1),
   `from validate` (×1). ~10 `sys.path.insert` shims to update.
4. **Doc references:** `CLAUDE.md`, `PIPELINE_ARCHITECTURE.md`, `analysis/newsletter/CLAUDE.md`,
   `analysis/rbi_*/CLAUDE.md`, the per-period command lists. Update script paths.
5. **Output paths unaffected** (scripts write to `web/public/data/...` via ROOT-relative paths → fixed by #1).

## Migration plan (phased, verify each step; commit per phase)

- **Phase 0 — `core/paths.py`** + repoint the ~12 ROOT-computing scripts to it (no moves yet; gates still
  green). De-risks every later move.
- **Phase 1 — move the already-generic scripts** into `core/`, `guards/`, `crosssource/` (low risk — few
  importers). Update the 4 path-ref files. Run both gates + build + freshness after.
- **Phase 2 — group per-pipeline scripts** under `pipelines/sibc/` and `pipelines/atm_pos/` (no behaviour
  change yet, just relocation + path/import/doc updates). Run both gates.
- **Phase 3 — converge the gate:** replace `run_evals`/`run_atm_pos_evals` with one `core/gate.py` driven by
  each pipeline's `pipeline.json`. Prove identical output on BOTH pipelines (diff the eval summaries).
- **Phase 4 — `legacy/`** the retired scripts; tidy docs.
- **Later — source #3:** author only `pipelines/{x}/pipeline.json` + `extract.py`. If it runs end-to-end with
  zero new top-level scripts, the design is validated.

## Verification gate (run after every phase)
```bash
python3 analysis/.../gate (sibc)      # ALL CHECKS PASSED + build
python3 analysis/.../gate (atm_pos)
python3 analysis/check_signal_freshness.py
python3 analysis/check_derived_fresh.py
# git diff the eval summaries before/after each phase — they must be identical
```

## Why now-design / later-execute
Designing on the 2 known pipelines makes the abstraction concrete (not speculative); executing in a fresh,
full-context session keeps the 49-file path surgery safe; validating with #3 proves it. Git makes every phase
revertible. **Pairs with:** the engineering principle in CLAUDE.md and [[feedback-design-for-long-term]].
