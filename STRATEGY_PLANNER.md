# India Credit Lens — Strategy

> **v3.0 · September 2026 · Author: Abhinav.** Strategy only: who we serve, what we sell, why it
> is defensible, and in what order it gets monetised. **What is being built now is in `PLAN.md`;
> standing rules are in `DECISIONS.md`; how the system works is in `ARCHITECTURE.md`.** This
> document changes when the strategy changes, not when a feature ships. v2.1 (May 2026) described
> a pipeline that has since been rebuilt; its execution sections were removed and are in git history.

---

## 1. Positioning

> **India Credit Lens** is the intelligence layer on top of India's public lending data —
> turning fragmented regulatory releases into structured signals, a causal model that says
> *why* credit moved, and numbers that trace to the source, for anyone building, running or
> investing in Indian credit.

**Decision filter** (every feature, source and piece of content):
1. Does it build expert positioning in the Indian lending ecosystem?
2. Does it attract CPOs, CROs, credit analysts or PE/VC at NBFCs, banks or fintechs?
3. Does it move toward a monetisable asset (consulting, a CPO role, or a SaaS subscriber)?

No to all three → deprioritise.

---

## 2. The model we are adapting: BankRegData

A 16-year-old, 2–3 person, unfunded, profitable US company that turned public FFIEC/FDIC call
reports into a subscription platform (1,275+ clients). Its formula:

```
Public regulatory data + pre-processed metrics + peer benchmarking + alerts
  = subscription revenue from banking professionals
```

It worked because the data is free but useless unparsed, hundreds of precomputed ratios save
analysts days, alerts create stickiness, and it sold to a niche with budget and pain.

**Our adaptation adds one layer BankRegData does not have: the causal model.** BankRegData shows
what happened. We show what happened, why, and what it connects to, with every number traceable.

---

## 3. The market

| Factor | US (BankRegData) | India (Credit Lens) |
|---|---|---|
| Regulatory data | Structured, XBRL, API-ready | Fragmented XLSX/PDF, manual downloads, revisions |
| Competition at the interpretation layer | Established (S&P, Moody's, Bloomberg) | Near zero |
| Credit market | Mature | Among the fastest-growing globally |
| Publishers | 2 (FFIEC, FDIC) | RBI, MoSPI, NABARD, SIDBI, bureaus, SROs — 20+ releases |

**The gap:** DBIE and eSankhyiki are data warehouses with no interpretation; Bloomberg/Refinitiv
are expensive and not India-lending-specific; consultancy reports are infrequent and generic;
LinkedIn commentary has opinions without data. Nobody sits between the raw release and the
decision.

---

## 4. What we sell: the three things an LLM cannot fake

1. **Numbers that trace.** Every published number is checked against the computed signal store
   before it ships. An LLM narrates; it never decides a number. This is the trust layer, and it is
   what makes the rest sellable to a risk officer.
2. **The causal layer.** A system model per source (entities, channels, sourced external forces)
   re-evaluated against the data every release: which drivers are firing, which mixes are being
   *steered* versus *drifting*, where new credit is going relative to where the book sits. Forces
   enter only with a verified source.
3. **Cross-source joins.** Bank credit to NBFCs *and* what NBFCs lend; card counts *and* card
   balances; soon credit *and* the output it finances (MoSPI). No single release can say these.

**The depth-of-job ladder is where the price is:**
*describe the market* (commodity, marketing) → *benchmark a specific player* (mid-ticket, sticky)
→ *inform a specific decision* (high-ticket, defensible). Most output today is "describe". The
money is in moving the engine toward "decide".

---

## 5. Who we serve, and the distribution reality

**Buyers:** credit, product and strategy teams at NBFCs, banks and fintechs; PE/VC in Indian
lending; consultants.

**The reachable network is not the buyer.** The warm graph is tech and fintech product people, not
bank credit leadership. Aggregate bank-credit content posted to that graph under-performs because
it is not that audience's world, not because the insight is weak. Two consequences:
- **Payments is the bridge.** UPI QR vs POS, acquiring concentration and card-market structure are
  fintech-builder content and match the warm network.
- **Bank-leadership credit content needs a non-warm channel** (direct outreach, communities).

**Channel state (Sep 2026):** the dashboard (`indiacreditlens.com`, three sources) is live. Substack
is paused while the author reads a few cycles as a reader. LinkedIn posts are written by the author
in their own voice from verified numbers the platform supplies. X needs its own design.

**Open strategic fork:** (a) bend the content toward the reachable network (fintech and payments
intelligence for builders), or (b) keep the bank-leadership thesis and build a cold channel. They
lead to different products. Undecided.

---

## 6. The content ladder

```
① Free reads — LinkedIn posts, Substack (paused)        awareness, email capture
② Dashboard — indiacreditlens.com                       depth, credibility, SEO     FREE, live
③ Monthly Digest — the reasoning, not just conclusions  first monetisation rung     ₹999–1,999/mo
④ Product intelligence — cross-source view per product  institutional               ₹25–75k/yr
⑤ Consulting — the engine applied to one lender         high margin, low volume     ₹5–15L/mandate
```

Each rung's call to action points to the rung directly above it. **The reasoning chain (fact →
inference → hypothesis) is the proprietary asset:** the free dashboard gives conclusions; paid tiers
give the reasoning.

