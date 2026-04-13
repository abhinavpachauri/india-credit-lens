# India Credit Lens — Root Context

> Read this file at the start of every session. It is the single source of truth for
> project state, rules, and build priorities.
> Full strategy detail: `STRATEGY_PLANNER.md`

---

## What This Is

India Credit Lens (`indiacreditlens.com`) is a public intelligence platform that turns
Indian regulatory credit reports into structured, executive-level insights for lending
professionals — NBFCs, banks, fintechs, PE/VC funds.

**Model:** BankRegData (US) — 2-person SaaS on public regulatory data, 1,275+ clients.
**Differentiator:** Not just metrics. A causal model layer that explains *why* credit
moved, not just that it moved. Structured as a content ladder from free (LinkedIn) to
paid (product intelligence subscriptions and consulting).

---

## Decision Filter

Before any feature, report, content, or technical decision — ask:

1. Does it build Abhinav's **expert positioning** in the Indian lending ecosystem?
2. Does it attract **CPOs, CROs, credit analysts, PE/VC** at NBFCs/banks/fintechs?
3. Does it move toward a **monetisable asset** (consulting, CPO role, or SaaS subscriber)?

If the answer to all three is no — deprioritise it.

---

## Current Platform State (April 2026)

| Component | Status |
|---|---|
| RBI SIBC dashboard | **Live** — 7 sections, 45 annotations, interactive charts |
| SEO layer | **Live** — metadata, OG image, sitemap, JSON-LD |
| LinkedIn carousel generator | **Live** — `analysis/carousel/generate_carousel.py` |
| Free newsletter generator | **Live** — `analysis/newsletter/generate_newsletter.py` |
| system_model.json (Jan 2026) | **Live** — `analysis/rbi_sibc_2026-02-27/system_model.json` |
| report_analysis_prompt.md | **Live** — `analysis/report_analysis_prompt.md` |
| System View dashboard tab | Planned |
| Monthly Digest generator | Planned |
| Gold Loan Monitor page | Planned |
| Email/Substack CTA on dashboard | Planned |

---

## The Content Ladder

Every output lives on this ladder. Each rung CTAs to the rung directly above — never skip.

```
① LinkedIn Carousel (PDF)        FREE    Awareness, top of funnel
        ↓  "read the full analysis"
② Free Newsletter (Substack)     FREE    Email capture, engagement
        ↓  "explore all signals on the dashboard"
③ Dashboard (indiacreditlens.com) FREE   Depth, credibility, SEO
        ↓  "get the full system model and lender strategy"
④ Monthly Digest (Substack paid) PAID    First monetisation — ₹999–1,999/month
        ↓  "get product-specific intelligence"
⑤ Product Intelligence (SaaS)   PAID    ₹25–75k/year per product monitor
        ↓  "let's apply this to your context"
⑥ Consulting Mandates            PAID    ₹5–15L/engagement
```

---

## Four Outputs Per Report (Non-Negotiable)

Every report analysis runs in one Claude pass and produces four outputs:

```
sections.json + PDF
  ├─ Output 1: ANNOTATIONS        → web/lib/reports/[id].ts       (dashboard)
  ├─ Output 2: Markdown docs       → analysis/[id]_[date]/         (human-readable)
  │            gaps.md + insights.md + opportunities.md
  ├─ Output 3: system_model.json   → analysis/[id]_[date]/         (causal model)
  └─ Output 4: newsletter_config.json → analysis/newsletter/       (content generators)
```

`system_model.md` is **retired**. `system_model.json` is the single source of truth.
See `analysis/report_analysis_prompt.md` for the full prompt and output schemas.

---

## The Generator Pipeline

All content outputs are Python scripts reading JSON configs.
**Claude produces configs once. Regeneration is script-only — no Claude needed.**

| Script | Input | Output |
|---|---|---|
| `analysis/carousel/generate_carousel.py` | `carousel_config.json` | `carousel_YYYY-MM-DD.pdf` |
| `analysis/newsletter/generate_newsletter.py` | `newsletter_config.json` | `newsletter_YYYY-MM-DD.md` |
| `generate_digest.py` *(planned)* | `system_model.json` | `digest_YYYY-MM-DD.md` + PDF |
| `generate_mermaid.py` *(planned)* | `system_model.json` | `system_YYYY-MM-DD.mmd` |

---

## The System Model (`system_model.json`)

The causal graph of the credit system per report period. Powers all three renderers
(newsletter, diagram, dashboard System View tab).

**Node tiers:** `driver` / `sector` / `gap` / `opportunity` / `pressure`

**Edge types:** `causes` / `suppresses` / `reroutes_demand_to` / `reinforces` /
`creates_risk` / `creates_opportunity` / `is_data_gap` / `creates_gap` / `signals` / `contrast`

**Critical rule:** `annotation_ids` in every node must exactly match `id` fields from
Output 1 (ANNOTATIONS). Copy-paste — never retype or reinterpret.

---

## Product Intelligence — The SaaS Layer

Product monitors are cross-report dashboards organised by credit product.
Lenders think by product, not by report source.

