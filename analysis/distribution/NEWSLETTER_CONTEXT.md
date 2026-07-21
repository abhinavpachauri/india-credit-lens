# Long-form channel (Substack) — India Credit Lens

> **Moved into `analysis/distribution/` on 2026-07-21.** The newsletter was never a
> separate system — it is this layer's long-form channel, sitting beside LinkedIn.
> It now shares the source layer, the gate, and the output contract with every other
> channel. Old paths (`analysis/newsletter/*`) are gone; see the file table below.

> Execution context for the professional Substack newsletter (indiacreditlens.substack.com).
> Audience: credit & product professionals in fintech/lending. NEVER mentions tickers/stocks —
> that content belongs to the retail publication (see `ICL_RETAIL_90DAY_PLAN.md`).

---

## What this is (v2, rebuilt 2026-07-04)

A **deterministic rendering layer** over the same gate-validated artifacts the dashboards
use. No LLM calls, no hand-authored stats, no retired artifacts. Two posts per data cycle:

| Post | Script | Published | Content |
|---|---|---|---|
| **Release read** | `issues/merged_issue.py --pipeline {sibc\|atm_pos}` | within 24h of the RBI release | L1: headline stats, status flips vs prior period, new trackers, one validated insight card per section |
| **Deep read** | `issues/deep_read.py` | mid-cycle (~2 weeks later) | L2/L3: cross-system ecosystem cards with computed basis, live openings, watch-outs |

Both are prepared from the same gate run; publishing is staggered so one monthly cycle
gives a fortnightly presence.

**v1 (config-authored + mermaid images + LinkedIn packages) is retired** to
`analysis/legacy/newsletter_v1/` — it depended on subsystems.json and Stage-4 mermaid,
both retired in the v4.0 cutover. LinkedIn posts are now written by the user in their
own voice (deliberate decision, 2026-07-03) — there is no LinkedIn generator.

---

## Architecture (mirrors the pipeline discipline)

```
distribution_sources.py  data layer (shared with every channel) — reads ONLY validated artifacts:
                           signals.db                → headline stats, status flips, new trackers
                           sibc_l1_annotations.json  → SIBC cards   (Check 2g validated)
                           atm_pos_insights.json     → payments cards (Stage 4c validated)
                           opportunities_feed.json   → L2/L3 cards  (Check 4f validated)
longform_render.py       render layer — typed blocks → .md (canonical) + .html (Substack paste)
validate_distribution.py the gate (shared with every channel) — check_doc() runs BEFORE any file is written:
                           1. card blocks must match a validated feed VERBATIM (curate, never alter)
                           2. numbers in a template block must trace to the signals THAT BLOCK
                              declares — no issue-wide pool, no fallback (see below)
issues/merged_issue.py   Post 1 — one generic generator, pipeline-parameterized
issues/deep_read.py      Post 2 — cross-system, reads the opportunities feed
```

A failing issue is **never written** (self-gating). Negative-tested: invented template
number → fail; reworded card → fail. Unit tests: `analysis/tests/test_newsletter.py`.

### The gate was rescoped 2026-07-21 — and why that mattered

Measured with `analysis/measure_groundedness.py`, the original gate caught **0%** of
injected numbers. It passed 9.1%, 47.3% and 812.6% into a body paragraph. Not a bug in
the check — a bug in its ground truth: one pool of every signal the issue declared
(735 values), matched with the card policy's ratio grounding, accounts for essentially
any number. It had passed every hand-written negative test since it was built, because
those test the numbers the author already suspects.

Now: **each block declares its own signals** (`{"signals": [...]}`, or `"signal"` per
statgrid item) and is judged only by those; a block that declares none grounds nothing;
tolerance is `core.traceability.DISTRIBUTION` (rounding width, no ratios); and values
are grounded through `fmt_value` itself, so "₹2.9L Cr" is accepted because the renderer
produced it. **100% / 99.5% catch, 0 false rejections, output byte-identical.**

Two rules for anyone editing the generators:
- **A block that states a number must declare its signals.** No declaration means no
  grounding, which is correct — connective prose carries no figures.
- **A block that counts the document rather than the data** ("…and 10 more on the
  dashboard") is marked `"meta": True`. Explicit at the point of authorship, so the
  exemption is auditable.

## Voice rules (template strings)

Simple Indian conversational English. Short sentences. No consulting-speak (leverage,
robust, structural tailwind, deepening, ecosystem…). Statuses render via
`STATUS_WORD` (accelerating / growing steadily / slowing / falling) — never raw
analyst statuses. Card prose passes through verbatim from the validated feeds; if its
tone needs fixing, fix the **eval prompt** upstream (next cycle), never the card text here.

## Publishing workflow (per cycle)

```
□  Ingestion gate green for the release (this regenerates every input this layer reads)
□  python3 analysis/distribution/issues/merged_issue.py [--pipeline atm_pos]
□  Open output/release_read_*.html in a browser → select all → copy → paste into Substack
□  Add charts manually in Substack (screenshot the dashboard section, or skip)
□  Publish within 24h of the RBI release
□  ~2 weeks later: python3 analysis/distribution/issues/deep_read.py → same paste flow
□  Update signal_registry.json if a published signal was confirmed/refuted (editorial record)
```

## Files

| File | Purpose |
|---|---|
| `distribution_sources.py` | Data layer, shared with LinkedIn slots |
| `longform_render.py` | md + Substack-HTML renderers |
| `validate_distribution.py` | Traceability gate (`check_doc` + `check_slate`) |
| `issues/merged_issue.py` | Post 1 generator |
| `issues/deep_read.py` | Post 2 generator |
| `signal_registry.json` | Editorial record of every signal ever published (kept from v1) |
| `output_longform/` | Rendered issues (`release_read_*`, `deep_read_*`) + v1 history |
| `../legacy/newsletter_v1/` | Retired v1: config-driven generator, LinkedIn/images scripts |
