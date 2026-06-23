# Handoff — Engineering Health / Technical-Design Correctness (the non-functional track)

**Framing (Risham, 2026-06-23):** we've optimised for *functional* correctness (does the output trace, is it
fresh, is it aligned). We have **not** systematically addressed *technical* correctness — architecture
legibility, optimality, reusability, understandability, test coverage, design-system coherence. This doc is
the authoritative backlog + cadence for that track. None of it is blocking today; it's the work that keeps the
platform scalable and trustworthy as it grows. **Pairs with `HANDOFF_RESTRUCTURE.md`** (reusability is partly
solved there).

Honest grading of the current state (`A`=good, `C`=gap, `F`=absent):

| Dimension | Grade | Reality |
|---|---|---|
| Authoritative architecture | **C** | `PIPELINE_ARCHITECTURE.md` (stage prose) + 49/49 module docstrings exist; **no system-level data-flow diagram, artifact lineage, or module-dependency reference**, no README |
| Unit tests / correctness | **F** | **1 test file, 9 tests** (`tests/test_system_state.py`, S3 only). The deterministic core is untested. Zero web tests (no runner configured) |
| Optimality / performance | **C** | one win shipped (4.6 MB CSV → precompute); **no systematic perf pass**; the gate cold-starts ~20 python subprocesses/run; freshness recomputes ALL periods each commit |
| Reusability | **C** | per-pipeline one-off scripts + near-duplicate validators; **addressed by `HANDOFF_RESTRUCTURE.md`** (core/ generics) |
| Understandability | **B–** | strong module docstrings; gaps: no per-dir READMEs, naming drift (e.g. prop still named `rows` after `AtmPosRow→AtmPosSeries`) |
| Design-system coherence (web) | **C** | DLS exists + shared (`dls/InsightCard`, `InsightCTAStrip`, `SectionCard`, `theme.ts`); SIBC vs payments **have drifted before** (chart components, legend toggles, YoY mode) — needs a recurring audit |

---

## 1. Authoritative end-to-end architecture (build `ARCHITECTURE.md`)

`PIPELINE_ARCHITECTURE.md` says *how stages run*; it is **not** a system-of-record for *how data and modules
connect*. Create a top-level `ARCHITECTURE.md` with: (a) a **data-flow diagram** source→…→UI, (b) an
**artifact-lineage table** (which file is produced by which script and consumed by which — e.g.
`consolidated.csv → {signals.db, chart_series.json, system_model}`), (c) a **module-dependency map** (post-
restructure: `core/` ← `pipelines/{name}/`), (d) the **invariants in one place** (determinism, traceability,
single-source, the guards Check 2e/2f/2g/4c/4f and what each enforces), (e) the **layer model** L1/L2/L3.

**Canonical flow (seed for the diagram — keep this accurate):**
```
raw XLSX → extract → validate → consolidate (CSV = single source)
  → L1 compute (signals.db, deterministic)        ──┐
  → L1 evaluate (LLM, prompt v1.11, via API)        │→ insight annotations (traceable: Check 2g/4c)
  → chart_series.json (compact, web)                │
  → L2 model (skeleton[det] + behavioral[authored,sourced])
  → S3 dynamic state (signals fire on model, det)   │
  → opportunities (status from firing) + narrative(LLM)  →  /opportunities (traceable: Check 4f strict)
  → L2b cross-source (ontology hub + composition)
  → S4 inference (proposes sourced forces; manual)
Guards: 2e schema · 2f signals.db freshness · 2g/4c insight traceability · 4f opportunity traceability · derived-fresh
```

## 2. Unit tests for the deterministic core (highest correctness ROI)

The platform's value *is* "deterministic + traceable", yet the compute is unverified except by
consistency-gates (which catch drift, not wrong-from-the-start logic). Add golden/property tests for:
- **`signals/compute/`** methods — `csv_total_yoy`, `csv_streak` (both directions), `csv_total_ratio`,
  `csv_ratio_sum`, category/scan — against a tiny fixture CSV with hand-computed expected values.
- **SIBC date-normalisation** (`update_web_data.py`) — the Apr/May/Mar remap + `date_overrides`. This is
  error-prone and currently only human-gated; a wrong remap silently corrupts every downstream number.
- **Traceability validators** — `extract_numbers` (FY-range edge cases like `FY22-24`), matching tolerance,
  the YoY drift guard.
- **`generate_chart_series` + `buildSectionData`** — total/by_type/top_n/individual + MoM/YoY derive, vs a
  fixture (guards the perf-refactor against regressions).
- Choose a runner: keep `pytest` for python; add **Vitest** for web `lib/` pure functions. Wire `pytest` into
  the gates (currently `tests/` runs nowhere automatic).

## 3. Optimality / performance pass

- Gate latency: ~20 cold python subprocess starts per run; consider an in-process orchestrator or batching.
- `check_signal_freshness` recomputes every period from CSV on every commit (pre-commit) — fine now, watch as
  periods grow; could scope to changed periods.
- Audit any remaining client-side heavy lifting on the web (the payments CSV is fixed; verify SIBC `data.ts`
  PapaParse stays small; `/opportunities` `section-chart-data.ts`).

## 4 & 5. Reusability + understandability

- Reusability: see `HANDOFF_RESTRUCTURE.md` (converge per-pipeline one-offs onto `core/`). Also dedupe the
  near-identical traceability validators (`validate_sibc_traceability` vs `validate_atm_pos_insights` share
  `extract_numbers`/matching — already partially imported; finish the consolidation).
- Understandability: one **README per top-level dir** (`core/`, `pipelines/`, `signals/`, `guards/`) stating
  its contract; a **naming-consistency pass** (e.g. rename the `rows` prop → `series` post-refactor; consistent
  `*_validate` vs `validate_*`). Keep the 100% module-docstring rule.

## 6. Design-system coherence (web) — needs a CADENCE, not a one-off

The two dashboards share the DLS but drift. Establish a **recurring check (every few days / each web PR)**:
- Both pipelines use the same `dls/` primitives, `theme.ts` colours (`pickColor`, `TYPE_COLOR`, accents),
  card shell, insight-card/CTA-strip structure, controls layout, mobile rules (375px), dark mode.
- Chart parity: trend modes, legend-toggle behaviour, highlight/intelligence mode, the new Total/series
  conventions stay aligned across SIBC and payments.
- Tooling: the `vercel:react-best-practices` skill + a short DLS checklist in `web/AGENTS.md`. Consider a
  visual-regression snapshot once Vitest/Playwright exists.

---

## Recommended order (when this track is picked up)
1. **`ARCHITECTURE.md`** (cheap, high-leverage; do alongside the restructure so it documents the target).
2. **Deterministic-core unit tests + wire pytest into the gate** (highest correctness ROI; do before the
   restructure move so it catches migration regressions).
3. Restructure (`HANDOFF_RESTRUCTURE.md`) — reusability.
4. Perf pass + READMEs + naming.
5. Stand up the **design-coherence cadence** (web).

**Note:** these are non-functional/quality investments — schedule them deliberately, not squeezed into
feature work. Git-revertible, gate-verified. Pairs with [[feedback-design-for-long-term]].
