# India Credit Lens — Strategy Planner
> Applying the BankRegData Model to the Indian Lending Intelligence Market

**Version:** 2.0 | **Updated:** April 2026 | **Author:** Abhinav
**Status:** Foundation built → Content ladder live → Product monitors next

---

## 1. The BankRegData Blueprint (What We're Adapting)

BankRegData is a 16-year-old, 2–3 person US company that turned publicly available FFIEC/FDIC call report data into a subscription SaaS platform with 1,275+ clients and 10,800+ daily users. No funding raised. Private. Profitable.

**Their formula:**
```
Public Regulatory Data  +  Pre-processed Metrics  +  Peer Benchmarking  +  Alerts
  = Subscription Revenue from banking professionals
```

**Why it worked:**
- Data is free and public — but useless without parsing
- 525+ pre-calculated ratios saved analysts days of work
- Automated threshold alerts created stickiness
- Product-specific dashboards sold to relevant teams (not just "the whole bank")
- Targeted a niche who had budget and pain

**India Credit Lens adapts this as:**
```
RBI + CRIF + CIBIL + SIDBI + NABARD + PLFS + more
  + Systems View  +  Signal vs Noise  +  Strategic Opportunities  +  Causal Model
  = Intelligence Platform for Indian Lending Professionals
```

**The key evolution from BankRegData:** We add a causal layer (system_model.json) that connects data signals to macro drivers. BankRegData shows you what happened. India Credit Lens shows you what happened, why, and what to do about it.

---

## 2. The Indian Market Context

### Why India is a better opportunity than the US right now