---

## 7. Product intelligence (the SaaS layer)

Lenders think by product, not by report, so the paid layer is organised by credit product.

| Monitor | What it tracks | Sources | Unlocked by |
|---|---|---|---|
| **Gold Loan** | Size, pace, collateral cycle, NBFC vs bank share | SIBC + NBFC (+ CIBIL, FSR) | live data today; bureau adds risk |
| **MSME Credit** | Size-wise growth, formalisation, access gaps | SIBC + NBFC + SIDBI + MoSPI (ASUSE) | SIDBI / MoSPI |
| **Housing Finance** | PSL housing, bank vs HFC/NBFC, ticket bands | SIBC + NBFC + NABARD | NBFC live |
| **Personal Credit Health** | Cards, consumer durables, the unsecured cycle | SIBC + payments + CIBIL | bureau |
| **Supply Chain Finance** | Trade credit, TReDS flows | SIBC + TReDS | TReDS |

Free: current period, single-source signals, a few key metrics. Paid (₹25–75k/yr): the
cross-source view, full history, a quarterly briefing, threshold alerts.

---

## 8. Data sources

**Principle:** a new source earns its place by the *joins* it unlocks, not by its own content.
Each is ingested through the same manifest-driven gate; a source that needs a new capability
(a cadence, an API pull, a PDF table) pays for it once, for every later source of that kind.

| Status | Sources |
|---|---|
| **Live** | RBI SIBC (bank credit by sector) · RBI ATM/POS/card statistics (payments, 63 banks) · RBI NBFC sectoral deployment |
| **Decided next, in order** | RBI regulatory watch (circulars attached to the model) → BSR-1 (credit by occupation, quarterly) → Lending & Deposit Rates (price of credit) |
| **Candidate: MoSPI eSankhyiki** | The real economy behind the credit: IIP/ISP output, CPI/WPI prices, NAS GVA, PLFS jobs, ASI/ASUSE enterprises. Official REST API. Position in the order undecided (§8.1) |
| **Candidate: RBI Tier 2** | Bank Lending Survey, consumer confidence, inflation expectations, PPI, TReDS |
| **Commercial** | CIBIL, CRIF, Experian, MFIN. Rights differ from public data; needs a licence decision before ingestion |
| **Rejected** | Bank results and presentations as a *source*: unstructured, and per-bank credit is annual only (STRBI). §11 holds the strategic question behind it |

### 8.1 MoSPI eSankhyiki: why it matters

