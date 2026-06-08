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
        id: "nonfood-credit-all-the-signal",
        layer: 2,
        title: "Non-food credit is the only number that matters",
        body: "Non-food credit is ₹212.9L Cr of the ₹213.6L Cr total at Mar 2026 — 99.7% of bank credit. " +
              "Food credit at ₹0.70L Cr at Mar 2026 is minimal and seasonal. " +
              "The +16.1% FY26 headline growth is entirely a non-food signal.",
        implication: "Non-food credit is the signal for cross-cycle comparisons — it tracks banking system capacity. " +
                     "Food credit matters separately as a seasonal indicator of MSP procurement scale " +
                     "(tracked in the next annotation). For cross-cycle comparisons, anchor to March-end non-food figures.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
        claim_type: "data",
        basis: {
          facts:      [
            "Non-food credit: ₹212.9L Cr of ₹213.6L Cr total at Mar 2026 — 99.7% of Bank Credit",
            "Food credit: ₹0.70L Cr at Mar 2026",
            "FY26 +16.1% headline growth is entirely a non-food signal",
          ],
          inferences: [
            "Non-food credit is the structurally relevant metric for banking system capacity — food credit is seasonal procurement financing",
            "March-end non-food is the clean anchor for cross-cycle comparisons because it strips out seasonal kharif procurement peaks",
          ],
        },
      },
      {
        id: "food-credit-jan-artifact",
        layer: 2,
        title: "Food credit cycle growing — 5× in two years at March-end",
        body: "The seasonal pattern is real — kharif procurement agencies draw in Jan and repay by March — but both peaks and troughs are rising. " +
              "March-end: ₹0.21L Cr (Mar 2024) → ₹0.29L Cr (Mar 2025, +38.4%) → ₹0.70L Cr (Mar 2026, +139.4%). " +
              "Jan peaks: ₹0.46L Cr (Jan 2024) → ₹0.89L Cr (Jan 2026, +95%). " +
              "The mechanism is MSP procurement growth — larger procurement volumes each cycle.",
        implication: "The FY-to-date figure from a January observation overstates the annual run-rate — March-end is the right anchor. " +
                     "But the March-end YoY trend is unambiguously up. Food credit is a growing cycle, not seasonal noise.",
        preferredMode: "absolute",
        effect: { highlight: ["Food Credit"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "March-end food credit: ₹0.21L Cr (Mar 2024) → ₹0.29L Cr (Mar 2025, +38.4%) → ₹0.70L Cr (Mar 2026, +139.4%)",
            "Jan peaks: ₹0.46L Cr (Jan 2024) → ₹0.89L Cr (Jan 2026, +95%)",
            "Both peaks and troughs are rising across two cycles",
          ],
          inferences: [
            "Seasonal pattern (Jan peak, March trough) is caused by kharif procurement agencies drawing in Jan and repaying by March — mechanism not stated in SIBC, inferred from PSU procurement structure",
            "Rising absolute peaks and troughs indicate the underlying procurement cycle is growing, not merely seasonal noise",
            "The mechanism is MSP procurement growth — MSP announcement values and procurement volumes are rising each cycle",
          ],
          hypothesis: [
            "Future food credit growth depends on MSP policy and procurement agency behaviour — could reverse if procurement strategy changes or FCI reforms proceed",
          ],
        },
      },
    ],
    gaps: [
      {
        id: "bankcredit-april-date-convention",
        layer: 2,
        hidden: true,
        title: "Bank Credit uses April fortnight dates — treat them as FY-end",
        body: "Bank Credit aggregate columns are labelled 'Apr 2024' (Apr 5, 2024) and 'Apr 2025' (Apr 4, 2025) " +
              "because RBI publishes on a fortnightly cycle. Sub-sectors (Agriculture, Industry, Services, Personal Loans) " +
              "use Mar 22, 2024 and Mar 21, 2025 — different actual dates in the same statement. " +
              "The published 16.1% YoY variation uses RBI's own variation column, not a recomputed figure.",
        implication: "Treat all Bank Credit date labels as FY-end snapshots. " +
                     "Do not mix Bank Credit totals with sector sub-totals in an arithmetic sum — the dates are not identical.",
        preferredMode: "yoy",
        effect: { dash: ["Bank Credit"] },
        claim_type: "data",
        basis: {
          facts:      [
            "Bank Credit aggregate columns labelled Apr 2024 (Apr 5, 2024) and Apr 2025 (Apr 4, 2025) — RBI fortnightly cycle",
            "Sub-sectors use Mar 22, 2024 and Mar 21, 2025 — different actual dates in the same statement",
            "Published 16.1% YoY uses RBI's own variation column, not a recomputed figure",
          ],
          inferences: [
            "Different actual dates within the same SIBC statement create an arithmetic mismatch if mixed naively across rows",
            "RBI's fortnightly publication cycle is the structural cause of this date offset — the 'April' label is the closest fortnight to March 31",
          ],
        },
      },
    ],
    opportunities: [
      {
        id: "credit-cycle-expansion",
        layer: 3,
        title: "₹29.6L Cr added in one year — the largest annual absolute add in this dataset",
        body: "FY26 added ₹29.6L Cr (Mar 2025 → Mar 2026), vs ₹18.2L Cr in FY25 — a 63% increase in annual flow. " +
              "This is not a rate-driven cyclical recovery — it reflects formalisation of credit access " +
              "across MSME, retail, and services. The structural drivers are 4-5 year tailwinds.",
        implication: "Lenders with scalable origination have a compounding tailwind. " +
                     "The FY27 base is now ₹213.6L Cr — a 16% growth rate would require adding ₹34L Cr. " +
                     "The absolute origination target rises every year.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit", "Bank Credit"], dim: ["Food Credit"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "FY26 added ₹29.6L Cr (Mar 2025 → Mar 2026) vs ₹18.2L Cr in FY25 — 63% increase in annual flow",
            "Bank Credit: ₹184.0L Cr (Apr 2025) → ₹213.6L Cr (Mar 2026)",
          ],
          inferences: [
            "'Formalisation of credit access' rather than rate-driven recovery characterisation derives from MSME, retail, services growth drivers visible in sub-sector data",
            "4-5 year structural tailwind framing inferred from GST formalisation timeline (2017-19) and UDYAM registration cohorts (2020+) now reaching credit age",
            "FY27 requires adding ₹34L Cr at 16% growth — computed from ₹213.6L Cr × 0.16",
          ],
          hypothesis: [
            "Whether absolute additions keep rising depends on RBI policy rates, NPA cycle evolution, and macro growth remaining above 6%",
          ],
        },
      },
    ],
  },

  // ── Section 2: Main Sectors ────────────────────────────────────────────────
  mainSectors: {
    insights: [

    ],
    gaps: [
      {
        id: "main-sectors-undercount",
        layer: 2,
        title: "Main sector totals undercount system credit by ₹10.6L Cr",
        body: "Agriculture + Industry + Services + Personal Loans at Mar 2026 sum to ₹202.3L Cr. " +
              "Total Bank Credit is ₹213.6L Cr. Adding Food Credit (₹0.70L Cr) reaches ₹203.0L Cr. " +
              "₹10.6L Cr — roughly 5% of bank credit — is unclassified: small business loans, public-sector advances, and other categories.",
        implication: "Treat the main-sector view as 'selected sectors' coverage. " +
                     "For full system accounting, anchor on the Bank Credit total. " +
                     "Any macro leverage ratio built from sector sums will understate total credit by ~5%.",
        preferredMode: "absolute",
        effect: {},
        claim_type: "data",
        basis: {
          facts:      [
            "Agriculture + Industry + Services + Personal Loans = ₹202.3L Cr at Mar 2026",
            "Total Bank Credit: ₹213.6L Cr (adding Food Credit ₹0.70L Cr reaches ₹203.0L Cr)",
            "Gap: ₹10.6L Cr — ~5% of total bank credit unclassified",
          ],
          inferences: [
            "Gap includes small business loans, public-sector advances, and other unclassified categories — implied by structure of SIBC statement",
            "Any macro leverage ratio built from sector sums will understate total credit by approximately 5%",
          ],
        },
      },
    ],
    opportunities: [
      {
        id: "services-credit-entry",
        layer: 3,
        title: "Services sector credit is the fastest-growing main channel",
        body: "Services grew from ₹44.1L Cr (Jan 2024) to ₹60.6L Cr (Mar 2026) — a ₹16.5L Cr addition in 27 months. " +
              "Within services: NBFCs ₹20.66L Cr (+26.3%), Computer Software accelerating, CRE and Trade both above 16% YoY. " +
              "Each sub-sector has distinct risk and opportunity profiles.",
        implication: "Lenders building service-sector credit capabilities — IT working capital, logistics finance, " +
                     "hospitality project finance — are entering the fastest-growing formal credit channel.",
        preferredMode: "absolute",
        effect: { highlight: ["Services"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Services: ₹44.1L Cr (Jan 2024) → ₹60.6L Cr (Mar 2026) — ₹16.5L Cr addition in 27 months",
            "NBFCs ₹20.66L Cr (+26.3%), CRE +16.2%, Trade +16.1% within Services FY26",
          ],
          inferences: [
            "Each services sub-sector has distinct risk and opportunity profile — NBFCs vs CRE vs Trade require different product capabilities",
            "Lenders building IT working capital, logistics finance, hospitality project finance are entering the fastest-growing formal credit channel",
          ],
          hypothesis: [
            "Whether sub-sector growth rates persist depends on NBFC cycle timing, policy rates, and commercial real estate demand in data centre and grade-A office",
          ],
        },
      },
    ],
  },

  // ── Section 3: Industry by Size ────────────────────────────────────────────
  industryBySize: {
    insights: [

    ],
    gaps: [
      {
        id: "size-definition-boundary-issue",
        layer: 2,
        title: "MSME size boundaries shift with regulatory revisions",
        body: "The Micro, Small, and Medium categories follow MSMED Act definitions. " +
              "A Micro enterprise crossing the turnover threshold migrates to Small, inflating growth without new credit. " +
              "Some portion of the 33.1% YoY in Micro and Small is definitional migration, not real lending growth.",
        implication: "Treat 33.1% as an upper bound on real MSME credit growth. " +
                     "Cross-reference against UDYAM registration data and PSL MSE figures to isolate genuine lending. " +
                     "PSL MSE at +29.5% provides a partial sanity check.",
        preferredMode: "yoy",
        effect: { dash: ["Micro and Small"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Micro and Small YoY: +33.1% FY26",
            "MSME categories follow MSMED Act definitions — size boundaries defined by turnover and investment thresholds",
          ],
          inferences: [
            "Enterprise reclassification when crossing MSMED Act thresholds inflates the series growth without reflecting new credit disbursement",
            "PSL MSE at +29.5% uses a different boundary definition and provides a partial sanity check — consistent direction reduces (but doesn't eliminate) the reclassification concern",
            "33.1% should be treated as an upper bound on real MSME credit growth; true disbursement growth is lower",
          ],
          hypothesis: [
            "The precise share attributable to reclassification vs genuine new lending cannot be quantified from SIBC alone — requires UDYAM and MSME census data",
          ],
        },
      },
    ],
    opportunities: [
      {
        id: "msme-first-cycle-window",
        layer: 3,
        title: "Alt-data MSME underwriting is now essential — not optional",
        body: "Micro and Small: ₹7.17L Cr (Jan 2024) → ₹10.63L Cr (Mar 2026), adding ₹3.46L Cr in 27 months. " +
              "A meaningful share are first-cycle formal borrowers post-GST and UDYAM with thin or blank bureau histories. " +
              "GST-registered MSMEs from 2019-22 now have 4-6 years of digital financial history (GST returns, UPI flows, e-way bills).",
        implication: "Lenders who build alternative underwriting before bureau coverage fills in will have 2-3 years of pricing advantage. " +
                     "FY27-28 will be the first stress test for these alt-data models. Loss curves could surprise — " +
                     "first-cycle borrowers have no through-the-cycle performance history.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small", "Medium"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Micro and Small: ₹7.17L Cr (Jan 2024) → ₹10.63L Cr (Mar 2026), adding ₹3.46L Cr in 27 months",
          ],
          inferences: [
            "'Meaningful share are first-cycle formal borrowers' — inference from the timing of GST registration (2017–19) and UDYAM enrolment (2020+) cohorts reaching credit age",
            "GST-registered MSMEs from 2019–22 now have 4–6 years of digital financial history (GST returns, UPI flows, e-way bills) — timeline arithmetic",
            "2–3 year pricing advantage window for alt-data underwriting — inference from competitive dynamics: data network effects take 2–3 years to replicate",
          ],
          hypothesis: [
            "FY27–28 will be the first stress test — first-cycle borrowers have no through-the-cycle performance history; loss curves could surprise",
          ],
        },
      },
    ],
  },

  // ── Section 4: Services ────────────────────────────────────────────────────
  services: {
    insights: [
      {
        id: "nbfc-risk-weight-cycle-complete",
        layer: 2,
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
        claim_type: "inference",
        basis: {
          facts:      [
            "Bank credit to NBFCs: ₹15.23L Cr (Mar 2024) → ₹16.35L Cr (Mar 2025, +7.4%) → ₹20.66L Cr (Mar 2026, +26.3%)",
            "FY25 incremental: ₹1.12L Cr; FY26 incremental: ₹4.30L Cr — nearly 4×",
          ],
          inferences: [
            "The 2023 RBI risk-weight hike on consumer lending (Nov 2023 circular) constrained bank-to-NBFC flows in FY24–25 — causal link inferred from timing of circular and observed FY25 slowdown to +7.4%",
            "'Risk-weight cycle fully absorbed' characterisation requires knowledge of the RBI Nov 2023 circular on unsecured and consumer lending risk weights",
            "Banks actively re-building NBFC lending books in FY26 inferred from the 4× flow acceleration back to pre-tightening trajectory",
          ],
          hypothesis: [
            "RBI could re-tighten if NBFC sector overheats again — watch RBI Financial Stability Reports H1 FY27 for any systemic risk signal",
          ],
        },
      },

    ],
    gaps: [
      {
        id: "nbfc-double-counting",
        layer: 2,
        title: "Bank credit to NBFCs is double-counted in any system aggregate",
        body: "NBFC credit at ₹20.66L Cr (Mar 2026) is the largest single line in the Services category. " +
              "Bank credit to NBFCs becomes NBFC on-lending to retail and MSME borrowers — those downstream loans " +
              "appear again in personal-loan or industrial-loan tables. There is no system-wide deduplicated view.",
        implication: "When triangulating debt-to-income or debt-to-GDP ratios, deduct bank-to-NBFC flow first. " +
                     "Headline household-leverage numbers that add bank credit + NBFC credit are systematically overstated.",
        preferredMode: "absolute",
        effect: { highlight: ["NBFCs"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "NBFC credit at ₹20.66L Cr (Mar 2026) is the largest single line in Services",
            "Bank credit to NBFCs is the upstream funding; NBFC on-lending to retail/MSME is downstream",
          ],
          inferences: [
            "Bank-to-NBFC credit flow becomes downstream NBFC loans to retail and MSME borrowers — those loans appear again in personal loans and industrial sub-sector tables",
            "No system-wide deduplicated credit view exists in SIBC — the double-counting is structural, not a data error",
            "Household leverage ratios that add bank credit + NBFC credit systematically overstate total debt — the NBFC channel is intermediate, not additive",
          ],
        },
      },
      {
        id: "other-services-opacity",
        layer: 2,
        title: "Other Services is ₹12.4L Cr with no breakdown",
        body: "'Other Services' at ₹12.4L Cr (Feb 2026) is ~21% of the entire Services sector. " +
              "It grew from ₹9.37L Cr (Jan 2024) to ₹12.36L Cr (Feb 2026) — +31.9% in 24 months. " +
              "Without sub-classification, this growth is analytically opaque.",
        implication: "Any services-sector analysis that treats 'Other Services' as a residual is ignoring 21% of the book. " +
                     "BSR-1 quarterly data provides granular sub-classification; SIBC does not.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Services"], dash: ["Other Services"] },
        claim_type: "data",
        basis: {
          facts:      [
            "'Other Services': ₹9.37L Cr (Jan 2024) → ₹12.36L Cr (Feb 2026), +31.9% in 24 months",
            "~21% of the entire Services sector at ₹12.4L Cr — larger than CRE, Computer Software, or Transport",
          ],
          inferences: [
            "Without sub-classification, the growth drivers of the second-largest services component are analytically opaque",
            "BSR-1 quarterly data from RBI provides granular sub-classification; SIBC does not publish it at this level",
          ],
        },
      },
    ],
    opportunities: [
      {
        id: "co-lending-infrastructure",
        layer: 3,
        title: "Co-lending and warehouse-financing infrastructure for the bank-NBFC cycle",
        body: "Bank credit to NBFCs added ₹4.30L Cr in FY26 alone — nearly 4× the FY25 flow of ₹1.12L Cr. " +
              "NBFCs need bank balance sheet capacity; banks need NBFC origination reach. " +
              "The product wedges: co-origination agreements, warehouse lines, LMS with co-lending partition logic.",
        implication: "Tech and product builders have a 12-18 month window before in-house tooling at large banks fills the gap. " +
                     "Loan-management systems with co-lending support, partition logic, and audit-trail rigour are the specific need.",
        preferredMode: "yoy",
        effect: { highlight: ["NBFCs", "Trade", "Commercial Real Estate"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Bank credit to NBFCs added ₹4.30L Cr in FY26 — nearly 4× the FY25 flow of ₹1.12L Cr",
          ],
          inferences: [
            "NBFCs need bank balance sheet capacity; banks need NBFC origination reach — strategic complementarity inference from the two-sided structure of bank-NBFC partnerships",
            "Co-origination agreements, warehouse lines, and LMS with co-lending partition logic are the specific product wedges — inferred from the contractual and operational requirements of co-lending",
            "12–18 month window before in-house tooling fills the gap — inference from enterprise software build cycles at large banks",
          ],
          hypothesis: [
            "Window size depends on how quickly tier-1 banks build internal infrastructure — could compress if large bank tech teams accelerate",
          ],
        },
      },
      {
        id: "trade-finance-compounder",
        layer: 3,
        title: "Trade credit at ₹13.1L Cr, 16% YoY — the services sector's anchor",
        body: "Trade credit: ₹9.85L Cr (Jan 2024) → ₹11.27L Cr (Jan 2025) → ₹13.09L Cr (Jan 2026). " +
              "+33% in 2 years. The second-largest services sub-sector (after NBFCs and Other Services combined). " +
              "Invoice discounting, buyer-financed supply chains, and distributor credit all fall here.",
        implication: "Trade finance is large, recurring, and underserved by digital-first lenders. " +
                     "Fintech platforms building supply chain finance have direct access to the fastest-compounding sub-sector in services by absolute size.",
        preferredMode: "absolute",
        effect: { highlight: ["Trade"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Trade credit: ₹9.85L Cr (Jan 2024) → ₹11.27L Cr (Jan 2025) → ₹13.09L Cr (Jan 2026) — +33% in 2 years",
            "2nd-largest services sub-sector by credit outstanding",
          ],
          inferences: [
            "Invoice discounting, buyer-financed supply chains, and distributor credit are the primary instruments in this category — inferred from the operational structure of Trade financing",
            "Fintech platforms building supply chain finance have direct access to the fastest-compounding services sub-sector by absolute credit size",
          ],
        },
      },
    ],
  },

  // ── Section 5: Personal Loans ──────────────────────────────────────────────
  personalLoans: {
    insights: [

    ],
    gaps: [
      {
        id: "personal-loans-aggregate-hides-divergence",
        layer: 2,
        title: "The personal loans aggregate is a weighted average of opposite trends",
        body: "Personal Loans at +16.2% YoY (FY26) is a weighted average of Gold Loans +123%, " +
              "Vehicle Loans +18.6%, Credit Card Outstanding +3.5%, and Consumer Durables -5.3%. " +
              "These are opposite policy and demand signals bundled into one number.",
        implication: "Never use the Personal Loans aggregate to make a directional point. " +
                     "Always disaggregate into secured vs unsecured, or by product type. " +
                     "The 2023 RBI risk-weight tightening on unsecured is still working through the book.",
        preferredMode: "yoy",
        effect: {},
        claim_type: "data",
        basis: {
          facts:      [
            "Personal Loans aggregate +16.2% YoY FY26",
            "Within: Gold Loans +123.1%, Vehicle Loans +18.6%, Credit Cards +3.5%, Consumer Durables -5.3%",
          ],
          inferences: [
            "Weighted average of opposite directional trends makes the aggregate directionally misleading for product-level strategy",
            "RBI 2023 risk-weight tightening on unsecured credit is still working through the book — requires circular knowledge to explain the divergence pattern",
          ],
        },
      },
      {
        id: "gold-loans-reclassification-overstates-demand",
        layer: 2,
        title: "Gold loans 123% overstates real disbursement demand — separate stock from flow",
        body: "Two effects compound: RBI's Sep 2024 circular required bullet-repayment gold loans to migrate from " +
              "agri/business categories into 'loans against gold jewellery'. Gold prices also rose ~30%, expanding collateral value. " +
              "Both effects are one-time stock adjustments, fully recognised by Mar 2026.",
        implication: "When forecasting gold-loan trajectory into FY27, separate stock effect (reclassification, done) " +
                     "from flow effect (real new disbursements). " +
                     "Stress-test for a gold-price reversal >20% — LTV ratios on marginal loans are already aggressive.",
        preferredMode: "yoy",
        effect: { dash: ["Gold Loans"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Gold loans grew 5× from Mar 2024 (₹0.93L Cr) to Mar 2026 (₹4.60L Cr)",
          ],
          inferences: [
            "RBI Sep 2024 circular required bullet-repayment gold loans to migrate from agri/business categories to 'loans against gold jewellery' — requires knowledge of the circular",
            "Gold prices rose ~30% in the period, expanding collateral value on existing loan portfolios",
            "Both effects are one-time stock adjustments fully recognised by Mar 2026 — no ongoing flow inflation after this date",
          ],
          hypothesis: [
            "Stress-test for a gold-price reversal >20% — LTV ratios on marginal gold loans may be aggressive if origination during the price peak was at elevated collateral values",
          ],
        },
      },
      {
        id: "other-personal-loans-opacity",
        layer: 2,
        title: "Other Personal Loans is 25% of the portfolio — no breakdown",
        body: "'Other Personal Loans': ₹13.96L Cr (Jan 2024) → ₹15.11L Cr (Jan 2025) → ₹16.85L Cr (Jan 2026). " +
              "+20.7% in 2 years. Larger than Vehicle Loans and Education combined. " +
              "Likely includes salary advances, top-up home loans, personal overdrafts — classification is opaque.",
        implication: "Any personal loans analysis that treats 'Other Personal Loans' as a residual is ignoring 25% of the book. " +
                     "Use BSR-1 quarterly for sub-classification.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Personal Loans"], dash: ["Other Personal Loans"] },
        claim_type: "data",
        basis: {
          facts:      [
            "'Other Personal Loans': ₹13.96L Cr (Jan 2024) → ₹15.11L Cr (Jan 2025) → ₹16.85L Cr (Jan 2026)",
            "+20.7% in 2 years — larger than Vehicle Loans and Education combined",
          ],
          inferences: [
            "Likely includes salary advances, top-up home loans, and personal overdrafts — classification inference from typical retail loan product structures",
            "BSR-1 quarterly data from RBI provides the sub-classification required for meaningful analysis of this bucket",
          ],
        },
      },
    ],
    opportunities: [
      {
        id: "gold-loan-market-entry",
        layer: 3,
        title: "Gold lending market is being re-segmented — banks vs NBFCs",
        body: "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹4.60L Cr (Mar 2026). " +
              "Gold NBFCs (Muthoot, Manappuram) have had market exclusivity for decades. " +
              "Banks are structurally cheaper (lower cost of funds) and offer diversified collateral products. " +
              "Operational moat (assay, cash management, branch density) — not regulatory — is the real barrier.",
        implication: "Banks entering gold lending compete on rate. Gold NBFCs must compete on speed and doorstep service. " +
                     "For new entrants: partnership models with gold NBFCs are operationally faster than building branch operations from zero.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹4.60L Cr (Mar 2026)",
          ],
          inferences: [
            "Gold NBFCs (Muthoot, Manappuram) have had market exclusivity for decades — market structure inference requiring knowledge of the gold lending competitive landscape",
            "Banks are structurally cheaper (lower cost of funds) — inference from bank vs NBFC funding cost differential in Indian credit markets",
            "Operational moat (assay, cash management, branch density) — not regulatory — is the real entry barrier; inferred from the absence of regulatory restrictions on bank gold lending",
          ],
        },
      },
      {
        id: "vehicle-ev-credit",
        layer: 3,
        title: "Vehicle loans +18.6% — EV-specific credit is the next product layer",
        body: "Vehicle loans: ₹5.61L Cr (Jan 2024) → ₹7.39L Cr (Mar 2026), +31.7% in 27 months. " +
              "EV sales crossed 20L units in FY25. Standard vehicle finance doesn't address battery degradation risk, " +
              "EV residual values, or subsidy-linked EMI structures.",
        implication: "First-mover advantage in EV-specific credit is 2-3 years wide. " +
                     "Fleet EV lending (e-commerce, last-mile logistics) is the highest-volume entry point. " +
                     "Watch Q2 FY27 PV and 2W EV penetration data for trajectory.",
        preferredMode: "absolute",
        effect: { highlight: ["Vehicle Loans"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Vehicle loans: ₹5.61L Cr (Jan 2024) → ₹7.39L Cr (Mar 2026), +31.7% in 27 months",
          ],
          inferences: [
            "EV sales crossed 20L units in FY25 — external market data (VAHAN, SIAM) used as context for the credit category growth",
            "Standard vehicle finance doesn't address battery degradation risk, EV residual values, or subsidy-linked EMI structures — product gap inference from EV economics",
          ],
          hypothesis: [
            "First-mover advantage in EV-specific credit is 2–3 years wide — depends on competitive response timing and EV penetration rate",
            "Fleet EV lending (e-commerce, last-mile logistics) as highest-volume entry point — hypothesis about which segment has the best risk/volume tradeoff",
          ],
        },
      },
    ],
  },

  // ── Section 6: Priority Sector ─────────────────────────────────────────────
  prioritySector: {
    insights: [

      {
        id: "psl-housing-anomalous-surge",
        layer: 2,
        title: "PSL Housing +39.8% YoY — this is a definition change, not real housing demand",
        body: "PSL Housing: ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025, -1.1% YoY) → ₹10.44L Cr (Mar 2026, +39.8% YoY). " +
              "The near-reversal follows RBI's October 2024 PSL housing limit revision (metro: ₹35L → ₹45L; non-metro: ₹25L → ₹35L). " +
              "Existing loans were reclassified IN — they are not new originations.",
        implication: "Never cite PSL Housing growth as a demand signal. " +
                     "The genuine new lending signal is personalLoans.Housing at +11.5% YoY (₹30.1L Cr → ₹33.6L Cr) — use that.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"], dash: ["Housing"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "PSL Housing: ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025, -1.1%) → ₹10.44L Cr (Mar 2026, +39.8%)",
            "personalLoans.Housing: +11.5% YoY at ₹30.1L Cr → ₹33.6L Cr",
          ],
          inferences: [
            "RBI October 2024 PSL housing limit revision (metro: ₹35L → ₹45L; non-metro: ₹25L → ₹35L) is the direct cause — requires knowledge of the RBI circular",
            "Existing mortgages reclassified into the PSL bucket — not new originations — requires understanding of how PSL limit revisions trigger reclassification",
            "personalLoans.Housing at +11.5% is the correct new lending signal — a different series in the same report that is not affected by the PSL reclassification",
          ],
        },
      },

    ],
    gaps: [
      {
        id: "psl-housing-reclassification",
        layer: 2,
        title: "PSL housing data contaminated by a regulatory revision — not flagged in the report",
        body: "The PSL housing loan limit revision reclassified existing mortgages into the PSL bucket. " +
              "The ₹2.97L Cr apparent addition in FY26 represents existing loans now visible in a different column — not new disbursements. " +
              "The SIBC report presents this as +39.8% growth with no footnote.",
        implication: "Before quoting PSL housing growth, always check whether a limit revision fell in the period. " +
                     "Non-PSL Housing growth (+11.5% YoY) is the correct proxy for genuine new affordable housing lending.",
        preferredMode: "yoy",
        effect: { dash: ["Housing"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "PSL Housing growth: +39.8% YoY FY26 (Statement 6)",
            "personalLoans.Housing growth: +11.5% YoY (Statement 5) — the same underlying product category, different statement",
          ],
          inferences: [
            "RBI October 2024 PSL housing limit revision reclassified existing mortgages into the PSL bucket — requires external circular knowledge",
            "₹2.97L Cr apparent addition in FY26 represents existing loans visible in a new column, not new originations",
            "SIBC presents this as +39.8% with no footnote — a data quality inference about the absence of disclosure in the source document",
          ],
        },
      },
      {
        id: "psl-totals-not-additive",
        layer: 2,
        title: "PSL category totals cannot be summed — Weaker Sections overlaps everything",
        body: "Weaker Sections at ₹20.32L Cr (Feb 2026) is a cross-cutting subset of the PSL total. " +
              "SC/ST borrowers, small farmers, and SHG members appear in Agriculture, MSME, and Housing rows simultaneously. " +
              "Summing all PSL rows overstates the PSL book by a significant margin.",
        implication: "Use the official PSL achievement ratios from RBI annual reports, not this table's arithmetic sum. " +
                     "The correct PSL total is 40% of ANBC — use that as the denominator.",
        preferredMode: "absolute",
        effect: { dash: ["Weaker Sections"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Weaker Sections: ₹20.32L Cr (Feb 2026) — a cross-cutting PSL sub-category",
          ],
          inferences: [
            "Weaker Sections (SC/ST, small farmers, SHG members) appear simultaneously in Agriculture, MSME, and Housing rows — cross-cutting classification creates double-counting if summed",
            "Correct PSL total is 40% of ANBC per RBI PSL guidelines — not the arithmetic sum of category rows",
            "Any PSL analysis that sums the category rows will overstate the PSL book by the Weaker Sections overlap",
          ],
        },
      },
    ],
    opportunities: [
      {
        id: "renewable-energy-project-finance",
        layer: 3,
        title: "Renewable energy PSL: ₹0.14L Cr for a ₹20L Cr opportunity",
        body: "Renewable Energy PSL: ₹0.06L Cr (Mar 2024) → ₹0.10L Cr (Mar 2025, +78.3%) → ₹0.14L Cr (Feb 2026, +35.2% FY). " +
              "India needs ₹20-25L Cr of renewable energy investment by 2030. " +
              "Bank credit stands at 0.007% of total bank credit — the gap between need and supply is structural.",
        implication: "No incumbent lender has built renewable energy project finance capabilities at scale. " +
                     "First-movers on DISCOM offtake risk underwriting, distributed solar credit, and battery storage finance " +
                     "will own this market for a decade.",
        preferredMode: "fy",
        effect: { highlight: ["Renewable Energy"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Renewable Energy PSL: ₹0.06L Cr (Mar 2024) → ₹0.10L Cr (Mar 2025, +78.3%) → ₹0.14L Cr (Feb 2026, +35.2% FY)",
            "₹0.14L Cr = 0.007% of ₹213.6L Cr total bank credit",
          ],
          inferences: [
            "India needs ₹20–25L Cr of renewable energy investment by 2030 — NITI Aayog/IRENA/MNRE projection; not in SIBC",
            "No incumbent lender has built renewable energy project finance capabilities at scale — market structure observation requiring industry knowledge",
          ],
          hypothesis: [
            "First-movers on DISCOM offtake risk underwriting, distributed solar, and battery storage finance will own this market for a decade — depends on regulatory evolution, grid integration, and DISCOM financial health",
          ],
        },
      },
      {
        id: "pslc-trading-tooling",
        layer: 3,
        title: "PSLC trading volume rising — banks need automated compliance tooling",
        body: "As MSME PSL books grow at 29.5% YoY, the PSL certificate (PSLC) trading market on RBI's e-Kuber platform " +
              "becomes more active. Banks with excess PSL achievement sell to those with deficits. " +
              "Tracking real-time PSL achievement ratios against ANBC requires live data integration.",
        implication: "Compliance tech products that automate ANBC calculation, PSL gap forecasting, and PSLC trade timing " +
                     "reduce regulatory risk and optimize cost of PSL compliance for mid-size banks.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small Enterprises"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "PSL Micro and Small Enterprises: +29.5% YoY in FY26",
          ],
          inferences: [
            "PSLC trading on RBI's e-Kuber platform becomes more active as PSL books grow asymmetrically across banks — inferred from the mechanics of PSLC markets: asymmetric growth creates buyers and sellers",
            "Compliance tech for ANBC calculation, PSL gap forecasting, and PSLC trade timing is a specific, operational product need for mid-size banks",
          ],
        },
      },
    ],
  },

  // ── Section 7: Industry by Type ────────────────────────────────────────────
  industryByType: {
    insights: [

    ],
    gaps: [
      {
        id: "infrastructure-sub-classification-absent",
        layer: 2,
        title: "Infrastructure is the largest industrial sub-sector — completely opaque",
        body: "'Infrastructure' at ₹14.9L Cr (Mar 2026) aggregates roads, power, telecom, railways, ports, and urban infra. " +
              "Each sub-type has different growth drivers, tenor, and credit quality. " +
              "+9.5% YoY at the aggregate may mask contraction in some sub-types and strong growth in others.",
        implication: "Never cite infrastructure credit growth without specifying which sub-type. " +
                     "Use MCA filings, NITI Aayog project monitoring, or RBI BSR-1 for sub-sector breakdown.",
        preferredMode: "absolute",
        effect: { highlight: ["Infrastructure"], dash: ["Infrastructure"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "'Infrastructure': ₹14.9L Cr (Mar 2026), +9.5% YoY — the single largest industrial sub-sector",
          ],
          inferences: [
            "Infrastructure aggregates roads, power, telecom, railways, ports, and urban infra — each sub-type has different growth drivers, tenor, and credit quality",
            "+9.5% aggregate may mask contraction in some sub-types (e.g., highway repayments) and strong growth in others (e.g., data centers) — requires sub-classification not available in SIBC",
            "MCA filings, NITI Aayog project monitoring, or RBI BSR-1 provide the sub-sector breakdown required for meaningful analysis",
          ],
        },
      },
      {
        id: "industry-type-partition-not-exact",
        layer: 2,
        title: "Industry sub-types do not sum to the Industry total",
        body: "The industry-by-type breakdown does not perfectly reconcile to the industry total from the main sector view. " +
              "Some sub-sectors use different classification vintages, and 'Other Industries' is a residual bucket. " +
              "Treat the type breakdown as indicative, not additive.",
        implication: "Do not sum industry sub-types as a cross-check against the main industry total — they will not reconcile. " +
                     "Use each view independently for its own trend analysis.",
        preferredMode: "absolute",
        effect: { dash: ["Infrastructure"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "Industry sub-types do not sum to the Industry total from the main sector view",
          ],
          inferences: [
            "Some sub-sectors use different classification vintages within the same SIBC publication",
            "RBI uses a residual 'Other Industries' bucket that is not consistently sized across periods",
            "Different source tables within SIBC (Statements 4, 5, 6) have different reconciliation levels and date anchors",
          ],
        },
      },
    ],
    opportunities: [
      {
        id: "pli-supply-chain-finance",
        layer: 3,
        title: "PLI supply chains: one anchor yields 50-100 supplier credit relationships",
        body: "All Engineering credit added ₹1.21L Cr in FY26. " +
              "PLI-approved anchor companies (electronics, defence, EV components) have 50-100 tier-2 suppliers. " +
              "Supply chain finance against anchor-validated invoices removes the need for individual MSME underwriting.",
        implication: "One supply chain finance agreement with a PLI anchor generates a multi-counterparty portfolio. " +
                     "Banks that signed on PLI anchors as current account clients in 2022-24 are positioned to offer this now.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
        claim_type: "inference",
        basis: {
          facts:      [
            "All Engineering credit added ₹1.21L Cr in FY26",
          ],
          inferences: [
            "PLI-approved anchor companies (electronics, defence, EV components) have 50–100 tier-2 suppliers — inference from the supply chain depth of PLI sectors",
            "Supply chain finance against anchor-validated invoices removes the need for individual MSME underwriting — inferred from the mechanics of reverse-factoring and anchor-led supply chain finance",
            "Banks that signed PLI anchors as current account clients in 2022–24 are positioned — inference from relationship banking: CA relationships precede credit relationships",
          ],
        },
      },

    ],
  },

};
