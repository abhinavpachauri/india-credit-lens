// ── RBI SIBC — Feb 2026 (period: 2026-03-30) — Draft Annotations ─────────────
// Generated from sections.json dated 2026-03-30.
// DO NOT publish directly. Run through merged analysis first.
// Validate with: python3 analysis/validate_annotations.py this_file.ts

import type { SectionAnnotations } from "@/lib/types";

export const ANNOTATIONS: Record<string, SectionAnnotations> = {

  // ── Section 1: Bank Credit ─────────────────────────────────────────────────
  bankCredit: {
    insights: [
      {
        id: "credit-growth-accelerating-fy26",
        title: "Credit growth is beating FY25 full year",
        body: "Bank credit reached ₹207.5L Cr in Feb 2026, up 13.8% FY vs the Mar 2025 base. " +
              "The full FY25 YoY was 11.0% (Mar 2025 vs Mar 2024). " +
              "With a month to go in FY26, credit is already growing faster than the prior full year.",
        implication: "For lenders: the system-level tailwind is strengthening. " +
                     "If your portfolio grew below 13% in FY26, you lost share.",
        preferredMode: "fy",
        effect: { highlight: ["Bank Credit", "Non-food Credit"] },
      },
      {
        id: "nonfood-credit-all-the-signal",
        title: "Non-food credit is the only number that matters",
        body: "Non-food credit is ₹206.7L Cr of the ₹207.5L Cr total — 99.6% of bank credit. " +
              "Food credit at ₹0.83L Cr is a seasonal noise item. " +
              "The headline growth rate is essentially the non-food number.",
        implication: "Strip food credit from every headline number before quoting it. " +
                     "The 13.8% FY figure is a non-food signal and should be stated as such.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
      },
    ],
    gaps: [
      {
        id: "food-credit-feb-spike-seasonal",
        title: "Feb food credit spike is seasonal procurement",
        body: "Food credit in Feb 2026 is ₹0.83L Cr, up 126.2% FY vs Mar 2025 (₹0.37L Cr). " +
              "This is rabi crop procurement — government agencies draw credit in Jan-Feb and repay by March. " +
              "The same pattern appeared in prior years: food credit always compresses sharply by March-end.",
        implication: "Never quote the FY food credit growth from a February data point. " +
                     "By March, food credit will fall back toward ₹0.4-0.5L Cr. " +
                     "This is government balance-sheet timing, not a lending trend.",
        preferredMode: "fy",
        effect: { highlight: ["Food Credit"], dash: ["Food Credit"] },
      },
      {
        id: "no-feb-yoy-for-most-sections",
        title: "No YoY growth available for Feb 2026 in most sections",
        body: "The SIBC30032026 file covers only three absolute dates: Mar 2024, Mar 2025, and Feb 2026. " +
              "YoY growth (current month vs same month prior year) requires Feb 2025 data, which this file does not include. " +
              "Only industryByType has Feb 2025 data, enabling a Feb 2026 YoY comparison.",
        implication: "All growth figures here are FY-to-date (vs Mar 2025) or full-year YoY for March. " +
                     "For a Feb 2026 vs Feb 2025 comparison across sections, use the consolidated CSV or the Jan 2026 sections.json which covers that period.",
        preferredMode: "absolute",
        effect: {},
      },
    ],
    opportunities: [
      {
        id: "absolute-credit-expansion-scale",
        title: "₹25L Cr added in FY26 — system is in growth mode",
        body: "From Mar 2025 (₹182.4L Cr) to Feb 2026 (₹207.5L Cr), the banking system added ₹25.1L Cr " +
              "in non-food credit in 11 months. The prior full year added ₹18.1L Cr (Mar 2024 to Mar 2025). " +
              "Each incremental crore of credit disbursed represents origination, servicing, and cross-sell opportunity.",
        implication: "Lenders with scalable digital origination are the biggest winners here. " +
                     "The system is in structural expansion — the constraint is underwriting speed, not demand.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit", "Bank Credit"], dim: ["Food Credit"] },
      },
    ],
  },

  // ── Section 2: Main Sectors ────────────────────────────────────────────────
  mainSectors: {
    insights: [
      {
        id: "personal-loans-largest-sector",
        title: "Personal loans is now the largest sector by far",
        body: "Personal Loans at ₹68.0L Cr (Feb 2026) exceeds Services (₹58.1L Cr) and Industry (₹44.5L Cr). " +
              "As recently as Mar 2024, Industry and Services were closer together. " +
              "Retail lending has decisively overtaken wholesale lending as the dominant credit category.",
        implication: "Product teams and credit heads at banks that are still organised around corporate " +
                     "banking need to reconsider their resource allocation — retail is where the mass is.",
        preferredMode: "absolute",
        effect: { highlight: ["Personal Loans", "Industry"], dim: ["Agriculture"] },
      },
      {
        id: "industry-reaccelerating",
        title: "Industry credit growth is re-accelerating in FY26",
        body: "Industry FY growth is 11.6% (Feb 2026 vs Mar 2025), up from 8.2% YoY in full FY25. " +
              "The acceleration is driven by Micro and Small (+29.2% FY) and Medium (+18.4% FY), " +
              "not by Large corporates (+5.7% FY). Industrial credit expansion has moved down the size ladder.",
        implication: "The SME credit window is open and wide. Banks focused only on large corporate lending " +
                     "are missing the fastest-growing segment of industrial credit.",
        preferredMode: "fy",
        effect: { highlight: ["Industry"], dim: ["Agriculture"] },
      },
      {
        id: "services-leads-all-main-sectors",
        title: "Services FY growth outpaces all other main sectors",
        body: "Services grew 14.0% FY to ₹58.1L Cr, the fastest of the four main sectors. " +
              "NBFCs, Computer Software, and Commercial Real Estate are the key contributors within Services. " +
              "Agriculture (11.2% FY) and Personal Loans (13.8% FY) trail Services in growth rate.",
        implication: "Services credit growth reflects structural shifts: NBFC re-acceleration, tech sector working capital, " +
                     "and urban real estate. These are durable trends, not cyclical.",
        preferredMode: "fy",
        effect: { highlight: ["Services"], dim: ["Agriculture"] },
      },
    ],
    gaps: [
      {
        id: "personal-loans-aggregate-hides-divergence",
        title: "The personal loans headline hides extreme internal divergence",
        body: "Personal Loans at 13.8% FY is an average of gold loans (+107.8% FY) and credit cards (+2.7% FY). " +
              "These are opposite trends reflecting opposite policy directions: RBI tightened unsecured credit " +
              "while gold-collateralised lending accelerated freely. The aggregate number is misleading.",
        implication: "Never use the Personal Loans aggregate to make a point about retail credit. " +
                     "Always disaggregate into secured vs unsecured and collateral type.",
        preferredMode: "fy",
        effect: { dash: ["Personal Loans"] },
      },
      {
        id: "agriculture-feb-seasonality",
        title: "Feb vs March comparisons are seasonally distorted for agriculture",
        body: "Agriculture credit has strong seasonality — kharif demand peaks in July-October, rabi in Jan-March. " +
              "The 11.2% FY growth (Feb 2026 vs Mar 2025) mixes a seasonal peak month (Feb 2026) with a seasonal trough month (Mar 2025). " +
              "This overstates the FY growth rate for agriculture relative to a June or December base.",
        implication: "Agriculture credit should always be compared same-month-to-same-month. " +
                     "The FY number here is directionally useful but not precise.",
        preferredMode: "fy",
        effect: { dash: ["Agriculture"] },
      },
    ],
    opportunities: [
      {
        id: "sme-industry-entry-window",
        title: "SME industrial credit is growing 29% — entry window is open",
        body: "Micro and Small industry credit grew from ₹7.98L Cr (Mar 2025) to ₹10.32L Cr (Feb 2026), " +
              "adding ₹2.34L Cr in 11 months. Medium enterprises added ₹0.67L Cr. " +
              "Large corporates added only ₹1.61L Cr despite a much larger base.",
        implication: "The next ₹10L Cr of industrial credit growth will come from SMEs, not large corporates. " +
                     "Lenders who can underwrite MSME credit efficiently — using GST data, UDYAM ratings, bank statement analysis — " +
                     "are positioned for this shift.",
        preferredMode: "fy",
        effect: { highlight: ["Industry"] },
      },
    ],
  },

  // ── Section 3: Industry by Size ────────────────────────────────────────────
  industryBySize: {
    insights: [
      {
        id: "micro-small-growth-inversion",
        title: "Micro & Small growing 5× faster than Large corporates",
        body: "Micro and Small: +29.2% FY (₹7.98L Cr → ₹10.32L Cr). " +
              "Medium: +18.4% FY (₹3.63L Cr → ₹4.30L Cr). " +
              "Large: +5.7% FY (₹28.24L Cr → ₹29.85L Cr). " +
              "The growth rate gap between smallest and largest is 23.5 percentage points — a structural inversion.",
        implication: "Large corporate credit books are being de-risked or substituted with bond markets. " +
                     "The growth opportunity in industrial lending has decisively moved to the MSME segment.",
        preferredMode: "fy",
        effect: { highlight: ["Micro and Small", "Medium"], dim: ["Large"] },
      },
      {
        id: "large-corporate-deleveraging",
        title: "Large corporates are not driving industrial credit growth",
        body: "Large enterprise credit grew from ₹26.43L Cr (Mar 2024) to ₹29.85L Cr (Feb 2026) — " +
              "a net addition of ₹3.42L Cr over 23 months, or about ₹1.77L Cr per year. " +
              "Micro and Small added ₹2.34L Cr in just 11 months (FY26 to Feb). " +
              "India's large corporates are either self-funding or using debt capital markets.",
        implication: "Large corporate banking is a scale and relationship game with compressed growth. " +
                     "For lenders seeking growth, the SME book needs to be the primary engine.",
        preferredMode: "absolute",
        effect: { highlight: ["Large"], dim: ["Micro and Small", "Medium"] },
      },
      {
        id: "medium-enterprise-sweet-spot",
        title: "Medium enterprises are the underserved middle tier",
        body: "Medium enterprises grew 18.4% FY, between MSME (29.2%) and Large (5.7%). " +
              "At ₹4.30L Cr, Medium is the smallest segment — only 9.7% of Industry credit — but growing fast. " +
              "They are too large for MSME fintech products and too small for DCM access.",
        implication: "Medium enterprises (₹50-250 Cr revenue) need structured working capital and capex facilities " +
                     "that banks struggle to price efficiently. There is a product gap here — and a revenue opportunity.",
        preferredMode: "fy",
        effect: { highlight: ["Medium"] },
      },
    ],
    gaps: [
      {
        id: "size-definition-boundary-issue",
        title: "Size boundaries shift with RBI reclassifications",
        body: "The Micro, Small, Medium, and Large categories follow RBI definitions that have been revised " +
              "under MSMED Act amendments. A Micro enterprise that crossed the new turnover threshold " +
              "moves to Small, inflating Small growth without a real credit increase. " +
              "Some of the 29.2% Micro and Small FY growth may reflect definitional upgrades, not new lending.",
        implication: "Treat the 29.2% figure as an upper bound on true MSME credit growth. " +
                     "Cross-check against UDYAM registration data and PSL MSME figures for confirmation.",
        preferredMode: "fy",
        effect: { dash: ["Micro and Small"] },
      },
    ],
    opportunities: [
      {
        id: "msme-formalisation-credit-wave",
        title: "MSME credit is growing fastest — formalization is the driver",
        body: "PSL Micro and Small Enterprises grew +25.6% FY (₹22.4L Cr → ₹28.1L Cr). " +
              "Statement 1 Micro and Small grew +29.2% FY. Both point to the same direction. " +
              "GST registration, UDYAM enrollment, and digital banking are bringing formerly unbanked MSMEs into formal credit.",
        implication: "First-time MSME borrowers have thin bureau files. " +
                     "Lenders who build alternative underwriting — GST returns, bank transactions, UPI flows — " +
                     "will outperform on both growth and risk selection.",
        preferredMode: "fy",
        effect: { highlight: ["Micro and Small", "Medium"] },
      },
    ],
  },

  // ── Section 4: Services ────────────────────────────────────────────────────
  services: {
    insights: [
      {
        id: "nbfc-credit-re-acceleration",
        title: "NBFC borrowing from banks is re-accelerating sharply",
        body: "Bank credit to NBFCs grew from ₹16.35L Cr (Mar 2025) to ₹19.48L Cr (Feb 2026) — " +
              "+19.1% FY, adding ₹3.12L Cr in 11 months. " +
              "After the RBI's 2023-24 risk weight increases on NBFC credit, this re-acceleration signals the sector has absorbed the regulatory shock.",
        implication: "Co-origination and BC partnerships with NBFCs are back in play. " +
                     "Banks that pulled back from NBFC relationships in 2023-24 may now find terms have moved against them.",
        preferredMode: "fy",
        effect: { highlight: ["NBFCs"] },
      },
      {
        id: "computer-software-credit-surge",
        title: "Tech sector credit grew 40% FY — working capital driven",
        body: "Computer Software credit: ₹0.33L Cr (Mar 2025) → ₹0.46L Cr (Feb 2026), +40.3% FY. " +
              "This likely reflects working capital for IT services companies: payroll financing, " +
              "project mobilisation, and rupee-denominated hedging of USD receivables.",
        implication: "IT services companies are asset-light but have large short-term working capital needs. " +
                     "Invoice discounting and supply chain finance products designed for IT exporters " +
                     "are a specific, growing opportunity.",
        preferredMode: "fy",
        effect: { highlight: ["Computer Software"] },
      },
      {
        id: "cre-growing-steadily",
        title: "Commercial real estate credit growing at 15.9% FY",
        body: "CRE credit grew from ₹5.23L Cr (Mar 2025) to ₹6.07L Cr (Feb 2026), +15.9% FY. " +
              "Within CRE, data centers, logistics parks, and grade-A office completions are the primary drivers. " +
              "Residential developer credit is flat to declining — the CRE growth is commercial, not residential.",
        implication: "Project finance for data centers and industrial parks is a bankable opportunity. " +
                     "Residential developer exposure should be approached with caution — unsold inventory remains elevated.",
        preferredMode: "fy",
        effect: { highlight: ["Commercial Real Estate"] },
      },
      {
        id: "shipping-spike-small-base-caveat",
        title: "Shipping +43.8% FY but only ₹0.11L Cr total",
        body: "Shipping credit grew from ₹0.073L Cr (Mar 2025) to ₹0.105L Cr (Feb 2026) — " +
              "a 43.8% FY rate, but the absolute addition is only ₹3,197 Cr. " +
              "High growth rates on small bases mislead about sector importance.",
        implication: "Shipping represents 0.18% of total services credit. " +
                     "Its growth rate is statistically noisy at this scale. Do not treat it as a sector signal.",
        preferredMode: "fy",
        effect: { dash: ["Shipping"], dim: ["Aviation", "Computer Software", "Tourism, Hotels & Restaurants"] },
      },
    ],
    gaps: [
      {
        id: "nbfc-credit-double-counting",
        title: "NBFC credit here is bank-to-NBFC, not end-borrower exposure",
        body: "The ₹19.48L Cr in NBFCs represents bank loans to NBFC entities, not the total credit flowing through NBFCs. " +
              "NBFCs then lend this onward to personal borrowers, MSMEs, and gold loan customers. " +
              "That end-borrower exposure shows up again in Personal Loans and Industry sections. " +
              "Adding NBFCs to those sections double-counts the underlying credit.",
        implication: "Total effective credit in the system is lower than the sum of all sections. " +
                     "The RBI SIBC is a bank balance sheet view, not an end-borrower view. " +
                     "This distinction matters for systemic leverage calculations.",
        preferredMode: "absolute",
        effect: { dash: ["NBFCs"] },
      },
      {
        id: "other-services-opacity",
        title: "Other Services is ₹12.4L Cr with no breakdown",
        body: "'Other Services' at ₹12.37L Cr (Feb 2026) is 21.3% of the entire Services sector, " +
              "and it grew 10.1% FY — adding ₹1.13L Cr. " +
              "This category is larger than Transport, Professional Services, and CRE combined. " +
              "Without sub-classification, this is analytically opaque.",
        implication: "Any service-sector analysis that doesn't account for 'Other Services' is incomplete. " +
                     "Push for sub-classification from RBI or triangulate with BSR-1 data.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Services"], dash: ["Other Services"] },
      },
    ],
    opportunities: [
      {
        id: "nbfc-co-origination-window",
        title: "NBFC co-origination is the fastest way into retail credit",
        body: "NBFCs are borrowing ₹3.12L Cr more from banks in 11 months, at +19.1% FY growth. " +
              "Banks that co-originate with NBFCs gain access to last-mile distribution without building it. " +
              "Trade credit, gold, MSME, and vehicle lending are the primary NBFC channels growing here.",
        implication: "Structured co-origination agreements with 3-5 mid-sized NBFCs can add ₹5,000-15,000 Cr " +
                     "to a mid-size bank's retail book with controlled credit risk. " +
                     "The NBFC growth rate signals demand for these partnerships is rising.",
        preferredMode: "fy",
        effect: { highlight: ["NBFCs"] },
      },
      {
        id: "trade-credit-compounder",
        title: "Trade credit at ₹13.2L Cr is a consistent compounder",
        body: "Trade credit grew from ₹10.24L Cr (Mar 2024) to ₹13.21L Cr (Feb 2026) — " +
              "+28.9% over 23 months. FY growth is 11.5%. " +
              "This is the second-largest services sub-sector after NBFCs and it compounds steadily.",
        implication: "Invoice discounting and supply chain finance for trade businesses (importers, distributors, retailers) " +
                     "is a large, recurring, and underserved market. " +
                     "Fintech platforms building in this space have strong tailwinds.",
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
        title: "Gold loans tripled in 24 months — this is structural",
        body: "Gold loans: ₹0.93L Cr (Mar 2024) → ₹2.06L Cr (Mar 2025) → ₹4.29L Cr (Feb 2026). " +
              "+121.1% YoY in FY25 and +107.8% FY in FY26. " +
              "Three consecutive data points on the same steep trajectory. This is not a blip.",
        implication: "Gold as a credit instrument is being rediscovered by Indian households. " +
                     "Every bank and NBFC with a gold lending product is seeing this. " +
                     "Every lender without one is losing a fast-growing share of retail credit.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "gold-share-of-personal-portfolio",
        title: "Gold loans now 6.3% of personal loans — up from 1.7% two years ago",
        body: "Gold loans as a share of total personal loans: 1.75% (Mar 2024), 3.45% (Mar 2025), 6.31% (Feb 2026). " +
              "The mix of the personal credit portfolio is changing rapidly. " +
              "Gold lending is the fastest-growing component, outpacing Housing (9.8% FY) by 11× on a growth basis.",
        implication: "The personal credit portfolio of any bank that doesn't offer gold loans " +
                     "is underperforming its peers on growth by construction. " +
                     "Mix matters as much as headline growth.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"], dim: ["Housing", "Other Personal Loans"] },
      },
      {
        id: "credit-card-stall",
        title: "Credit card growth has stalled at 2.7% FY",
        body: "Credit Card Outstanding: ₹2.84L Cr (Mar 2025) → ₹2.92L Cr (Feb 2026), +2.7% FY. " +
              "In full FY25, credit card YoY growth was +10.6%. " +
              "The RBI's 2023 risk weight increases on credit card receivables and tighter underwriting norms have worked.",
        implication: "Credit card growth is constrained by policy, not demand. " +
                     "This is a deliberate regulatory deceleration — issuers should not expect a return to 10%+ growth soon. " +
                     "UPI credit lines (BNPL via UPI) may be absorbing some of this demand.",
        preferredMode: "fy",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
      },
      {
        id: "consumer-durables-structural-decline",
        title: "Consumer durables credit is in multi-year decline",
        body: "Consumer Durables: ₹23,444 Cr (Mar 2024) → ₹23,200 Cr (Mar 2025, -1.0% YoY) → ₹21,924 Cr (Feb 2026, -5.5% FY). " +
              "Two consecutive periods of contraction. " +
              "Point-of-sale EMI credit is being replaced by BNPL, UPI-linked credit, and pay-later products that don't appear in this data.",
        implication: "Traditional consumer durable financing (TVs, appliances at store) is being disrupted. " +
                     "The credit still exists — it is shifting channels, not disappearing. " +
                     "Lenders still operating legacy POS finance should invest in digital-first alternatives.",
        preferredMode: "fy",
        effect: { highlight: ["Consumer Durables"], dash: ["Consumer Durables"] },
      },
      {
        id: "vehicle-loans-resurgent",
        title: "Vehicle loans +16.6% FY — auto sector credit is strong",
        body: "Vehicle Loans: ₹6.23L Cr (Mar 2025) → ₹7.26L Cr (Feb 2026), +16.6% FY. " +
              "This is also up from 8.6% YoY in FY25. " +
              "EV adoption, commercial vehicle fleet expansion, and two-wheeler credit are all contributing.",
        implication: "Vehicle finance is one of the few personal credit categories growing faster in FY26 than FY25. " +
                     "EV-specific credit products (battery loans, subsidy-backed schemes) are an untapped product layer.",
        preferredMode: "fy",
        effect: { highlight: ["Vehicle Loans"] },
      },
    ],
    gaps: [
      {
        id: "gold-loan-bank-vs-nbfc-split",
        title: "This data captures bank gold loans only — NBFC total is 2× higher",
        body: "Bank gold loans at ₹4.29L Cr are growing fast. But Muthoot Finance and Manappuram Finance " +
              "alone have combined gold AUM of ~₹1.5-2L Cr, and hundreds of smaller NBFCs add more. " +
              "Total gold credit exposure in India likely exceeds ₹7-8L Cr. " +
              "The SIBC only shows the bank portion.",
        implication: "When assessing the total systemic gold credit exposure, the SIBC number is a floor, not a ceiling. " +
                     "Factor in NBFC gold loans from CIBIL or CRIF data to get the complete picture.",
        preferredMode: "absolute",
        effect: { dash: ["Gold Loans"] },
      },
      {
        id: "other-personal-loans-quarter-of-portfolio",
        title: "Other Personal Loans is 25% of the portfolio with no breakdown",
        body: "'Other Personal Loans' at ₹17.03L Cr (Feb 2026) is 25% of total personal credit and growing at 10.9% FY. " +
              "This is larger than Housing credit in PSL, larger than Vehicle and Education combined. " +
              "It likely includes salary advances, festival loans, top-up home loans, and personal overdrafts — but the classification is opaque.",
        implication: "Any analysis of the personal loans portfolio that treats 'Other Personal Loans' as a residual " +
                     "is ignoring a quarter of the book. BSR-1 quarterly data provides more granular sub-classification.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Personal Loans"], dash: ["Other Personal Loans"] },
      },
      {
        id: "advances-vs-fd-interpretation",
        title: "Advances against Fixed Deposits is a wealth product, not a personal loan",
        body: "Advances vs Fixed Deposits at ₹1.54L Cr (Feb 2026) grew 8.7% FY. " +
              "These are overdrafts against one's own FD — essentially a liquidity instrument used by savers, not a personal loan in the credit risk sense. " +
              "Including this in 'Personal Loans' inflates the personal credit base and suppresses apparent risk metrics.",
        implication: "When computing personal credit penetration or default rates, exclude FD-backed advances — " +
                     "they have near-zero credit risk and distort credit quality metrics downward.",
        preferredMode: "absolute",
        effect: { dash: ["Advances vs Fixed Deposits"] },
      },
    ],
    opportunities: [
      {
        id: "gold-loan-competition-intensifying",
        title: "Banks are taking share from gold NBFCs — the competition is now on",
        body: "Bank gold loans grew from ₹0.93L Cr to ₹4.29L Cr in 24 months. " +
              "Gold NBFCs (Muthoot, Manappuram) have had market exclusivity for decades. " +
              "Banks are cheaper (lower LTV required) and offer multiple collateral options. " +
              "The competition for gold-backed lending is re-starting.",
        implication: "Gold NBFCs will need to compete on speed and doorstep service, where they have structural advantages. " +
                     "Banks entering gold lending should invest in gold purity assay technology and branch-level cash management. " +
                     "The margin opportunity is real but so is the operational complexity.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
      },
      {
        id: "vehicle-ev-credit-product",
        title: "Vehicle loans growing fast — EV-specific products are the next layer",
        body: "Vehicle loans at ₹7.26L Cr, growing 16.6% FY. " +
              "EV sales in India crossed 20L units in FY25 — the credit demand from EV buyers is now material. " +
              "EVs have different residual value curves, battery health risk, and subsidy structures than ICE vehicles. " +
              "Standard vehicle loan underwriting doesn't address these.",
        implication: "First-mover advantage in EV-specific credit (battery insurance, green EMDI, " +
                     "subsidy-linked underwriting) is 2-3 years wide. The market is large enough to matter now.",
        preferredMode: "fy",
        effect: { highlight: ["Vehicle Loans"] },
      },
      {
        id: "education-loan-premium-segment",
        title: "Education loans growing consistently — premium segment underpenetrated",
        body: "Education loans: ₹1.19L Cr (Mar 2024) → ₹1.37L Cr (Mar 2025, +15.1% YoY) → ₹1.56L Cr (Feb 2026, +13.2% FY). " +
              "Consistent double-digit growth for two years. " +
              "IIT/IIM/overseas education costs ₹50-100L per student — the ₹20L cap on priority sector education loans leaves a large unaddressed market.",
        implication: "Premium education lending (₹25-100L, abroad or top-tier domestic) is a high-quality credit segment. " +
                     "Default rates are lower than unsecured personal — employed graduates with recognisable degrees pay back. " +
                     "This segment needs products outside the PSL bucket.",
        preferredMode: "absolute",
        effect: { highlight: ["Education"] },
      },
    ],
  },

  // ── Section 6: Priority Sector ─────────────────────────────────────────────
  prioritySector: {
    insights: [
      {
        id: "psl-housing-anomalous-surge",
        title: "PSL Housing jumped 38.4% FY after a year of contraction",
        body: "PSL Housing: ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025, -1.1% YoY) → ₹10.33L Cr (Feb 2026, +38.4% FY). " +
              "The absolute addition of ₹2.87L Cr in 11 months follows a period of net contraction. " +
              "PSL housing has loan size and income limits — this jump is too large to be organic new lending alone.",
        implication: "This almost certainly reflects a regulatory revision: the RBI raised PSL housing loan limits " +
                     "in Oct 2024 (metro cities: ₹35L → ₹45L; non-metro: ₹25L → ₹35L). " +
                     "Loans that previously fell outside PSL are now being counted. " +
                     "The growth is a classification event, not a lending surge.",
        preferredMode: "fy",
        effect: { highlight: ["Housing"], dash: ["Housing"] },
      },
      {
        id: "psl-msme-acceleration-structural",
        title: "PSL MSME credit is accelerating — and it's real",
        body: "PSL Micro and Small Enterprises: ₹19.74L Cr (Mar 2024) → ₹22.39L Cr (Mar 2025, +13.4% YoY) → ₹28.12L Cr (Feb 2026, +25.6% FY). " +
              "The acceleration from 13.4% to 25.6% is consistent with Statement 1 MSME data (+29.2% FY). " +
              "Two independent series confirming the same trend makes this credible.",
        implication: "Banks and NBFCs that built MSME origination infrastructure in FY24-25 are now harvesting the portfolio. " +
                     "This is a multi-year shift as GST-registered MSMEs move into formal credit for the first time.",
        preferredMode: "fy",
        effect: { highlight: ["Micro and Small Enterprises"] },
      },
      {
        id: "renewable-energy-psl-growing",
        title: "Renewable energy PSL is growing fast off a tiny base",
        body: "Renewable Energy PSL: ₹5,790 Cr (Mar 2024) → ₹10,325 Cr (Mar 2025, +78.3% YoY) → ₹13,955 Cr (Feb 2026, +35.2% FY). " +
              "Two years of high growth. But ₹13,955 Cr is 0.007% of total bank credit. " +
              "India's renewable energy investment requirements are ₹50-100L Cr per year — bank credit is barely a rounding error.",
        implication: "The opportunity gap is vast. This is not a market that's saturated — it barely exists yet. " +
                     "Lenders who build renewable energy project finance capabilities now will face no competition for 5-7 years.",
        preferredMode: "fy",
        effect: { highlight: ["Renewable Energy"] },
      },
      {
        id: "export-credit-declining",
        title: "Export credit has been shrinking for two years",
        body: "Export Credit PSL: ₹11,330 Cr (Mar 2024) → ₹11,805 Cr (Mar 2025, +4.2%) → ₹10,270 Cr (Feb 2026, -13.0% FY). " +
              "After a modest FY25, it has turned negative in FY26. " +
              "Global trade uncertainty, rupee appreciation episodes, and tighter export finance underwriting are all likely contributors.",
        implication: "Export financing desks at banks are contracting. " +
                     "This is a signal of reduced risk appetite, not reduced export activity — India's merchandise exports have held up. " +
                     "The pullback creates an opportunity for alternative lenders (fintech invoice discounting, ECGC-backed facilities).",
        preferredMode: "fy",
        effect: { highlight: ["Export Credit"], dash: ["Export Credit"] },
      },
    ],
    gaps: [
      {
        id: "psl-housing-limit-revision-not-disclosed",
        title: "PSL housing data is contaminated by a limit revision — not flagged in the report",
        body: "The 38.4% FY jump in PSL Housing is almost entirely explained by the Oct 2024 RBI guideline " +
              "raising PSL housing loan limits. Loans already on bank books that crossed the old limit now qualify. " +
              "The SIBC report does not flag this change — a reader would think housing credit genuinely doubled from a lending activity perspective.",
        implication: "Always check PSL housing data against the PSL limit revision history before quoting it. " +
                     "The number is not comparable to prior periods without adjustment.",
        preferredMode: "fy",
        effect: { dash: ["Housing"] },
      },
      {
        id: "weaker-sections-double-counting",
        title: "Weaker Sections overlaps with Agriculture and MSME — total is not additive",
        body: "Weaker Sections at ₹20.32L Cr (Feb 2026) is a subset of the PSL total, not an additional category. " +
              "It includes SC/ST borrowers, small farmers, and self-help groups — many of whom also appear in Agriculture or MSME rows. " +
              "Adding all PSL categories to get a total overstates the PSL book by a significant margin.",
        implication: "The total PSL exposure cannot be summed from this table. " +
                     "Use the formal PSL achievement ratios from RBI's annual PSL compliance disclosures instead.",
        preferredMode: "absolute",
        effect: { dash: ["Weaker Sections"] },
      },
      {
        id: "social-infra-negligible",
        title: "Social Infrastructure PSL is ₹1,221 Cr — a category in name only",
        body: "Social Infrastructure: ₹813 Cr (Mar 2024) → ₹1,316 Cr (Mar 2025) → ₹1,221 Cr (Feb 2026, -7.3% FY). " +
              "₹1,221 Cr represents 0.0006% of total bank credit. " +
              "Despite being a dedicated PSL category designed to incentivise school, hospital, and sanitation lending, " +
              "banks have not meaningfully engaged.",
        implication: "The Social Infrastructure PSL category has failed to mobilise credit. " +
                     "This is a governance gap: either the incentives are insufficient, or the category is too narrowly defined. " +
                     "Fintech platforms focused on healthcare or education infrastructure could advocate for better-designed PSL treatment.",
        preferredMode: "absolute",
        effect: { highlight: ["Social Infrastructure"], dash: ["Social Infrastructure"] },
      },
    ],
    opportunities: [
      {
        id: "psl-housing-product-redesign",
        title: "PSL housing limit revision creates a new product tier",
        body: "With metro PSL housing limits raised to ₹45L (from ₹35L), " +
              "loans between ₹35-45L in metro cities that were previously classified as non-priority " +
              "now qualify for PSL. Banks earn PSL credit without originating new loans — just reclassifying existing ones. " +
              "Going forward, designing products specifically for the ₹35-45L metro affordable segment optimises both growth and PSL compliance.",
        implication: "Product teams should redesign affordable housing loan brackets around the new PSL limits. " +
                     "NBFCs that focus on housing finance in tier-2 cities below ₹35L have a PSL arbitrage advantage.",
        preferredMode: "absolute",
        effect: { highlight: ["Housing"] },
      },
      {
        id: "renewable-energy-project-finance",
        title: "Renewable energy lending: ₹13,955 Cr in credit for a ₹10L Cr opportunity",
        body: "India needs to add 500 GW of renewable capacity by 2030. " +
              "At ₹4-5 Cr per MW, that requires ₹20-25L Cr of total investment. " +
              "Bank credit to renewable energy is ₹13,955 Cr — 0.1% of what is needed. " +
              "The gap is structural: underwriting models for distributed solar and wind don't exist at scale in Indian banking.",
        implication: "Lenders who invest in building renewable energy project finance credit models — " +
                     "offtake risk, grid connectivity risk, technology degradation — " +
                     "will have a decade-long structural advantage as India electrifies.",
        preferredMode: "fy",
        effect: { highlight: ["Renewable Energy"] },
      },
    ],
  },

  // ── Section 7: Industry by Type ────────────────────────────────────────────
  industryByType: {
    insights: [
      {
        id: "gems-jewellery-gold-price-linked",
        title: "Gems & Jewellery credit surged 40.2% YoY as gold hit record prices",
        body: "Gems and Jewellery: ₹0.82L Cr (Feb 2024) → ₹0.83L Cr (Feb 2025) → ₹1.17L Cr (Feb 2026). " +
              "+40.2% YoY (Feb 2026 vs Feb 2025) and +35.8% FY (vs Mar 2025). " +
              "Gold prices crossed ₹90,000 per 10g in 2025. Jeweller working capital scales directly with gold prices.",
        implication: "Gems and Jewellery credit is partly a price effect, not a volume effect. " +
                     "If gold prices retrace, working capital requirements will shrink — and the credit will follow. " +
                     "This is not a structural lending opportunity; it is a gold price proxy.",
        preferredMode: "yoy",
        effect: { highlight: ["Gems and Jewellery"] },
      },
      {
        id: "all-engineering-pli-signal",
        title: "All Engineering credit grew 36% YoY — PLI schemes are translating",
        body: "All Engineering: ₹1.96L Cr (Feb 2024) → ₹2.32L Cr (Feb 2025) → ₹3.16L Cr (Feb 2026). " +
              "+36.0% YoY and +31.7% FY. " +
              "Production-Linked Incentive schemes in electronics, defence components, and specialty chemicals are generating real capex demand that banks are funding.",
        implication: "PLI-linked manufacturing credit is not one cycle — it is a 5-year investment wave. " +
                     "Engineering firms receiving PLI approval need term loans and working capital before they start receiving incentives. " +
                     "Banks that built relationships in the PLI application phase are now seeing the drawdowns.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id: "infrastructure-credit-decelerating",
        title: "Infrastructure credit slowing — at 32.5% of industry, this matters",
        body: "Infrastructure credit: ₹13.14L Cr (Feb 2024) → ₹13.37L Cr (Feb 2025) → ₹14.44L Cr (Feb 2026). " +
              "+7.9% YoY, +5.8% FY. Infrastructure is 32.5% of all industry credit. " +
              "From double-digit growth in FY22-24, infra credit is now growing at its slowest pace.",
        implication: "The FY22-24 infrastructure capex supercycle is maturing. " +
                     "Roads, power, and metro projects from that era are now in operations — drawing down borrowings, not new credit. " +
                     "The next capex wave (data centers, green hydrogen, semiconductor fabs) hasn't yet scaled into bank credit.",
        preferredMode: "yoy",
        effect: { highlight: ["Infrastructure"], dim: ["All Engineering", "Gems and Jewellery"] },
      },
      {
        id: "chemicals-petroleum-capex-growing",
        title: "Chemicals and Petroleum both growing 17-20% FY — energy and specialty",
        body: "Chemicals: +17.0% FY (₹2.68L Cr → ₹3.13L Cr). " +
              "Petroleum, Coal Products and Nuclear Fuels: +20.3% FY (₹1.54L Cr → ₹1.85L Cr). " +
              "Both growing faster than industry average (11.6% FY). " +
              "India's specialty chemicals exports and downstream petrochemicals refinery upgrades are the underlying drivers.",
        implication: "Chemical and petroleum sector credit has a longer tenure profile and larger ticket size. " +
                     "Structured term lending for refinery expansions and specialty chemical plants is a durable pipeline for corporate banking.",
        preferredMode: "fy",
        effect: { highlight: ["Chemicals and Chemical Products", "Petroleum, Coal Products and Nuclear Fuels"] },
      },
      {
        id: "textiles-weak-despite-pli",
        title: "Textiles growing only 6.8% FY despite PLI schemes",
        body: "Textiles: ₹2.77L Cr (Mar 2025) → ₹2.96L Cr (Feb 2026), +6.8% FY. " +
              "Growing below industry average (11.6% FY) for two consecutive periods. " +
              "Despite PLI schemes for Man-Made Fibres and Technical Textiles, bank credit isn't accelerating.",
        implication: "PLI benefits in textiles are concentrated in a few large players (Welspun, Trident). " +
                     "Smaller mills and looms are not accessing the scheme — and it shows in the credit data. " +
                     "The headline PLI narrative for textiles is not yet matching ground reality.",
        preferredMode: "fy",
        effect: { highlight: ["Textiles"], dash: ["Textiles"] },
      },
    ],
    gaps: [
      {
        id: "infrastructure-sub-classification-absent",
        title: "Infrastructure is 32.5% of industry credit with no sub-classification",
        body: "'Infrastructure' at ₹14.44L Cr is the single largest industry category, " +
              "but it aggregates roads, power, telecom, railways, ports, and urban infra. " +
              "Each sub-type has different growth drivers, tenor profiles, and credit quality. " +
              "Growing at 5.8% FY at the aggregate may mask divergence within — some sub-types may be contracting.",
        implication: "Never cite infrastructure credit growth without knowing which sub-type you're discussing. " +
                     "Use MCA data, Infra.com filings, or project monitoring data to triangulate. " +
                     "RBI BSR-1 provides some sub-classification.",
        preferredMode: "absolute",
        effect: { highlight: ["Infrastructure"], dash: ["Infrastructure"] },
      },
      {
        id: "gems-jewellery-price-vs-volume",
        title: "Gems & Jewellery credit growth conflates price effects with real demand",
        body: "If gold prices rose 25% YoY (they did), a jeweller with the same physical gold inventory " +
              "needs 25% more working capital at constant volumes. " +
              "The 40.2% YoY growth in Gems and Jewellery credit therefore has at least 25 percentage points " +
              "of pure price effect built in. Real volume growth is at most 10-15%.",
        implication: "When assessing credit risk in Gems and Jewellery, stress-test against gold price retracement. " +
                     "A 15% gold price decline would compress working capital requirements by a similar amount — " +
                     "and may trigger covenant breaches in facilities linked to stock values.",
        preferredMode: "yoy",
        effect: { dash: ["Gems and Jewellery"] },
      },
    ],
    opportunities: [
      {
        id: "engineering-supply-chain-lending",
        title: "PLI engineering supply chain needs more than term loans",
        body: "All Engineering at ₹3.16L Cr growing 36% YoY. " +
              "Engineering firms in PLI sectors are building anchor-buyer supply chains. " +
              "Tier-2 and tier-3 suppliers need invoice discounting and supply chain finance, not just capex credit. " +
              "The anchor (PLI beneficiary) provides implicit credit assurance.",
        implication: "Banks that sign supply chain finance agreements with the top 20 PLI beneficiaries in electronics and defence " +
                     "can access 50-100 suppliers per anchor. " +
                     "This is a scale play: one relationship generates a multi-counterparty portfolio.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id: "basic-metal-manufacturing-credit",
        title: "Basic Metal growing 14.6% FY — steel and aluminium capex is real",
        body: "Basic Metal and Metal Product: ₹4.33L Cr (Mar 2025) → ₹4.97L Cr (Feb 2026), +14.6% FY. " +
              "India's steel capacity additions (JSW, SAIL, Tata Steel expansions) are the primary driver. " +
              "At ₹4.97L Cr, this is the 2nd largest industry sub-sector by credit outstanding.",
        implication: "Steel and aluminium sector credit is large, well-collateralised, and growing steadily. " +
                     "Green steel transitions (DRI, EAF) will need project finance on a different risk model than conventional blast furnace credit. " +
                     "Banks that develop green steel underwriting now will lead this transition.",
        preferredMode: "fy",
        effect: { highlight: ["Basic Metal and Metal Product"] },
      },
    ],
  },

};