Every live source measures credit. None measures what the credit finances, so the platform can
say "industry credit +20%" and cannot say whether industry produced +4% or +20%. eSankhyiki is
the official home of the other side of that ratio.

| Dataset | Cadence | The lending question | Pairs with |
|---|---|---|---|
| IIP (NIC 2-digit, use-based) | monthly | Is credit to an industry running ahead of its output, or behind it? | SIBC industry by type; consumer durables |
| ISP | monthly | The same for services | SIBC services |
| NAS (GVA by sector; household liabilities) | quarterly / annual | Credit intensity by sector; household debt ratio | SIBC main sectors; NBFC |
| CPI / WPI | monthly | Real credit growth | every credit series |
| PLFS | monthly / quarterly | The income base behind personal-loan growth | personal loans; payments |
| ASI / ASUSE | annual | Formal vs informal enterprise finance | MSME cuts |
| AIDIS (NSS 77) | one-off (2019) | Institutional vs non-institutional household debt, as a baseline | Layer 2 gap nodes |

Access verified 2026-09-24/26: `api.mospi.gov.in` returns JSON (it needs legacy TLS
renegotiation, opted into for that host only). **IIP and WPI were both rebased to 2022-23**, a
base the published API spec does not list: IIP runs April 2023 → July 2026 on it (M+1, the same
lag as SIBC), WPI to August 2026. Findings of the probe and the build rules are in `PLAN.md`.

**The first reading, and why it is not publishable yet.** July 2026, credit YoY vs output YoY:
chemicals +24.0% vs −2.7%, petroleum +34.0% vs +1.3%, food processing +22.3% vs +2.6%, vehicles
+32.2% vs +22.2%. The gap is large in most industries, but credit is in nominal rupees and IIP is a
real volume index, so part of every gap is price. The publishable comparison needs the WPI for
the same product group: that is what makes this three datasets (IIP + WPI + SIBC), not two.

---

## 9. Revenue model

| Tier | Product | Price | Customer |
|---|---|---|---|
| Free | Dashboard + free posts | ₹0 | Analysts, students, discovery |
| Digest | Monthly Digest (paid) | ₹999–1,999/mo | Senior analysts, consultants |
| Product Monitor | Per-product intelligence | ₹25–75k/yr | NBFC/bank/fintech product and credit teams |
| Team | Multi-product + data access | ₹1.5–3L/yr | Strategy teams, multi-product fintechs |
| Enterprise | Full suite, custom, white-label | ₹5–15L/yr | Large banks, PE funds, consulting firms |
| Consulting | Per engagement | ₹5–15L/mandate | NBFCs and fintechs needing custom intelligence |

| Scenario | Horizon | Assumptions | ARR |
|---|---|---|---|
| Conservative | Year 1 | 50 paid digest + 1 consulting project | ₹8–12L |
| Moderate | Year 2 | 200 paid digest + 5 product-monitor subscribers | ₹40–60L |
| Target | Year 3 | 500 paid digest + 20 monitors + 1 enterprise | ₹1.5–2Cr |
| Scale | Year 4–5 | 100+ institutional + data access + licensing | ₹4–5Cr |

**The highest-ticket dimensions** are data feed / API, white-label, peer benchmarking and investor
intelligence; sector monitors sold as many small subscriptions carry a support drag.

### Launch triggers (in order)

| Tier | Trigger |
|---|---|
| Consulting | No build required. First priority, via outreach |
| Paid digest | An engaged free audience (≥50 subscribers or equivalent reach) |
| Gold Loan monitor | Bureau data, or the SIBC + NBFC join presented as a product |
| MSME monitor | SIDBI or MoSPI enterprise data ingested |
| Data access / API | Three or more inbound requests |

Consulting monetises first; the digest runs in parallel; monitors unlock as their sources land;
data access comes last, after proven signal quality and inbound demand.

---

## 10. The moat

