---
name: model-pass
description: Run the Layer 2a system-model pass for a pipeline after a current-period ingest — UPDATE (interim month, additive) or FOUNDATION (March year-end, rebuild). Use after /ingest-period, or when the user asks to update the causal model.
disable-model-invocation: true
---

# Layer 2a model pass

**Inputs:** pipeline id and period. **Mode is read, never assumed:** `is_fy_end` in the
pipeline's `timeline.json`. `true` → FOUNDATION; anything else → UPDATE. The first-ever period of
a new source is also FOUNDATION. If unsure, UPDATE.

**Done when:** `python3 analysis/core/validate_system_model.py --pipeline {p}` PASSES, and the
full gate (`gate.py --pipeline {p} ...`) regenerates the skeleton, S3 state and opportunities green.

## What the model is (read once)

`analysis/{data_dir}/merged/system_model.json`. The **skeleton** (entities + structural edges) is
regenerated from the CSV by the gate. Never edit it by hand. You own only the **behavioral
layer**: channels, `force_instances`, loops, opportunity/risk/gap nodes. A force is an EXTERNAL
cause that is not itself observable in our data; a published statistic is a candidate signal,
not a force. Spec: `analysis/SYSTEM_MODEL_SPEC.md`; cross-source: `analysis/COMPOSITION_SPEC.md`.

## UPDATE (every interim month): additive only

1. Read S3 for the period (`system_state_{period}.json`): which forces fire, which edges reversed,
   and which `mix_states` changed regime (steered / drifting / contested / reallocating).
2. The new causes come from `/s4-source`, which proposes, sources and promotes. Do not author a
   force here without a verified source. A hypothesis with no source is allowed (`claim_type:
   hypothesis`); a decorative citation is not.
3. Never restructure existing nodes or edges. Set `_meta.mode = "update"` and bump
   `_meta.last_updated`.
4. An **honest null** (nothing new cleared the source bar) is written into `_meta.update_note`.
   It is a valid outcome; do not manufacture a force to make the pass look productive.

## FOUNDATION (March file): rebuild

1. Everything in UPDATE, plus a full review of the behavioral layer against the year's data.
2. `_meta.mode = "foundation"`, `_meta.last_foundation_date = {dataDate}`.
3. **Hand-written SIBC annotations** (`analysis/rbi_sibc/merged/annotations_merged.ts`, 26 live,
   last changed 2026-06-12). ⏸ Ask the user whether to refresh or retire them.
   Annotation IDs are **permanent**: before promoting, run
   `python3 analysis/pipelines/sibc/promote_annotations.py --dry-run` and justify every removed ID.
   Then promote with the same script (never `cp`).
4. ⏸ PAID: re-run Stage 5 evaluate after the rebuild (same approval rule as `/ingest-period`).

## Checks

```bash
python3 analysis/core/validate_system_model.py --pipeline {p}
python3 analysis/guards/audit_force_sources.py          # every inference-claiming force verifies
python3 analysis/core/gate.py --pipeline {p} --merged --skip-build   # SIBC; --period for others
```
`audit_force_sources` fetches live pages, so it is not a gate stage. `unreachable` (network) is
reported apart from `NOT ON PAGE` (a false citation); only the second is a defect.

## Traps

- A force that cites our own series cites its **effect** as its cause.
- A force's **effective date** must fall so that it is in force across the signal window, or the
  proposal is `expired`. Check the date first; that is where the time goes.
- Edits to `system_model.json` trigger the edit hook (`hook_validate.py` → the v4 validator). A
  failure there is real now; it no longer cries wolf.
