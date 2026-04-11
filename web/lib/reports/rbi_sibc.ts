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

  bankCredit: {
    insights: [
      {
        id: "credit-growth-reaccelerated",
        title: "Credit growth is genuinely speeding up",
        body: "Non-food credit grew +11.3% YoY in Jan 2025 and +14.4% in Jan 2026. " +
              "In absolute terms, ₹25.7L Cr was added between Jan 2025 and Jan 2026 — " +
              "vs ₹18.1L Cr added in the prior year. This is not base effect; FY growth " +
              "confirms it at +12.0% (Jan 2026 vs Mar 2025).",
        implication: "For lenders: the credit cycle is expanding. If your portfolio grew " +
                     "less than 14% in FY25-26 (to Jan), you lost market share.",
        preferredMode: "yoy",
        effect: { highlight: ["Non-food Credit"] },
      },
      {
        id: "food-credit-irrelevant-to-headline",
        title: "Food credit is 0.4% of total — ignore it for the headline",
        body: "Food credit at ₹0.89L Cr is 0.44% of total bank credit (₹204.8L Cr). " +
              "Even with its +58.9% YoY growth, its contribution to the headline growth " +
              "rate is less than 0.1 percentage point. The 14.6% headline is essentially " +
              "the non-food number.",
        implication: "When reading system-level credit direction, strip food credit from the " +
                     "headline entirely. The 14.6% YoY is a non-food signal. Food credit " +
                     "volatility in January reflects government procurement timing — it has " +
                     "no bearing on the credit cycle or lender strategy.",
        preferredMode: "absolute",
        effect: { dim: ["Food Credit"], highlight: ["Bank Credit", "Non-food Credit"] },
      },
    ],
    gaps: [
      {
        id: "food-credit-jan-artifact",
        title: "Food credit spikes every January — by design",
        body: "Food credit in Jan 2024 was ₹0.456L Cr; by Mar 2024 it dropped 49% to ₹0.231L Cr. " +
              "Same pattern: Jan 2025 ₹0.562L Cr → Mar 2025 ₹0.365L Cr (−35%). " +
              "Jan 2026 shows ₹0.893L Cr — expect this to drop to ~₹0.55L Cr by Mar 2026. " +
              "This is government kharif crop procurement timing, not structural credit growth.",
        implication: "The FY growth figure for Food Credit in Jan 2026 is +144.4% vs Mar 2025. " +
                     "That number is meaningless for trend analysis. Never quote food credit " +
                     "growth from a January data point without this caveat.",
        preferredMode: "fy",
        effect: { highlight: ["Food Credit"], dash: ["Food Credit"] },
      },
    ],
    opportunities: [
      {
        id: "non-food-credit-structural-expansion",
        title: "₹25L Cr added in 12 months — system is in growth mode",
        body: "Non-food credit went from ₹178.1L Cr (Jan 2025) to ₹203.9L Cr (Jan 2026) — " +
              "₹25.8L Cr in absolute addition. The prior year added ₹18.1L Cr. " +
              "At this trajectory, the system crosses ₹230L Cr by Jan 2027.",
        implication: "Lenders with scalable origination and low cost of credit assessment " +
                     "have a large tailwind. This is a market-level opportunity, not sector-specific.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
      },
    ],
  },

  mainSectors: {
    insights: [
      {
        id: "personal-loans-largest-sector",
        title: "Retail lending is now the biggest sector",
        body: "Personal loans at ₹67.2L Cr (Jan 2026) exceeds Services (₹57.2L Cr), " +
              "Industry (₹43.9L Cr), and Agriculture (₹25.1L Cr). This was true in Jan 2024 " +
              "too (₹52.3L Cr), but the gap has grown: personal loans now exceed industry " +
              "by ₹23.3L Cr, up from ₹16.2L Cr two years ago.",
        implication: "The centre of gravity in Indian banking has moved to retail. " +
                     "A bank or NBFC that isn't competitive in retail lending is competing " +
                     "in a shrinking share of the market.",
        preferredMode: "absolute",
        effect: { highlight: ["Personal Loans"] },
      },
      {
        id: "industry-reacceleration-msme-driven",
        title: "Industry growth tripled — but it's all MSME",
        body: "Industry YoY growth went from +8.3% (Jan 2025) to +12.1% (Jan 2026). " +
              "That reacceleration is entirely driven by Micro & Small (+31.2% YoY) and " +
              "Medium (+22.3% YoY). Large corporate credit grew just +5.5%.",
        implication: "Anyone reading 'industry credit grew 12%' and concluding large " +
                     "corporate lending is picking up is wrong. The growth is happening " +
                     "at the smaller end.",
        preferredMode: "yoy",
        effect: { highlight: ["Industry"] },
      },
      {
        id: "services-personal-loan-twin-engines",
        title: "Services and retail are carrying 61% of credit",
        body: "Services (₹57.2L Cr) and Personal Loans (₹67.2L Cr) together account for " +
              "₹124.5L Cr — 61% of total sectoral credit. Both are growing above the " +
              "system average: Services +15.5% and Personal Loans +14.9% YoY (Jan 2026). " +
              "Industry and Agriculture, at 34% of credit, are both below average.",
        implication: "Portfolio weight should follow where the system is growing. Industry " +
                     "and Agriculture are both growing below the 14.6% system average. " +
                     "The two structural growth engines are Services and retail — and the " +
                     "gap between them and the laggards is widening every period.",
        preferredMode: "yoy",
        effect: { highlight: ["Services", "Personal Loans"], dim: ["Agriculture", "Industry"] },
      },
    ],
    gaps: [
      {
        id: "agriculture-jan-march-swing",
        title: "Agriculture Jan vs March can vary 8–10% — which is real?",
        body: "Agriculture in Jan 2025 showed +12.2% YoY; by Mar 2025, same year, " +
              "it dropped to +10.4% YoY. In Jan 2026 it's +11.4%. The underlying trend " +
              "is 10–12% growth, but picking any single data point can give you a misleading read. " +
              "Services and Personal Loans are stable across months and more reliable to track.",
        implication: "Agriculture growth figures should be quoted as a range or as a " +
                     "March-to-March comparison only. Jan agriculture numbers include seasonal " +
                     "procurement credit that inflates the stock.",
        preferredMode: "yoy",
        effect: { highlight: ["Agriculture"], dash: ["Agriculture"] },
      },
      {
        id: "industry-share-declining-despite-growth",
        title: "Industry is growing but still losing share",
        body: "Industry's share of total sectoral credit: Jan 2024 = 22.5%, Jan 2026 = 21.4%. " +
              "Even with +12.1% YoY growth, it is growing slower than the system average " +
              "of 14.6% — so its share keeps shrinking. This has been true for at least 2 years.",
        implication: "Industry's share of total credit will keep declining until its growth " +
                     "rate exceeds the 14.6% system average. Two consecutive years of share " +
                     "loss — even while growing in absolute terms — is a structural signal, " +
                     "not a cyclical one. The sub-sector mix (MSME vs Large) matters more " +
                     "than the sector headline.",
        preferredMode: "absolute",
        effect: { highlight: ["Industry"], dim: ["Services", "Personal Loans"] },
      },
    ],
    opportunities: [
      {
        id: "services-acceleration-sustained",
        title: "Services is the most consistent high-growth sector",
        body: "Services has grown above 12% YoY in every data point in this dataset: " +
              "+12.3% (Jan 2025), +12.0% (Mar 2025), +15.5% (Jan 2026). " +
              "It added ₹13.1L Cr in absolute terms from Jan 2024 (₹44.1L Cr) to Jan 2026 " +
              "(₹57.2L Cr) — the second-largest absolute addition after personal loans.",
        implication: "Services sub-sectors — particularly NBFCs (₹19L Cr, +17.8%), " +
                     "Trade (₹13.1L Cr, +16.1%), and Commercial Real Estate (₹6.0L Cr, +16.2%) " +
                     "— offer sustained lending opportunity with reliable growth.",
        preferredMode: "absolute",
        effect: { highlight: ["Services"] },
      },
    ],
  },

  industryBySize: {
    insights: [
      {
        id: "micro-small-acceleration-breakout",
        title: "Micro & Small credit tripled its growth rate",
        body: "Micro and Small enterprise credit grew +9.6% YoY in Jan 2025. " +
              "By Jan 2026 it's +31.2% YoY — a 3x acceleration in 12 months. " +
              "In absolute terms: Jan 2025 ₹7.86L Cr → Jan 2026 ₹10.31L Cr, " +
              "adding ₹2.45L Cr in a single year vs ₹0.69L Cr the prior year.",
        implication: "Something structural changed between Mar 2025 and Jan 2026. " +
                     "Whether it's UDYAM-linked formalisation, PSLC flows, or genuine " +
                     "new lending — Micro & Small is now the fastest-growing size segment " +
                     "in industry by a wide margin.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"] },
      },
      {
        id: "large-corporate-structurally-slow",
        title: "Large corporate credit is consistently the slowest",
        body: "Large enterprises grew +6.8% (Jan 2025), +6.9% (Mar 2025), +5.5% (Jan 2026). " +
              "Over 2 years (Jan 2024 to Jan 2026), Large credit grew just 12.6% cumulatively " +
              "vs Micro & Small's 43.8% and Medium's 44.9%.",
        implication: "Large companies are either using capital markets, ECBs, or deleveraging " +
                     "their bank relationships. The bank lending opportunity in industry has " +
                     "definitively moved to smaller businesses.",
        preferredMode: "yoy",
        effect: { highlight: ["Large"], dim: ["Micro and Small", "Medium"] },
      },
      {
        id: "medium-enterprises-fastest-2yr",
        title: "Medium enterprises grew 44.9% in 2 years",
        body: "Medium enterprise credit: Jan 2024 ₹2.94L Cr → Jan 2026 ₹4.26L Cr — " +
              "a 44.9% increase in 24 months. This segment has been consistently strong: " +
              "+18.4% (Jan 2025), +18.5% (Mar 2025), +22.3% (Jan 2026). " +
              "No quarter has been below 18% YoY growth in this dataset.",
        implication: "For lenders: Medium enterprises have delivered 18%+ YoY growth in " +
                     "every data point in this dataset — no miss, no volatility. This is not " +
                     "a hot segment with one good quarter; it is the most consistently " +
                     "growing size segment in industry credit over 2 years.",
        preferredMode: "yoy",
        effect: { highlight: ["Medium"] },
      },
    ],
    gaps: [
      {
        id: "msme-formalisation-not-new-borrowing",
        title: "Part of MSME growth is businesses becoming visible, not new borrowing",
        body: "UDYAM registrations since 2022 have brought millions of businesses into " +
              "the formal economy for the first time. Their credit history is thin or blank. " +
              "A portion of the +31.2% Micro & Small growth reflects these newly-visible " +
              "entities, not businesses that previously had bank credit growing at that rate.",
        implication: "Bureau checks on new MSME borrowers will return thin files. " +
                     "Lenders relying solely on credit scores for MSME underwriting are " +
                     "missing the opportunity and misreading the risk. GST data, UPI " +
                     "transaction history, and TReDS invoice flows are better signals.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"], dash: ["Micro and Small"] },
      },
      {
        id: "large-dominated-absolute-stock",
        title: "Large still holds 67% of industry credit despite slow growth",
        body: "At Jan 2026, Large = ₹29.3L Cr, Micro & Small = ₹10.3L Cr, Medium = ₹4.3L Cr. " +
              "Large accounts for 67% of total industry credit. Its slow growth (5.5% YoY) " +
              "is dragging the sector headline number down — without it, MSME+Medium would " +
              "show 28%+ growth.",
        implication: "Do not quote 'industry credit grew 12.1%' without decomposing it. " +
                     "Strip Large corporates and the remaining MSME and Medium segments " +
                     "grew 28%+. A credit strategy that tracks the aggregate headline " +
                     "misses where the growth is actually happening.",
        preferredMode: "absolute",
        effect: { highlight: ["Large"], dim: ["Micro and Small", "Medium"] },
      },
    ],
    opportunities: [
      {
        id: "medium-enterprise-underserved-window",
        title: "Medium enterprises: fastest growing, smallest stock",
        body: "Medium enterprise credit at ₹4.26L Cr is growing at +22.3% YoY but " +
              "is only 10% of total industry credit. At current growth rates, " +
              "it doubles in under 4 years. These businesses have GST records, " +
              "some bureau history, and genuine working capital and capex needs.",
        implication: "The sweet spot: businesses too large for microfinance but too small " +
                     "for large corporate credit teams. Ticket sizes ₹50L–₹5Cr, " +
                     "underwritten with cash flow rather than collateral.",
        preferredMode: "yoy",
        effect: { highlight: ["Medium", "Micro and Small"] },
      },
    ],
  },

  services: {
    insights: [
      {
        id: "nbfc-dominates-services-credit",
        title: "NBFCs take one-third of all services credit",
        body: "Non-Banking Financial Companies at ₹19.05L Cr are 33% of total services " +
              "credit (₹57.2L Cr). Growing +17.8% YoY — faster than the services average. " +
              "From Jan 2024 (₹14.95L Cr) to Jan 2026 (₹19.05L Cr) is +27.4% in 2 years. " +
              "Banks are actively funding the NBFC lending chain.",
        implication: "When NBFC credit grows, it's bank money flowing to end borrowers " +
                     "through a middleman. For banks without retail reach, NBFCs are their " +
                     "route to segments they can't serve directly. For NBFCs, cheap bank funding " +
                     "is the input that makes their model viable.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-Banking Financial Companies (NBFCs)"] },
      },
      {
        id: "trade-credit-steady-growth",
        title: "Trade credit is ₹13L Cr and growing 16% annually",
        body: "Trade credit grew from ₹9.85L Cr (Jan 2024) to ₹13.09L Cr (Jan 2026) — " +
              "a 32.9% increase in 2 years. YoY: +14.5% (Jan 2025), +15.6% (Mar 2025), " +
              "+16.1% (Jan 2026). The growth is consistent and accelerating slightly.",
        implication: "For lenders: Trade credit is large (₹13L Cr), consistently growing " +
                     "(14–16% YoY for 3 periods), and addressable through supply chain " +
                     "financing and invoice discounting. TReDS-linked origination is the " +
                     "entry point — the data trail is verifiable and the segment is " +
                     "underserved by specialist lenders.",
        preferredMode: "yoy",
        effect: { highlight: ["Trade"] },
      },
      {
        id: "tourism-recovery-complete",
        title: "Tourism credit is recovering — +19.2% is a post-COVID catch-up signal",
        body: "Tourism, Hotels and Restaurants grew just +5.8% YoY in Jan 2025. " +
              "By Jan 2026 that's +19.2% YoY (₹0.97L Cr vs ₹0.82L Cr). " +
              "The sector is clearly back — hospitality capex and working capital " +
              "is being funded again.",
        implication: "For lenders: Hospitality credit has normalised. The sector that was " +
                     "structurally avoided during and after COVID is now growing at +19.2% YoY " +
                     "and accessing bank credit for working capital and capex again. " +
                     "Risk profiles have recovered — the window for lenders who stayed away " +
                     "to re-enter on better terms is open.",
        preferredMode: "yoy",
        effect: { highlight: ["Tourism, Hotels and Restaurants"] },
      },
    ],
    gaps: [
      {
        id: "shipping-data-discontinuity",
        title: "Shipping data broke in Jan 2026 — do not use this number",
        body: "Shipping credit was ₹7.1L Cr (Jan 2024), ₹7.1L Cr (Mar 2024), " +
              "₹7.2L Cr (Jan 2025), ₹7.3L Cr (Mar 2025), then suddenly ₹0.104L Cr in Jan 2026. " +
              "This is a 98.6% drop in one quarter. This is not a real credit contraction — " +
              "it is a classification or reporting change in the RBI dataset.",
        implication: "Ignore all Shipping YoY figures until the series is restated. " +
                     "Do not use Shipping data from Jan 2026 for any analysis.",
        preferredMode: "absolute",
        effect: { highlight: ["Shipping"], dash: ["Shipping"] },
      },
      {
        id: "transport-operators-sharp-deceleration",
        title: "Transport credit growth collapsed from 12% to 4.3%",
        body: "Transport Operators YoY: +12.0% (Jan 2025), +12.6% (Mar 2025), +4.3% (Jan 2026). " +
              "In FY terms vs Mar 2025: just +2.3%. This is a sharp, recent deceleration. " +
              "The sector went from in-line-with-market to well-below-market growth in one period.",
        implication: "Commercial vehicle fleet expansion has slowed. This may reflect higher " +
                     "borrowing costs, slower freight growth, or fleet operators front-loading " +
                     "purchases in FY24-25. Track this sector closely in the next data release.",
        preferredMode: "yoy",
        effect: { highlight: ["Transport Operators"], dash: ["Transport Operators"] },
      },
    ],
    opportunities: [
      {
        id: "computer-software-small-but-growing",
        title: "IT services credit grew 20.7% from a very small base",
        body: "Computer Software grew from ₹0.263L Cr (Jan 2024) to ₹0.407L Cr (Jan 2026) — " +
              "+54.8% in 2 years. YoY: +28.2% (Jan 2025), +27.0% (Mar 2025), +20.7% (Jan 2026). " +
              "At ₹0.41L Cr, this is tiny relative to sector size — " +
              "India's IT sector revenue is ₹22L Cr+ annually, yet bank credit is ₹0.41L Cr.",
        implication: "IT companies are underleveraged relative to their cash flows. " +
                     "The opportunity is in structured working capital, acquisition financing, " +
                     "and employee stock loan programs — not traditional collateral-based lending.",
        preferredMode: "yoy",
        effect: { highlight: ["Computer Software"] },
      },
      {
        id: "commercial-real-estate-steady-opportunity",
        title: "Commercial Real Estate: ₹6L Cr and growing 16% consistently",
        body: "Commercial Real Estate grew from ₹4.51L Cr (Jan 2024) to ₹5.98L Cr (Jan 2026) — " +
              "+32.6% in 2 years. Every data point shows 13–16% YoY growth. " +
              "This is a sector where bank credit is the primary financing vehicle.",
        implication: "For lenders: Commercial Real Estate has compounded at 15% for two years " +
                     "with no period of volatility. Offices, warehouses, and retail malls — " +
                     "particularly in Tier 2 cities — are where demand is growing. Large " +
                     "ticket, collateralised, and bank credit is the dominant financing route.",
        preferredMode: "absolute",
        effect: { highlight: ["Commercial Real Estate"] },
      },
    ],
  },

  personalLoans: {
    insights: [
      {
        id: "gold-loans-structural-surge",
        title: "Gold loans went up 4.4x in 24 months",
        body: "Loans against gold jewellery: Jan 2024 ₹0.915L Cr → Jan 2025 ₹1.75L Cr → " +
              "Jan 2026 ₹4.01L Cr. Three consecutive data points show accelerating growth: " +
              "+91.4% (Jan 2025), +121.1% (Mar 2025), +128.8% (Jan 2026) YoY. " +
              "This is not seasonal — every quarter in this dataset shows the same direction.",
        implication: "Gold is emerging as the dominant collateral in retail lending. " +
                     "At ₹4L Cr outstanding and +128.8% YoY, it will likely cross ₹8–9L Cr " +
                     "by Jan 2027 at this rate. Any lender without a gold loan product is " +
                     "watching competitors grow 10x faster in this segment.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"] },
      },
      {
        id: "credit-cards-stagnating",
        title: "Credit card growth has stalled at 1.5%",
        body: "Credit card outstanding: ₹2.585L Cr (Jan 2024) → ₹2.921L Cr (Jan 2025) → " +
              "₹2.964L Cr (Jan 2026). Growth dropped from +13.0% (Jan 2025) to just +1.5% (Jan 2026). " +
              "In FY terms (vs Mar 2025): +4.2%. The category is essentially flat.",
        implication: "RBI's unsecured lending guardrails appear to be biting. " +
                     "Credit card growth, which was 30%+ in FY22-23, has now stalled. " +
                     "Banks are slowing origination or tightening limits on existing cardholders.",
        preferredMode: "yoy",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
      },
      {
        id: "vehicle-loans-reaccelerating",
        title: "Vehicle loans picked up — +17.1% after a slow patch",
        body: "Vehicle loans: +9.7% (Jan 2025), +8.6% (Mar 2025), +17.1% (Jan 2026). " +
              "Absolute: ₹5.61L Cr (Jan 2024) → ₹7.21L Cr (Jan 2026), +28.5% in 2 years. " +
              "The Jan 2026 acceleration is notable — from sub-10% back into high teens.",
        implication: "For lenders: Vehicle credit has recovered from its mid-2025 slowdown " +
                     "and is back above the system average at +17.1% YoY. Treat this as a " +
                     "one-data-point signal — do not build strategy on it until March 2026 " +
                     "data confirms whether the acceleration holds.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicle Loans"] },
      },
    ],
    gaps: [
      {
        id: "advances-shares-bonds-reclassified",
        title: "Advances against shares/bonds data broke in Mar 2025",
        body: "This category shows large values (Jan 2024–Jan 2025) that drop to near-zero " +
              "by Mar 2025 and Jan 2026. This is a reclassification event, not real " +
              "credit contraction. The YoY growth figure for this series in Jan 2026 (+5.1%) " +
              "is computed against an already-reclassified Jan 2025 value and is unreliable.",
        implication: "Do not use 'Advances to Individuals against share, bonds, etc.' " +
                     "for trend analysis until the series is restated or explained by RBI. " +
                     "Exclude it from any portfolio comparison.",
        preferredMode: "absolute",
        effect: { highlight: ["Advances to Individuals against share, bonds, etc."], dash: ["Advances to Individuals against share, bonds, etc."] },
      },
      {
        id: "housing-dominates-but-growing-slowest",
        title: "Housing is 49% of personal loans but growing slowest",
        body: "Housing at ₹32.78L Cr is 49% of personal loans. It's growing +11.1% YoY — " +
              "the slowest of all growing sub-categories. Gold loans at ₹4.01L Cr are " +
              "growing 12x faster. The composition of personal loans is quietly shifting " +
              "away from housing toward gold, vehicle, and education credit.",
        implication: "The housing credit share of personal loans will decline from 49% " +
                     "unless it accelerates. This has implications for risk profiles, " +
                     "collateral quality, and tenor mix of retail loan books.",
        preferredMode: "absolute",
        effect: { highlight: ["Housing (Including Priority Sector Housing)"], dim: ["Loans against gold jewellery"] },
      },
      {
        id: "consumer-durables-declining",
        title: "Consumer durable loans are shrinking — EMI financing is moving off-bank",
        body: "Consumer Durables: ₹0.239L Cr (Jan 2024) → ₹0.224L Cr (Jan 2026). " +
              "Negative YoY in every period: -2.4% (Jan 2025), -1.0% (Mar 2025), -4.0% (Jan 2026). " +
              "This is a category that is declining in bank credit — probably because " +
              "BNPL and fintech EMI platforms have taken this business away from banks.",
        implication: "This category will not recover in bank credit. BNPL and fintech EMI " +
                     "platforms have structurally displaced bank financing for consumer " +
                     "durables. If your consumer durables book is growing, investigate " +
                     "whether you are taking on quality that fintechs have already declined.",
        preferredMode: "yoy",
        effect: { highlight: ["Consumer Durables"], dash: ["Consumer Durables"] },
      },
    ],
    opportunities: [
      {
        id: "gold-loan-market-open",
        title: "Gold loan growth shows no signs of peaking",
        body: "Gold loans grew +91.4% (Jan 2025), +121.1% (Mar 2025), +128.8% (Jan 2026) — " +
              "the growth rate is itself accelerating, not decelerating. " +
              "At ₹4.01L Cr today, this segment is still smaller than Vehicle Loans (₹7.2L Cr). " +
              "The headroom is large.",
        implication: "The entry ticket for gold lending is low — Indian households hold " +
                     "~25,000 tonnes of gold. Lenders who can do digital gold valuation " +
                     "and doorstep processing have a cost advantage over traditional branches.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"] },
      },
      {
        id: "education-loans-steady-growth",
        title: "Education loans growing 14% with no signs of reversal",
        body: "Education loans: ₹1.172L Cr (Jan 2024) → ₹1.549L Cr (Jan 2026) — +32% in 2 years. " +
              "YoY: +15.9% (Jan 2025), +15.1% (Mar 2025), +14.0% (Jan 2026). " +
              "Consistent, socially critical, and often priority-sector qualifying.",
        implication: "Education loans combine priority sector benefits with long-tenor, " +
                     "relatively low-default profiles at the secured end. " +
                     "Under-penetrated for premium higher education abroad — average ticket " +
                     "sizes there are 10x+ domestic.",
        preferredMode: "absolute",
        effect: { highlight: ["Education"] },
      },
    ],
  },

  prioritySector: {
    insights: [
      {
        id: "psl-housing-surge",
        title: "PSL housing grew 37.9% — from flat to explosive",
        body: "PSL Housing was stagnant or declining: -1.3% (Jan 2025), -1.1% (Mar 2025). " +
              "Then Jan 2026: +37.9% YoY, ₹10.31L Cr vs ₹7.47L Cr — an addition of ₹2.84L Cr " +
              "in 12 months. This is the sharpest acceleration of any PSL sub-category in the dataset.",
        implication: "Something changed between Mar 2025 and Jan 2026 for PSL housing — " +
                     "either a policy push, definitional change, or lenders reclassifying " +
                     "existing loans. This warrants investigation before using these numbers.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"] },
      },
      {
        id: "msme-psl-growing-faster-than-overall",
        title: "PSL MSME growing 24.8% — tracking overall MSME credit growth",
        body: "PSL Micro and Small Enterprises: ₹19.4L Cr (Jan 2024) → ₹27.35L Cr (Jan 2026), " +
              "+24.8% YoY. This broadly tracks the industry-by-size MSME growth, " +
              "suggesting PSL classification is keeping pace with actual MSME credit growth.",
        implication: "For lenders with PSL obligations: MSME credit is doing double duty — " +
                     "meeting PSL targets while accessing a structurally growing segment. " +
                     "Building MSME origination now captures the business return and PSL " +
                     "compliance benefit simultaneously, without needing separate PSL strategies.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small Enterprises"] },
      },
    ],
    gaps: [
      {
        id: "psl-cross-classification",
        title: "These PSL numbers cannot be added up — they overlap",
        body: "Priority Sector (PSL) categories are not separate buckets. The same loan can appear in multiple PSL lines at once — " +
              "an MSME loan in agriculture is counted under both MSE and Agriculture. PSL Housing is a portion of total housing credit, not additional to it. " +
              "Add up all the PSL lines and you will count many loans twice.",
        implication: "Only the overall PSL target (40% of net bank credit) has legal meaning. Never add up the PSL sub-categories to estimate the total opportunity — the number you get will be much larger than the real pool.",
        preferredMode: "absolute",
        effect: {
          highlight: ["Micro and Small Enterprises", "Housing"],
          dim: ["Others"],
        },
      },
      {
        id: "export-credit-shrinking",
        title: "Export credit is contracting — -17.2% YoY",
        body: "Export credit: ₹0.121L Cr (Jan 2024) → ₹0.107L Cr (Jan 2026). " +
              "YoY: +6.9% (Jan 2025), +5.3% (Mar 2025), -17.2% (Jan 2026). " +
              "From growth to contraction in one period. The PSL category for export " +
              "credit is not gaining from any broader credit expansion.",
        implication: "Exporters are either not accessing PSL-classified bank credit, " +
                     "or lenders are retreating from this sub-category. " +
                     "Not a lending opportunity given the trend.",
        preferredMode: "yoy",
        effect: { highlight: ["Export Credit"], dash: ["Export Credit"] },
      },
      {
        id: "renewable-energy-and-social-infra-data-break",
        title: "Renewable Energy and Social Infrastructure data broke in Mar 2025",
        body: "Renewable Energy: ₹5.4L Cr (Jan 2024), ₹5.8L Cr (Mar 2024), ₹7.6L Cr (Jan 2025), " +
              "then ₹0.103L Cr (Mar 2025), ₹0.122L Cr (Jan 2026). " +
              "Social Infrastructure shows the same discontinuity. " +
              "These are reclassifications, not real credit changes. " +
              "The YoY growth figures are computed against the reclassified tiny base and are meaningless.",
        implication: "Do not use Renewable Energy or Social Infrastructure PSL data " +
                     "for trend analysis. The series broke in Mar 2025.",
        preferredMode: "absolute",
        effect: { highlight: ["Renewable Energy", "Social Infrastructure"], dash: ["Renewable Energy", "Social Infrastructure"] },
      },
    ],
    opportunities: [
      {
        id: "psl-housing-tier3-origination",
        title: "Affordable housing opportunity is in smaller cities",
        body: "PSL housing growing +37.9% is the strongest combination in this data: government demand support via PMAY, small loan sizes meaning lower loss if something goes wrong, " +
              "and strong repayment behaviour in the towns where most of this demand sits. The constraint isn't demand — it is distribution. " +
              "Very few lenders have origination infrastructure in Tier 3 and 4 cities.",
        implication: "Building or partnering for origination in 50 targeted semi-urban clusters — through agents, business correspondents, or co-lending with housing finance companies — gets you to where the demand is. You earn both the business and PSL credit certificates.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"] },
      },
      {
        id: "weaker-sections-large-growing",
        title: "Weaker sections: ₹20L Cr and growing — the PSLC market signal",
        body: "Weaker Sections (incl. PSLC-SF/MF): ₹15.89L Cr (Jan 2024) → ₹20.08L Cr (Jan 2026), " +
              "+26.3% in 2 years. YoY: +12.9% (Jan 2025), +15.3% (Mar 2025), +11.9% (Jan 2026). " +
              "The PSLC component means banks are actively buying certificates to meet targets — " +
              "and the underlying microfinance/small farmer credit is growing regardless.",
        implication: "Lenders that can originate in weaker sections directly — " +
                     "microfinance, NBFC-MFIs, SFBs — are both serving a growing segment " +
                     "and generating PSLC inventory they can sell to banks that can't reach these borrowers.",
        preferredMode: "absolute",
        effect: { highlight: ["Weaker Sections including net PSLC- SF/MF"] },
      },
    ],
  },

  industryByType: {
    insights: [
      {
        id: "infrastructure-dominates-but-slowest",
        title: "Infrastructure is 33% of industry credit but growing slowest",
        body: "Infrastructure at ₹14.27L Cr (Jan 2026) is 33% of total industry-by-type credit. " +
              "Yet its YoY growth is just +6.4% — the slowest of any meaningful sub-sector. " +
              "From Jan 2024 (₹13.11L Cr) to Jan 2026 (₹14.27L Cr): +8.8% in 2 years. " +
              "Large infrastructure credit is not where the growth is.",
        implication: "For lenders: Large infrastructure bank credit is not the opportunity. " +
                     "Capital markets, ECBs, and government budgets are the primary funding " +
                     "vehicles for large infra projects. The bank credit opportunity in " +
                     "industry is in Engineering (+35.9%), Basic Metal (+13.8%), and " +
                     "Chemicals (+15.1%) — not Infrastructure.",
        preferredMode: "absolute",
        effect: { highlight: ["Infrastructure"], dim: ["All Engineering", "Gems and Jewellery"] },
      },
      {
        id: "engineering-gems-breakout",
        title: "Engineering and Gems & Jewellery both surged 35%+ YoY",
        body: "All Engineering: +18.0% (Jan 2025) → +22.0% (Mar 2025) → +35.9% (Jan 2026). " +
              "Gems & Jewellery: +5.1% (Jan 2025) → +1.0% (Mar 2025) → +35.6% (Jan 2026). " +
              "Both accelerated sharply in the most recent period. Different drivers — " +
              "Engineering likely capex, Gems & Jewellery likely gold price effect on working capital.",
        implication: "For lenders: these two sub-sectors look identical in the YoY chart " +
                     "but are entirely different bets. Engineering's acceleration is " +
                     "structural — PLI-linked capex. Gems & Jewellery's is gold-price-sensitive " +
                     "and could reverse if gold prices correct. Treat them as separate " +
                     "lending categories with different risk profiles.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering", "Gems and Jewellery"] },
      },
      {
        id: "basic-metal-steady-grower",
        title: "Basic Metal is the steady backbone of industrial credit",
        body: "Basic Metal and Metal Product: ₹3.81L Cr (Jan 2024) → ₹4.94L Cr (Jan 2026), " +
              "+29.8% in 2 years. YoY: +14.1% (Jan 2025), +12.8% (Mar 2025), +13.8% (Jan 2026). " +
              "Three periods of double-digit consistent growth — no volatility, no anomaly.",
        implication: "For lenders: Basic Metal (steel, aluminium, copper) is the quiet " +
                     "backbone of construction and manufacturing credit — growing at market " +
                     "rate for three consecutive periods, no anomalies, tangible collateral, " +
                     "large ticket sizes. A stable, low-surprise segment in an environment " +
                     "of high sector volatility.",
        preferredMode: "yoy",
        effect: { highlight: ["Basic Metal and Metal Product"] },
      },
    ],
    gaps: [
      {
        id: "infrastructure-drags-sector-average",
        title: "Infrastructure's slow growth hides faster growth elsewhere",
        body: "If you strip Infrastructure (₹14.27L Cr, +6.4%) from the industry total, " +
              "the remaining sub-sectors combined grew significantly faster. " +
              "The headline 'industry grew 12.1%' is pulled down by Infrastructure's " +
              "weight. The manufacturing and processing sub-sectors tell a different story.",
        implication: "Always decompose industry credit before quoting the headline. " +
                     "Engineering (+35.9%), Basic Metal (+13.8%), and Chemicals (+15.1%) " +
                     "all outperform the system average of 14.6%. Infrastructure's weight " +
                     "makes these invisible in the aggregate — the sector is structurally " +
                     "stronger than the headline 12.1% suggests.",
        preferredMode: "yoy",
        effect: { dim: ["Infrastructure"] },
      },
      {
        id: "gems-jewellery-gold-price-effect",
        title: "Gems & Jewellery surge may be gold price inflation, not volume growth",
        body: "Gems & Jewellery was barely growing (+5.1% Jan 2025, +1.0% Mar 2025) " +
              "then surged to +35.6% in Jan 2026. Gold prices rose ~30% over this period. " +
              "Working capital loans for jewellers are collateralized against gold inventory — " +
              "when the inventory value rises, the eligible loan amount rises too.",
        implication: "Don't read Gems & Jewellery +35.6% as an expansion in the jewellery " +
                     "business. It may simply reflect higher gold prices inflating the " +
                     "collateral and loan amounts without any change in actual business volume.",
        preferredMode: "yoy",
        effect: { highlight: ["Gems and Jewellery"], dash: ["Gems and Jewellery"] },
      },
    ],
    opportunities: [
      {
        id: "engineering-capex-cycle",
        title: "Engineering credit growing 35.9% — capex cycle has started",
        body: "All Engineering went from ₹1.94L Cr (Jan 2024) to ₹3.11L Cr (Jan 2026) — " +
              "+60.5% in 2 years. The acceleration: +18.0% → +22.0% → +35.9% YoY " +
              "across three successive periods. This is a consistent directional signal " +
              "of manufacturing capex financing picking up.",
        implication: "Engineering companies borrowing for capacity expansion have " +
                     "long loan tenors, tangible collateral, and cash flows tied to " +
                     "order books. If you have the technical underwriting capability, " +
                     "this segment is growing 3x faster than bank credit overall.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id: "chemicals-steady-double-digit",
        title: "Chemicals growing 15.1% — steady industrial financing opportunity",
        body: "Chemicals and Chemical Products: ₹2.42L Cr (Jan 2024) → ₹3.05L Cr (Jan 2026), " +
              "+25.9% in 2 years. YoY: +9.5% (Jan 2025), +7.4% (Mar 2025), +15.1% (Jan 2026). " +
              "The acceleration in the latest period is notable.",
        implication: "For lenders: Chemicals is a diversified sector — pharma intermediates, " +
                     "specialty chemicals, agrochem, paints. Growing at 15% with low " +
                     "volatility across three periods. Smaller ticket sizes than " +
                     "infrastructure but better growth trajectory and diversified " +
                     "end-markets reduce concentration risk.",
        preferredMode: "yoy",
        effect: { highlight: ["Chemicals and Chemical Products"] },
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