| Layer | What it is | Today |
|---|---|---|
| **Traceability** | Every published number checked against computed signals; paid model calls gated | Built |
| **Causal model** | Per-source system model with sourced forces, re-evaluated each release | Built (3 sources) |
| **Cross-source joins** | Relationships no single release can show | Early |
| **Historical depth** | A signal history that compounds with every release | Building (24 SIBC readings) |
| **Author credibility** | The author's lending domain expertise | Strong |
| **Per-bank granularity** | India has no regulator-level per-bank credit disclosure; assembling it would not be copyable | Not started (§11) |
| **Network effects** | More subscribers → better benchmarks | Future |

---

## 11. Phases (outcomes, not task lists)

| Phase | Outcome | State |
|---|---|---|
| **0 · Foundation** | Three live sources, causal layer, traceability gates, public dashboard | ✅ Done (Sep 2026) |
| **1 · Audience** | A reachable audience that returns: a channel that works for the chosen fork (§5), and a first consulting enquiry | **Now** |
| **2 · First revenue** | Paid digest or first product monitor; first paid consulting project. ₹8–15L ARR | — |
| **3 · Product suite** | Several product monitors, alerts, benchmarking, first enterprise pilot. ₹50L–1Cr ARR | — |
| **4 · Platform** | Data access, white-label, state/district intelligence. ₹3–5Cr ARR | — |

**Open strategic questions (decide, do not drift):**
1. **The audience fork** (§5): fintech builders via payments, or bank leadership via a cold channel.
2. **Per-bank granularity.** It is the keystone for benchmarking and investor intelligence, but bank
   filings may not disclose lending detail at the granularity needed. Validate on 2–3 filings
   before committing; building it would reshape the roadmap.
3. **Which paid wedge to test first:** fintech go-to-market intelligence (faster, lower ticket,
   warm network) or fintech-lending investor intelligence (slower, highest ticket).

---

## 12. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Distribution never reaches buyers | **High** | The audience fork (§5) is the first strategic decision, not a content problem |
| Low paying subscribers | Medium | Consulting monetises first; the digest is parallel, not dependent |
| Regulators restrict data use | Low | All data is public; the analysis is original work |
| Source formats change or revise | Medium | Format detection, freshness recomputes, gated remaps |
| A competitor copies the surface | Medium | Traceability + causal model + history + author credibility |
| Model costs | Low | Computation is deterministic; paid calls are approved per run with a $5 ceiling |
| Solo-operator bandwidth | Medium | Skills, gates and a single living plan keep sessions cheap to restart |

---

## 13. Parked: ICL-Retail (the retail-investor track)

*Not active. Kept as a strategic option; revisit only after Phase 1 answers the audience fork.*

**Thesis.** Government data → sector → listed-stock transmission intelligence for direct-equity
retail investors: *"See what government data says about your stocks — before the market reads
the PDF."* Same engine and repo; a different audience, packaging and price point.

**The product is three things:** a transmission layer (release → specific listed names), a dated
public call register that can be scored, and "your stocks × these signals" alerts.

**SEBI guardrail (non-negotiable).** Analytics and monitoring language only; no buy/sell/target
language anywhere, free or paid. Enforced by the `SEBI_BANNED` lint in
`distribution/slot_render.lint_compliance`. Revisit Research Analyst registration only if the
product ever makes recommendations.

**Pricing if launched:** ₹1,999 per half-year or ₹3,999/yr; the first 100 founding members at
₹1,999/yr for life. Free tier: 3 tickers, current period, no alerts.

**Gates if launched (the kill-switch must not be softened):** DG1 ≥100 emails or ≥300 followers
after 4 weekly notes (fail = packaging, not thesis) · DG2 ≥300 emails at ≥25% open (fail =
distribution) · DG3 ≥20 paying (fewer than 5 on a 500+ list = wrong willingness to pay; stop).

*Model inspiration: BankRegData (US) — 1,275 clients, 2–3 people, 16 years, no funding.*
