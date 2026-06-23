# Handoff — Architecture / Engineering-Health track (2026-06-23)

This is the non-functional track from `HANDOFF_TECH_QUALITY.md` (architecture legibility,
test coverage, the `analysis/` restructure). This session closed three of its items and
left the `analysis/` file relocation fully mapped for a fresh session. Active product focus
is still LinkedIn distribution (`HANDOFF_2026-06-23.md`); this is the parallel track.

## TL;DR for the next session

The architectural **substance is done**: there is now ONE manifest-driven gate runner
(`analysis/core/gate.py`) that reproduces both legacy gates with verdict parity. What's left
is **mechanical**: the `analysis/` file relocation + retiring the two legacy gates. The exact
coupling map + 7-step batch plan is in **`analysis/core/MANIFEST_DESIGN.md`** ("P1/P2
file-move execution map"). Start there.

## What was done this session (6 commits on `main`)

| Commit | What |
|---|---|
| `0898da4` | **Architecture-as-code.** `analysis/architecture/{discover,render,reconcile}.py` + authored `ARCHITECTURE.md`. Structural facts are DERIVED from code (`graph.json` → `ARCHITECTURE.generated.md`); prose docs are VALIDATED against code (`reconcile.py --strict`, clean today). |
| `2705519` | **§4 P0 — repo-root centralized.** `analysis/core/paths.py` (resolves root via `.git` walk) + 34 scripts repointed via a move-safe bootstrap. Root resolution no longer breaks when files move. |
| `9bd97f2` | **Deterministic-core unit tests.** 9 → 74 golden tests (compute SIBC + ATM/POS, date-normalisation, traceability). pytest wired as "Check T" (first stage) in BOTH gates; negative-tested (a failing test fails the gate, exit 1). |
| `232fe40` | **§4 P3 — manifest-driven gate.** `analysis/core/gate.py` + `analysis/pipelines/{sibc,atm_pos}/pipeline.json`. One runner, driven by per-pipeline manifests. Verdict parity verified vs both legacy gates. |
| `4868fb2` | **P1/P2 move execution map** appended to `MANIFEST_DESIGN.md` (coupling verified). |
| _(this)_ | This handoff. |

## Decisions made (with rationale)

1. **Architecture is derived from code, not hand-written.** A prose `ARCHITECTURE.md` of
   structural facts would be the exact "parallel copy that drifts" the #1 principle forbids.
   So: derive lineage/call-graph/dep-map from code; validate the prose docs against code.
   Authored MD holds only stable rationale (invariants, layer model, guard purposes).
2. **Tests before the restructure.** The deterministic core was unverified (only consistency-
   gated). Added golden tests first so the file moves have a regression net.
3. **P3 (gate convergence) before P1/P2 (file moves).** Design-before-move: built + parity-
   proved the manifest-driven gate on the current known-good layout, so the risky convergence
   is verified before anything relocates.
4. **Three buckets, not one mega-engine.** `core/` generic engines (param by `--pipeline`) ·
   `pipelines/{id}/` custom modules conforming to a contract · one `core/gate.py`. The manifest
   declares WHAT runs in WHAT order; no engine inspects the pipeline id. Evidence-driven:
   `generate_atm_pos_insights` (1866 ln) vs `generate_analysis_report` (329 ln) genuinely
   diverge → insight generators stay custom, NOT merged. Only the shared traceability
   number-core is to be de-duplicated.
5. **`requires` + `on_fail:stop` (manifest) unify the two gates' divergent failure policies**
   (SIBC run-all vs ATM/POS short-circuit) declaratively — no two code paths.
6. **Defer the file relocation to a fresh session.** It's a coordinated 25+-reference cluster
   (see below), low functional value (legibility), and regression-risky to rush at the tail of
   a long session. The substance is already delivered; relocation is mechanical.

## Current state (verified clean this session)

- Build: green (9 routes). Both gates: green. Unit tests: 74 pass.
- Data: CSV 1032 (SIBC) / 47,370 (ATM/POS) rows; signals.db fresh.
- UI: Credit 7 sections + Payments LLM annotations render; 0 console errors.
- `reconcile.py --strict`: clean. `check_derived_fresh`: clean. No derived-artifact drift.
- **Both `run_evals.py` / `run_atm_pos_evals.py` (legacy) AND `core/gate.py` (new) work and
  agree.** Nothing is retired yet — gate.py runs alongside the legacy gates.

## What's next (in order) — full detail in `analysis/core/MANIFEST_DESIGN.md`

1. **P1: move `generate_skeleton` → `core/`** + rewrite its **9 `import generate_skeleton as gs`**
   sites (→ `from core import generate_skeleton as gs`; keep the filename). Do this alone — it's
   the import hub. Verify the full matrix, commit.
2. **P1: move the remaining generic engines** (subprocess-only, easy) → `core/` + `guards/` +
   `crosssource/`; repoint `gate.py` CORE_MAP + `run_evals` + `run_atm_pos_evals` +
   `check_derived_fresh` + `git_hooks/pre-commit` + `generate_merge` + `hook_validate`.
3. **Full-mode parity** for gate.py (SIBC per-period, ATM/POS xlsx-ingest), then **retire the
   two legacy gates** (point callers at `gate.py --pipeline {id}`).
4. **Behavior-merge the two diverged `extract_numbers`** → `core/traceability.py` (SIBC strips
   FY/ISO/quarter; ATM/POS handles B/M/K/x/% + REL_TOL 0.005 vs 0.02). Write ATM/POS
   traceability tests FIRST, then a parameterized superset.
5. **P2: move per-pipeline modules** → `pipelines/{id}/` + update each manifest's `modules` map.
6. **P4: `legacy/` the retired scripts**; update docs (CLAUDE.md, PIPELINE_ARCHITECTURE.md,
   per-period command lists); add `core/` to the architecture discoverer `SCAN_DIRS`.
7. **Then:** web Vitest for `lib/` pure fns; perf pass; design-system-coherence cadence.

## Verification matrix to run after EACH move batch

```
python3 -m pytest analysis/tests/ -q
python3 analysis/run_evals.py --period merged --merged --skip-build      # legacy, must stay green until retired
python3 analysis/core/gate.py --pipeline sibc --merged --skip-build      # new, must match
python3 analysis/core/gate.py --pipeline atm_pos --period 2026-04-30 --skip-build
python3 analysis/check_derived_fresh.py
python3 analysis/architecture/reconcile.py --strict
cd web && npm run build
git status -s    # revert any incidental timestamped artifact churn before committing
```

## Acceptance bar (when is the architecture "acceptable")

The litmus test: **a new source #3 = `pipelines/{x}/pipeline.json` + a thin `extract.py`, with
zero new top-level scripts and zero `if pipeline ==` in `core/`.** gate.py + manifests already
make this essentially true; completing the relocation + legacy-gate retirement makes it clean.

## Key files

| File | Role |
|---|---|
| `ARCHITECTURE.md` | Authored rationale (invariants, layer model, guard purposes) |
| `ARCHITECTURE.generated.md` | Derived structural facts (regenerate: `discover.py && render.py`) |
| `analysis/core/MANIFEST_DESIGN.md` | **P3 design + the P1/P2 move execution map — read first** |
| `analysis/core/gate.py` | The one manifest-driven gate runner |
| `analysis/pipelines/{sibc,atm_pos}/pipeline.json` | The two gate sequences as data |
| `analysis/core/paths.py` | Centralized repo-root resolution |
| `analysis/architecture/reconcile.py` | "Docs can't lie" guard (`--strict`) |
| `HANDOFF_TECH_QUALITY.md` | The full engineering-health backlog (this is §1/§2/§4 of it) |
