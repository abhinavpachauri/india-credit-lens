// ── RBI SIBC Report — Data Layer ─────────────────────────────────────────────
// Loads and transforms RBI Sector/Industry-wise Bank Credit data.
// Produces the universal ReportSection[] + Report shape consumed by the UI.

import {
  loadData, buildSeries, buildGrowthSeries, childrenOf,
  uniqueDates, latestValue, formatDate,
  type CreditRow,
} from "@/lib/data";
import type { Report, ReportSection, ChartPoint, SectionAnnotations } from "@/lib/types";

// ── Annotation content ────────────────────────────────────────────────────────

export const ANNOTATIONS: Record<string, SectionAnnotations> = {

  // ── Section 1: Bank Credit ─────────────────────────────────────────────────
  bankCredit: {
    insights: [
      {
        id: "credit-growth-accelerating-fy26",
        title: "FY26 closed: +17.1% YoY — strongest growth rate in this dataset",
        body: "Bank Credit: ₹182.44L Cr (Mar 2025) → ₹213.61L Cr (Mar 2026), +17.1% YoY — strongest in this dataset. " +
              "Mar-to-Mar add: ₹31.17L Cr in FY26 vs ₹18.12L Cr in FY25 — 72% more year on year. " +
              "Within FY26: Jan 2026 FY-to-date +12.2%, Feb 2026 +13.8%, Mar 2026 +17.1% — acceleration was back-loaded to Q4.",
        implication: "Every main sector accelerated simultaneously — no laggard in the system. " +
                     "Portfolios growing below 17% in FY26 lost share in a system-wide tailwind. " +
                     "Capital and origination capacity, not end-user demand, was the binding constraint entering FY27.",
        preferredMode: "yoy",
        effect: { highlight: ["Non-food Credit"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Bank Credit Mar 2025: ₹182.44L Cr; Mar 2026: ₹213.61L Cr",
            "YoY growth rate Mar 2026: +17.1% (growthData)",
            "All four main sectors (Agriculture +15.7%, Industry +15.0%, Services +19.0%, Personal Loans +16.2%) accelerated in FY26"
          ],
          inferences: [
            "Simultaneous acceleration across all four main sectors eliminates demand-side sector-rotation as the explanation — the binding constraint was systemic supply-side capacity (capital adequacy, origination infrastructure, credit decisioning bandwidth)"
          ],
        },
      },
      {
        id: "three-year-credit-trajectory",
        title: "₹49.3L Cr added in 24 months — each year outpaces the last",
        body: "Bank Credit Mar-to-Mar: FY25 added ₹18.12L Cr (+11.0% YoY), FY26 added ₹31.17L Cr (+17.1% YoY) — FY26 added 72% more than FY25. " +
              "Total 24-month add (Mar 2024→Mar 2026): ₹49.29L Cr. " +
              "At +17.1%, maintaining the FY26 rate in FY27 requires originating ₹36.5L Cr in a single year.",
        implication: "Two consecutive years of acceleration may signal a structural phase shift in credit supply — " +
                     "but FY24 and FY25 both logged identical 11.0% growth before the FY26 jump. " +
                     "Whether this is a new structural cycle or a post-election fiscal impulse requires FY27 confirmation.",
        preferredMode: "absolute",
        effect: { highlight: ["Bank Credit", "Non-food Credit"], dim: ["Food Credit"] },
        claim_type: "hypothesis",
        basis: {
          facts: [
            "Bank Credit Mar 2024: ₹164.32L Cr; Mar 2025: ₹182.44L Cr; Mar 2026: ₹213.61L Cr",
            "FY25 annual add (Mar-to-Mar): ₹18.12L Cr; FY26 annual add: ₹31.17L Cr",
            "FY24 YoY at Mar 2025 and FY25 YoY at Mar 2025 both record +11.0%"
          ],
          inferences: [
            "Accelerating absolute additions with a rising YoY growth rate are consistent with compounding structural expansion"
          ],
          hypothesis: [
            "A multi-year credit supercycle requires FY27-28 confirmation — two identical 11.0% years (FY24, FY25) before one acceleration year (FY26) is insufficient to rule out a cyclical bounce or post-election fiscal impulse"
          ],
        },
      },
      {
        id: "nonfood-credit-all-the-signal",
        title: "Non-food credit is ₹212.91L Cr — 99.7% of the headline",
        body: "Non-food credit is ₹212.91L Cr of the ₹213.61L Cr total at Mar 2026 — 99.7% of bank credit. " +
              "Food credit at ₹0.70L Cr at Mar 2026 is minimal and seasonal. " +
              "The +17.1% YoY headline is entirely a non-food credit signal.",
        implication: "Always strip food credit from headline numbers before quoting them. " +
                     "Jan and Feb observations show elevated food credit due to kharif procurement cycles — " +
                     "always anchor growth comparisons to March-end figures.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
        claim_type: "data",
      },
    ],
    gaps: [
      {
        id: "food-credit-jan-artifact",
        title: "Food credit spikes every January — by design",
        body: "Food credit: ₹0.46L Cr (Jan 2024) → ₹0.89L Cr (Jan 2026) → ₹0.70L Cr (Mar 2026). " +
              "By March-end each year it compresses sharply — government kharif procurement agencies draw and repay seasonally. " +
              "The Jan 2026 FY-to-date figure of +144.4% for Food Credit is meaningless for trend analysis.",
        implication: "Never cite food credit FY or YoY growth from a January observation. " +
                     "March-end data is the only valid anchor for food credit comparisons.",
        preferredMode: "fy",
        effect: { highlight: ["Food Credit"], dash: ["Food Credit"] },
        claim_type: "data",
      },
      {
        id: "three-fy-end-snapshots-only",
        title: "Three March-end readings in this dataset — trend confirmed, cycle unconfirmed",
        body: "This merged dataset has March-end readings for Mar 2024, Mar 2025, and Mar 2026 only. " +
              "FY24 and FY25 both recorded +11.0% YoY growth — two flat years before the FY26 jump to +17.1%. " +
              "One year of acceleration following two years at the same level is insufficient to distinguish a structural phase shift from a one-year cyclical bounce.",
        implication: "Use 'acceleration' and 'fastest in this dataset' — not 'supercycle' or 'structural shift'. " +
                     "The FY27 March-end reading is the first data point that can confirm or refute the FY26 acceleration as durable.",
        preferredMode: "yoy",
        effect: { dash: ["Bank Credit"] },
        claim_type: "inference",
      },
    ],
    opportunities: [
      {
        id: "credit-cycle-expansion",
        title: "Annual origination target rises ₹5-7L Cr each year — build scale infrastructure now",
        body: "FY26 Mar-to-Mar add: ₹31.17L Cr. At +17.1%, FY27 requires adding ₹36.5L Cr to hold the growth rate. " +
              "Annual origination volume requirements are compounding — lenders operating on manual or semi-automated underwriting cannot scale at this pace. " +
              "The window to build infrastructure before peak FY27 volumes is the current 12-18 months.",
        implication: "NBFCs and fintechs should build co-origination infrastructure and automated credit decisioning now. " +
                     "Every quarter of delay raises the minimum origination volume required to hold market share. " +
                     "Banks with scalable origination infrastructure have a durable compounding advantage.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit", "Bank Credit"], dim: ["Food Credit"] },
        claim_type: "inference",
        basis: {
          facts: [
            "FY26 annual add: ₹31.17L Cr",
            "FY27 implied add at 17.1% growth: ₹36.5L Cr (17.1% × ₹213.61L Cr)"
          ],
          inferences: [
            "Each year of compounding growth raises the minimum origination volume required to hold market share; lenders without scalable infrastructure face a widening capacity gap"
          ],
        },
      },
    ],
  },

  // ── Section 2: Main Sectors ────────────────────────────────────────────────
  mainSectors: {
    insights: [
      {
        id: "fy26-all-sectors-synchronised",
        title: "All four main sectors accelerated in FY26 — no laggard in the system",
        body: "FY26 YoY at Mar 2026: Agriculture +15.7%, Industry +15.0%, Services +19.0%, Personal Loans +16.2%. " +
              "FY25 comparison at Mar 2025: Agriculture +10.4%, Industry +8.2%, Services +12.0%, Personal Loans +11.7%. " +
              "Every sector added 3.5–7.0pp to its growth rate — a synchronised broad-based expansion.",
        implication: "A synchronised multi-sector credit acceleration of this magnitude is unusual. " +
                     "Lenders with concentrated exposure in any single sector still captured the tailwind — " +
                     "but those with diversified origination across sectors held the strongest position.",
        preferredMode: "yoy",
        effect: { highlight: ["Industry", "Services", "Personal Loans", "Agriculture"] },
        claim_type: "data",
      },
      {
        id: "services-growth-acceleration",
        title: "Services hit +19.0% YoY in FY26 — fastest main sector, steepest acceleration",
        body: "Services YoY: +12.0% (Mar 2025) → +15.5% (Jan 2026) → +19.0% (Mar 2026) — fastest main sector in FY26. " +
              "The 7.0pp acceleration from FY25 to FY26 is the steepest single-sector move in this dataset. " +
              "Primary driver: bank credit to NBFCs went from +7.4% (FY25) to +26.3% (FY26), adding ₹4.31L Cr incremental.",
        implication: "Services credit growth is structural, driven by NBFC re-acceleration and financial sector deepening. " +
                     "Services has overtaken Personal Loans as the fastest-growing main category in FY26.",
        preferredMode: "yoy",
        effect: { highlight: ["Services"], dim: ["Agriculture"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Services YoY Mar 2025: +12.0%; Mar 2026: +19.0%",
            "NBFCs YoY Mar 2025: +7.4%; Mar 2026: +26.3%",
            "NBFC incremental FY26: ₹4.31L Cr (₹16.35L Cr → ₹20.66L Cr)"
          ],
          inferences: [
            "NBFCs are the largest sub-sector in Services; a 4× increase in their incremental flow accounts for the bulk of the 7.0pp Services sector acceleration"
          ],
        },
      },
      {
        id: "industry-reaccelerating",
        title: "Industry YoY: 8.2% → 15.0% — 6.8pp acceleration, SME-led recovery",
        body: "Industry YoY: +8.2% (FY25) → +15.0% (FY26), a 6.8pp step-up (Services accelerated 7.0pp — the steepest). " +
              "Within Industry: Micro and Small +33.1%, Medium +21.7%, Large +8.9% — growth concentrated in SMEs, not large corporates. " +
              "Sub-sector drivers: All Engineering +32.2%, Petroleum +32.5%, Basic Metal +19.4%.",
        implication: "The industrial credit re-acceleration is SME-led with a PLI capex overlay at the top. " +
                     "Banks organised around large corporate lending are missing the fastest-growing industrial segment.",
        preferredMode: "yoy",
        effect: { highlight: ["Industry"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Industry YoY Mar 2025: +8.2%; Mar 2026: +15.0%",
            "Micro and Small YoY Mar 2026: +33.1%; Large YoY Mar 2026: +8.9%",
            "All Engineering YoY Mar 2026: +32.2%; Petroleum: +32.5%; Basic Metal: +19.4%"
          ],
          inferences: [
            "Growth concentration in Micro & Small and PLI-aligned sub-sectors (Engineering, Petroleum, Metal) indicates the recovery is bottom-up and capex-driven, not broad-based large-corporate lending"
          ],
        },
      },
      {
        id: "personal-loans-largest-sector",
        title: "Personal Loans: ₹69.41L Cr — still the largest sector, growing +16.2% YoY",
        body: "Personal Loans: ₹59.73L Cr (Mar 2025, implied) → ₹69.41L Cr (Mar 2026), +16.2% YoY. " +
              "At ₹69.41L Cr, it is the single largest main sector — above Services (₹60.61L Cr), Industry (₹45.82L Cr), and Agriculture (₹26.46L Cr). " +
              "The aggregate masks extremes: Gold Loans +123.1%, Vehicle Loans +18.6%, Credit Cards +3.5%, Consumer Durables -5.3%.",
        implication: "Retail lending has decisively overtaken wholesale as the dominant credit category. " +
                     "But the aggregate is an average of opposite trends — always disaggregate into product type before drawing conclusions.",
        preferredMode: "absolute",
        effect: { highlight: ["Personal Loans"], dim: ["Agriculture"] },
        claim_type: "data",
      },
    ],
    gaps: [
      {
        id: "personal-loans-aggregate-hides-divergence",
        title: "The personal loans aggregate bundles opposite policy signals into one number",
        body: "Personal Loans at +16.2% YoY (FY26) is a weighted average of four opposite signals: " +
              "gold loans +123.1%, vehicle loans +18.6%, credit cards +3.5%, consumer durables -5.3%. " +
              "These are opposite policy and demand signals — the 2023 RBI risk-weight circular is contracting unsecured while gold prices and EV adoption are expanding secured.",
        implication: "Never use the Personal Loans aggregate to make a directional point. " +
                     "Disaggregate into secured vs unsecured, or by product type. " +
                     "The 2023 RBI risk-weight tightening on unsecured credit is still working through the book.",
        preferredMode: "yoy",
        effect: { dash: ["Personal Loans"] },
        claim_type: "data",
      },
      {
        id: "main-sectors-undercount",
        title: "Main sector totals undercount system credit by ₹10.6L Cr",
        body: "Agriculture + Industry + Services + Personal Loans at Mar 2026 sum to ₹202.30L Cr. " +
              "Total Bank Credit is ₹213.61L Cr. Adding Food Credit (₹0.70L Cr) reaches ₹203.00L Cr. " +
              "₹10.6L Cr — roughly 5% of bank credit — is unclassified: small business loans, public-sector advances, and other categories.",
        implication: "Treat the main-sector view as 'selected sectors' coverage. " +
                     "For full system accounting, anchor on the Bank Credit total. " +
                     "Any macro leverage ratio built from sector sums will understate total credit by ~5%.",
        preferredMode: "absolute",
        effect: { dash: ["Bank Credit"] },
        claim_type: "data",
      },
    ],
    opportunities: [
      {
        id: "services-credit-entry",
        title: "Services sector credit: fastest-growing main channel, ₹16.5L Cr added in 27 months",
        body: "Services grew from ₹44.1L Cr (Jan 2024) to ₹60.6L Cr (Mar 2026) — ₹16.5L Cr added in 27 months. " +
              "Within Services: NBFCs ₹20.66L Cr (+26.3%), Trade ₹13.76L Cr (+16.2%), CRE ₹6.27L Cr (+19.9%), Computer Software +39.0%. " +
              "Each sub-sector has distinct risk and opportunity profiles.",
        implication: "Lenders should build services-sector credit capabilities — IT working capital, supply chain finance, hospitality project finance, co-origination with NBFCs — to enter the fastest-growing formal credit channel. " +
                     "NBFCs in the co-lending space and fintechs with trade-finance products are best positioned to capture the current momentum.",
        preferredMode: "absolute",
        effect: { highlight: ["Services"] },
        claim_type: "inference",
      },
    ],
  },

  // ── Section 3: Industry by Size ────────────────────────────────────────────
  industryBySize: {
    insights: [
      {
        id: "micro-small-growth-tripled",
        title: "Micro & Small: +8.9% → +33.1% YoY in one year — inflection confirmed",
        body: "Micro and Small YoY: +8.9% (Mar 2025) → +33.1% (Mar 2026), adding ₹2.65L Cr in one year. " +
              "Absolute credit: ₹7.98L Cr (Mar 2025) → ₹10.63L Cr (Mar 2026). " +
              "FY26 incremental: ₹2.65L Cr — 4× the FY25 incremental of ₹0.65L Cr. " +
              "PSL Micro and Small Enterprises confirms independently: +13.4% (FY25) → +29.5% (FY26), ₹22.39L Cr → ₹29.01L Cr.",
        implication: "Jan, Feb, and Mar 2026 all show 29–33% growth — not a one-month spike. " +
                     "The MSME credit market has crossed an inflection driven by GST formalisation, UDYAM enrolment, and digital banking reaching millions of first-cycle borrowers.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"], dim: ["Large"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Micro and Small YoY Mar 2025: +8.9%; Mar 2026: +33.1%",
            "Micro and Small absolute: ₹7.98L Cr (Mar 2025) → ₹10.63L Cr (Mar 2026)",
            "PSL MSE YoY Mar 2026: +29.5% — independent series aligned"
          ],
          inferences: [
            "Two independent data series (industry-by-size and PSL MSME) showing consistent acceleration rules out a single-series data artefact; the acceleration is real",
            "GST formalisation (2017-19) and UDYAM registration wave created a large pool of newly formalised MSMEs with growing bureau histories — first-cycle credit expansion is the most consistent structural explanation"
          ],
        },
      },
      {
        id: "large-corporate-stagnant",
        title: "Large corporates: +8.9% YoY — the slowest industrial segment in FY26",
        body: "Large enterprise YoY: +6.9% (Mar 2025) → +8.9% (Mar 2026) — slowest industrial segment in FY26. " +
              "Absolute credit: ₹28.77L Cr (Mar 2025, implied) → ₹30.77L Cr (Mar 2026). " +
              "In FY26, Large added ₹2.00L Cr while Micro and Small added ₹2.65L Cr — SMEs added more absolute credit than Large for the first time in this dataset.",
        implication: "Large corporate banking is a relationship-maintenance business, not a growth one in FY26. " +
                     "Banks optimising for growth must re-allocate origination resources and underwriting bandwidth to the SME segment.",
        preferredMode: "yoy",
        effect: { highlight: ["Large"], dim: ["Micro and Small", "Medium"] },
        claim_type: "data",
      },
      {
        id: "medium-enterprise-sweet-spot",
        title: "Medium enterprises: +21.7% YoY — the structurally underserved middle tier",
        body: "Medium enterprise YoY: +18.5% (Mar 2025) → +21.7% (Mar 2026) — above system average in both years. " +
              "The Medium tier is growing faster than Large (+8.9%) and consistently above the system average (+17.1%). " +
              "Too large for standard MSME fintech products and too small for DCM access — the structural gap persists.",
        implication: "Medium enterprises (₹50–250 Cr revenue) are the most underserved segment in formal credit. " +
                     "Structured working capital and capex facilities for this tier represent a durable, undercrowded market. " +
                     "Both bank and NBFC coverage remains thin relative to the growth signal.",
        preferredMode: "yoy",
        effect: { highlight: ["Medium"] },
        claim_type: "data",
      },
    ],
    gaps: [
      {
        id: "size-definition-boundary-issue",
        title: "MSME size boundaries shift with regulatory revisions — growth is overstated",
        body: "The Micro, Small, and Medium categories follow MSMED Act definitions linked to turnover thresholds. " +
              "A Micro enterprise crossing the threshold migrates to Small, inflating the Small count without new credit disbursement. " +
              "Some portion of the 33.1% YoY in Micro and Small reflects definitional migration, not real new lending.",
        implication: "Treat 33.1% as an upper bound on real MSME credit growth. " +
                     "PSL MSE at +29.5% provides a partial cross-check — the true organic growth rate is likely 25–30%.",
        preferredMode: "yoy",
        effect: { dash: ["Micro and Small"] },
        claim_type: "inference",
      },
      {
        id: "large-enterprise-sector-mix-invisible",
        title: "Large corporates at ₹30.77L Cr — no sub-sector breakdown available here",
        body: "Large enterprise credit (₹30.77L Cr, +8.9% YoY) aggregates infrastructure, manufacturing, energy, and financial large caps. " +
              "The industry-by-size breakdown does not sub-classify by type. " +
              "The +8.9% average may mask contraction in some industries and strong growth in others.",
        implication: "Use industryByType section for the sub-sector story within Large enterprise credit. " +
                     "Infrastructure (+9.5%) and Engineering (+32.2%) in the type breakdown suggest significant divergence within the Large segment.",
        preferredMode: "yoy",
        effect: { dash: ["Large"] },
        claim_type: "inference",
      },
    ],
    opportunities: [
      {
        id: "msme-first-cycle-window",
        title: "Alt-data MSME underwriting: 2–3 year pricing advantage before bureau coverage fills in",
        body: "Micro and Small: ₹7.98L Cr (Mar 2025) → ₹10.63L Cr (Mar 2026), adding ₹2.65L Cr in one year. " +
              "A meaningful share are first-cycle formal borrowers post-GST and UDYAM with thin or blank bureau histories. " +
              "GST-registered MSMEs from 2019-22 now have 4–6 years of digital financial history (GST returns, UPI flows, e-way bills).",
        implication: "Lenders should build alternative underwriting using GST cashflow data before bureau coverage fills in — the pricing advantage window is FY27-29. " +
                     "FY27-28 will be the first stress test for alt-data models; first-cycle borrowers have no through-the-cycle performance history, so size exposures conservatively until loss curves establish.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small", "Medium"] },
        claim_type: "inference",
      },
    ],
  },

  // ── Section 4: Services ────────────────────────────────────────────────────
  services: {
    insights: [
      {
        id: "nbfc-risk-weight-cycle-complete",
        title: "NBFC credit +26.3% YoY — the 2023 risk-weight constraint fully absorbed",
        body: "Bank credit to NBFCs: ₹15.23L Cr (Mar 2024) → ₹16.35L Cr (Mar 2025, +7.4%) → ₹20.66L Cr (Mar 2026, +26.3%). " +
              "Incremental flow: FY25 ₹1.12L Cr, FY26 ₹4.31L Cr — nearly 4× the prior year. " +
              "The 2023 RBI risk-weight increase on consumer lending worked through NBFC balance sheets in FY24-25; banks re-built NBFC lending books aggressively in FY26.",
        implication: "Co-origination, warehouse financing, and loan-management infrastructure for bank-NBFC partnerships " +
                     "are the operative product wedges for FY27. " +
                     "Watch H1 FY27 RBI Financial Stability Reports — RBI could re-tighten if NBFC sector growth overheats again.",
        preferredMode: "yoy",
        effect: { highlight: ["NBFCs"] },
        claim_type: "inference",
        basis: {
          facts: [
            "NBFCs YoY Mar 2025: +7.4%; Mar 2026: +26.3%",
            "NBFC incremental FY25: ₹1.12L Cr; FY26: ₹4.31L Cr",
            "RBI November 2023 circular raised risk weights on consumer loans to NBFCs from 100% to 125%"
          ],
          inferences: [
            "The compression in FY25 (+7.4%) followed immediately by the reversal in FY26 (+26.3%) is temporally consistent with a 12-18 month balance sheet adjustment cycle after the risk-weight hike"
          ],
        },
      },
      {
        id: "computer-software-multi-year-surge",
        title: "Computer Software: +39.0% YoY in FY26 — three years of structural growth",
        body: "Computer Software: ₹0.26L Cr (Jan 2024) → ₹0.34L Cr (Jan 2025) → ₹0.41L Cr (Jan 2026) → ₹0.46L Cr (Mar 2026). " +
              "+28.2% YoY (Jan 2025), +20.7% YoY (Jan 2026), and +39.0% YoY (Mar 2026). " +
              "IT services working capital scales directly with headcount growth and project pipeline volume.",
        implication: "IT services working capital — project mobilisation, payroll bridging, USD receivables hedging — " +
                     "is a structurally growing credit category. Invoice discounting and supply chain finance " +
                     "products tailored for IT exporters are a durable, specific opportunity.",
        preferredMode: "yoy",
        effect: { highlight: ["Computer Software"] },
        claim_type: "data",
      },
      {
        id: "transport-operators-decelerating",
        title: "Transport Operators: +12.6% in FY25, +9.6% in FY26 — deceleration confirmed",
        body: "Transport Operators YoY: +12.6% (Mar 2025) → trough +4.3% (Jan 2026) → +9.6% (Mar 2026). " +
              "The sector recovered through H2 FY26 but closed the year well below FY25 levels. " +
              "Absolute credit: ₹2.54L Cr (Mar 2025) → ₹2.87L Cr (Mar 2026) — growth slowed materially.",
        implication: "Transport credit deceleration likely reflects fleet overcapacity in some segments following the post-COVID fleet normalisation cycle. " +
                     "Lenders with heavy transport exposure should track fleet utilisation rates as a leading indicator of repayment stress.",
        preferredMode: "yoy",
        effect: { highlight: ["Transport Operators"], dash: ["Transport Operators"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Transport Operators YoY Mar 2025: +12.6%; Jan 2026: +4.3%; Mar 2026: +9.6%"
          ],
          inferences: [
            "A trough at Jan 2026 with partial recovery to Mar 2026 suggests mid-year stress followed by stabilisation — fleet overcapacity is the most consistent explanation given the post-COVID fleet expansion cycle of FY22-24"
          ],
        },
      },
      {
        id: "cre-trade-consistent-growth",
        title: "CRE +19.9% and Trade +16.2% YoY in FY26 — both accelerating",
        body: "Commercial Real Estate YoY: +13.7% (Mar 2025) → +19.9% (Mar 2026), at ₹6.27L Cr. " +
              "Trade YoY: +15.6% (Mar 2025) → +16.2% (Mar 2026), at ₹13.76L Cr. " +
              "Trade is the second-largest services sub-sector by outstanding credit after NBFCs.",
        implication: "CRE growth reflects data center, logistics, and grade-A office demand — not residential developer exposure. " +
                     "Trade credit at ₹13.76L Cr growing 16% is the largest opportunity within services by absolute outstanding size.",
        preferredMode: "yoy",
        effect: { highlight: ["Commercial Real Estate", "Trade"] },
        claim_type: "data",
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
                     "Headline household-leverage numbers that sum bank credit and NBFC credit are systematically overstated.",
        preferredMode: "absolute",
        effect: { dash: ["NBFCs"] },
        claim_type: "inference",
      },
      {
        id: "other-services-opacity",
        title: "Other Services is ₹12.75L Cr with no breakdown — 21% of the sector is opaque",
        body: "'Other Services' at ₹12.75L Cr (Mar 2026) is ~21% of the entire Services sector. " +
              "It grew from ₹9.37L Cr (Jan 2024) to ₹12.75L Cr (Mar 2026) — +36% in 27 months. " +
              "Without sub-classification, this growth cannot be attributed or stress-tested.",
        implication: "Any services-sector analysis that treats 'Other Services' as a residual is ignoring 21% of the book. " +
                     "RBI's BSR-1 quarterly data provides granular sub-classification; SIBC does not.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Services"], dash: ["Other Services"] },
        claim_type: "data",
      },
    ],
    opportunities: [
      {
        id: "co-lending-infrastructure",
        title: "Build co-lending and warehouse-financing infrastructure for the bank-NBFC cycle",
        body: "Bank credit to NBFCs added ₹4.31L Cr in FY26 alone — nearly 4× the FY25 flow of ₹1.12L Cr. " +
              "NBFCs need bank balance sheet capacity; banks need NBFC origination reach. " +
              "The product wedges are co-origination agreements, warehouse lines, and LMS with co-lending partition logic.",
        implication: "Tech and product builders should enter the bank-NBFC infrastructure space in the next 12-18 months — before in-house tooling at large banks fills the gap. " +
                     "Loan-management systems with co-lending support, partition logic, and audit-trail rigour are the specific product need.",
        preferredMode: "absolute",
        effect: { highlight: ["NBFCs"] },
        claim_type: "inference",
      },
      {
        id: "trade-finance-compounder",
        title: "Trade credit at ₹13.76L Cr, +16.2% YoY — second-largest services sub-sector",
        body: "Trade credit: ₹9.85L Cr (Jan 2024) → ₹11.27L Cr (Jan 2025) → ₹13.09L Cr (Jan 2026) → ₹13.76L Cr (Mar 2026). " +
              "+40% in 27 months. The second-largest services sub-sector after NBFCs by outstanding balance. " +
              "Invoice discounting, buyer-financed supply chains, and distributor credit all fall here.",
        implication: "Fintechs building supply chain finance should target trade credit — large, recurring, and underserved by digital-first lenders. " +
                     "The sector compounds at 16%+ YoY and has direct access through GST e-way bill and invoice data already available digitally.",
        preferredMode: "absolute",
        effect: { highlight: ["Trade"] },
        claim_type: "data",
      },
    ],
  },

  // ── Section 5: Personal Loans ──────────────────────────────────────────────
  personalLoans: {
    insights: [
      {
        id: "gold-loans-structural-surge",
        title: "Gold loans 5× in 24 months — ₹0.93L Cr (Mar 2024) to ₹4.60L Cr (Mar 2026)",
        body: "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹2.06L Cr (Mar 2025, +121.1% YoY) → ₹4.60L Cr (Mar 2026, +123.1% YoY). " +
              "Share of personal credit: 1.6% (Mar 2024) → 3.5% (Mar 2025) → 6.6% (Mar 2026). " +
              "Two compounding effects: RBI Sep 2024 circular reclassified bullet-repayment gold loans from 'agri'/'business' buckets; " +
              "gold prices rose ~30% in FY26, expanding collateral value on existing books.",
        implication: "Most of the 5× growth is reclassification plus collateral price effect — not net new disbursement demand. " +
                     "Specialised gold NBFCs (Manappuram, Muthoot) and southern banks hold the operational capability. " +
                     "Banks without physical-collateral handling should build product partnerships, not direct origination.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Gold Loans Mar 2024: ₹0.93L Cr; Mar 2025: ₹2.06L Cr (+121.1%); Mar 2026: ₹4.60L Cr (+123.1%)",
            "RBI circular Sep 2024 required bullet-repayment gold loans to move from agriculture/business classification to 'loans against gold jewellery'",
            "Gold prices (MCX) rose approximately 28-32% in FY26"
          ],
          inferences: [
            "The reclassification moved a stock of existing loans; the gold price rise expanded LTV-based credit limits — both are one-time effects. Organic new disbursement demand explains a smaller fraction of the 5× increase."
          ],
        },
      },
      {
        id: "credit-card-collapse",
        title: "Credit cards: +3.5% YoY in FY26 — policy-constrained, not demand-constrained",
        body: "Credit Card Outstanding YoY: +10.6% (Mar 2025) → +1.5% (Jan 2026) → +3.5% (Mar 2026). " +
              "FY26 incremental: ₹10,094 Cr vs ₹27,350 Cr in FY25 — under one-third the prior-year pace. " +
              "Consumer Durables in outright contraction: -1.0% (FY25) → -5.3% (FY26). " +
              "The RBI 2023 risk-weight increases on unsecured retail are confirmed as structurally binding.",
        implication: "Credit card growth is policy-constrained. " +
                     "Revenue mix must pivot to fee income, interchange, and float — not revolving NII. " +
                     "UPI credit lines and BNPL are absorbing displaced demand through channels not visible in SIBC data.",
        preferredMode: "yoy",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
        claim_type: "data",
      },
      {
        id: "vehicle-loans-accelerating",
        title: "Vehicle loans: +8.6% → +18.6% YoY — growth doubled in FY26",
        body: "Vehicle Loans YoY: +8.6% (Mar 2025) → +18.6% (Mar 2026) — growth doubled year on year. " +
              "Absolute: ₹6.23L Cr (Mar 2025) → ₹7.39L Cr (Mar 2026), incremental FY26: ₹1.16L Cr. " +
              "EV adoption, commercial fleet renewal, and two-wheeler financing are all contributing.",
        implication: "Auto sector credit is in a strong expansion cycle. " +
                     "OEM captive NBFCs (Bajaj Finance, M&M Finance) hold the largest share on the personal side; " +
                     "fleet EV financing is the highest-volume next layer.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicle Loans"] },
        claim_type: "data",
      },
      {
        id: "consumer-durables-accelerating-decline",
        title: "Consumer durables: -5.3% YoY in FY26 — three consecutive periods of contraction",
        body: "Consumer Durables YoY: -2.4% (Jan 2025), -1.0% (Mar 2025), -5.3% (Mar 2026) — three consecutive periods of contraction. " +
              "Book declined from ₹23,445 Cr (Mar 2025) to ₹21,962 Cr (Mar 2026). " +
              "The contraction is accelerating, not stabilising.",
        implication: "Point-of-sale consumer durable finance is being displaced by BNPL and embedded credit. " +
                     "The credit doesn't disappear — it migrates off-SIBC reporting. Traditional POS financing is in structural decline.",
        preferredMode: "yoy",
        effect: { highlight: ["Consumer Durables"], dash: ["Consumer Durables"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Consumer Durables YoY: -2.4% (Jan 2025), -1.0% (Mar 2025), -5.3% (Mar 2026)",
            "Book: ₹23,445 Cr (Mar 2025) → ₹21,962 Cr (Mar 2026) — absolute decline"
          ],
          inferences: [
            "Accelerating contraction in a period of broader credit expansion rules out a macro demand explanation; displacement by BNPL/embedded credit is the most consistent explanation"
          ],
        },
      },
    ],
    gaps: [
      {
        id: "gold-loans-reclassification-overstates-demand",
        title: "Gold loans +123% overstates real disbursement demand — stock vs flow",
        body: "Two one-time effects compound: the RBI Sep 2024 circular moved existing bullet-repayment gold loans from " +
              "agri/business categories into 'loans against gold jewellery'; gold prices also rose ~30%, expanding collateral value. " +
              "Both effects are stock adjustments — recognised by Mar 2026 and unlikely to repeat at this magnitude.",
        implication: "When forecasting gold-loan trajectory into FY27, separate stock effect (reclassification, done) " +
                     "from flow effect (real new disbursements). " +
                     "Stress-test for a gold-price reversal >20% — LTV ratios on marginal loans are already elevated.",
        preferredMode: "yoy",
        effect: { dash: ["Gold Loans"] },
        claim_type: "inference",
      },
      {
        id: "other-personal-loans-opacity",
        title: "Other Personal Loans is ₹17.34L Cr — 25% of the portfolio with no breakdown",
        body: "'Other Personal Loans': ₹13.96L Cr (Jan 2024) → ₹15.11L Cr (Jan 2025) → ₹16.85L Cr (Jan 2026) → ₹17.34L Cr (Mar 2026). " +
              "+24.2% in 27 months. Larger than Vehicle Loans and Education combined. " +
              "Likely includes salary advances, top-up home loans, personal overdrafts — exact sub-classification is opaque.",
        implication: "Any personal loans analysis that treats 'Other Personal Loans' as a residual is ignoring 25% of the book. " +
                     "Use BSR-1 quarterly for sub-classification when product-level analysis is required.",
        preferredMode: "absolute",
        effect: { highlight: ["Other Personal Loans"], dash: ["Other Personal Loans"] },
        claim_type: "data",
      },
    ],
    opportunities: [
      {
        id: "gold-loan-market-entry",
        title: "Gold lending is being re-segmented — banks vs NBFCs on rate vs speed",
        body: "Gold Loans: ₹0.93L Cr (Mar 2024) → ₹4.60L Cr (Mar 2026) — a 5× increase that is attracting new bank entrants. " +
              "Gold NBFCs (Muthoot, Manappuram) have had market exclusivity for decades. " +
              "Banks are structurally cheaper (lower cost of funds) but lag on speed, branch density, and physical assay operations.",
        implication: "Banks entering gold lending should build product partnerships with gold NBFCs rather than competing on origination infrastructure from scratch — the operational moat (assay capability, cash management, doorstep service) takes 3-5 years to replicate. " +
                     "New entrants should target the urban, app-enabled gold loan segment where speed is less critical than rate.",
        preferredMode: "absolute",
        effect: { highlight: ["Gold Loans"] },
        claim_type: "inference",
      },
      {
        id: "vehicle-ev-credit",
        title: "Vehicle loans +18.6% — develop EV-specific credit as the next product layer",
        body: "Vehicle loans: ₹6.23L Cr (Mar 2025) → ₹7.39L Cr (Mar 2026), +18.6% YoY — fastest vehicle credit growth in this dataset. " +
              "EV sales crossed 20L units in FY25. Standard vehicle finance doesn't address battery degradation risk, " +
              "EV residual values, or subsidy-linked EMI structures.",
        implication: "Lenders should develop EV-specific credit products — the first-mover advantage window is 2-3 years wide. " +
                     "Fleet EV lending (e-commerce, last-mile logistics) is the highest-volume entry point; Q2 FY27 PV and 2W EV penetration data will confirm trajectory.",
        preferredMode: "absolute",
        effect: { highlight: ["Vehicle Loans"] },
        claim_type: "inference",
      },
    ],
  },

  // ── Section 6: Priority Sector ─────────────────────────────────────────────
  prioritySector: {
    insights: [
      {
        id: "psl-msme-structural-acceleration",
        title: "PSL MSME: +13.4% (FY25) → +29.5% (FY26) — two independent series aligned",
        body: "PSL Micro and Small Enterprises: ₹22.39L Cr (Mar 2025, +13.4% YoY) → ₹29.01L Cr (Mar 2026, +29.5% YoY). " +
              "The industry-by-size breakdown confirms independently: Micro & Small grew +8.9% (FY25) → +33.1% (FY26), ₹7.98L Cr → ₹10.63L Cr. " +
              "Both series point in the same direction — this acceleration is credible.",
        implication: "PSL incentives are compounding alongside the formalisation wave. " +
                     "Banks that built MSME origination infrastructure in FY24-25 are now harvesting PSL credit at scale.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small Enterprises"] },
        claim_type: "data",
      },
      {
        id: "psl-housing-anomalous-surge",
        title: "PSL Housing +39.8% YoY — a definition change, not new housing demand",
        body: "PSL Housing: ₹7.55L Cr (Mar 2024) → ₹7.47L Cr (Mar 2025, -1.1% YoY) → ₹10.44L Cr (Mar 2026, +39.8% YoY). " +
              "The reversal follows RBI's October 2024 PSL housing loan limit revision (metro: ₹35L → ₹45L; non-metro: ₹25L → ₹35L). " +
              "Existing loans were reclassified INTO the PSL bucket — they are not new originations.",
        implication: "Never cite PSL Housing growth as a demand signal. " +
                     "The genuine new lending proxy is personalLoans Housing at +11.5% YoY — that is the correct benchmark for affordable housing origination.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"], dash: ["Housing"] },
        claim_type: "inference",
        basis: {
          facts: [
            "PSL Housing YoY Mar 2025: -1.1%; Mar 2026: +39.8%",
            "RBI circular Oct 2024 revised PSL housing loan limits: metro ₹35L → ₹45L; non-metro ₹25L → ₹35L",
            "personalLoans Housing YoY Mar 2026: +11.5% (no regulatory revision)"
          ],
          inferences: [
            "A sudden reversal from -1.1% to +39.8% in a single year, coinciding precisely with a loan-limit revision, is near-certain evidence of reclassification of existing stock — not new disbursement"
          ],
        },
      },
      {
        id: "export-credit-declining",
        title: "Export credit: turned negative — -8.4% YoY at Mar 2026",
        body: "Export Credit PSL: ₹11,805 Cr (Mar 2025, +5.3% YoY) → ₹11,436 Cr (Mar 2026, -8.4% YoY). " +
              "After modest FY25 growth, it contracted in FY26. " +
              "Global trade uncertainty, rupee volatility, and tighter underwriting are the contributing factors.",
        implication: "Export finance desks are contracting in the formal banking system. " +
                     "India's merchandise exports held up in FY26 — the pullback reflects risk appetite, not demand. " +
                     "Fintech invoice discounting and ECGC-backed facilities have a window while banks pull back.",
        preferredMode: "yoy",
        effect: { highlight: ["Export Credit"], dash: ["Export Credit"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Export Credit YoY Mar 2025: +5.3%; Mar 2026: -8.4%",
            "India's merchandise export value in FY26 was broadly stable YoY"
          ],
          inferences: [
            "Credit contraction in a period of stable export volumes indicates lender risk-appetite pullback, not demand destruction — creating a gap that non-bank trade finance can fill"
          ],
        },
      },
    ],
    gaps: [
      {
        id: "psl-housing-reclassification",
        title: "PSL housing data contaminated by a regulatory revision — not flagged in the report",
        body: "The RBI Oct 2024 PSL housing loan limit revision reclassified existing mortgages into the PSL bucket. " +
              "The ₹2.97L Cr apparent addition in FY26 represents existing loans now visible in a different column — not new disbursements. " +
              "The SIBC report presents this as +39.8% growth with no footnote or qualification.",
        implication: "Before citing PSL housing growth in any period that follows a limit revision, verify whether a definitional change falls within the window. " +
                     "Non-PSL Housing (+11.5% YoY) is the correct proxy for genuine new affordable housing origination.",
        preferredMode: "yoy",
        effect: { dash: ["Housing"] },
        claim_type: "inference",
      },
      {
        id: "psl-totals-not-additive",
        title: "PSL category totals cannot be summed — Weaker Sections overlaps everything",
        body: "Weaker Sections at ₹20.71L Cr (Mar 2026) is a cross-cutting subset of the PSL total. " +
              "SC/ST borrowers, small farmers, and SHG members appear simultaneously in Agriculture, MSME, and Housing rows. " +
              "Summing all PSL rows overstates the total PSL book by a significant margin.",
        implication: "Use the official PSL achievement ratios from RBI Annual Reports — not this table's arithmetic sum. " +
                     "The correct PSL total denominator is 40% of ANBC (Adjusted Net Bank Credit).",
        preferredMode: "absolute",
        effect: { dash: ["Weaker Sections"] },
        claim_type: "data",
      },
    ],
    opportunities: [
      {
        id: "renewable-energy-project-finance",
        title: "Renewable energy PSL: ₹0.14L Cr against a ₹20L Cr+ national investment need",
        body: "Renewable Energy PSL: ₹0.06L Cr (Mar 2024) → ₹0.10L Cr (Mar 2025, +78.3% YoY) → ₹0.14L Cr (Mar 2026, +34.1% YoY). " +
              "India needs ₹20–25L Cr of renewable energy investment by 2030 per MNRE targets. " +
              "Bank credit stands at 0.07% of total bank credit — the gap between capital need and supply is structural.",
        implication: "No incumbent lender has built renewable energy project finance capabilities at scale. " +
                     "Lenders that develop DISCOM offtake risk underwriting, distributed solar credit, and battery storage finance in the next 2-3 years will own this market for a decade. " +
                     "PSL classification makes renewable energy lending doubly attractive — it counts toward mandatory targets.",
        preferredMode: "fy",
        effect: { highlight: ["Renewable Energy"] },
        claim_type: "inference",
      },
      {
        id: "pslc-trading-tooling",
        title: "Develop PSL compliance analytics — PSLC trading volume rising with MSME growth",
        body: "As MSME PSL books grow at 29.5% YoY, the PSL certificate (PSLC) trading market on RBI's e-Kuber platform " +
              "becomes more active. Banks with excess PSL achievement sell to those with deficits. " +
              "Tracking real-time PSL achievement ratios against ANBC requires live data integration across the book.",
        implication: "Mid-size banks should build or procure PSLC compliance analytics — ANBC calculation, PSL gap forecasting, and PSLC trade timing — before regulatory pressure on PSL shortfalls intensifies in FY27. " +
                     "Compliance tech vendors should target treasury and regulatory teams at banks with ₹50,000–500,000 Cr balance sheets where manual tracking creates the most risk.",
        preferredMode: "absolute",
        effect: { highlight: ["Micro and Small Enterprises"] },
        claim_type: "inference",
      },
    ],
  },

  // ── Section 7: Industry by Type ────────────────────────────────────────────
  industryByType: {
    insights: [
      {
        id: "pli-capex-broadening-confirmed",
        title: "PLI capex broadened in FY26: Engineering +32.2%, Petroleum +32.5%, Metal +19.4%",
        body: "FY26 YoY: All Engineering +32.2% (₹3.17L Cr), Petroleum +32.5% (₹2.04L Cr), Basic Metal +19.4% (₹5.18L Cr). " +
              "Also accelerating: Vehicles & Parts +18.1% (₹1.41L Cr), Chemicals +14.9% (₹3.08L Cr), Food Processing +14.0% (₹2.50L Cr). " +
              "FY25 comparison: Engineering +22.0%, Petroleum +16.5%, Basic Metal +12.8% — every sector accelerated.",
        implication: "The PLI capex story has spread beyond electronics into Petroleum, Basic Metal, and Chemicals — a broad-based industrial capex revival. " +
                     "Banks underweight in industrial term loans have under-priced upside heading into FY27.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering", "Petroleum, Coal Products and Nuclear Fuels", "Basic Metal and Metal Product"] },
        claim_type: "inference",
        basis: {
          facts: [
            "All Engineering YoY FY25: +22.0%; FY26: +32.2%",
            "Petroleum YoY FY25: +16.5%; FY26: +32.5%",
            "Basic Metal YoY FY25: +12.8%; FY26: +19.4%",
            "Vehicles & Parts, Chemicals, Food Processing all accelerated in FY26"
          ],
          inferences: [
            "Simultaneous acceleration across multiple capital-intensive sub-sectors in one year is consistent with government capex stimulus (PLI, infrastructure push) translating into credit drawdown"
          ],
        },
      },
      {
        id: "gems-jewellery-gold-price-proxy",
        title: "Gems & Jewellery +41.4% YoY — mostly a gold price proxy, not volume",
        body: "Gems and Jewellery: ₹0.83L Cr (Feb 2025) → ₹1.21L Cr (Mar 2026), +41.4% YoY — mostly a gold price proxy. " +
              "Gold prices rose approximately 28–32% in FY26. " +
              "Working capital for jewellers scales directly with gold prices — at least 25pp of this growth is a price effect, not volume.",
        implication: "Real volume growth is 10–15%. A 15–20% gold price correction would compress working capital requirements and may trigger LTV covenant breaches. " +
                     "Stress-test gems & jewellery portfolios against gold price decline scenarios before extending new facilities.",
        preferredMode: "yoy",
        effect: { highlight: ["Gems and Jewellery"], dash: ["Gems and Jewellery"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Gems and Jewellery YoY Mar 2026: +41.4%",
            "Gold MCX prices rose approximately 28-32% in FY26"
          ],
          inferences: [
            "Jeweller working capital is directly indexed to gold inventory value; a 30% price rise implies 30pp of the 41.4% growth is mechanical collateral inflation — not new disbursement demand"
          ],
        },
      },
      {
        id: "infrastructure-decelerating",
        title: "Infrastructure at +9.5% YoY in FY26 — half the system rate, early repayment cycle",
        body: "Infrastructure: ₹13.37L Cr (Mar 2025) → ₹14.94L Cr (Mar 2026), +9.5% YoY — half the system rate of +17.1%. " +
              "Still the largest industrial sub-sector by outstanding but barely expanding relative to its size. " +
              "Projects from the 2019–24 highway and metro construction wave are now in operations, repaying loans rather than drawing.",
        implication: "Infrastructure credit books built on the last construction cycle face high repayments and declining new origination. " +
                     "The next capex wave (data centers, green hydrogen, semiconductor fabs) is 2–4 years from scale. " +
                     "Banks should identify anchor relationships in next-generation infrastructure early — before it becomes consensus.",
        preferredMode: "yoy",
        effect: { highlight: ["Infrastructure"], dim: ["All Engineering"] },
        claim_type: "inference",
        basis: {
          facts: [
            "Infrastructure YoY Mar 2025: +2.8%; Mar 2026: +9.5% — growing but well below system average of +17.1%",
            "Infrastructure is the largest industry sub-sector at ₹14.94L Cr"
          ],
          inferences: [
            "Highway, metro, and port projects awarded in 2019-24 typically reach peak drawdown in years 2-4 and enter repayment in years 5-7; the current book is consistent with projects transitioning from construction to operations"
          ],
          hypothesis: [
            "Data centers, green hydrogen, and semiconductor fabs as the next capex wave is directionally supported by policy announcements but none has yet reached scale credit drawdown — requires confirmation over FY27-29"
          ],
        },
      },
      {
        id: "chemicals-petroleum-capex",
        title: "Chemicals +14.9% YoY, Petroleum +32.5% YoY — specialty and energy capex real",
        body: "Chemicals and Chemical Products: +14.9% YoY at ₹3.08L Cr (Mar 2026), above system average. " +
              "Petroleum, Coal Products: +32.5% YoY at ₹2.04L Cr (Mar 2026) — matching All Engineering as the top accelerators. " +
              "Both growing faster than the industry average in FY26. India's specialty chemicals export drive and refinery upgrade cycle are the primary drivers.",
        implication: "Chemical and petroleum credit carries longer tenure and larger ticket sizes than most industry sub-sectors. " +
                     "Structured term lending for refinery expansions and specialty chemical plants is a durable corporate banking pipeline for FY27-28.",
        preferredMode: "yoy",
        effect: { highlight: ["Chemicals and Chemical Products", "Petroleum, Coal Products and Nuclear Fuels"] },
        claim_type: "data",
      },
    ],
    gaps: [
      {
        id: "infrastructure-sub-classification-absent",
        title: "Infrastructure is ₹14.94L Cr with zero sub-sector visibility",
        body: "'Infrastructure' at ₹14.94L Cr (Mar 2026) aggregates roads, power, telecom, railways, ports, and urban infrastructure. " +
              "Each sub-type has different growth drivers, tenor, and credit quality. " +
              "The +9.5% aggregate may mask contraction in some sub-types and strong growth in others — power and data center credit likely diverge from road/port.",
        implication: "Never cite infrastructure credit growth without specifying which sub-type. " +
                     "MCA filings, NITI Aayog project monitoring, or RBI BSR-1 are the sources for sub-sector breakdown.",
        preferredMode: "absolute",
        effect: { highlight: ["Infrastructure"], dash: ["Infrastructure"] },
        claim_type: "inference",
      },
      {
        id: "industry-type-partition-not-exact",
        title: "Industry sub-types don't reconcile to the Industry total in Main Sectors",
        body: "The industry-by-type breakdown in this section does not reconcile to the Industry Total shown in Main Sectors. " +
              "Sub-sectors use different classification vintages, and an 'Other Industries' residual absorbs unclassified credit. " +
              "The gap is small but real — do not treat this section as an arithmetic decomposition of the headline.",
        implication: "Use this section for within-series trend analysis only — e.g. tracking Infrastructure or Engineering individually. " +
                     "Do not sum sub-types to cross-check or reconstruct the Industry Total.",
        preferredMode: "absolute",
        effect: { dash: ["Infrastructure"] },
        claim_type: "data",
      },
    ],
    opportunities: [
      {
        id: "pli-supply-chain-finance",
        title: "One PLI anchor yields 50–100 supplier credit relationships — build the chain",
        body: "All Engineering credit: ₹2.59L Cr (Mar 2025, implied) → ₹3.17L Cr (Mar 2026), adding ₹1.21L Cr in FY26. " +
              "PLI-approved anchor companies (electronics, defence, EV components) have 50–100 tier-2 and tier-3 suppliers. " +
              "Supply chain finance against anchor-validated invoices removes the need for individual MSME underwriting.",
        implication: "Banks and fintechs should target PLI anchor companies for supply chain finance agreements — " +
                     "one anchor relationship generates a multi-counterparty MSME portfolio. " +
                     "Banks that signed PLI anchors as current-account clients in 2022-24 are best positioned to offer this now.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
        claim_type: "inference",
      },
      {
        id: "basic-metal-capex-lending",
        title: "Basic Metal +19.4% YoY — develop green steel project finance before the transition",
        body: "Basic Metal and Metal Product: +19.4% YoY in FY26, reaching ₹5.18L Cr at Mar 2026. " +
              "India's steel capacity additions (JSW, SAIL, Tata Steel expansions) are driving the current cycle. " +
              "The 2nd-largest industrial sub-sector by credit outstanding, now growing close to system average.",
        implication: "Lenders should develop green steel project finance capability now — DRI and EAF-based capacity requires a different risk model than conventional BF-BOF. " +
                     "Banks that build green steel underwriting in FY27-28 will lead the transition; FY30-32 is when the largest investments will need project finance.",
        preferredMode: "yoy",
        effect: { highlight: ["Basic Metal and Metal Product"] },
        claim_type: "inference",
      },
    ],
  },

};

