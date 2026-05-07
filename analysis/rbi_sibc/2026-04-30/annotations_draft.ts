// ── RBI SIBC — Mar 2026 (period: 2026-04-30) — Draft Annotations ─────────────
// Generated from sections.json dated 2026-04-30.
// File format: annual_3col (3 FY-end snapshots: Mar 2024, Mar 2025, Mar 2026).
// bankCredit uses Apr 5 2024 / Apr 4 2025 / Mar 31 2026 dates per RBI fortnight convention.
// DO NOT publish directly. Run through merged analysis first.
// Validate with: python3 analysis/validate_annotations.py this_file.ts

import type { SectionAnnotations } from "@/lib/types";

export const ANNOTATIONS: Record<string, SectionAnnotations> = {

  // ── Section 1: Bank Credit ─────────────────────────────────────────────────
  bankCredit: {
    insights: [
      {
        id: "bank-credit-fy26-acceleration",
        title: "Bank credit growth nearly doubled in FY26 vs FY25",
        body: "Total bank credit reached ₹213.6L Cr at Mar 2026, growing 16.1% vs Apr 2025. " +
              "The prior year (Apr 2025 vs Apr 2024) grew only 11.0%. " +
              "FY26 added ₹29.6L Cr in 11 months — nearly ₹11L Cr more than FY25 added in a full year.",
        implication: "For lenders: this is the strongest credit cycle of the post-pandemic era. " +
                     "If your FY26 portfolio grew below 16%, you lost share in a system-wide tailwind.",
        preferredMode: "absolute",
        effect: { highlight: ["Bank Credit", "Non-food Credit"] },
      },
      {
        id: "non-food-credit-99pct-of-total",
        title: "Non-food credit is 99.7% of bank credit",
        body: "Non-food credit at ₹212.9L Cr is ₹0.70L Cr away from total Bank Credit at Mar 2026. " +
              "Food Credit is ₹0.70L Cr — under 0.5% of the system. " +
              "Every meaningful credit story is a non-food credit story.",
        implication: "Strip food credit from any aggregate quote. " +
                     "The 16.1% growth headline is a non-food number; food credit's swings are government balance-sheet timing.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
      },
      {
        id: "two-year-credit-add-46-lcr",
        title: "Banking added ₹47.8L Cr of credit in two years",
        body: "From Apr 2024 (₹165.9L Cr) to Mar 2026 (₹213.6L Cr), bank credit expanded by ₹47.8L Cr. " +
              "That is more than the entire bank credit base of FY12 added in 24 months. " +
              "FY25 contributed ₹18.2L Cr; FY26 contributed ₹29.6L Cr — the pace is accelerating, not steady.",
        implication: "Capital, not demand, is now the binding constraint. " +
                     "Banks running close to capital adequacy floors will lose share to better-capitalised peers in FY27.",
        preferredMode: "absolute",
        effect: { highlight: ["Bank Credit"] },
      },
    ],
    gaps: [
      {
        id: "bankcredit-uses-april-dates",
        title: "Bank Credit dates are early-April fortnights, not Mar-end",
        body: "RBI publishes Bank Credit on its fortnightly cycle: Apr 5 2024 and Apr 4 2025 are the FY24-end and FY25-end snapshots. " +
              "Sub-sectors (Agriculture, Industry, Services, Personal Loans) use the calendar Mar 22 / Mar 21 dates. " +
              "Mar 31 2026 is the actual FY26-end across both blocks.",
        implication: "When citing 'Mar 2024' or 'Mar 2025' for bank credit aggregates, the underlying date is the early-April fortnight. " +
                     "This is a labelling convention, not a real timing gap — values are FY-end snapshots in both cases.",
        preferredMode: "absolute",
        effect: { dash: ["Bank Credit", "Food Credit", "Non-food Credit"] },
      },
      {
        id: "fy-data-empty-in-bankcredit",
        title: "FY-to-date growth is not displayable for bank credit in this file",
        body: "The dashboard's FY view requires a March base column to anchor the FY growth calculation. " +
              "Because Bank Credit's prior columns are early-April fortnights, the file has no internal March anchor for the aggregate. " +
              "FY data displays correctly for sectors 1–4 (Mar 22 2024, Mar 21 2025, Mar 31 2026) but not for the bank credit aggregate itself.",
        implication: "Use the Absolute or YoY views for bank credit aggregate — not FY. " +
                     "The 16.1% growth figure shown in this period uses RBI's published variation column, not a recomputed FY number.",
        preferredMode: "absolute",
        effect: { dim: ["Bank Credit", "Food Credit", "Non-food Credit"] },
      },
    ],
    opportunities: [
      {
        id: "credit-cycle-deployment-window",
        title: "FY26's ₹29.6L Cr deployment is a once-in-cycle origination window",
        body: "FY26 added ₹29.6L Cr in incremental bank credit — the largest single-year add ever in nominal terms. " +
              "Origination, KYC, underwriting, and collection capacity are now the binding constraints. " +
              "Lenders who built digital origination spine in FY24-25 are capturing disproportionate share.",
        implication: "If you sell to lenders: origination, alternative-data underwriting, and collections-tech are the three highest-conviction wallets right now. " +
                     "If you are a lender: hire ops capacity ahead of demand, not after.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit", "Bank Credit"] },
      },
    ],
  },

  // ── Section 2: Main Sectors ────────────────────────────────────────────────
  mainSectors: {
    insights: [
      {
        id: "all-four-main-sectors-accelerated",
        title: "Every main sector accelerated in FY26",
        body: "Agriculture went 10.4% → 15.7% YoY; Industry 8.2% → 15.0%; Services 12.0% → 19.0%; Personal Loans 11.7% → 16.2%. " +
              "All four moved up by 4–7 percentage points. " +
              "There is no laggard in the main-sector view — this is broad-based, not selective acceleration.",
        implication: "When the entire credit composition is accelerating in unison, a sector-rotation thesis underperforms a beta-on-the-system thesis. " +
                     "Lenders should focus on share within sectors, not picking which sector to lean into.",
        preferredMode: "yoy",
        effect: { highlight: ["Agriculture", "Industry", "Services", "Personal Loans"] },
      },
      {
        id: "services-takes-growth-leadership",
        title: "Services has taken growth leadership from Personal Loans",
        body: "Services grew 19.0% YoY in FY26 (Mar 2026 vs Mar 2025) — the fastest of the four. " +
              "Personal Loans, which led growth in prior periods, came in second at 16.2%. " +
              "The driver is NBFCs (+26.3% YoY) — bank lending to NBFCs reignited after the FY25 risk-weight squeeze.",
        implication: "Services credit is now the leading wallet for the next 6–12 months. " +
                     "Within Services, NBFC on-lending and CRE are the highest-velocity sub-segments — co-lending and warehouse financing structures will see the most interest.",
        preferredMode: "yoy",
        effect: { highlight: ["Services", "Personal Loans"], dim: ["Agriculture"] },
      },
      {
        id: "industry-credit-recovery-confirmed",
        title: "Industry credit is back from a multi-year slowdown",
        body: "Industry grew 8.2% in FY25 → 15.0% in FY26. The acceleration is led by Micro and Small (+33.1%) " +
              "and Medium (+21.7%). Large industry stays modest at 8.9%. " +
              "Industrial credit growth has moved permanently down the size ladder.",
        implication: "Banks built around large-corporate relationships are missing the action. " +
                     "MSME-focused lenders, supply-chain financiers, and B2B fintechs are the natural inheritors of the next ₹10L Cr of industrial credit.",
        preferredMode: "yoy",
        effect: { highlight: ["Industry"] },
      },
    ],
    gaps: [
      {
        id: "main-sectors-undercount-bank-credit",
        title: "1+2+3+4 sums to ₹202.3L Cr — ₹10.6L Cr short of total bank credit",
        body: "Adding Agriculture, Industry, Services, and Personal Loans for Mar 2026 gives ₹202.3L Cr. " +
              "Adding Food Credit (₹0.70L Cr) brings it to ₹203.0L Cr — but total bank credit is ₹213.6L Cr. " +
              "The ₹10.6L Cr gap is 'other' non-food lending not captured in any of the four main sectors.",
        implication: "Treat the main-sector view as 'selected sectors' coverage, not 'all sectors'. " +
                     "Roughly 5% of bank credit is invisible at this granularity.",
        preferredMode: "absolute",
        effect: { dash: ["Agriculture", "Industry", "Services", "Personal Loans"] },
      },
      {
        id: "annual-file-only-three-points",
        title: "Three data points limit what we can say about within-FY pacing",
        body: "This file gives only Mar 2024, Mar 2025, and Mar 2026. " +
              "We can compute year-end-to-year-end growth but not when within FY26 the acceleration happened. " +
              "Was it front-loaded (Apr-Sep 2025) or back-loaded (Jan-Mar 2026)?  This file cannot say.",
        implication: "For pacing analysis, supplement this with the consolidated CSV which has Jan/Feb monthly snapshots. " +
                     "Quoting only this file's growth rates risks projecting a flat trajectory through FY26 when the reality may be lumpy.",
        preferredMode: "absolute",
        effect: {},
      },
    ],
    opportunities: [
      {
        id: "share-not-direction-thesis",
        title: "The right thesis for FY27 is share within Services or MSME, not sector picking",
        body: "Every main sector grew 15-19% in FY26. Picking 'Services over Industry' adds 4 points of beta; " +
              "picking the right NBFC partner within Services or the right region within MSME can add 20+. " +
              "Concentration of opportunity is at the sub-sector and counterparty level, not the sector level.",
        implication: "Diligence the on-lending counterparty (NBFC, fintech, regional bank) more than the sector exposure. " +
                     "Underwriting differentiation — not portfolio choice — is the FY27 alpha source.",
        preferredMode: "yoy",
        effect: { highlight: ["Services", "Industry", "Personal Loans"] },
      },
      {
        id: "agriculture-overlooked-acceleration",
        title: "Agriculture credit accelerated to 15.7% but gets no airtime",
        body: "Agriculture grew from 10.4% YoY in FY25 to 15.7% in FY26. " +
              "The absolute add is ₹3.59L Cr in one year — larger than the entire Gold Loans book at Mar 2026 (₹4.60L Cr). " +
              "Most credit commentary still treats agriculture as a flat, mandate-driven category.",
        implication: "Agri-fintech, FPO lending, and warehouse-receipt financing have been overlooked relative to size. " +
                     "Banks with rural reach and digital land-record integration are best positioned.",
        preferredMode: "yoy",
        effect: { highlight: ["Agriculture"] },
      },
    ],
  },

  // ── Section 3: Industry by Size ────────────────────────────────────────────
  industryBySize: {
    insights: [
      {
        id: "micro-small-explosion",
        title: "Micro & Small grew 33.1% YoY — the largest single acceleration in the file",
        body: "Micro and Small industrial credit went from 8.9% YoY in FY25 to 33.1% YoY in FY26. " +
              "The absolute add was ₹2.65L Cr in FY26 vs ₹0.65L Cr in FY25 — over four times the prior year's flow. " +
              "No other size segment moved by more than 13 percentage points.",
        implication: "MSME credit is the single highest-velocity wallet in the system. " +
                     "If you are not building product specifically for sub-₹50 Cr borrowers in FY27, you are not in the dominant flow.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"] },
      },
      {
        id: "large-industry-still-slow",
        title: "Large industry credit grew only 8.9% — half the system rate",
        body: "Large-industry credit moved from 6.9% YoY in FY25 to 8.9% YoY in FY26. " +
              "Large balances are still ₹30.8L Cr — three times the Micro & Small book — but absorbing little incremental credit. " +
              "Either large corporates are deleveraging or they are funding capex through bond markets.",
        implication: "For coverage bankers: large corporate fee income is a stable but flat wallet. " +
                     "Cross-sell to vendor MSMEs and supply-chain finance offer better revenue per account.",
        preferredMode: "yoy",
        effect: { highlight: ["Large"], dim: ["Micro and Small", "Medium"] },
      },
    ],
    gaps: [
      {
        id: "msme-formalisation-vs-real-demand",
        title: "Some of Micro & Small's surge is formalisation, not new lending",
        body: "Part of the 33.1% growth is businesses becoming visible to banks for the first time after GST and UDYAM enrolment, " +
              "not businesses that were already borrowing growing their loans. " +
              "The economy under ₹50 Cr revenue did not grow 33% in one year — the formally measurable part of it did.",
        implication: "First-cycle MSME borrowers have thin or blank bureau histories. " +
                     "Underwriting differentiation will come from alternative data (GST, UPI, e-way bills, supplier confirmations), not bureau scores.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"], dash: ["Micro and Small"] },
      },
    ],
    opportunities: [
      {
        id: "msme-underwriting-data-stack",
        title: "Alternative-data underwriting for thin-file MSMEs is a multi-year wallet",
        body: "Micro and Small added ₹2.65L Cr of credit in FY26 alone. " +
              "If even 30% of that flow is to first-time formal borrowers, that is ₹0.8L Cr of brand-new exposure being underwritten without bureau scores. " +
              "GST data, payment-rail signals, and e-way-bill volumes are the new credit history.",
        implication: "Lenders without an alternative-data underwriting stack are flying blind on the fastest-growing book. " +
                     "Buy-side opportunity: data partnerships with GSPs and account aggregators have outsized leverage right now.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"] },
      },
      {
        id: "supply-chain-finance-vs-medium",
        title: "Medium industry at 21.7% is the under-priced bracket",
        body: "Medium industry grew 21.7% YoY — between Micro & Small's hype and Large's torpor. " +
              "It is the bracket that has formal accounts, audited financials, and bureau histories — but is small enough that the market is not crowded. " +
              "Few large lenders cover this bracket directly.",
        implication: "Mid-market term loans, working capital, and partial-secured CC limits are an under-served zone. " +
                     "Large NBFCs and emerging banks (Bandhan, Equitas, RBL) are most naturally positioned.",
        preferredMode: "yoy",
        effect: { highlight: ["Medium"] },
      },
    ],
  },

  // ── Section 4: Services ────────────────────────────────────────────────────
  services: {
    insights: [
      {
        id: "nbfc-tap-reopens",
        title: "Bank credit to NBFCs grew 26.3% — the post-squeeze recovery is now over",
        body: "NBFC credit went from 7.4% YoY in FY25 (post-RBI risk-weight increase) to 26.3% YoY in FY26. " +
              "Absolute flow: ₹4.30L Cr added in FY26 vs ₹1.12L Cr in FY25 — nearly 4x. " +
              "The capital impact of the 2023 risk-weight rise has been fully absorbed.",
        implication: "NBFCs are once again the dominant on-lending counterparty for retail and MSME credit. " +
                     "Banks with strong NBFC franchises (Axis, ICICI, HDFC) are capturing the rebound; co-origination structures get the next leg.",
        preferredMode: "yoy",
        effect: { highlight: ["NBFCs"] },
      },
      {
        id: "computer-software-tourism-acceleration",
        title: "Computer Software and Tourism credit are the surprise services accelerators",
        body: "Computer Software grew 27.0% → 39.0% YoY between FY25 and FY26 (₹45,738 Cr at Mar 2026). " +
              "Tourism, Hotels & Restaurants went 7.1% → 23.0% YoY. " +
              "These are working-capital signals: tech companies hiring, hospitality post-pandemic capex.",
        implication: "Sector-aware lenders should expand SLAs for IT-services working capital and hotel-property loans now. " +
                     "Both segments still have small absolute books (under ₹1.1L Cr each), so origination capacity matters more than balance-sheet limits.",
        preferredMode: "yoy",
        effect: { highlight: ["Computer Software", "Tourism, Hotels & Restaurants"] },
      },
      {
        id: "cre-strength-continues",
        title: "Commercial Real Estate credit grew 19.9% — broad-based, not metro-only",
        body: "CRE credit went from ₹4.60L Cr (Mar 2024) to ₹6.27L Cr (Mar 2026) — 36% in two years. " +
              "FY26 alone added ₹1.04L Cr at 19.9% YoY. " +
              "Tier-2/3 commercial real estate (warehousing, logistics parks, fulfilment centres) is the under-recognised driver.",
        implication: "Lease-rental discounting (LRD) and warehouse-anchored CRE structures are the operative products. " +
                     "Banks with strong project-finance teams and digitised CRE underwriting will continue to dominate.",
        preferredMode: "yoy",
        effect: { highlight: ["Commercial Real Estate"] },
      },
    ],
    gaps: [
      {
        id: "nbfc-double-counting-systemic",
        title: "Bank credit to NBFCs is counted twice in the system view",
        body: "Bank credit to NBFCs (₹20.66L Cr at Mar 2026) becomes NBFC on-lending to retail and MSME borrowers — " +
              "which then appears again in personal-loan or industrial-loan stats published by NBFCs themselves. " +
              "There is no system-wide deduplicated view of end-borrower credit.",
        implication: "Add-up of bank + NBFC retail credit overstates true household leverage. " +
                     "When triangulating debt-to-income or debt-to-GDP ratios, deduct bank-to-NBFC flow first.",
        preferredMode: "absolute",
        effect: { highlight: ["NBFCs"], dash: ["NBFCs"] },
      },
    ],
    opportunities: [
      {
        id: "co-lending-window-fy27",
        title: "Co-lending and warehouse financing structures have the open runway through FY27",
        body: "With NBFC bank credit growing at 26.3% YoY and absolute incremental flow of ₹4.30L Cr in FY26, " +
              "the bilateral co-lending and structured warehouse arrangements are the most active product wedge. " +
              "Banks need NBFC origination reach; NBFCs need balance sheet capacity.",
        implication: "If you build co-lending tech (loan management systems, partition logic, audit trails), the next 12–18 months are the buying window. " +
                     "Banks with weak in-house tech are the natural buyers.",
        preferredMode: "yoy",
        effect: { highlight: ["NBFCs"] },
      },
      {
        id: "shipping-aviation-thin-coverage",
        title: "Shipping (₹0.10L Cr) and Aviation (₹0.53L Cr) are both small and accelerating",
        body: "Shipping grew 3.4% → 42.2% YoY; Aviation 16.2% → 6.3%. " +
              "Both are tiny relative to NBFCs or Trade, but Shipping just turned a corner and Aviation has room to re-accelerate if airline orders convert. " +
              "This is whitespace where one or two specialised lenders can take meaningful share.",
        implication: "Specialty lenders building asset-finance for fleet vessels or aircraft should target FY27. " +
                     "PSU banks (SBI, Bank of India) are natural incumbents but face thin product depth — opportunity for product-led private lenders.",
        preferredMode: "yoy",
        effect: { highlight: ["Shipping", "Aviation"] },
      },
    ],
  },

  // ── Section 5: Personal Loans ──────────────────────────────────────────────
  personalLoans: {
    insights: [
      {
        id: "gold-loans-five-x-in-two-years",
        title: "Gold Loans grew 5x in 24 months — from ₹0.93L Cr to ₹4.60L Cr",
        body: "Gold Loans were ₹93,301 Cr at Mar 2024, ₹2.06L Cr at Mar 2025, and ₹4.60L Cr at Mar 2026. " +
              "Two consecutive YoY growth rates of ~120% (121.1% then 123.1%). " +
              "This is the most extreme retail credit reclassification + price effect in recent memory.",
        implication: "Gold loan share of personal credit has gone from 1.7% to 6.6% in two years. " +
                     "Lenders with branch density in tier-3/4 markets (Manappuram, Muthoot, IIFL, Federal Bank) are the structural winners.",
        preferredMode: "yoy",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "credit-card-flattening-confirmed",
        title: "Credit card growth fell to 3.5% — the unsecured slowdown is real",
        body: "Credit Card outstanding went 10.6% YoY in FY25 to just 3.5% YoY in FY26 (₹2.94L Cr at Mar 2026). " +
              "Incremental flow: ₹10,094 Cr in FY26 vs ₹27,350 Cr in FY25 — under one-third the pace. " +
              "RBI's 2023 risk-weight increase and tighter unsecured lending guidance are biting on the cards book.",
        implication: "Card-led acquisition strategies are losing credit-utilisation upside. " +
                     "Issuers need to pivot revenue toward fee, interchange, and float — not net-interest income on revolving balances.",
        preferredMode: "yoy",
        effect: { highlight: ["Credit Card Outstanding"] },
      },
      {
        id: "vehicle-loans-double-pace-acceleration",
        title: "Vehicle loans accelerated from 8.6% to 18.6% YoY — one of the period's quiet stories",
        body: "Vehicle Loans went from ₹5.73L Cr (Mar 2024) → ₹6.23L Cr (Mar 2025) → ₹7.39L Cr (Mar 2026). " +
              "FY25 added ₹0.49L Cr; FY26 added ₹1.16L Cr — over 2x the absolute pace. " +
              "Two-wheelers, used cars, and EV-segment loans are the likely contributors.",
        implication: "Auto-financiers with strong dealer-floor presence and EV-specialist underwriting are positioned to take share. " +
                     "Captive NBFCs of OEMs (Bajaj, Mahindra, Tata) will compete aggressively on rate.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicle Loans"] },
      },
    ],
    gaps: [
      {
        id: "gold-mostly-reclassification-and-price",
        title: "Most of Gold Loan growth is reclassification and price, not new collateral",
        body: "RBI's Sep 2024 circular tightened reporting on gold loans — bullet repayment products previously booked as 'agri loans' or 'business loans' " +
              "had to be reclassified into 'gold loans against jewellery'. Gold prices also rose ~30% over the period. " +
              "Both effects compound: more loans visible AS gold loans, each loan secured by collateral that became more valuable.",
        implication: "The 123% YoY rate overstates the real credit demand. Underwriting capacity must adjust if gold prices revert. " +
                     "When you quote the gold loan trajectory in 2027, separate stock effect (reclassification) from flow effect (real new loans).",
        preferredMode: "yoy",
        effect: { highlight: ["Gold Loans"], dash: ["Gold Loans"] },
      },
      {
        id: "consumer-durables-contracting",
        title: "Consumer Durables credit is contracting — it shrunk in both FY25 and FY26",
        body: "Consumer Durables went ₹23,445 Cr (Mar 2024) → ₹23,201 Cr (Mar 2025) → ₹21,962 Cr (Mar 2026). " +
              "FY25: -1.0% YoY. FY26: -5.3% YoY. " +
              "It is the only personal-loan sub-category in absolute decline.",
        implication: "Either CD demand has migrated to BNPL/embedded fintech (which sit outside the SIBC tally) or the CD-on-card stack absorbed the volume. " +
                     "Standalone CD-financing as a product category is shrinking — pivot to embedded / BNPL stacks.",
        preferredMode: "absolute",
        effect: { highlight: ["Consumer Durables"], dash: ["Consumer Durables"] },
      },
    ],
    opportunities: [
      {
        id: "gold-loan-bank-vs-nbfc-tier3",
        title: "Specialised gold-loan NBFCs still own the disbursement velocity",
        body: "With Gold Loans at ₹4.60L Cr and growing at 123% YoY, banks can't keep up on operational throughput — " +
              "gold loans require physical collateral handling, valuation, and short-tenor operational cadence that branch banks struggle with. " +
              "Specialised NBFCs and tier-3/4 banks dominate disbursement.",
        implication: "Gold-loan NBFCs (Manappuram, Muthoot, IIFL Finance) and southern banks (Federal, KVB, Karnataka Bank) are the structural winners. " +
                     "Build product or partnership angles with these counterparts — direct competition is operationally difficult.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "housing-steady-mid-teens",
        title: "Housing credit at ₹33.6L Cr is the workhorse — quietly compounding 11.5% YoY",
        body: "Housing went ₹27.2L Cr → ₹30.1L Cr → ₹33.6L Cr in two years. FY25: 10.7%. FY26: 11.5%. " +
              "It is the second-largest personal-loan sub-category and the most predictable. " +
              "No acceleration, no deceleration — pure compounding.",
        implication: "Housing finance specialists (HDFC Bank, ICICI, LIC Housing, BAF) maintain the steady wallet. " +
                     "Affordable-housing and tier-2/3 origination are the share-gain levers; metros are saturated.",
        preferredMode: "absolute",
        effect: { highlight: ["Housing"] },
      },
    ],
  },

  // ── Section 6: Priority Sector ─────────────────────────────────────────────
  prioritySector: {
    insights: [
      {
        id: "psl-mse-confirms-msme-wave",
        title: "PSL MSE credit grew 29.5% YoY — confirming the MSME wave from the size view",
        body: "Priority Sector MSE went from ₹19.74L Cr → ₹22.39L Cr → ₹29.01L Cr. " +
              "FY25 was 13.4%, FY26 jumped to 29.5%. " +
              "Cross-validates the industryBySize view: Micro & Small at +33.1% YoY in FY26.",
        implication: "Priority sector lending requirements (40% of ANBC for domestic banks) are now binding. " +
                     "Banks short of PSL targets are buying via Priority Sector Lending Certificates (PSLCs) — a tradable wallet for over-achievers.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small Enterprises"] },
      },
      {
        id: "psl-renewable-still-hot",
        title: "PSL Renewable Energy continues to grow at 34.1% — small base, big trajectory",
        body: "Renewable Energy under PSL was ₹5,790 Cr (Mar 2024) → ₹10,325 Cr (Mar 2025) → ₹13,848 Cr (Mar 2026). " +
              "FY25: 78.3%. FY26: 34.1%. " +
              "Deceleration is from a high base, not a slowdown — absolute add of ₹3,524 Cr in FY26 is still material.",
        implication: "Solar rooftop, wind-electrolyser, and EV-charging-infra are the three highest-velocity sub-categories. " +
                     "Specialist green-finance NBFCs (REC, PFC, IREDA, Power Trust) and PSU banks are the natural lenders.",
        preferredMode: "yoy",
        effect: { highlight: ["Renewable Energy"] },
      },
    ],
    gaps: [
      {
        id: "psl-housing-39-pct-classification-event",
        title: "PSL Housing went -1.1% to +39.8% YoY — almost certainly a definition change",
        body: "Housing under PSL was ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025) → ₹10.44L Cr (Mar 2026). " +
              "FY25 was actually -1.1%, then FY26 jumped 39.8%. " +
              "RBI revised PSL housing limits in Oct 2024 (metro: ₹35L → ₹45L; non-metro: ₹25L → ₹35L) — existing loans were reclassified IN, not newly originated.",
        implication: "Do not quote PSL Housing's 39.8% as a demand signal. " +
                     "It is a classification event. Real housing demand is in the personalLoans.Housing line at 11.5%, which is where the underlying lending behaviour lives.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"], dash: ["Housing"] },
      },
      {
        id: "psl-others-and-export-negatives",
        title: "PSL Export Credit and PSL Others are both contracting",
        body: "Export Credit under PSL went ₹11,849 Cr → ₹12,479 Cr → ₹11,436 Cr. FY26 YoY: -8.4%. " +
              "PSL Others went ₹61,015 Cr → ₹49,287 Cr → ₹44,820 Cr. FY26 YoY: -9.6%. " +
              "Both are dropping in absolute terms — likely category redefinitions migrating loans into MSE or Housing PSL buckets.",
        implication: "Treat PSL line-level YoY rates skeptically — they are subject to definition migration each year. " +
                     "PSL aggregate trends are more reliable than PSL line trends.",
        preferredMode: "absolute",
        effect: { highlight: ["Export Credit", "Others"], dash: ["Export Credit", "Others"] },
      },
    ],
    opportunities: [
      {
        id: "pslc-trading-arbitrage",
        title: "PSL Certificates trading is a quiet ₹15K Cr+ wallet most fintechs ignore",
        body: "With PSL targets binding and segment-wise sub-categories all moving (MSE +29.5%, Renewable +34.1%, Housing +39.8% via reclassification), " +
              "the PSLC market clearing volume has expanded materially. " +
              "Traditional banks that overshoot PSL sell certificates; banks short on targets buy them.",
        implication: "Treasury teams and capital-markets desks at PSU and private banks are the natural users. " +
                     "Build digital PSLC trading + analytics tooling for treasuries — the manual spreadsheet workflow is ripe for SaaS replacement.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small Enterprises", "Renewable Energy"] },
      },
    ],
  },

  // ── Section 7: Industry by Type ────────────────────────────────────────────
  industryByType: {
    insights: [
      {
        id: "engineering-petroleum-capex-broadening",
        title: "Capex credit broadening: Engineering, Petroleum, Basic Metal all accelerated",
        body: "All Engineering: 22.0% → 32.2% YoY (₹3.17L Cr at Mar 2026). " +
              "Petroleum, Coal: 16.5% → 32.5% YoY. Basic Metal: 12.8% → 19.4%. " +
              "Cement turned from -0.0% to +9.0%. The PLI capex story has spread beyond electronics.",
        implication: "Capex-themed term-loan books are the operative wallet for project finance teams in FY27. " +
                     "Banks underweight industrial term loans (PSU banks especially) have under-priced upside; private banks are likely already over-allocated.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering", "Petroleum, Coal Products and Nuclear Fuels", "Basic Metal and Metal Product", "Cement and Cement Products"] },
      },
      {
        id: "gems-jewellery-massive-jump",
        title: "Gems & Jewellery industrial credit jumped from 1.0% to 41.4% YoY",
        body: "Gems and Jewellery industrial credit was nearly flat in FY25 (1.0%), then surged to 41.4% in FY26. " +
              "Same root cause as the gold loan retail surge: gold prices crossed ₹90,000/10g in 2025, " +
              "expanding jeweller working capital requirements.",
        implication: "Gems & Jewellery credit is mechanically linked to gold price — if gold reverses, working-capital exposures will roll off fast. " +
                     "Specialised jewellery-lending banks (Federal, Yes, IndusInd) need active gold-price hedging on the underlying book.",
        preferredMode: "yoy",
        effect: { highlight: ["Gems and Jewellery"] },
      },
      {
        id: "infrastructure-laggard-mild-rebound",
        title: "Infrastructure credit grew only 9.5% — still lagging the system rate",
        body: "Infrastructure was the largest single industrial book at ₹14.94L Cr (Mar 2026), but FY26 growth was only 9.5% — " +
              "barely above FY25's 2.8%. " +
              "The FY21-24 infra capex supercycle (highways, metro, power) has matured; new categories (data centres, green hydrogen) have not yet reached scale.",
        implication: "PSU banks heavy on infrastructure (SBI, Bank of Baroda, Canara) will see infra book stabilise as a percentage of total credit. " +
                     "Project finance teams should pivot toward data centre and green-hydrogen pipeline preparation in FY27.",
        preferredMode: "yoy",
        effect: { highlight: ["Infrastructure"] },
      },
    ],
    gaps: [
      {
        id: "industry-by-type-doesnt-tie-to-industry",
        title: "Industry-by-type sums to less than the Industry main-sector total",
        body: "Adding all 19 industry sub-types for Mar 2026 gives ₹46.95L Cr, while the Industry main sector total is ₹45.82L Cr. " +
              "Some sub-types (e.g. 'Other Industries' at ₹3.48L Cr) are catch-all buckets that overlap with named categories. " +
              "Treat the sub-type view as a partition for trend-spotting, not an exact accounting decomposition.",
        implication: "Don't quote sub-type sums as definitive sector composition. " +
                     "Use the size-bucket view (Micro/Medium/Large) for accounting and the type view for thematic analysis.",
        preferredMode: "absolute",
        effect: {},
      },
    ],
    opportunities: [
      {
        id: "vehicle-parts-supply-chain-finance",
        title: "Vehicles & Vehicle Parts credit at +18.1% YoY signals EV supply-chain heating up",
        body: "Vehicle, Vehicle Parts and Transport Equipment industrial credit went from 5.2% → 18.1% YoY. " +
              "Absolute book is ₹1.41L Cr — small, but the acceleration tracks the EV ramp-up at OEMs (Tata, Mahindra, Hyundai-India). " +
              "Tier-1 and Tier-2 component suppliers are entering capex.",
        implication: "Supply-chain financing for vehicle component suppliers is a high-conviction product wedge for FY27. " +
                     "Co-origination with OEM captives or platform models (TReDS, M1xchange) accelerates onboarding.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicles, Vehicle Parts and Transport Equipment"] },
      },
      {
        id: "food-processing-recovery",
        title: "Food Processing credit recovered from 5.1% to 14.0% YoY",
        body: "Food Processing went ₹2.09L Cr → ₹2.20L Cr → ₹2.50L Cr. " +
              "FY25 was sluggish (5.1%); FY26 nearly tripled to 14.0%. " +
              "Cold-chain, FMCG-private-label, and packaged-food capex are the visible drivers.",
        implication: "Agri-supply-chain banks (HDFC, KMB) and specialist NBFCs (Manappuram Food Finance, Mahindra Finance Agri) are best positioned. " +
                     "Processing-park funding under PMKSY and government cluster schemes is another pipeline.",
        preferredMode: "yoy",
        effect: { highlight: ["Food Processing"] },
      },
    ],
  },

};