| Factor | US (BankRegData) | India (Credit Lens) |
|---|---|---|
| Regulatory data | Highly structured, XBRL, API-ready | PDF-heavy, fragmented, harder to parse |
| Competition | Established (S&P, Moody's, Bloomberg) | Near zero at this interpretation layer |
| Market size | Mature credit market | Fastest growing credit market globally |
| Digital penetration | High, saturated | Growing rapidly — fintech boom |
| Report publishers | FFIEC, FDIC (2 sources) | RBI, CRIF, CIBIL, SIDBI, NABARD, PLFS, Sa-Dhan, MFI Network (8+ sources) |
| Insight hunger | Moderate (data already structured) | High (data is raw PDFs, no synthesis) |

### The gap no one is filling
- **DBIE** (RBI's own portal) = data warehouse, no interpretation
- **Bloomberg/Refinitiv** = too expensive, not India lending-specific
- **Consultancy reports** = expensive, infrequent, generic
- **LinkedIn thought leaders** = opinions without data
- **India Credit Lens** = structured, visual, strategic intelligence + causal model at low cost

---

## 3. The Content Ladder (How Readers Become Customers)

Every piece of content sits on a ladder. The goal is to pull readers up the ladder over time. Each rung has one CTA — to the rung directly above it. Never skip rungs.

```
① Free Newsletter (Substack)
   System narrative + 2 signals + 1 gap + 1 opportunity + what to watch
   FREE | Email capture, engagement | Monthly

        ↓  "explore all 42 signals on the dashboard"

② Dashboard (indiacreditlens.com)
   All annotations, all charts, interactive System View tab
   FREE | Depth, credibility, SEO | Always live

        ↓  "get the full system model and lender strategy"

③ Monthly Digest (Substack paid)
   Full causal narrative + forward view + lender strategy + cross-report signals
   PAID ₹999–1,999/month | First monetisation rung | Monthly PDF

        ↓  "get product-specific intelligence for your segment"

④ Product Intelligence Pages (SaaS)
   Cross-report dashboards per credit product (Gold, MSME, Housing etc.)
   PAID ₹25–75k/year per product | Institutional subscriptions | Always live

        ↓  "let's apply this to your specific lending context"

⑤ Consulting Mandates
   Per-engagement strategic analysis for NBFCs, banks, fintechs, PE/VC
   PAID ₹5–15L/engagement | High margin, low volume | Opportunistic
```

---

## 4. Distribution Strategy (LinkedIn → Substack Funnel)

The content ladder only works if content reaches the right people. Distribution fills the top of the funnel — LinkedIn drives awareness, Substack captures emails. The website provides SEO discoverability and credibility but is not an active funnel step at this stage.

### The funnel in practice

LinkedIn short-form post → Substack free subscription → Substack paid digest → consulting enquiry

All LinkedIn CTAs point to Substack. Never to the website.

### One report = 8–10 posts, spread over 4–6 weeks

Each SIBC release produces 6 subsystem themes and 8 cross-period insights — each is a standalone LinkedIn post. Short-form text posts drive awareness and funnel to the newsletter. No content drought, no new analysis needed between posts.

### Insight-first framing (non-negotiable)

Every post leads with the finding, never the source.

- ❌ "Feb 2026 SIBC analysis is out"
- ✅ "Gold loans tripled in 24 months while credit cards flatlined. Two products, one RBI decision."

### Short-form format

3–5 lines. One specific number. One implication for lenders. One Substack CTA. Text posts with precise data points deliver high engagement per unit of effort.

### RBI event-reactive posts

When RBI publishes a monetary policy decision, a new circular, or a relevant report, respond within 24 hours with a data point from the existing SIBC analysis. `rbi_monitor.py` automates daily RSS checks and alerts when relevant releases land. Reactive posts have the highest engagement — they meet the audience when attention is already high.

### Data-backing contract

Every claim in a distribution post must trace to a validated pipeline output — a specific insight from `insights.md`, a node stat from `system_model.json`, or a series value from `sections_merged.json`. Posts are not generated from memory or raw data. This is the same discipline as `validate_content.py` for annotations, applied to public distribution content.

Full execution rules are in `analysis/newsletter/CLAUDE.md`.

---

## 5. Four Outputs Per Report (Non-Negotiable Framework)

Every report analysed in a single Claude pass produces four structured outputs: dashboard annotations, markdown docs (insights / gaps / opportunities), `system_model.json` (causal graph), and `newsletter_config.json`. This single-pass discipline keeps analysis consistent and makes all content regeneration script-only — no Claude cost after the initial analysis pass.

Full output schemas, file naming conventions, and validator commands are in `analysis/report_analysis_prompt.md` and `PIPELINE_ARCHITECTURE.md`.

---

## 6. The Generator Pipeline (Config-Driven, No Claude to Regenerate)

Claude produces a JSON config once per report. All content outputs — newsletter markdown, monthly digest, mermaid diagrams — are regenerated by Python scripts reading that config. Editing the config and re-running the script is the full regeneration workflow. No Claude token cost after the initial analysis pass.

Full script inventory, input/output paths, and current status are in `PIPELINE_ARCHITECTURE.md`.

---

## 7. The System Model (The Causal Layer — Our Differentiator)

Every report period produces a `system_model.json` — a structured causal graph connecting macro drivers to sector outcomes to opportunities, risks, and data gaps. Every node links to exact annotation IDs from the dashboard — no reinterpretation, pure structural indexing.

Each driver, opportunity, pressure, and gap node carries a `claim_type` field — `data` (sourced directly from the report), `inference` (sourced externally via Stage 6b `source_claims.py`), or `hypothesis` (flagged but not blocked). This source verification layer — enforced by `validate_claims.py` as a pipeline gate — separates structured intelligence from opinion.

This JSON powers three renderers: the newsletter generator, the mermaid diagram generator, and the planned System View dashboard tab. Full node/edge schema and annotation_id constraints are in `analysis/report_analysis_prompt.md`.

**What makes this the paid layer:** BankRegData shows you metrics. The system model shows you why the metrics moved, what connects them, and what to watch for next — with verifiable sourcing on every claim. That causal intelligence is what the Monthly Digest sells.

---

## 8. Product Intelligence — The SaaS Monetisation Layer

The paid SaaS tier is **product-specific intelligence pages** — cross-report views organised by credit product. Lenders think by product, not by report source.

### Five priority product monitors

| Monitor | What it tracks | Report sources | Build priority |
|---|---|---|---|
| **Gold Loan Monitor** | Market size, LTV risk, household stress, delinquency | RBI SIBC + CIBIL + RBI FSR + CRIF | **P1** — SIBC data live now |
| **MSME Credit Monitor** | Size-wise growth, bureau gaps, formalisation signals | RBI SIBC + SIDBI Pulse + CRIF + CIBIL | **P1** — after SIDBI added |
| **Housing Finance Monitor** | PSL housing, PMAY pipeline, Tier 3/4 distribution | RBI SIBC PSL + CIBIL + NABARD | P2 |
| **Personal Credit Health** | Cards, consumer durables, fintech displacement | CIBIL + RBI SIBC | P2 |
| **Supply Chain Finance** | Engineering, trade credit, TReDS flows | RBI SIBC + TReDS data | P3 |

### Free vs Paid line per monitor

```
FREE (SEO + discovery):
  Current period only · Single-report signals · 3 key metrics · Public

PAID ₹25–75k/year (institutional):
  Cross-report aggregated view · Full historical data
  Quarterly PDF briefing (generated from system_model.json)
  Email alert when tracked signal crosses threshold
  PSLC opportunity flags for PSL-eligible lenders
```

### Pricing rationale
BankRegData: 1,275 clients, estimated $2–5M USD ARR with 2–3 people.
India equivalent at 5–10x lower pricing: 50–200 institutional subscribers × ₹25–75k/year = **₹1.25–15Cr ARR at scale**.

---

## 9. Report Sources — Full Pipeline with Product Monitor Mapping

### Tier 1 — Active pipeline (feeds product monitors)

| Report | What it covers | Status | Feeds |
|---|---|---|---|
| **RBI SIBC** | Bank credit by sector/industry | **Live** | Gold, MSME, Housing, Personal, Supply Chain |
| **CIBIL Quarterly** | Retail credit health, delinquency | Next (P1) | Gold, MSME, Housing, Personal |
| **RBI BSR-1 Quarterly** | Bank-level credit — most granular | Next (P1) | All monitors |
| **CRIF MSME Report** | Commercial credit, bureau penetration | Next (P2) | MSME, Supply Chain |
| **SIDBI MSME Pulse** | MSME access gaps, stress, underserved | Next (P2) | MSME |
| **NABARD** | Agriculture, rural credit | Later | Housing, MSME |
| **RBI FSR** | Financial stability, systemic risk | Later | Gold, NBFC risk |
| **PLFS** | Labour force income — demand-side signal | Later | Personal, Housing |

### Tier 2 — Macro and sentiment signals (evaluated April 2026, ingestion planned)

Draft ingestion plans for all sources below are in `DATA_SOURCES.md`. Pipeline redesign required before ingestion begins. All 9 sources passed the decision filter.

| Report ID | Report | What it adds | Product monitors it feeds |
|---|---|---|---|
| `rbi_walr` | Lending and Deposit Rates of SCBs | Credit pricing — WALR/EBLR by sector | All monitors (pricing layer) |
| `rbi_bls` | Bank Lending Survey | Banker demand sentiment + terms tightening by sector | All monitors (forward view) |
| `rbi_uccs` | Urban Consumer Confidence Survey | Urban household confidence, income, spending net responses | Personal Credit Health, MSME |
| `rbi_iesh` | Inflation Expectations Survey of Households | Urban household inflation expectations (current, 3M, 1Y) | Personal Credit Health, Housing |
| `rbi_rccs` | Rural Consumer Confidence Survey | Rural confidence — rural/urban divergence signal | Gold Loan, MSME, Housing |
| `rbi_spf` | Survey of Professional Forecasters | Repo rate + CPI + credit growth professional consensus | All monitors — **web scrape pipeline** |
| `rbi_atm_pos` | Bank-wise ATM/POS/Card Statistics | Card infrastructure + credit/debit transaction volumes | Consumer Credit dashboard |
| `rbi_ppi` | Entity-wise PPI Statistics | EMI card issuance + BNPL wallet proxy | Consumer Credit dashboard |
| `rbi_treds` | Entity-wise TReDS Statistics | MSME invoice financing velocity | MSME Credit Monitor, Supply Chain Finance |

### Adding a new report — always ask first:
1. Which product monitors does it feed?
2. Does it unlock cross-report signals that aren't possible without it?
3. Build data pipeline → run analysis prompt → update product monitor pages

---

## 10. Revenue Model

### Tier structure

| Tier | Product | Price | Target customer |
|---|---|---|---|
| **Free** | Dashboard + free newsletter | ₹0 | Analysts, students, discovery |
| **Digest** | Monthly Digest (Substack paid) | ₹999–1,999/month | Senior analysts, consultants, individual professionals |
| **Product Monitor** | Per-product intelligence page | ₹25–75k/year | NBFC/bank/fintech product and credit teams |
| **Team** | Multi-product + API access | ₹1.5–3L/year | Strategy teams, fintechs with multiple product lines |
| **Enterprise** | Full suite + custom reports + white-label | ₹5–15L/year | Large banks, PE funds, consulting firms |
| **Consulting** | Per-engagement | ₹5–15L/mandate | NBFCs, fintechs needing custom intelligence |

### Revenue scenarios

| Scenario | Timeline | Key assumptions | ARR |
|---|---|---|---|
| Conservative | Year 1 | 50 Substack paid + 1 consulting project | ₹8–12L |
| Moderate | Year 2 | 200 Substack paid + 5 product monitor subscribers | ₹40–60L |
| Target | Year 3 | 500 Substack paid + 20 product monitors + 1 enterprise | ₹1.5–2Cr |
| Scale | Year 4–5 | 100+ institutional + API + data licensing | ₹4–5Cr |

---

## 11. Phased Roadmap

### Phase 0: Foundation ✅ COMPLETE
- [x] Dashboard live on Vercel — RBI SIBC, 7 sections, 42 annotations (Jan–Feb 2026 merged)
- [x] SEO layer — metadata, OG image, sitemap, JSON-LD
- [x] Analysis pipeline — report_analysis_prompt.md, four-output framework
- [x] system_model.json schema — nodes, edges, annotation_ids, claim_type fields
- [x] Stage 6b live — source_claims.py enriches nodes with external citations
- [x] Check 2c live — validate_claims.py gates claim_type + source on all nodes
- [x] Free newsletter generator — delta_v2 format (HELD / CHANGED / NEW), Substack markdown
- [x] RBI SIBC pipeline — Jan 2026 and Feb 2026 periods ingested, merged, and live
- [x] New data source evaluation — 9 sources assessed, draft plans in DATA_SOURCES.md

---

### Phase 1: Content Engine → Email List (Now — Month 6)
**Goal: 500+ Substack subscribers, 2,000+ LinkedIn followers, first consulting enquiry**

- [ ] Publish newsletter for every new RBI SIBC release
- [ ] Add email/Substack CTA to dashboard footer
- [ ] Add BSR-1 Quarterly (next report — most granular bank-level data)
- [ ] Add CIBIL Quarterly (unlocks Gold Loan Monitor MVP)
- [ ] System View tab on dashboard (interactive causal diagram)
- [ ] Connect indiacreditlens.com domain on Vercel

**Investment:** Time only
**Success metric:** 500 newsletter subscribers, 1 consulting enquiry

---

### Phase 2: First Monetisation (Month 6–12)
**Goal: ₹5–15L ARR, validate paid content model**

- [ ] Launch Monthly Digest on Substack paid (₹999–1,999/month)
  - generate_digest.py producing premium PDF from system_model.json
  - Full system narrative + forward view + lender strategy section
- [ ] Launch Gold Loan Monitor (first product intelligence page)
  - Free: 3 metrics, current period, single report
  - Paid: cross-report (SIBC + CIBIL), full history, quarterly PDF, alerts
- [ ] Add SIDBI MSME Pulse — unlocks MSME Monitor MVP
- [ ] First paid consulting project (close via LinkedIn + dashboard credibility)

**Investment:** ₹10–30K (tooling, design)
**Revenue target:** ₹8–15L ARR

---

### Phase 3: Product Monitor Suite (Month 12–24)
**Goal: ₹50L–1Cr ARR, systematic institutional sales**

- [ ] MSME Credit Monitor live (cross-report: SIBC + SIDBI + CRIF + CIBIL)
- [ ] Housing Finance Monitor live
- [ ] Personal Credit Health Monitor live
- [ ] Signal alert system — email when tracked metric crosses threshold
- [ ] API access for Team tier
- [ ] Approach 2–3 NBFCs / fintechs for enterprise pilot
- [ ] Peer benchmarking feature (BankRegData's killer feature — compare lenders)
- [ ] Quarterly "India Lending Intelligence" live event / webinar

**Investment:** ₹50K–2L (possible part-time analyst hire)
**Revenue target:** ₹50L–1Cr ARR

---

### Phase 4: Platform Business (Year 3–5)
**Goal: ₹3–5Cr ARR, defensible moat**

- [ ] Full API marketplace — fintechs integrate India Credit Lens signals
- [ ] AI-assisted report parsing (new reports auto-processed)
- [ ] State/district-level credit intelligence layer
- [ ] Supply Chain Finance Monitor (TReDS data integration)
- [ ] Enterprise white-labelling for consulting firms
- [ ] International expansion — SE Asia credit intelligence (same framework)

---

## 12. The Moat (What Makes This Hard to Copy)

| Moat Layer | Description | Strength today |
|---|---|---|
| **Data curation** | Manual + AI parsing of 8+ regulatory sources | Growing |
| **Causal model layer** | system_model.json — not just metrics, but why | Unique |
| **Framework consistency** | Same 4-output lens applied to all reports | Established |
| **Author credibility** | Abhinav's lending domain expertise | Strong |
| **Historical depth** | Year-over-year trend library that compounds | Building |
| **Generator pipeline** | Config-driven content — scales without manual effort | Live |
| **Network effects** | More subscribers → better peer benchmarks | Future |

---

## 13. Monetization Roadmap

The reasoning chain — fact → inference → hypothesis — is the proprietary asset.
The free dashboard gives conclusions. Paid tiers give the reasoning.

### Free tier (current)
- Dashboard: 7 sections, 48+ annotations, causal system model
- Newsletter (Substack free): top 6 signals per issue with explained reasoning
- Dashboard claim-type badge: `DATA` / `INFERRED` / `HYPOTHESIS` on each annotation
  — planned for next build cycle, no engineering cost

### Paid Tier 1 — Premium Substack (₹2,000–5,000/mo or $25–50/mo)
*Target: 50+ free subscribers before launching*
- Full annotation set (all 48+, not just the 6 newsletter signals)
- `basis` chain per annotation — fact → inference → hypothesis, structured
- System model narrative: causal diagram explained in prose per section
- What changed vs prior period: annotation diff, upgraded/downgraded signals
- Trigger: when newsletter hits 50 free subscribers

### Paid Tier 2 — Quarterly Analyst Report (PDF, ₹15,000–25,000/report or ₹50,000/year)
*Target: NBFCs, banks, PE/VC funds wanting board-ready credit environment briefing*
- Full system model as a structured deliverable: causal diagram + all basis chains
- Formatted for credit committee — defensible, cited, claim-typed
- Every claim traces to a data point or a named external source
- Consulting entry product: a NBFC paying for this report is 3 calls from a retainer
- Trigger: after 2 newsletter issues published, cold outreach to 10 target NBFCs

### Paid Tier 3 — API / Structured Data (SaaS, $200–500/mo per seat)
*Target: fintechs and NBFCs wanting to embed credit signals into internal tools*
- Structured JSON: annotations + basis chains + claim_type, per RBI cycle
- Powers: credit appetite frameworks, portfolio review tools, lending playbooks
- The annotation schema is already machine-readable — `basis` field makes it
  genuinely useful structured intelligence, not just text
- Trigger: 3+ inbound requests for data access (signals product-market fit)

### Sequencing rule
Consulting monetises first (no product build required). Substack paid is parallel.
API is last — requires proven signal quality and inbound demand.

---

## 14. Key Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| RBI / regulators restrict data use | Low | All data is public; analysis and interpretation is original work |
| Low initial paying subscribers | Medium | Consulting monetises first; Substack paid is parallel, not dependent |
| Report publishing is slow/manual | Medium | Generator pipeline already reduces this — parsers next |
| Competitor launches similar product | Medium | Causal model + personal brand + 2-year head start is the moat |
| Platform costs spiral | Low | Vercel free tier handles early scale; infra cost <₹5K/mo until ₹1Cr ARR |
| Token costs for analysis | Low | Config-driven pipeline means Claude runs once per report, not per output |

---

## 14. Immediate Next Actions

See `CLAUDE.md → Next Builds` for the current prioritised execution queue across both tracks (Track A: content & platform; Track B: multi-source pipeline). This document holds the strategic roadmap — CLAUDE.md holds the live task list.

---

## 14. The Positioning Statement

> **India Credit Lens** is the intelligence layer on top of India's public lending data —
> turning fragmented regulatory reports into structured signals, causal models, and
> actionable strategy for anyone building, running, or investing in Indian credit.

---

*Next review: July 2026 | Track against Phase 1 milestones*
*Model inspiration: BankRegData (US) — 1,275 clients, 2–3 people, 16 years, no funding*