// ── Internal helper ───────────────────────────────────────────────────────────

function makeSection(
  rows:        CreditRow[],
  id:          string,
  title:       string,
  icon:        string,
  accentIndex: number,
  codes:       string[],
  labels:      Record<string, string>,
  pctLabel:    string,
  opts:        { psl?: boolean; stmt?: string } = {},
  filterable = false
): ReportSection | null {
  if (codes.length === 0) return null;

  const absoluteData: ChartPoint[] = buildSeries(rows, codes, labels, opts);
  const growthData:   ChartPoint[] = buildGrowthSeries(rows, codes, labels, "yoy", opts);
  const fyData:       ChartPoint[] = buildGrowthSeries(rows, codes, labels, "fy",  opts);
  const seriesNames:  string[]     = codes.map((c) => labels[c] ?? c);

  return {
    id,
    title,
    icon,
    accentIndex,
    absoluteData,
    growthData,
    fyData,
    seriesNames,
    pctLabel,
    filterable,
    annotations: ANNOTATIONS[id] ?? { insights: [], gaps: [], opportunities: [] },
  };
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Build all sections from pre-loaded rows. */
export function buildSections(rows: CreditRow[]): ReportSection[] {
  const sections: (ReportSection | null)[] = [];

  // 1 — Bank Credit (top-level: total, food, non-food)
  sections.push(makeSection(
    rows,
    "bankCredit", "Bank Credit", "🏦", 0,
    ["I", "II", "III"],
    { I: "Bank Credit", II: "Food Credit", III: "Non-food Credit" },
    "% of Bank Credit"
  ));

  // 2 — Main Sectors
  sections.push(makeSection(
    rows,
    "mainSectors", "Main Sectors", "📊", 1,
    ["1", "2", "3", "4"],
    { "1": "Agriculture", "2": "Industry", "3": "Services", "4": "Personal Loans" },
    "% Share"
  ));

  // 3 — Industry by Size (children of code "2", Statement 1 only)
  const sec3 = childrenOf(rows, "2", { stmt: "Statement 1" });
  sections.push(makeSection(
    rows,
    "industryBySize", "Industry by Size", "🏭", 2,
    sec3.codes, sec3.labels, "% of Industry",
    { stmt: "Statement 1" }
  ));

  // 4 — Services sub-sectors (children of code "3")
  const sec4 = childrenOf(rows, "3");
  sections.push(makeSection(
    rows,
    "services", "Services", "🛎️", 3,
    sec4.codes, sec4.labels, "% of Services"
  ));

  // 5 — Personal Loans sub-categories (children of code "4")
  const sec5 = childrenOf(rows, "4");
  sections.push(makeSection(
    rows,
    "personalLoans", "Personal Loans", "💳", 4,
    sec5.codes, sec5.labels, "% of Personal Loans"
  ));

  // 6 — Priority Sector Lending (PSL memo rows)
  const pslRows   = rows.filter((r) => r.is_priority_sector_memo);
  const pslCodes  = [...new Set(pslRows.map((r) => r.code))].sort();
  const pslLabels: Record<string, string> = {};
  pslRows.forEach((r) => { pslLabels[r.code] = r.sector; });
  sections.push(makeSection(
    rows,
    "prioritySector", "Priority Sector", "⭐", 5,
    pslCodes, pslLabels, "% of Priority Sector",
    { psl: true }
  ));

  // 7 — Industry by Type (Statement 2, filterable — many sub-sectors)
  const sec7 = childrenOf(rows, "2", { stmt: "Statement 2" });
  sections.push(makeSection(
    rows,
    "industryByType", "Industry by Type", "🔩", 6,
    sec7.codes, sec7.labels, "% of Industry",
    { stmt: "Statement 2" },
    true  // filterable
  ));

  return sections.filter((s): s is ReportSection => s !== null);
}

/** Load the full report (fetches CSV internally). */
export async function loadReport(): Promise<Report> {
  const rows     = await loadData();
  const dates    = uniqueDates(rows);
  const dataDate = dates[dates.length - 1] ?? "";

  return {
    id:              "rbi_sibc",
    title:           "RBI Sector/Industry-wise Bank Credit",
    source:          "Reserve Bank of India — SIBC Return",
    dataDate,
    latestDate:      formatDate(dataDate),
    totalBankCredit: latestValue(rows, "I"),
    sections:        buildSections(rows),
  };
}
