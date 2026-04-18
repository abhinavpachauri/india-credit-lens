// ── RBI SIBC — Merged Annotations (Jan + Feb 2026 SIBC files) ────────────────
// Generated from sections_merged.json (dataDate: 2026-03-30).
// This is the LIVE annotation set for web/lib/reports/rbi_sibc.ts.
// Covers: Jan 2024, Mar 2024, Jan 2025, Mar 2025, Jan 2026, Feb 2026.

import type { SectionAnnotations } from "@/lib/types";

export const ANNOTATIONS: Record<string, SectionAnnotations> = {

  // ── Section 1: Bank Credit ─────────────────────────────────────────────────
  bankCredit: {
    insights: [
      {
        id: "credit-growth-accelerating-fy26",
        title: "Credit is growing faster each month of FY26",
        body: "Non-food credit: +11.3% YoY in Jan 2025, +11.0% in Mar 2025, +14.4% in Jan 2026. " +
              "Within FY26: +12.0% FY in Jan 2026, +13.5% FY in Feb 2026. " +
              "The trend is not flattening — it is building.",
        implication: "For lenders: the system-wide tailwind is strengthening month-on-month. " +
                     "Portfolios that grew below 14% YoY in Jan 2026 lost market share.",
        preferredMode: "yoy",
        effect: { highlight: ["Non-food Credit"] },
      },
      {
        id: "three-year-credit-trajectory",
        title: "Bank credit added ₹44L Cr in two years",
        body: "Bank Credit: ₹160.4L Cr (Jan 2024) → ₹178.7L Cr (Jan 2025) → ₹204.8L Cr (Jan 2026). " +
              "₹44.4L Cr added in 24 months. Growth rate itself is accelerating: +11.4% (Jan 2025) vs +14.6% (Jan 2026). " +
              "This is compounding, not steady-state expansion.",
        implication: "India's banking system is in the early phase of a multi-year credit supercycle. " +
                     "The base effect will eventually slow YoY, but absolute additions will keep growing if the economy holds.",
        preferredMode: "absolute",
        effect: { highlight: ["Bank Credit", "Non-food Credit"], dim: ["Food Credit"] },
      },
      {
        id: "nonfood-credit-all-the-signal",
        title: "Non-food credit is the only number that matters",
        body: "Non-food credit is ₹203.9L Cr of the ₹204.8L Cr total in Jan 2026 — 99.6% of bank credit. " +
              "Food credit at ₹0.89L Cr is a seasonal noise item that spikes in Jan-Feb every year. " +
              "The headline growth rate is essentially the non-food number.",
        implication: "Always strip food credit from headline numbers before quoting them. " +
                     "The +14.6% YoY in Jan 2026 is entirely a non-food signal.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
      },
    ],
    gaps: [
      {
        id: "food-credit-jan-artifact",
        title: "Food credit spikes every January — by design",
        body: "Food credit: ₹0.46L Cr (Jan 2024) → ₹0.56L Cr (Jan 2025) → ₹0.89L Cr (Jan 2026). " +
              "By March-end each year it compresses sharply: ₹0.23L Cr (Mar 2024), ₹0.37L Cr (Mar 2025). " +
              "This is government kharif procurement timing — agencies draw and repay seasonally.",
        implication: "Never cite food credit FY or YoY growth from a January observation. " +
                     "The Jan 2026 FY figure of +144.4% for Food Credit is meaningless for trend analysis.",
        preferredMode: "fy",
        effect: { highlight: ["Food Credit"], dash: ["Food Credit"] },
      },
    ],
    opportunities: [
      {
        id: "credit-cycle-expansion",
        title: "₹26L Cr added in one year — this is structural expansion",
        body: "Jan 2025 → Jan 2026: bank credit grew from ₹178.7L Cr to ₹204.8L Cr, adding ₹26.1L Cr. " +
              "The prior year (Jan 2024 → Jan 2025) added ₹18.3L Cr. " +
              "Each successive year is adding more absolute credit than the prior year.",
        implication: "Lenders with scalable origination have a compounding tailwind. " +
                     "This is not a rate-driven cyclical — it is a structural expansion of the formal credit system.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit", "Bank Credit"], dim: ["Food Credit"] },
      },
    ],
  },

  // ── Section 2: Main Sectors ────────────────────────────────────────────────
  mainSectors: {
    insights: [
      {
        id: "services-growth-acceleration",
        title: "Services hit 15.5% YoY in Jan 2026 — strongest in 3 years",
        body: "Services YoY: +12.3% (Jan 2025) → +15.5% (Jan 2026). " +
              "At ₹57.2L Cr, Services is growing faster than Personal Loans (14.9% YoY) and nearly 3× faster than Industry (12.1% YoY). " +
              "NBFCs, Computer Software, CRE, and Trade are all accelerating simultaneously.",
        implication: "Services credit growth reflects durable structural shifts, not a cyclical bump. " +
                     "NBFC re-acceleration and tech-sector working capital are the primary drivers — both are multi-year trends.",
        preferredMode: "yoy",
        effect: { highlight: ["Services"], dim: ["Agriculture"] },
      },
      {
        id: "industry-reaccelerating",
        title: "Industry YoY jumped from 8.3% to 12.1% in one year",
        body: "Industry YoY: +8.3% (Jan 2025) → +12.1% (Jan 2026). " +
              "The 3.8pp acceleration is the largest single-year move in this cycle. " +
              "Micro and Small (+31.2% YoY) and Medium (+22.3% YoY) are driving it — Large corporates grew only +5.5%.",
        implication: "The industrial credit re-acceleration is not broad-based. It is entirely an SME story. " +
                     "Banks still organised around large corporate lending are missing the fastest-growing industrial segment.",
        preferredMode: "yoy",
        effect: { highlight: ["Industry"] },
      },
      {
        id: "personal-loans-largest-sector",
        title: "Personal loans is now the largest sector — and still accelerating",
        body: "Personal Loans: ₹52.3L Cr (Jan 2024) → ₹58.5L Cr (Jan 2025) → ₹67.2L Cr (Jan 2026). " +
              "YoY growth accelerated from +11.9% (Jan 2025) to +14.9% (Jan 2026). " +
              "At ₹67.2L Cr, Personal Loans exceeds Services (₹57.2L Cr) and Industry (₹43.9L Cr).",
        implication: "Retail lending has decisively overtaken wholesale as the dominant credit category. " +
                     "But the aggregate masks extreme internal divergence — gold loans +100%+, credit cards barely +1.5%.",
        preferredMode: "absolute",
        effect: { highlight: ["Personal Loans"], dim: ["Agriculture"] },
      },
    ],
    gaps: [
      {
        id: "personal-loans-aggregate-hides-divergence",
        title: "The personal loans aggregate is an average of opposite trends",
        body: "Personal Loans at +14.9% YoY (Jan 2026) is a weighted average of gold loans growing >100%, " +
              "vehicle loans +17.1%, credit cards +1.5%, and consumer durables -4.0%. " +
              "These are opposite policy and demand signals bundled into one number.",
        implication: "Never use the Personal Loans aggregate to make a directional point. " +
                     "Always disaggregate into secured vs unsecured, or by product type.",
        preferredMode: "yoy",
        effect: { dash: ["Personal Loans"] },
      },
    ],
    opportunities: [
      {
        id: "services-credit-entry",
        title: "Services sector credit is the fastest-growing channel",
        body: "Services grew from ₹44.1L Cr (Jan 2024) to ₹57.2L Cr (Jan 2026) — +29.6% in 24 months. " +
              "Within services, Computer Software (+20.7% YoY), CRE (+16.2%), and Trade (+16.1%) all outpace the sector average. " +
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
        title: "Micro & Small YoY growth tripled in one year: 9.6% → 31.2%",
        body: "Micro and Small YoY: +9.6% (Jan 2025) → +31.2% (Jan 2026). " +
              "Absolute credit: ₹7.17L Cr (Jan 2024) → ₹7.86L Cr (Jan 2025) → ₹10.31L Cr (Jan 2026). " +
              "The jump from single-digit to 31% YoY growth is the sharpest acceleration in the dataset.",
        implication: "This is not a one-month anomaly. Both Jan and Feb 2026 show ~29-31% growth. " +
                     "The MSME credit market has crossed an inflection point — GST formalisation, " +
                     "UDYAM enrollment, and digital banking have made millions of MSMEs newly creditworthy.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"], dim: ["Large"] },
      },
      {
        id: "large-corporate-stagnant",
        title: "Large corporates: +5.5% YoY — the slowest in this dataset",
        body: "Large enterprise YoY: +6.8% (Jan 2025) → +5.5% (Jan 2026). " +
              "Absolute credit: ₹26.03L Cr (Jan 2024) → ₹27.79L Cr (Jan 2025) → ₹29.31L Cr (Jan 2026). " +
              "Large corporates grew ₹1.52L Cr in Jan 2026 vs Micro and Small growing ₹2.45L Cr — inversion confirmed.",
        implication: "Large corporate banking is a relationship maintenance game, not a growth one. " +
                     "Banks optimising for growth must re-allocate origination resources to the SME segment.",
        preferredMode: "yoy",
        effect: { highlight: ["Large"], dim: ["Micro and Small", "Medium"] },
      },
      {
        id: "medium-enterprise-sweet-spot",
        title: "Medium enterprises: 22.3% YoY — the underserved middle tier",
        body: "Medium enterprise YoY: +18.4% (Jan 2025) → +22.3% (Jan 2026). " +
              "At ₹4.26L Cr, Medium is the smallest size segment but growing the fastest after Micro and Small. " +
              "They are too large for MSME fintech products and too small for DCM access.",
        implication: "Medium enterprises (₹50-250 Cr revenue) are structurally underserved. " +
                     "Structured working capital and capex facilities for this tier represent a ₹1L Cr+ addressable market.",
        preferredMode: "yoy",
        effect: { highlight: ["Medium"] },
      },
    ],
    gaps: [
      {
        id: "size-definition-boundary-issue",
        title: "MSME size boundaries shift with regulatory revisions",
        body: "The Micro, Small, and Medium categories follow RBI definitions revised under MSMED Act amendments. " +
              "A Micro enterprise crossing the new turnover threshold moves to Small, inflating growth " +
              "without a real increase in credit. Some of the 31.2% YoY in Micro and Small is definitional migration.",
        implication: "Treat 31.2% as an upper bound on real MSME credit growth. " +
                     "Cross-reference against UDYAM registration data and PSL MSME figures to isolate genuine lending growth.",
        preferredMode: "yoy",
        effect: { dash: ["Micro and Small"] },
      },
    ],
    opportunities: [
      {
        id: "msme-first-cycle-window",
        title: "First-generation MSME borrowers are now underwritable at scale",
        body: "Micro and Small: ₹7.17L Cr (Jan 2024) → ₹10.31L Cr (Jan 2026), adding ₹3.14L Cr in 24 months. " +
              "GST-registered MSMEs from 2019-22 now have 4-6 years of digital financial history. " +
              "This is the window before bureau files fill up and the segment becomes competitive.",
        implication: "Lenders who build alternative underwriting — GST returns, bank statement cash-flows, " +
                     "UPI transaction history — before bureau coverage fills in will have 2-3 years of pricing advantage.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small", "Medium"] },
      },
    ],
  },

  // ── Section 4: Services ────────────────────────────────────────────────────
  services: {
    insights: [
      {
        id: "computer-software-multi-year-surge",
        title: "Computer Software credit up 55% in 2 years — not a blip",
        body: "Computer Software: ₹0.26L Cr (Jan 2024) → ₹0.34L Cr (Jan 2025) → ₹0.41L Cr (Jan 2026). " +
              "+28.2% YoY (Jan 2025) and +20.7% YoY (Jan 2026). " +
              "By Feb 2026 it reaches ₹0.46L Cr. This is 3 consecutive periods of 20%+ growth.",
        implication: "IT services working capital — project mobilisation, payroll bridging, USD receivables hedging — " +
                     "is a structurally growing credit category. Invoice discounting and supply chain finance " +
                     "products tailored for IT exporters are a specific, durable opportunity.",
        preferredMode: "yoy",
        effect: { highlight: ["Computer Software"] },
      },
      {
        id: "transport-operators-decelerating",
        title: "Transport Operators growth collapsed: 12% → 4.3% YoY in one year",
        body: "Transport Operators YoY: +12.0% (Jan 2025) → +4.3% (Jan 2026). " +
              "Absolute: ₹2.29L Cr (Jan 2024) → ₹2.57L Cr (Jan 2025) → ₹2.68L Cr (Jan 2026). " +
              "The deceleration from 12% to 4.3% is the sharpest in any services sub-sector.",
        implication: "Transport credit deceleration likely reflects a post-COVID-normalisation in trucking fleet additions " +
                     "and overcapacity in some segments. Lenders with heavy transport exposure should track fleet utilisation " +
                     "rates — a leading indicator of repayment stress.",
        preferredMode: "yoy",
        effect: { highlight: ["Transport Operators"], dash: ["Transport Operators"] },
      },
      {
        id: "cre-trade-consistent-growth",
        title: "CRE and Trade both accelerating: 14% → 16% YoY",
        body: "Commercial Real Estate YoY: +14.1% (Jan 2025) → +16.2% (Jan 2026), at ₹5.98L Cr. " +
              "Trade YoY: +14.5% (Jan 2025) → +16.1% (Jan 2026), at ₹13.09L Cr. " +
              "Both accelerating slightly. Trade is the 2nd-largest services sub-sector after Other Services.",
        implication: "CRE growth is data center, logistics, and grade-A office — not residential developer exposure. " +
                     "Trade credit at ₹13.09L Cr growing 16% is the single largest opportunity within services by absolute size.",
        preferredMode: "yoy",
        effect: { highlight: ["Commercial Real Estate", "Trade"] },
      },
    ],
    gaps: [
      {
        id: "nbfc-jan-data-absent",
        title: "NBFCs and Tourism are null in January data — series breaks exist",
        body: "The Jan 2024, Jan 2025, and Jan 2026 data points have null values for NBFCs and Tourism, Hotels & Restaurants. " +
              "These series are only populated at March-end. NBFC data (₹19.5L Cr, +19.1% FY) is only visible at Feb/Mar points. " +
              "This creates gaps in the YoY trend line for the largest services sub-sector.",
        implication: "For NBFC credit trends, use FY data only (March-to-March or March-to-February). " +
                     "The January YoY for overall services is incomplete because it excludes the NBFC series.",
        preferredMode: "absolute",
        effect: { dash: ["NBFCs", "Tourism, Hotels & Restaurants"] },
      },
      {
        id: "other-services-opacity",
        title: "Other Services is ₹12.4L Cr with no breakdown",
        body: "'Other Services' at ₹12.4L Cr (Feb 2026) is 21.3% of the entire Services sector. " +
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
        id: "trade-finance-compounder",
        title: "Trade credit at ₹13.1L Cr, 16% YoY — the services sector's anchor",
        body: "Trade credit: ₹9.85L Cr (Jan 2024) → ₹11.27L Cr (Jan 2025) → ₹13.09L Cr (Jan 2026). " +
              "+33% in 2 years. This is the second-largest services sub-sector and growing steadily across all periods. " +
              "Invoice discounting, buyer-financed supply chains, and distributor credit all fall here.",
        implication: "Trade finance is large, recurring, and underserved by digital-first lenders. " +
                     "Fintech platforms building in supply chain finance have direct access to the fastest-compounding sub-sector in services.",
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
        title: "Gold loans: ₹0.93L Cr → ₹4.29L Cr in 24 months. Not a cycle.",
        body: "Gold loans: ₹0.93L Cr (Mar 2024) → ₹2.06L Cr (Mar 2025, +121.1% YoY) → ₹4.29L Cr (Feb 2026, +107.8% FY). " +
              "Three consecutive data points on the same steep trajectory. " +
              "As a share of personal loans: 1.75% (Mar 2024) → 3.45% (Mar 2025) → 6.31% (Feb 2026).",
        implication: "Gold as a credit instrument is being rediscovered by Indian households. " +
                     "Every lender without a gold loan product is watching its personal credit market share compress.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "credit-card-collapse",
        title: "Credit card YoY fell from 13% to 1.5% in one year",
        body: "Credit Card Outstanding YoY: +13.0% (Jan 2025) → +1.5% (Jan 2026). " +
              "Absolute: ₹2.58L Cr (Jan 2024) → ₹2.92L Cr (Jan 2025) → ₹2.96L Cr (Jan 2026). " +
              "The RBI's 2023 risk weight increases have structurally constrained card growth.",
        implication: "Credit card growth is not recovering — it is policy-constrained. " +
                     "UPI credit lines and BNPL are absorbing displaced demand through channels not visible in this data. " +
                     "Issuers should invest in UPI-linked credit products before this migration completes.",
        preferredMode: "yoy",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
      },
      {
        id: "vehicle-loans-accelerating",
        title: "Vehicle loans growth doubled: 9.7% → 17.1% YoY",
        body: "Vehicle Loans YoY: +9.7% (Jan 2025) → +17.1% (Jan 2026). " +
              "Absolute: ₹5.61L Cr (Jan 2024) → ₹6.15L Cr (Jan 2025) → ₹7.21L Cr (Jan 2026). " +
              "One of the few personal credit categories where YoY growth has doubled year-on-year.",
        implication: "Auto sector credit is in a strong expansion — EV adoption, commercial fleet renewal, " +
                     "and two-wheeler financing are all contributing. This is not reversing soon.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicle Loans"] },
      },
      {
        id: "consumer-durables-accelerating-decline",
        title: "Consumer durables: three consecutive periods of negative growth",
        body: "Consumer Durables YoY: -2.4% (Jan 2025), -1.0% (Mar 2025), -4.0% (Jan 2026). " +
              "The decline is accelerating: what was -2.4% a year ago is now -4.0%. " +
              "Absolute credit fell from ₹0.24L Cr (Jan 2024) to ₹0.22L Cr (Jan 2026).",
        implication: "Point-of-sale consumer durable finance is being displaced by BNPL and embedded credit products. " +
                     "The credit doesn't disappear — it migrates off-SIBC. Traditional POS financing is in structural decline.",
        preferredMode: "yoy",
        effect: { highlight: ["Consumer Durables"], dash: ["Consumer Durables"] },
      },
    ],
    gaps: [
      {
        id: "gold-loans-null-in-jan",
        title: "Gold loans and Housing are null in January data",
        body: "The January SIBC file does not include Gold Loans or Housing data — these are only available at March-end. " +
              "The Jan 2026 personal loans YoY (+14.9%) is therefore computed without the two fastest and largest sub-components. " +
              "If gold loans grew as fast in Jan 2026 as in Mar 2025 (+121%), the true Jan YoY would be materially higher.",
        implication: "The January personal loans YoY figures systematically understate true growth because they " +
                     "exclude the categories that are growing fastest. Always cross-reference with March-end data for a complete picture.",
        preferredMode: "yoy",
        effect: { dash: ["Gold Loans", "Housing"] },
      },
      {
        id: "other-personal-loans-opacity",
        title: "Other Personal Loans is 25% of the portfolio — no breakdown",
        body: "'Other Personal Loans': ₹13.96L Cr (Jan 2024) → ₹15.11L Cr (Jan 2025) → ₹16.85L Cr (Jan 2026). " +
              "+20.7% in 2 years. This category is larger than Vehicle Loans and Education combined. " +
              "It likely includes salary advances, top-up home loans, personal overdrafts — but the classification is opaque.",
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
        body: "Bank gold loans grew from ₹0.93L Cr (Mar 2024) to ₹4.29L Cr (Feb 2026) in 23 months. " +
              "Gold NBFCs (Muthoot, Manappuram) have had market exclusivity for decades. " +
              "Banks are structurally cheaper (lower cost of funds) and offer diversified collateral products.",
        implication: "Banks entering gold lending can compete on rate. " +
                     "Gold NBFCs must compete on speed and doorstep service. " +
                     "The moat is operational (assay, cash management, auction) — not regulatory.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "vehicle-ev-credit",
        title: "Vehicle loans growing — EV-specific credit is the next product layer",
        body: "Vehicle loans: ₹5.61L Cr (Jan 2024) → ₹7.21L Cr (Jan 2026), +28.5% in 2 years. " +
              "EV sales crossed 20L units in FY25. Standard vehicle finance doesn't address battery degradation " +
              "risk, EV residual values, or subsidy-linked EMI structures.",
        implication: "First-mover advantage in EV-specific credit is 2-3 years wide. " +
                     "Fleet EV lending (e-commerce, last-mile logistics) is the highest-volume entry point.",
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
        title: "PSL MSME: +13.4% YoY in FY25, +25.6% FY in FY26",
        body: "PSL Micro and Small Enterprises: ₹19.74L Cr (Mar 2024) → ₹22.39L Cr (Mar 2025, +13.4%) → ₹28.12L Cr (Feb 2026, +25.6% FY). " +
              "The acceleration from 13.4% to 25.6% is confirmed by Statement 1 MSME data. " +
              "Two independent series pointing in the same direction — this is credible.",
        implication: "PSL incentives are working alongside the formalisation wave. " +
                     "Banks that built MSME origination infrastructure in FY24-25 are now harvesting PSL credit at scale.",
        preferredMode: "fy",
        effect: { highlight: ["Micro and Small Enterprises"] },
      },
      {
        id: "psl-housing-anomalous-surge",
        title: "PSL Housing +38.4% FY after -1.1% YoY — this is a classification event",
        body: "PSL Housing: ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025, -1.1% YoY) → ₹10.33L Cr (Feb 2026, +38.4% FY). " +
              "The near-doubling in 11 months follows a period of net contraction. " +
              "The RBI raised PSL housing loan limits in late 2024 — existing loans were reclassified, not new lending.",
        implication: "Never cite PSL housing growth without the classification-event caveat. " +
                     "The genuine new lending signal is the personal loans Housing series at +9.8% FY — use that.",
        preferredMode: "fy",
        effect: { highlight: ["Housing"], dash: ["Housing"] },
      },
      {
        id: "export-credit-declining",
        title: "Export credit: +4.2% in FY25, -13.0% FY in FY26",
        body: "Export Credit PSL: ₹11,330 Cr (Mar 2024) → ₹11,805 Cr (Mar 2025, +4.2%) → ₹10,270 Cr (Feb 2026, -13.0% FY). " +
              "After a modest FY25 it has turned negative. " +
              "Global trade uncertainty, rupee dynamics, and tighter underwriting are all contributing.",
        implication: "Export finance desks are contracting. " +
                     "India's merchandise exports have held up — the pullback is risk appetite, not demand. " +
                     "Fintech invoice discounting and ECGC-backed facilities have a window.",
        preferredMode: "fy",
        effect: { highlight: ["Export Credit"], dash: ["Export Credit"] },
      },
    ],
    gaps: [
      {
        id: "psl-housing-reclassification",
        title: "PSL housing data is contaminated by a regulatory revision — not flagged",
        body: "The PSL housing loan limit revision reclassified existing mortgages into the PSL bucket. " +
              "The ₹2.87L Cr apparent addition in 11 months represents existing loans, not new disbursements. " +
              "The SIBC report does not flag this change.",
        implication: "Before quoting PSL housing growth, always verify whether a limit revision fell in the period. " +
                     "Non-PSL Housing growth (+9.8% FY) is the correct proxy for genuine new affordable housing lending.",
        preferredMode: "fy",
        effect: { dash: ["Housing"] },
      },
      {
        id: "psl-totals-not-additive",
        title: "PSL category totals cannot be summed — Weaker Sections overlaps everything",
        body: "Weaker Sections at ₹20.32L Cr (Feb 2026) is a cross-cutting subset of the PSL total. " +
              "SC/ST borrowers, small farmers, and SHG members appear in Agriculture, MSME, and Housing rows simultaneously. " +
              "Summing all PSL rows overstates the PSL book by a significant margin.",
        implication: "Use the official PSL achievement ratios from RBI annual reports, not this table's arithmetic sum. " +
                     "The correct PSL total is 40% of ANBC — use that as the denominator for any PSL analysis.",
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
    ],
  },

  // ── Section 7: Industry by Type ────────────────────────────────────────────
  industryByType: {
    insights: [
      {
        id: "all-engineering-pli-signal",
        title: "All Engineering +36% YoY in Feb 2026 — PLI capex is in full drawdown",
        body: "All Engineering: ₹1.96L Cr (Feb 2024) → ₹2.32L Cr (Feb 2025) → ₹3.16L Cr (Feb 2026). " +
              "+36.0% YoY and +31.7% FY. ₹1.20L Cr added in 2 years — the fastest-growing large industry sub-sector. " +
              "PLI approvals from 2021-23 are now in the investment drawdown phase.",
        implication: "PLI-linked manufacturing credit is not one cycle — it is a 5-year investment wave. " +
                     "Banks that built PLI-sector relationships during application phases are seeing drawdowns now. " +
                     "Supply chain finance to tier-2 and tier-3 PLI suppliers is the next layer.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id: "gems-jewellery-gold-price-proxy",
        title: "Gems & Jewellery up 40% YoY — this is a gold price proxy, not volume",
        body: "Gems and Jewellery: ₹0.82L Cr (Feb 2024) → ₹0.83L Cr (Feb 2025) → ₹1.17L Cr (Feb 2026). " +
              "+40.2% YoY. Gold prices rose ~25% in the same period. " +
              "Jeweller working capital scales directly with gold prices — at least 25pp of this growth is a price effect.",
        implication: "Real volume growth is 10-15%. A 15-20% gold price retracement would compress " +
                     "working capital requirements and may trigger LTV covenant breaches. " +
                     "Stress-test gems & jewellery portfolios against gold price declines.",
        preferredMode: "yoy",
        effect: { highlight: ["Gems and Jewellery"], dash: ["Gems and Jewellery"] },
      },
      {
        id: "infrastructure-decelerating",
        title: "Infrastructure at +5.8% FY — the supercycle is maturing",
        body: "Infrastructure: ₹13.15L Cr (Feb 2024) → ₹13.37L Cr (Feb 2025) → ₹14.44L Cr (Feb 2026). " +
              "+7.9% YoY and +5.8% FY — the slowest in several years, despite being 32.5% of all industry credit. " +
              "Projects from the 2019-24 capex wave are in operations, repaying loans rather than drawing new ones.",
        implication: "Infrastructure credit books built on the last cycle face high repayments and low new origination. " +
                     "Banks need to identify the next capex wave (data centers, green hydrogen, semiconductor fabs) " +
                     "early — before it becomes consensus.",
        preferredMode: "yoy",
        effect: { highlight: ["Infrastructure"], dim: ["All Engineering"] },
      },
      {
        id: "chemicals-petroleum-capex",
        title: "Chemicals +17% FY, Petroleum +20% FY — specialty and energy capex real",
        body: "Chemicals and Chemical Products: ₹2.68L Cr → ₹3.13L Cr, +17.0% FY. " +
              "Petroleum, Coal Products and Nuclear Fuels: ₹1.54L Cr → ₹1.85L Cr, +20.3% FY. " +
              "Both growing faster than industry average (11.6% FY). India's specialty chemicals export push and refinery upgrades are the drivers.",
        implication: "Chemical and petroleum credit has longer tenure and larger ticket sizes than most industry sub-sectors. " +
                     "Structured term lending for refinery expansions and specialty chemical plants is a durable corporate banking pipeline.",
        preferredMode: "fy",
        effect: { highlight: ["Chemicals and Chemical Products", "Petroleum, Coal Products and Nuclear Fuels"] },
      },
    ],
    gaps: [
      {
        id: "infrastructure-sub-classification-absent",
        title: "Infrastructure is 32.5% of industry credit — completely opaque",
        body: "'Infrastructure' at ₹14.44L Cr aggregates roads, power, telecom, railways, ports, and urban infra. " +
              "Each sub-type has different growth drivers, tenor, and credit quality. " +
              "Growing at 5.8% FY at the aggregate level may mask contraction in some sub-types and strong growth in others.",
        implication: "Never cite infrastructure credit growth without specifying which sub-type. " +
                     "Use MCA filings, NITI Aayog project monitoring, or RBI BSR-1 for sub-sector breakdown.",
        preferredMode: "absolute",
        effect: { highlight: ["Infrastructure"], dash: ["Infrastructure"] },
      },
    ],
    opportunities: [
      {
        id: "pli-supply-chain-finance",
        title: "PLI supply chains: one anchor yields 50-100 supplier credit relationships",
        body: "All Engineering credit added ₹1.20L Cr in 2 years. " +
              "PLI-approved anchor companies (electronics, defence, EV components) have 50-100 tier-2 suppliers. " +
              "Supply chain finance against anchor-validated invoices removes the need for individual MSME underwriting.",
        implication: "One supply chain finance agreement with a PLI anchor generates a multi-counterparty portfolio. " +
                     "Banks that signed on PLI anchors as current account clients in 2022-24 are positioned to offer this now.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id: "basic-metal-capex-lending",
        title: "Basic Metal +14.6% FY — steel and aluminium capacity additions are real",
        body: "Basic Metal and Metal Product: ₹4.33L Cr (Mar 2025) → ₹4.97L Cr (Feb 2026), +14.6% FY. " +
              "India's steel capacity additions (JSW, SAIL, Tata Steel expansions) are the primary driver. " +
              "At ₹4.97L Cr, this is the 2nd-largest industry sub-sector by credit outstanding.",
        implication: "Green steel transitions (DRI, EAF) will need project finance on a different risk model " +
                     "than conventional blast furnace credit. Banks that develop green steel underwriting now " +
                     "will lead this transition — and it's still 2-3 years from becoming mainstream.",
        preferredMode: "fy",
        effect: { highlight: ["Basic Metal and Metal Product"] },
      },
    ],
  },

};
