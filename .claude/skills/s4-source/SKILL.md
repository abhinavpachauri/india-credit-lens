---
name: s4-source
description: S4 sourcing loop — generate hypotheses for what the causal model does not explain, triage them, source the worthwhile ones through the user's logged-in Chrome, and promote only verified forces. Use during /model-pass or when the user asks to work the S4 worklist.
disable-model-invocation: true
---

# S4: propose → triage → source → promote

**Done when:** every proposal in `analysis/s4_proposals/{period}.json` is either promoted into
the model, triaged with a verdict, or has an `attempts[]` record saying what was searched. After
that, `python3 analysis/guards/audit_force_sources.py` reports **NOT ON PAGE = 0**. S4 converts at
roughly 1 in 40, and most proposals are meant to die. The queue must shrink by **decision**, never
by omission.

## 1. Generate: ⏸ PAID

```bash
python3 analysis/core/run_inference.py            # detection + LLM proposals, all pipelines
python3 analysis/core/run_inference.py --no-llm   # detection only (free)
```
Proposal generation is a paid call: ⏸ give the user its estimate and wait for a yes, then run
with `ICL_LLM_OK=1` prefixed. `--verify-api` (the API source hunt) is also paid and is opt-in
because most allowlisted hosts block crawlers.

## 2. Triage what does not need a browser

```bash
python3 analysis/core/run_inference.py --worklist analysis/s4_proposals/{period}.json
python3 analysis/core/run_inference.py --triage FILE --index N --as {duplicate|expired|not_a_force|unsourceable} --note "why"
```
A `duplicate` must name the force it duplicates. `expired`: the instrument's effective date puts
it outside the window. `not_a_force`: a statistic, or our own series. Triage never promotes.

## 3. Source, one proposal at a time (the user's ritual)

For each surviving proposal, state these before searching:
1. **What must be true in the world** for this to explain the movement, including the effective
   date that would put it in force for the window.
2. **Ranked sources**: official first (rbi.org.in, pib.gov.in, then the rest of the T1 tier in
   `analysis/distribution/bank_sourcing.py` `ALLOWLIST`), then reports (T2), then press (T3).
3. **Search phrases, broad first.** Over-constrained queries return nothing; headline-shaped
   queries worked where `site:` queries failed.
4. Search and filter in the **user's logged-in Chrome** (the primary channel). Search by **what
   changed in the window**, not by the proposal's named target: one RBI document (PSL Directions
   2025) settled three forces that were each named something else.
5. ⏸ **The user decides.** Present the verbatim excerpt, URL, effective date and what it attaches to.

## 4. Record: the same gate whichever way the text was obtained

```bash
python3 analysis/core/run_inference.py --resolve FILE --index N --url URL \
  --excerpt "verbatim text" --page-file {saved page text} --in-force
```
`--in-force` is required to promote. The excerpt must literally appear on the page
(`bank_sourcing.excerpt_on_page`), from an allowlisted host. Then add the force to the model
(`/model-pass`) and re-run `validate_system_model.py`.

## Traps (each cost a day)

- **Check the checker.** `core.source_fetch.fetch_text` returns a **tuple** `(text, verdict)`;
  `len()` on it reported every host as "blocked". Before believing any probe, run one known-good
  URL (a Wikipedia page) and one known-bad one through it.
- An **outage is not a finding.** A credit/API error must be `check_error` (retryable), never
  `no_url`; 93 of 103 attempts once looked like "found nothing".
- **Blocked is real for some hosts** (NPCI, Business Standard): source those through Chrome.
  PIB and RBI article pages are machine-readable.
- An allowlist widening does not create evidence. A host on the list still needs a page that
  carries the quote, dated inside the window.
