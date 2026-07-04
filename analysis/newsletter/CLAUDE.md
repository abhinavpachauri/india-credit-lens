# Newsletter — India Credit Lens (v2)

> Execution context for the professional Substack newsletter (indiacreditlens.substack.com).
> Audience: credit & product professionals in fintech/lending. NEVER mentions tickers/stocks —
> that content belongs to the retail publication (see `ICL_RETAIL_90DAY_PLAN.md`).

---

## What this is (v2, rebuilt 2026-07-04)

A **deterministic rendering layer** over the same gate-validated artifacts the dashboards
use. No LLM calls, no hand-authored stats, no retired artifacts. Two posts per data cycle:

| Post | Script | Published | Content |
|---|---|---|---|
| **Release read** | `generate_release_read.py --pipeline {sibc\|atm_pos}` | within 24h of the RBI release | L1: headline stats, status flips vs prior period, new trackers, one validated insight card per section |
| **Deep read** | `generate_deep_read.py` | mid-cycle (~2 weeks later) | L2/L3: cross-system ecosystem cards with computed basis, live openings, watch-outs |

Both are prepared from the same gate run; publishing is staggered so one monthly cycle
gives a fortnightly presence.

**v1 (config-authored + mermaid images + LinkedIn packages) is retired** to
`analysis/legacy/newsletter_v1/` — it depended on subsystems.json and Stage-4 mermaid,
both retired in the v4.0 cutover. LinkedIn posts are now written by the user in their
own voice (deliberate decision, 2026-07-03) — there is no LinkedIn generator.

---

## Architecture (mirrors the pipeline discipline)

```
newsletter_sources.py    data layer — reads ONLY validated artifacts:
                           signals.db                → headline stats, status flips, new trackers
                           sibc_l1_annotations.json  → SIBC cards   (Check 2g validated)
                           atm_pos_insights.json     → payments cards (Stage 4c validated)
                           opportunities_feed.json   → L2/L3 cards  (Check 4f validated)
newsletter_render.py     render layer — typed blocks → .md (canonical) + .html (Substack paste)
validate_newsletter.py   the gate — check_doc() runs BEFORE any file is written:
                           1. card blocks must match a validated feed VERBATIM (curate, never alter)
                           2. numbers in template blocks must trace to the DECLARED signals'
                              flat numbers (scoped like Check 4f — period-wide is vacuous)
generate_release_read.py Post 1 — one generic generator, pipeline-parameterized
generate_deep_read.py    Post 2 — cross-system, reads the opportunities feed
```

A failing issue is **never written** (self-gating). Negative-tested: invented template
number → fail; reworded card → fail. Unit tests: `analysis/tests/test_newsletter.py`.

## Voice rules (template strings)

Simple Indian conversational English. Short sentences. No consulting-speak (leverage,
robust, structural tailwind, deepening, ecosystem…). Statuses render via
`STATUS_WORD` (accelerating / growing steadily / slowing / falling) — never raw
analyst statuses. Card prose passes through verbatim from the validated feeds; if its
tone needs fixing, fix the **eval prompt** upstream (next cycle), never the card text here.

## Publishing workflow (per cycle)

```
□  Ingestion gate green for the release (this regenerates every input this layer reads)
□  python3 analysis/newsletter/generate_release_read.py [--pipeline atm_pos]
□  Open output/release_read_*.html in a browser → select all → copy → paste into Substack
□  Add charts manually in Substack (screenshot the dashboard section, or skip)
□  Publish within 24h of the RBI release
□  ~2 weeks later: python3 analysis/newsletter/generate_deep_read.py → same paste flow
□  Update signal_registry.json if a published signal was confirmed/refuted (editorial record)
```

## Files

| File | Purpose |
|---|---|
| `newsletter_sources.py` | Data layer (see above) |
| `newsletter_render.py` | md + Substack-HTML renderers |
| `validate_newsletter.py` | Traceability gate (`check_doc`) |
| `generate_release_read.py` | Post 1 generator |
| `generate_deep_read.py` | Post 2 generator |
| `signal_registry.json` | Editorial record of every signal ever published (kept from v1) |
| `output/` | Rendered issues (`release_read_*`, `deep_read_*`) + v1 history |
| `../legacy/newsletter_v1/` | Retired v1: config-driven generator, LinkedIn/images scripts |
