// ── RBI SIBC — Merged Annotations (Jan 2026 + Feb 2026 + Mar 2026 SIBC files) ─
// Generated from sections_merged.json (dataDate: 2026-04-30).
// This is the LIVE annotation set for web/lib/reports/rbi_sibc.ts.
// Covers: Jan 2024, Mar 2024, Jan 2025, Mar 2025, Jan 2026, Feb 2026, Mar 2026.

import type { SectionAnnotations } from "@/lib/types";

export const ANNOTATIONS: Record<string, SectionAnnotations> = {

  // ── Section 1: Bank Credit ─────────────────────────────────────────────────
  bankCredit: {
    insights: [
      {
        id: "credit-growth-accelerating-fy26",
        title: "FY26 complete: +16.1% YoY — the strongest in this cycle",
        body: "Bank Credit at Mar 2026: ₹213.6L Cr. FY26 added ₹29.6L Cr — vs ₹18.2L Cr in FY25 and ₹23.5L Cr in FY24. " +
              "YoY growth: +11.0% (FY25) → +16.1% (FY26). " +
              "Within FY26: Jan 2026 FY was +12.0%, Feb 2026 FY was +13.5%, Mar 2026 FY confirmed +16.1%. The acceleration was back-loaded.",
        implication: "FY26 is closed. Every main sector accelerated simultaneously — no laggard. " +
                     "Portfolios that grew below 16% lost share in a system-wide tailwind. " +
                     "Capital, not demand, was the binding constraint entering FY27.",
        preferredMode: "yoy",
        effect: { highlight: ["Non-food Credit"] },
      },
      {
        id: "three-year-credit-trajectory",
        title: "Bank credit added ₹53L Cr in two years — compounding, not steady-state",
        body: "Bank Credit: ₹160.5L Cr (Apr 2024) → ₹184.0L Cr (Apr 2025) → ₹213.6L Cr (Mar 2026). " +
              "₹53.1L Cr added in 24 months. Each year adds more absolute credit than the prior: FY25 ₹18.2L Cr, FY26 ₹29.6L Cr — 63% more. " +
              "Growth rate accelerating: +11.0% (FY25) → +16.1% (FY26).",
        implication: "India's banking system is in the early phase of a multi-year credit supercycle. " +
                     "The base effect will eventually slow YoY, but absolute additions will keep growing if the economy holds. " +
                     "Lenders with scalable origination have a compounding tailwind.",
        preferredMode: "absolute",
        effect: { highlight: ["Bank Credit", "Non-food Credit"], dim: ["Food Credit"] },
      },
      {
        id: "nonfood-credit-all-the-signal",
        title: "Non-food credit is the only number that matters",
        body: "Non-food credit is ₹212.9L Cr of the ₹213.6L Cr total at Mar 2026 — 99.7% of bank credit. " +
              "Food credit at ₹0.70L Cr at Mar 2026 is minimal and seasonal. " +
              "The +16.1% FY26 headline growth is entirely a non-food signal.",
        implication: "Always strip food credit from headline numbers before quoting them. " +
                     "Jan and Feb observations will show elevated food credit due to kharif procurement cycles — " +
                     "always anchor growth comparisons to March-end figures.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
      },
      {
        id: "food-credit-jan-artifact",
        title: "Food credit cycle growing — 5× in two years at March-end",
        body: "The seasonal pattern is real — kharif procurement agencies draw in Jan and repay by March — but both peaks and troughs are rising. " +
              "March-end: ₹0.21L Cr (Mar 2024) → ₹0.29L Cr (Mar 2025, +38.4%) → ₹0.70L Cr (Mar 2026, +139.4%). " +
              "Jan peaks: ₹0.46L Cr (Jan 2024) → ₹0.89L Cr (Jan 2026, +95%). " +
              "The mechanism is MSP procurement growth — larger procurement volumes each cycle.",
        implication: "The FY-to-date figure from a January observation overstates the annual run-rate — March-end is the right anchor. " +
                     "But the March-end YoY trend is unambiguously up. Food credit is a growing cycle, not seasonal noise.",
        preferredMode: "absolute",
        effect: { highlight: ["Food Credit"] },
      },
    ],
    gaps: [
      {
        id: "bankcredit-april-date-convention",
        title: "Bank Credit uses April fortnight dates — treat them as FY-end",
        body: "Bank Credit aggregate columns are labelled 'Apr 2024' (Apr 5, 2024) and 'Apr 2025' (Apr 4, 2025) " +
              "because RBI publishes on a fortnightly cycle. Sub-sectors (Agriculture, Industry, Services, Personal Loans) " +
              "use Mar 22, 2024 and Mar 21, 2025 — different actual dates in the same statement. " +
              "The published 16.1% YoY variation uses RBI's own variation column, not a recomputed figure.",
        implication: "Treat all Bank Credit date labels as FY-end snapshots. " +
                     "Do not mix Bank Credit totals with sector sub-totals in an arithmetic sum — the dates are not identical.",
        preferredMode: "yoy",
        effect: { dash: ["Bank Credit"] },
      },
    ],
    opportunities: [
      {
        id: "credit-cycle-expansion",
        title: "₹29.6L Cr added in one year — the largest annual absolute add in this dataset",
        body: "FY26 added ₹29.6L Cr (Mar 2025 → Mar 2026), vs ₹18.2L Cr in FY25 — a 63% increase in annual flow. " +
              "This is not a rate-driven cyclical recovery — it reflects formalisation of credit access " +
              "across MSME, retail, and services. The structural drivers are 4-5 year tailwinds.",
        implication: "Lenders with scalable origination have a compounding tailwind. " +
                     "The FY27 base is now ₹213.6L Cr — a 16% growth rate would require adding ₹34L Cr. " +
                     "The absolute origination target rises every year.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit", "Bank Credit"], dim: ["Food Credit"] },
      },
    ],
  },

  // ── Section 2: Main Sectors ────────────────────────────────────────────────
  mainSectors: {
    insights: [
      {
        id: "fy26-all-sectors-synchronised",
        title: "All four main sectors accelerated in FY26 — no laggard in the system",
        body: "FY26 YoY: Agriculture +15.7%, Industry +15.0%, Services +19.0%, Personal Loans +16.2%. " +
              "FY25 comparison: Agriculture +10.4%, Industry +8.2%, Services +12.0%, Personal Loans +11.7%. " +
              "Every sector added 3.5-7.0pp to its growth rate — a synchronised broad-based expansion.",
        implication: "A synchronised multi-sector credit acceleration of this magnitude is unusual. " +
                     "The last comparable cycle was FY22-23 post-COVID re-opening. " +
                     "Lenders with concentrated exposure in any single sector still captured the tailwind.",
        preferredMode: "yoy",
        effect: { highlight: ["Industry", "Services", "Personal Loans", "Agriculture"] },
      },
      {
        id: "services-growth-acceleration",
        title: "Services hit 19.0% YoY in FY26 — fastest main sector two years running",
        body: "Services YoY: +12.3% (Jan 2025) → +15.5% (Jan 2026) → +19.0% (Mar 2026). " +
              "The acceleration built through FY26 and was confirmed at year-end. " +
              "Primary driver: bank credit to NBFCs went from +7.4% (FY25) to +26.3% (FY26), adding ₹4.30L Cr incremental.",
        implication: "Services credit growth is structural, not cyclical. " +
                     "NBFC re-acceleration and tech-sector working capital are multi-year drivers. " +
                     "The Services sector has overtaken Personal Loans as the fastest-growing main category.",
        preferredMode: "yoy",
        effect: { highlight: ["Services"], dim: ["Agriculture"] },
      },
      {
        id: "industry-reaccelerating",
        title: "Industry YoY jumped from 8.2% to 15.0% — biggest acceleration in this cycle",
        body: "Industry YoY: +8.2% (FY25) → +15.0% (FY26). " +
              "The 6.8pp acceleration is the largest single-year move across all main sectors. " +
              "Within Industry: Micro and Small +33.1%, Medium +21.7%, Large +8.9% — concentration in SMEs. " +
              "Sub-sector drivers: All Engineering +32.2%, Petroleum +32.5%, Basic Metal +19.4%.",
        implication: "The industrial credit re-acceleration is not broad-based top-down. " +
                     "It is SME-led with a PLI capex overlay at the top. " +
                     "Banks organised around large corporate lending are missing the fastest-growing industrial segment.",
        preferredMode: "yoy",
        effect: { highlight: ["Industry"] },
      },
      {
        id: "personal-loans-largest-sector",
        title: "Personal Loans: still the largest sector — ₹69.6L Cr, +16.2% YoY",
        body: "Personal Loans: ₹52.3L Cr (Jan 2024) → ₹58.5L Cr (Jan 2025) → ₹67.2L Cr (Jan 2026) → estimated ₹69.6L Cr (Mar 2026). " +
              "YoY +16.2% in FY26, vs +11.7% in FY25. " +
              "The aggregate masks extremes: Gold Loans +123.1%, Vehicle Loans +18.6%, Credit Cards +3.5%, Consumer Durables -5.3%.",
        implication: "Retail lending has decisively overtaken wholesale as the dominant credit category. " +
                     "But the aggregate is an average of opposite trends — always disaggregate into product type before drawing conclusions.",
        preferredMode: "absolute",
        effect: { highlight: ["Personal Loans"], dim: ["Agriculture"] },
      },
    ],
    gaps: [
      {
        id: "personal-loans-aggregate-hides-divergence",
        title: "The personal loans aggregate is a weighted average of opposite trends",
        body: "Personal Loans at +16.2% YoY (FY26) is a weighted average of gold loans growing +123%, " +
              "vehicle loans +18.6%, credit cards +3.5%, and consumer durables -5.3%. " +
              "These are opposite policy and demand signals bundled into one number.",
        implication: "Never use the Personal Loans aggregate to make a directional point. " +
                     "Always disaggregate into secured vs unsecured, or by product type. " +
                     "The 2023 RBI risk-weight tightening on unsecured is still working through the book.",
        preferredMode: "yoy",
        effect: { dash: ["Personal Loans"] },
      },
      {
        id: "main-sectors-undercount",
        title: "Main sector totals undercount system credit by ₹10.6L Cr",
        body: "Agriculture + Industry + Services + Personal Loans at Mar 2026 sum to ₹202.3L Cr. " +
              "Total Bank Credit is ₹213.6L Cr. Adding Food Credit (₹0.70L Cr) reaches ₹203.0L Cr. " +
              "₹10.6L Cr — roughly 5% of bank credit — is unclassified: small business loans, public-sector advances, and other categories.",
        implication: "Treat the main-sector view as 'selected sectors' coverage. " +
                     "For full system accounting, anchor on the Bank Credit total. " +
                     "Any macro leverage ratio built from sector sums will understate total credit by ~5%.",
        preferredMode: "absolute",
        effect: { dash: ["Bank Credit"] },
      },
    ],
    opportunities: [
      {
        id: "services-credit-entry",
        title: "Services sector credit is the fastest-growing main channel",
        body: "Services grew from ₹44.1L Cr (Jan 2024) to ₹60.6L Cr (Mar 2026) — a ₹16.5L Cr addition in 27 months. " +
              "Within services: NBFCs ₹20.66L Cr (+26.3%), Computer Software accelerating, CRE and Trade both above 16% YoY. " +
              "Each sub-sector has distinct risk and opportunity profiles.",
        implication: "Lenders building service-sector credit capabilities — IT working capital, logistics finance, " +
                     "hospitality project finance — are entering the fastest-growing formal credit channel.",
        preferredMode: "absolute",
        effect: { highlight: ["Services"] },
      },
    ],
  },

  // ── Section 3: Industry by Size ────────────────────────────────────────────
  industryBySize: {
    insights: [
      {
        id: "micro-small-growth-tripled",
        title: "Micro & Small: 9.6% → 33.1% YoY over one year — inflection confirmed",
        body: "Micro and Small YoY: +9.6% (FY25) → +33.1% (FY26). " +
              "Absolute credit: ₹7.17L Cr (Jan 2024) → ₹7.98L Cr (Mar 2025) → ₹10.63L Cr (Mar 2026). " +
              "FY26 incremental: ₹2.65L Cr — 4× the FY25 incremental of ₹0.64L Cr. " +
              "PSL MSE confirms: ₹22.4L Cr → ₹29.0L Cr, +29.5% YoY — two independent series aligned.",
        implication: "This is not a one-month anomaly — Jan, Feb, and Mar 2026 all show 29-33% growth. " +
                     "The MSME credit market has crossed an inflection. GST formalisation, UDYAM enrolment, " +
                     "and digital banking have made millions of MSMEs newly creditworthy.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"], dim: ["Large"] },
      },
      {
        id: "large-corporate-stagnant",
        title: "Large corporates: +8.9% YoY — the weakest industrial segment in FY26",
        body: "Large enterprise YoY: +6.8% (FY25) → +8.9% (FY26). " +
              "Absolute credit: ₹26.03L Cr (Jan 2024) → ₹29.31L Cr (Jan 2026) → Mar 2026 est ₹30L Cr. " +
              "In FY26, Large grew ₹2.7L Cr while Micro and Small grew ₹2.65L Cr — near-parity for the first time.",
        implication: "Large corporate banking is a relationship maintenance game, not a growth one. " +
                     "For the first time in this dataset, Micro & Small added approximately the same absolute credit as Large. " +
                     "Banks optimising for growth must re-allocate origination resources to the SME segment.",
        preferredMode: "yoy",
        effect: { highlight: ["Large"], dim: ["Micro and Small", "Medium"] },
      },
      {
        id: "medium-enterprise-sweet-spot",
        title: "Medium enterprises: +21.7% YoY — the structurally underserved middle tier",
        body: "Medium enterprise YoY: +18.4% (FY25) → +21.7% (FY26). " +
              "The medium tier is growing faster than Large (+8.9%) and nearly as fast as Micro & Small (+33.1%). " +
              "Too large for MSME fintech products and too small for DCM access — the structural gap persists.",
        implication: "Medium enterprises (₹50-250 Cr revenue) are the most underserved segment in formal credit. " +
                     "Structured working capital and capex facilities for this tier represent a ₹1L Cr+ addressable market. " +
                     "Both bank and NBFC coverage is thin here.",
        preferredMode: "yoy",
        effect: { highlight: ["Medium"] },
      },
    ],
    gaps: [
      {
        id: "size-definition-boundary-issue",
        title: "MSME size boundaries shift with regulatory revisions",
        body: "The Micro, Small, and Medium categories follow MSMED Act definitions. " +
              "A Micro enterprise crossing the turnover threshold migrates to Small, inflating growth without new credit. " +
              "Some portion of the 33.1% YoY in Micro and Small is definitional migration, not real lending growth.",
        implication: "Treat 33.1% as an upper bound on real MSME credit growth. " +
                     "Cross-reference against UDYAM registration data and PSL MSE figures to isolate genuine lending. " +
                     "PSL MSE at +29.5% provides a partial sanity check.",
        preferredMode: "yoy",
        effect: { dash: ["Micro and Small"] },
      },
    ],
    opportunities: [
      {
        id: "msme-first-cycle-window",
        title: "Alt-data MSME underwriting is now essential — not optional",
        body: "Micro and Small: ₹7.17L Cr (Jan 2024) → ₹10.63L Cr (Mar 2026), adding ₹3.46L Cr in 27 months. " +
              "A meaningful share are first-cycle formal borrowers post-GST and UDYAM with thin or blank bureau histories. " +
              "GST-registered MSMEs from 2019-22 now have 4-6 years of digital financial history (GST returns, UPI flows, e-way bills).",
        implication: "Lenders who build alternative underwriting before bureau coverage fills in will have 2-3 years of pricing advantage. " +
                     "FY27-28 will be the first stress test for these alt-data models. Loss curves could surprise — " +
                     "first-cycle borrowers have no through-the-cycle performance history.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small", "Medium"] },
      },
    ],
  },

  // ── Section 4: Services ────────────────────────────────────────────────────
  services: {
    insights: [
      {
        id: "nbfc-risk-weight-cycle-complete",
        title: "NBFC credit +26.3% YoY — the 2023 risk-weight cycle is fully absorbed",
        body: "Bank credit to NBFCs: ₹15.23L Cr (Mar 2024) → ₹16.35L Cr (Mar 2025, +7.4%) → ₹20.66L Cr (Mar 2026, +26.3%). " +
              "Incremental flow: FY25 ₹1.12L Cr, FY26 ₹4.30L Cr — nearly 4× the prior year. " +
              "The 2023 RBI risk-weight hike on consumer lending worked through NBFC balance sheets in FY24-25. " +
              "In FY26, banks are actively re-building NBFC lending books.",
        implication: "Co-origination, warehouse financing, and loan-management infrastructure for bank-NBFC partnerships " +
                     "are the operative product wedges for FY27. " +
                     "Watch H1 FY27 RBI Financial Stability Reports — RBI could re-tighten if NBFC sector overheats again.",
        preferredMode: "yoy",
        effect: { highlight: ["NBFCs"] },
      },
      {
        id: "computer-software-multi-year-surge",
        title: "Computer Software credit: 3 consecutive periods of 20%+ growth",
        body: "Computer Software: ₹0.26L Cr (Jan 2024) → ₹0.34L Cr (Jan 2025) → ₹0.41L Cr (Jan 2026) → ₹0.46L Cr (Feb 2026). " +
              "+28.2% YoY (Jan 2025) and +20.7% YoY (Jan 2026). " +
              "This is structural — IT services working capital scales with headcount and project volume.",
        implication: "IT services working capital — project mobilisation, payroll bridging, USD receivables hedging — " +
                     "is a structurally growing credit category. Invoice discounting and supply chain finance " +
                     "products tailored for IT exporters are a durable, specific opportunity.",
        preferredMode: "yoy",
        effect: { highlight: ["Computer Software"] },
      },
      {
        id: "transport-operators-decelerating",
        title: "Transport Operators growth collapsed: 12% → 4.3% YoY in one year",
        body: "Transport Operators YoY: +12.0% (Jan 2025) → +4.3% (Jan 2026). " +
              "Absolute: ₹2.29L Cr (Jan 2024) → ₹2.57L Cr (Jan 2025) → ₹2.68L Cr (Jan 2026). " +
              "The sharpest deceleration in any services sub-sector this cycle — post-COVID fleet normalisation.",
        implication: "Transport credit deceleration likely reflects fleet overcapacity in some segments. " +
                     "Lenders with heavy transport exposure should track fleet utilisation rates — a leading indicator of repayment stress.",
        preferredMode: "yoy",
        effect: { highlight: ["Transport Operators"], dash: ["Transport Operators"] },
      },
      {
        id: "cre-trade-consistent-growth",
        title: "CRE and Trade both accelerating: 14% → 16% YoY",
        body: "Commercial Real Estate YoY: +14.1% (Jan 2025) → +16.2% (Jan 2026), at ₹5.98L Cr (Jan 2026). " +
              "Trade YoY: +14.5% (Jan 2025) → +16.1% (Jan 2026), at ₹13.09L Cr (Jan 2026). " +
              "Both accelerating. Trade is the 2nd-largest services sub-sector after NBFCs and Other Services.",
        implication: "CRE growth is data center, logistics, and grade-A office — not residential developer exposure. " +
                     "Trade credit at ₹13.09L Cr growing 16% is the single largest opportunity within services by absolute size.",
        preferredMode: "yoy",
        effect: { highlight: ["Commercial Real Estate", "Trade"] },
      },
    ],
    gaps: [
      {
        id: "nbfc-double-counting",
        title: "Bank credit to NBFCs is double-counted in any system aggregate",
        body: "NBFC credit at ₹20.66L Cr (Mar 2026) is the largest single line in the Services category. " +
              "Bank credit to NBFCs becomes NBFC on-lending to retail and MSME borrowers — those downstream loans " +
              "appear again in personal-loan or industrial-loan tables. There is no system-wide deduplicated view.",
        implication: "When triangulating debt-to-income or debt-to-GDP ratios, deduct bank-to-NBFC flow first. " +
                     "Headline household-leverage numbers that add bank credit + NBFC credit are systematically overstated.",
        preferredMode: "absolute",
        effect: { dash: ["NBFCs"] },
      },
      {
        id: "other-services-opacity",
        title: "Other Services is ₹12.4L Cr with no breakdown",
        body: "'Other Services' at ₹12.4L Cr (Feb 2026) is ~21% of the entire Services sector. " +
              "It grew from ₹9.37L Cr (Jan 2024) to ₹12.36L Cr (Feb 2026) — +31.9% in 24 months. " +
              "Without sub-classification, this growth is analytically opaque.",
        implication: "Any services-sector analysis that treats 'Other Services' as a residual is ignoring 21% of the book. " +
                     "BSR-1 quarterly data provides granular sub-classification; SIBC does not.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Services"], dash: ["Other Services"] },
      },
    ],
    opportunities: [
      {
        id: "co-lending-infrastructure",
        title: "Co-lending and warehouse-financing infrastructure for the bank-NBFC cycle",
        body: "Bank credit to NBFCs added ₹4.30L Cr in FY26 alone — nearly 4× the FY25 flow of ₹1.12L Cr. " +
              "NBFCs need bank balance sheet capacity; banks need NBFC origination reach. " +
              "The product wedges: co-origination agreements, warehouse lines, LMS with co-lending partition logic.",
        implication: "Tech and product builders have a 12-18 month window before in-house tooling at large banks fills the gap. " +
                     "Loan-management systems with co-lending support, partition logic, and audit-trail rigour are the specific need.",
        preferredMode: "absolute",
        effect: { highlight: ["NBFCs"] },
      },
      {
        id: "trade-finance-compounder",
        title: "Trade credit at ₹13.1L Cr, 16% YoY — the services sector's anchor",
        body: "Trade credit: ₹9.85L Cr (Jan 2024) → ₹11.27L Cr (Jan 2025) → ₹13.09L Cr (Jan 2026). " +
              "+33% in 2 years. The second-largest services sub-sector (after NBFCs and Other Services combined). " +
              "Invoice discounting, buyer-financed supply chains, and distributor credit all fall here.",
        implication: "Trade finance is large, recurring, and underserved by digital-first lenders. " +
                     "Fintech platforms building supply chain finance have direct access to the fastest-compounding sub-sector in services by absolute size.",
        preferredMode: "absolute",
        effect: { highlight: ["Trade"] },
      },
    ],
  },

  // ── Section 5: Personal Loans ──────────────────────────────────────────────
  personalLoans: {
    insights: [
      {
        id: "gold-loans-structural-surge",
        title: "Gold loans 5× in 24 months — ₹0.93L Cr to ₹4.60L Cr",
        body: "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹2.06L Cr (Mar 2025, +121.1% YoY) → ₹4.60L Cr (Mar 2026, +123.1% YoY). " +
              "Share of personal credit: 1.7% (Mar 2024) → 3.5% (Mar 2025) → 6.6% (Mar 2026). " +
              "Two compounding effects: RBI Sep 2024 circular reclassified bullet-repayment gold loans from 'agri'/'business' buckets; " +
              "gold prices rose ~30%, expanding collateral value on existing books.",
        implication: "Most of the 5× growth is reclassification plus price effect — not net new disbursement demand. " +
                     "Specialised gold NBFCs (Manappuram, Muthoot, IIFL) and southern banks own the operational capability. " +
                     "Banks struggling with physical-collateral handling should build product partnerships, not direct competition.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "credit-card-collapse",
        title: "Credit cards: +3.5% YoY in FY26 — policy-constrained and confirmed",
        body: "Credit Card Outstanding YoY: +13.0% (Jan 2025) → +1.5% (Jan 2026) → +3.5% (FY26, Mar 2026). " +
              "FY26 incremental: ₹10,094 Cr vs ₹27,350 Cr in FY25 — under one-third the pace. " +
              "Consumer Durables in outright contraction: -1.0% (FY25) → -5.3% (FY26). " +
              "The RBI 2023 risk-weight increases on unsecured retail are confirmed as structurally binding.",
        implication: "Credit card growth is policy-constrained, not demand-constrained. " +
                     "Revenue mix must pivot to fee, interchange, and float — not revolving NII. " +
                     "UPI credit lines and BNPL are absorbing displaced demand through channels not visible in SIBC.",
        preferredMode: "yoy",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
      },
      {
        id: "vehicle-loans-accelerating",
        title: "Vehicle loans growth doubled: 8.6% → 18.6% YoY in FY26",
        body: "Vehicle Loans YoY: +8.6% (FY25) → +18.6% (FY26). " +
              "Absolute: ₹5.61L Cr (Jan 2024) → ₹6.23L Cr (Mar 2025) → ₹7.39L Cr (Mar 2026). " +
              "Incremental FY26: ₹1.16L Cr. EV adoption, commercial fleet renewal, and two-wheeler financing all contributing.",
        implication: "Auto sector credit is in a strong expansion cycle. " +
                     "OEM captive NBFCs (Bajaj Finance, M&M Finance) on the personal side; " +
                     "TReDS platforms and supply-chain finance teams on the Tier-1/Tier-2 component side.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicle Loans"] },
      },
      {
        id: "consumer-durables-accelerating-decline",
        title: "Consumer durables: -5.3% YoY in FY26 — three consecutive periods of negative growth",
        body: "Consumer Durables YoY: -2.4% (Jan 2025), -1.0% (FY25, Mar 2025), -5.3% (FY26, Mar 2026). " +
              "Book declined from ₹23,445 Cr (Mar 2025) to ₹21,962 Cr (Mar 2026). " +
              "The decline is accelerating, not stabilising.",
        implication: "Point-of-sale consumer durable finance is being displaced by BNPL and embedded credit. " +
                     "The credit doesn't disappear — it migrates off-SIBC. Traditional POS financing is in structural decline.",
        preferredMode: "yoy",
        effect: { highlight: ["Consumer Durables"], dash: ["Consumer Durables"] },
      },
    ],
    gaps: [
      {
        id: "gold-loans-reclassification-overstates-demand",
        title: "Gold loans 123% overstates real disbursement demand — separate stock from flow",
        body: "Two effects compound: RBI's Sep 2024 circular required bullet-repayment gold loans to migrate from " +
              "agri/business categories into 'loans against gold jewellery'. Gold prices also rose ~30%, expanding collateral value. " +
              "Both effects are one-time stock adjustments, fully recognised by Mar 2026.",
        implication: "When forecasting gold-loan trajectory into FY27, separate stock effect (reclassification, done) " +
                     "from flow effect (real new disbursements). " +
                     "Stress-test for a gold-price reversal >20% — LTV ratios on marginal loans are already aggressive.",
        preferredMode: "yoy",
        effect: { dash: ["Gold Loans"] },
      },
      {
        id: "other-personal-loans-opacity",
        title: "Other Personal Loans is 25% of the portfolio — no breakdown",
        body: "'Other Personal Loans': ₹13.96L Cr (Jan 2024) → ₹15.11L Cr (Jan 2025) → ₹16.85L Cr (Jan 2026). " +
              "+20.7% in 2 years. Larger than Vehicle Loans and Education combined. " +
              "Likely includes salary advances, top-up home loans, personal overdrafts — classification is opaque.",
        implication: "Any personal loans analysis that treats 'Other Personal Loans' as a residual is ignoring 25% of the book. " +
                     "Use BSR-1 quarterly for sub-classification.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Personal Loans"], dash: ["Other Personal Loans"] },
      },
    ],
    opportunities: [
      {
        id: "gold-loan-market-entry",
        title: "Gold lending market is being re-segmented — banks vs NBFCs",
        body: "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹4.60L Cr (Mar 2026). " +
              "Gold NBFCs (Muthoot, Manappuram) have had market exclusivity for decades. " +
              "Banks are structurally cheaper (lower cost of funds) and offer diversified collateral products. " +
              "Operational moat (assay, cash management, branch density) — not regulatory — is the real barrier.",
        implication: "Banks entering gold lending compete on rate. Gold NBFCs must compete on speed and doorstep service. " +
                     "For new entrants: partnership models with gold NBFCs are operationally faster than building branch operations from zero.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "vehicle-ev-credit",
        title: "Vehicle loans +18.6% — EV-specific credit is the next product layer",
        body: "Vehicle loans: ₹5.61L Cr (Jan 2024) → ₹7.39L Cr (Mar 2026), +31.7% in 27 months. " +
              "EV sales crossed 20L units in FY25. Standard vehicle finance doesn't address battery degradation risk, " +
              "EV residual values, or subsidy-linked EMI structures.",
        implication: "First-mover advantage in EV-specific credit is 2-3 years wide. " +
                     "Fleet EV lending (e-commerce, last-mile logistics) is the highest-volume entry point. " +
                     "Watch Q2 FY27 PV and 2W EV penetration data for trajectory.",
        preferredMode: "absolute",
        effect: { highlight: ["Vehicle Loans"] },
      },
    ],
  },

  // ── Section 6: Priority Sector ─────────────────────────────────────────────
  prioritySector: {
    insights: [
      {
        id: "psl-msme-structural-acceleration",
        title: "PSL MSME: +13.4% YoY in FY25, +29.5% YoY in FY26 — two independent series aligned",
        body: "PSL Micro and Small Enterprises: ₹19.74L Cr (Mar 2024) → ₹22.39L Cr (Mar 2025, +13.4%) → ₹29.0L Cr (Mar 2026, +29.5%). " +
              "Statement 3 industryBySize confirms: ₹7.98L Cr (Mar 2025) → ₹10.63L Cr (Mar 2026), +33.1%. " +
              "Both series point in the same direction — this is credible.",
        implication: "PSL incentives are compounding alongside the formalisation wave. " +
                     "Banks that built MSME origination infrastructure in FY24-25 are now harvesting PSL credit at scale.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small Enterprises"] },
      },
      {
        id: "psl-housing-anomalous-surge",
        title: "PSL Housing +39.8% YoY — this is a definition change, not real housing demand",
        body: "PSL Housing: ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025, -1.1% YoY) → ₹10.44L Cr (Mar 2026, +39.8% YoY). " +
              "The near-reversal follows RBI's October 2024 PSL housing limit revision (metro: ₹35L → ₹45L; non-metro: ₹25L → ₹35L). " +
              "Existing loans were reclassified IN — they are not new originations.",
        implication: "Never cite PSL Housing growth as a demand signal. " +
                     "The genuine new lending signal is personalLoans.Housing at +11.5% YoY (₹30.1L Cr → ₹33.6L Cr) — use that.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"], dash: ["Housing"] },
      },
      {
        id: "export-credit-declining",
        title: "Export credit: +4.2% in FY25, -13.0% FY in FY26",
        body: "Export Credit PSL: ₹11,330 Cr (Mar 2024) → ₹11,805 Cr (Mar 2025, +4.2%) → ₹10,270 Cr (Feb 2026, -13.0% FY). " +
              "After a modest FY25 it turned negative. " +
              "Global trade uncertainty, rupee dynamics, and tighter underwriting are all contributing.",
        implication: "Export finance desks are contracting. " +
                     "India's merchandise exports held up — the pullback is risk appetite, not demand. " +
                     "Fintech invoice discounting and ECGC-backed facilities have a window.",
        preferredMode: "fy",
        effect: { highlight: ["Export Credit"], dash: ["Export Credit"] },
      },
    ],
    gaps: [
      {
        id: "psl-housing-reclassification",
        title: "PSL housing data contaminated by a regulatory revision — not flagged in the report",
        body: "The PSL housing loan limit revision reclassified existing mortgages into the PSL bucket. " +
              "The ₹2.97L Cr apparent addition in FY26 represents existing loans now visible in a different column — not new disbursements. " +
              "The SIBC report presents this as +39.8% growth with no footnote.",
        implication: "Before quoting PSL housing growth, always check whether a limit revision fell in the period. " +
                     "Non-PSL Housing growth (+11.5% YoY) is the correct proxy for genuine new affordable housing lending.",
        preferredMode: "yoy",
        effect: { dash: ["Housing"] },
      },
      {
        id: "psl-totals-not-additive",
        title: "PSL category totals cannot be summed — Weaker Sections overlaps everything",
        body: "Weaker Sections at ₹20.32L Cr (Feb 2026) is a cross-cutting subset of the PSL total. " +
              "SC/ST borrowers, small farmers, and SHG members appear in Agriculture, MSME, and Housing rows simultaneously. " +
              "Summing all PSL rows overstates the PSL book by a significant margin.",
        implication: "Use the official PSL achievement ratios from RBI annual reports, not this table's arithmetic sum. " +
                     "The correct PSL total is 40% of ANBC — use that as the denominator.",
        preferredMode: "absolute",
        effect: { dash: ["Weaker Sections"] },
      },
    ],
    opportunities: [
      {
        id: "renewable-energy-project-finance",
        title: "Renewable energy PSL: ₹0.14L Cr for a ₹20L Cr opportunity",
        body: "Renewable Energy PSL: ₹0.06L Cr (Mar 2024) → ₹0.10L Cr (Mar 2025, +78.3%) → ₹0.14L Cr (Feb 2026, +35.2% FY). " +
              "India needs ₹20-25L Cr of renewable energy investment by 2030. " +
              "Bank credit stands at 0.007% of total bank credit — the gap between need and supply is structural.",
        implication: "No incumbent lender has built renewable energy project finance capabilities at scale. " +
                     "First-movers on DISCOM offtake risk underwriting, distributed solar credit, and battery storage finance " +
                     "will own this market for a decade.",
        preferredMode: "fy",
        effect: { highlight: ["Renewable Energy"] },
      },
      {
        id: "pslc-trading-tooling",
        title: "PSLC trading volume rising — banks need automated compliance tooling",
        body: "As MSME PSL books grow at 29.5% YoY, the PSL certificate (PSLC) trading market on RBI's e-Kuber platform " +
              "becomes more active. Banks with excess PSL achievement sell to those with deficits. " +
              "Tracking real-time PSL achievement ratios against ANBC requires live data integration.",
        implication: "Compliance tech products that automate ANBC calculation, PSL gap forecasting, and PSLC trade timing " +
                     "reduce regulatory risk and optimize cost of PSL compliance for mid-size banks.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small Enterprises"] },
      },
    ],
  },

  // ── Section 7: Industry by Type ────────────────────────────────────────────
  industryByType: {
    insights: [
      {
        id: "pli-capex-broadening-confirmed",
        title: "PLI capex broadened in FY26: Engineering +32%, Petroleum +33%, Metal +19%",
        body: "FY26 YoY by sub-sector: All Engineering +32.2% (₹3.17L Cr), Petroleum +32.5% (₹2.04L Cr), " +
              "Basic Metal +19.4% (₹5.18L Cr), Chemicals +14.9% (₹3.08L Cr), Food Processing +14.0% (₹2.50L Cr), " +
              "Vehicles & Parts +18.1% (₹1.41L Cr). " +
              "FY25 comparison: Engineering +22.0%, Petroleum +16.5%, Basic Metal +12.8% — every sector accelerated.",
        implication: "The PLI capex story has spread well beyond electronics. " +
                     "Petroleum, Basic Metal, and Cement all turning up signals a broad-based industrial capex revival. " +
                     "PSU banks underweight industrial term loans have under-priced upside for FY27.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering", "Petroleum, Coal Products and Nuclear Fuels", "Basic Metal and Metal Product"] },
      },
      {
        id: "gems-jewellery-gold-price-proxy",
        title: "Gems & Jewellery up 40% YoY — this is a gold price proxy, not volume",
        body: "Gems and Jewellery: ₹0.82L Cr (Feb 2024) → ₹0.83L Cr (Feb 2025) → ₹1.17L Cr (Feb 2026). " +
              "+40.2% YoY. Gold prices rose ~25-30% in the same period. " +
              "Jeweller working capital scales directly with gold prices — at least 25pp of this growth is a price effect.",
        implication: "Real volume growth is 10-15%. A 15-20% gold price retracement would compress " +
                     "working capital requirements and may trigger LTV covenant breaches. " +
                     "Stress-test gems & jewellery portfolios against gold price decline scenarios.",
        preferredMode: "yoy",
        effect: { highlight: ["Gems and Jewellery"], dash: ["Gems and Jewellery"] },
      },
      {
        id: "infrastructure-decelerating",
        title: "Infrastructure at +9.5% YoY in FY26 — the supercycle has matured",
        body: "Infrastructure: ₹13.37L Cr (Mar 2025) → ₹14.63L Cr (Mar 2026 est), +9.5% YoY. " +
              "Still the largest industrial sub-sector at ₹14.9L Cr (Mar 2026) but barely expanding relative to its size. " +
              "Projects from the 2019-24 highway/metro supercycle are in operations, repaying loans rather than drawing.",
        implication: "Infrastructure credit books built on the last cycle face high repayments and low new origination. " +
                     "The next capex wave (data centers, green hydrogen, semiconductor fabs) is still 2-4 years from scale. " +
                     "Banks need to identify anchor relationships early — before it becomes consensus.",
        preferredMode: "yoy",
        effect: { highlight: ["Infrastructure"], dim: ["All Engineering"] },
      },
      {
        id: "chemicals-petroleum-capex",
        title: "Chemicals +14.9% YoY, Petroleum +32.5% YoY — specialty and energy capex real",
        body: "Chemicals and Chemical Products: +14.9% YoY (₹3.08L Cr at Mar 2026). " +
              "Petroleum, Coal Products: +32.5% YoY (₹2.04L Cr at Mar 2026). " +
              "Both growing faster than the industry average in FY26. India's specialty chemicals export push and refinery upgrades are the drivers.",
        implication: "Chemical and petroleum credit has longer tenure and larger ticket sizes than most industry sub-sectors. " +
                     "Structured term lending for refinery expansions and specialty chemical plants is a durable corporate banking pipeline.",
        preferredMode: "yoy",
        effect: { highlight: ["Chemicals and Chemical Products", "Petroleum, Coal Products and Nuclear Fuels"] },
      },
    ],
    gaps: [
      {
        id: "infrastructure-sub-classification-absent",
        title: "Infrastructure is the largest industrial sub-sector — completely opaque",
        body: "'Infrastructure' at ₹14.9L Cr (Mar 2026) aggregates roads, power, telecom, railways, ports, and urban infra. " +
              "Each sub-type has different growth drivers, tenor, and credit quality. " +
              "+9.5% YoY at the aggregate may mask contraction in some sub-types and strong growth in others.",
        implication: "Never cite infrastructure credit growth without specifying which sub-type. " +
                     "Use MCA filings, NITI Aayog project monitoring, or RBI BSR-1 for sub-sector breakdown.",
        preferredMode: "absolute",
        effect: { highlight: ["Infrastructure"], dash: ["Infrastructure"] },
      },
      {
        id: "industry-type-partition-not-exact",
        title: "Industry sub-types do not sum to the Industry total",
        body: "The industry-by-type breakdown (Statement 5) does not perfectly reconcile to the industry total in Statement 1. " +
              "Some sub-sectors use different classification vintages, and 'Other Industries' is a residual bucket. " +
              "Cross-sectional arithmetic should treat Statement 5 as indicative, not additive.",
        implication: "Do not sum Statement 5 sub-sectors as a cross-check against the Statement 1 Industry total. " +
                     "Use each statement independently for its own trend analysis.",
        preferredMode: "absolute",
        effect: { dash: ["Infrastructure"] },
      },
    ],
    opportunities: [
      {
        id: "pli-supply-chain-finance",
        title: "PLI supply chains: one anchor yields 50-100 supplier credit relationships",
        body: "All Engineering credit added ₹1.21L Cr in FY26. " +
              "PLI-approved anchor companies (electronics, defence, EV components) have 50-100 tier-2 suppliers. " +
              "Supply chain finance against anchor-validated invoices removes the need for individual MSME underwriting.",
        implication: "One supply chain finance agreement with a PLI anchor generates a multi-counterparty portfolio. " +
                     "Banks that signed on PLI anchors as current account clients in 2022-24 are positioned to offer this now.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id: "basic-metal-capex-lending",
        title: "Basic Metal +19.4% YoY — steel and aluminium capacity additions real in FY26",
        body: "Basic Metal and Metal Product: +19.4% YoY in FY26, reaching ₹5.18L Cr at Mar 2026. " +
              "India's steel capacity additions (JSW, SAIL, Tata Steel expansions) are the primary driver. " +
              "The 2nd-largest industrial sub-sector by credit outstanding, now growing at close to the industry average.",
        implication: "Green steel transitions (DRI, EAF) will need project finance on a different risk model. " +
                     "Banks that develop green steel underwriting now will lead this transition — still 2-3 years from mainstream.",
        preferredMode: "yoy",
        effect: { highlight: ["Basic Metal and Metal Product"] },
      },
    ],
  },

};
