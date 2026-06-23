# Architecture

Authoritative system-of-record for *how India Credit Lens is built* — the rationale,
invariants, and layer model. It is split deliberately into two halves:

| Half | File | Kind | Maintenance |
|---|---|---|---|
| **Rationale** (this file) | `ARCHITECTURE.md` | Authored prose — *why* | Hand-edited; stable, doesn't drift |
| **Structure** | [`ARCHITECTURE.generated.md`](ARCHITECTURE.generated.md) | Derived facts — *what* | **Generated from code**; never hand-edited |

This split is itself an application of the platform's #1 engineering principle (below):
structural facts that drift — the data-flow, artifact lineage, gate call-graph, module
map — are **derived from the code that actually runs and guarded for freshness**, never
re-stated in prose that silently rots. Prose is reserved for what *doesn't* drift: the
design intent.

> `PIPELINE_ARCHITECTURE.md` is the *stage-by-stage operating manual* (how to run a period
> through the pipeline). This file is the *system model* (how data and modules connect and
> why). They are complementary.

---

## Engineering principle (non-negotiable) — design for the long term

This platform is **multi-pipeline by design** (SIBC, ATM/POS, future sources). Every
decision must scale to N ingestion types and N pipelines:

- **One generic mechanism per pipeline, not per-pipeline one-offs.**
- **Compute once, ship compact.** Precompute artifacts at build time; the browser never
  parses raw consolidated data or re-derives series.
- **Single source of truth.** No parallel copies that "agree today but could drift" —
  guard with a deterministic freshness/traceability check.
- Given "quick win vs proper fix", **default to the proper fix.**

---

## Invariants (what the guards exist to protect)

1. **Determinism.** Layer 1 compute, the system-model skeleton, S3 state, opportunity
   firing, and chart series are all deterministic functions of the consolidated CSV +
   authored model. The same input always yields the same output.
2. **Traceability.** Every number rendered in an insight, chain, implication, or
   opportunity must trace to a computed value (`signals.db` / `signals.json` / declared
   evidence). LLMs *narrate* grounded numbers; they never invent them.
3. **Single source of truth.** One consolidated CSV per pipeline; one signal store
   (`signals.db`); no parallel recomputation of a value that's already a registered signal.
4. **Freshness.** Derived artifacts are treated as stale until proven fresh — every commit
   re-derives the deterministic chain and fails on drift.
5. **Legibility.** The architecture is discoverable from code; the docs are validated
   against it, not trusted blind.

## Guards (each enforces an invariant — see the gates in `ARCHITECTURE.generated.md` §2)

| Guard | Enforces | What it checks |
|---|---|---|
| `validate_signal_history.py` (2e) | single-source | `signals.db` rows + registry schema + status sync |
| `check_signal_freshness.py` (2f/5b2) | freshness | recompute every period from CSV; fail on any drift |
| `validate_sibc_traceability.py` (2g) | traceability | every number in a SIBC insight traces to `signals.db` |
| `validate_atm_pos_insights.py` (4c) | traceability | ATM/POS analog of 2g (numbers → `signals.json`/db) |
| `validate_opportunity_traceability.py` (4f, strict) | traceability | opportunity numbers → driver's full `evidence_all` |
| `validate_system_model.py` | determinism/structure | skeleton + D1/D2/D3 discipline + force sourcing |
| `check_derived_fresh.py` (pre-commit) | freshness | re-derive the deterministic chain; fail on drift |
| `architecture/reconcile.py` | legibility | living docs' script/artifact refs exist on disk |

---

## Layer model

- **Layer 1 — Computable from the CSV alone.** Algorithmic, runs every period, no LLM for
  compute. Signals in `signals.db`; the LLM only *narrates* them for the insight layer.
- **Layer 2 — Crosses data boundaries.** Causal graph (`system_model.json`: deterministic
  skeleton + authored-and-sourced behavioral layer) → S3 maps live signals onto it → live
  opportunity/risk status → LLM narration. L2b composes across pipelines via the ontology
  hub. Findings = signals mapped onto the model, never independent LLM inference.
- **Layer 3 — Lending-workflow strategic implications.** Authored ~6-monthly; consumes the
  L2a/L2b causal graphs. (Ecosystem model still to be built.)

The canonical end-to-end flow (`raw XLSX → extract → consolidate → L1 compute → evaluate
→ chart series + model → S3 → opportunities → cross-source`) is rendered, with the exact
producing/consuming scripts, in [`ARCHITECTURE.generated.md`](ARCHITECTURE.generated.md) §1.

---

## Architecture tooling (`analysis/architecture/`)

Architecture-as-code: the structural doc is derived, not written.

```bash
python3 analysis/architecture/discover.py   # code → graph.json (imports, call-graph, lineage)
python3 analysis/architecture/render.py      # graph.json → ARCHITECTURE.generated.md
python3 analysis/architecture/reconcile.py   # validate living docs against code (--strict to gate)
```

- **`discover.py`** — static analysis: AST import graph + subprocess call-graph (authoritative)
  + artifact IO lineage (canonicalized; path-join + variable-binding reconstruction). Layout-
  agnostic (resolves repo root via `.git`), so it survives the planned `analysis/` restructure.
- **`render.py`** — renders the graph to the generated Markdown (data-flow, call-graph,
  lineage table, dep-map, drift findings).
- **`reconcile.py`** — the "docs can't lie" guard: every `*.py` and repo-relative artifact
  path named in a living doc must exist on disk. Forward-references marked "does not yet
  exist"/"planned" are exempt. Advisory today; `--strict` exits non-zero for gate wiring.

**IO lineage is a validator, not the source.** Python builds paths via `/` and f-strings,
so pure derivation of *which artifact* a script writes is necessarily heuristic; the
call-graph and import graph are exact. When the `pipeline.json` manifests land (the §4
restructure), they become the declared source for IO and `discover.py` validates them.