| Monitor | Sources | Priority |
|---|---|---|
| **Gold Loan Monitor** | RBI SIBC + CIBIL + RBI FSR + CRIF | **P1** |
| **MSME Credit Monitor** | RBI SIBC + SIDBI + CRIF + CIBIL | **P1** after SIDBI |
| **Housing Finance Monitor** | RBI SIBC PSL + CIBIL + NABARD | P2 |
| **Personal Credit Health** | CIBIL + RBI SIBC | P2 |
| **Supply Chain Finance** | RBI SIBC + TReDS | P3 |

**Free:** current period, single-report, 3 metrics (SEO + discovery)
**Paid ₹25–75k/year:** cross-report, full history, quarterly PDF, threshold alerts

---

## Report Pipeline

When adding a new report — ask first: which product monitors does it feed?

| Report | Status | Feeds |
|---|---|---|
| RBI SIBC | **Live** | Gold, MSME, Housing, Personal, Supply Chain |
| CIBIL Quarterly | Next (P1) | Gold, MSME, Housing, Personal |
| RBI BSR-1 Quarterly | Next (P1) | All monitors |
| CRIF MSME Report | Next (P2) | MSME, Supply Chain |
| SIDBI MSME Pulse | Next (P2) | MSME |
| NABARD | Later | Housing, MSME |
| RBI FSR | Later | Gold, NBFC risk |
| PLFS | Later | Personal, Housing |

---

## Authoring Rules

### Visual outputs — ASCII layout first (always)

For any visual output (carousel slide, newsletter layout, dashboard panel, chart,
OG image, product monitor page):

1. **ASCII layout first** — sketch proportions, zones, text hierarchy, sample content
2. **Get explicit approval** — do not write code until layout is confirmed
3. **Then implement** — translate approved ASCII directly into code

### Analysis outputs — annotation_ids are sacred

Never reinterpret annotations in system_model.json. The JSON organises and connects
what already exists in the ANNOTATIONS object. The only new content in Output 3
is driver nodes and edges.

### Git / deployment

- Never auto-push to GitHub
- Always run `npm run build` + `tsc --noEmit` first
- Show results and wait for explicit confirmation before `git push`

### Token efficiency

- Claude produces configs and JSON once per report
- All regeneration is script-only (carousel, newsletter, digest, diagram)
- system_model.json eliminates re-reading prose for every render pass

---

## Analytical Framework (for every report)

### Four checks per report

| Check | Question |
|---|---|
| **Metric selection** | Is the cited metric the most honest one? Does growth rate hide an absolute gap? |
| **Structural exclusions** | What populations are outside the dataset? Is it presented as representative when it isn't? |
| **Headline inflation** | Is a finding presented as segment-specific when it applies to all? Are baselines cherry-picked? |
| **Framing gaps** | What questions does the data raise that the report doesn't ask? |

### Systems view (required in every analysis)

| Element | Question |
|---|---|
| **Stocks** | What is accumulating? Current levels and trends? |
| **Flows** | What drives entry, growth, exit? Where are flows stalled? |
| **Reinforcing loops** | What compounding dynamics exist? What accelerates what? |
| **Balancing constraints** | What structural ceilings exist? What prevents growth? |
| **Delays** | What risks hidden today will surface in 12–36 months? |
| **Leverage points** | Where do small interventions produce outsized structural change? |

Systems view explains **why** the numbers look the way they do — not just what they are.
In the new pipeline, this is captured as `driver` nodes and `edges` in `system_model.json`.

---

## Key Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | This file — root context, auto-loaded |
| `STRATEGY_PLANNER.md` | Full strategy, revenue model, phased roadmap |
| `PIPELINE_ARCHITECTURE.md` | **Pipeline architecture, directory structure, stage checklist** |
| `analysis/report_analysis_prompt.md` | Master prompt for all report analyses |
| `analysis/run_evals.py` | Master eval orchestrator — run after every pipeline stage |
| `analysis/extract_sibc.py` | Stage 1: SIBC xlsx → sections.json |
| `analysis/generate_merge.py` | Stage 5: per-period sections.json[] → sections_merged.json |
| `analysis/rbi_sibc/timeline.json` | Registry of all ingested periods |
| `analysis/rbi_sibc/2026-02-27/` | Jan 2026 per-period outputs (sections, model, subsystems, docs) |
| `analysis/rbi_sibc/merged/` | Merged outputs across all periods |
| `analysis/newsletter/generate_newsletter.py` | Substack newsletter generator (script-only) |
| `analysis/newsletter/newsletter_config.json` | Newsletter content (edit per issue) |
| `web/lib/reports/rbi_sibc.ts` | Dashboard annotations — RBI SIBC (live, from merged) |
| `web/CLAUDE.md` | Web-specific context (Next.js, Vercel) |

---

## Next Builds (in order)

1. Connect `indiacreditlens.com` domain on Vercel
2. Add Substack/email CTA to dashboard footer
3. Publish Jan 2026 carousel + newsletter (screenshots needed, content ready)
4. System View tab on dashboard (interactive diagram from `system_model.json`)
5. `generate_digest.py` — premium monthly PDF
6. Gold Loan Monitor page (free version — data already in SIBC)
7. BSR-1 Quarterly — next report to add
8. CIBIL Quarterly — unlocks cross-report Gold Loan Monitor
