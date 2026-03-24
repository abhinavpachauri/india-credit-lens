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

const ANNOTATIONS: Record<string, SectionAnnotations> = {

  bankCredit: {
    insights: [],
    gaps: [
      {
        id:    "food-credit-jan-artifact",
        title: "Food credit: seasonal distortion",
        body:  "Food Credit's +58.9% YoY in Jan 2026 is a seasonal artifact. January is the procurement season peak; " +
               "by March, the same balance typically halves (Jan 2025: ₹0.56L Cr → Mar 2025: ₹0.37L Cr). " +
               "The high base comparison will reverse to near-zero by Mar 2026.",
        implication: "Any lender benchmarking portfolio growth against headline bank credit in January is using a seasonally distorted number. The durable growth signal is Non-food Credit, not the composite headline.",
        preferredMode: "yoy",
        effect: { highlight: ["Food Credit"], dash: ["Food Credit"] },
      },
    ],
    opportunities: [
      {
        id:    "non-food-structural-engine",
        title: "Non-food credit is the real engine",
        body:  "Non-food credit (₹203.9L Cr, +14.4% YoY) is the only structurally interpretable growth baseline — food credit is seasonal noise. " +
               "It has compounded at ~13% annually over the data window, consistent with nominal GDP growth plus financial deepening.",
        implication: "Lenders should benchmark their portfolio growth and product mix against non-food credit growth, not the headline total. Persistent underperformance vs non-food credit is a market share loss signal.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
      },
    ],
  },

  mainSectors: {
    insights: [
      {
        id:    "retail-overtook-corporate",
        title: "Retail overtook corporate",
        body:  "Personal Loans (₹67.2L Cr, 33%) now exceeds Industry (₹43.9L Cr, 21%). " +
               "The shift from corporate balance-sheet credit to retail origination is visible in the stock data — not just the growth narrative.",
        implication: "Products designed around large corporate relationships face a structural headwind. The credit opportunity is in mid-market and retail origination.",
        effect: { highlight: ["Personal Loans"] },
      },
    ],
    gaps: [
      {
        id:    "jan-vs-march-distorts",
        title: "Jan/Mar timing distorts sector YoY",
        body:  "Agriculture and Food Credit are structurally seasonal — January readings reflect kharif procurement peaks, " +
               "March readings reflect post-harvest troughs. YoY comparisons between January snapshots embed this seasonal structure, " +
               "making Agriculture growth rates appear higher or lower depending on base-month selection.",
        implication: "Sector-level growth rates in this dataset should be treated as directional, not precise. Agriculture YoY is least reliable; Services and Personal Loans are least affected by seasonality.",
        preferredMode: "yoy",
        effect: { highlight: ["Agriculture"], dash: ["Agriculture"] },
      },
    ],
    opportunities: [
      {
        id:    "services-personal-dual-engine",
        title: "Two sectors drive the credit system",
        body:  "Services (₹57.2L Cr, +15.5%) and Personal Loans (₹67.2L Cr, +14.9%) together represent 61% of non-food bank credit " +
               "and are growing faster than the system average. Industry (21%) and Agriculture (12%) are both below-average growers.",
        implication: "Lenders allocating product development and distribution capacity should orient primarily toward retail and services segments. These two sectors will continue to gain share at the expense of industry credit as a proportion of total bank deployment.",
        preferredMode: "absolute",
        effect: { highlight: ["Services", "Personal Loans"] },
      },
    ],
  },

  industryBySize: {
    insights: [
      {
        id:    "msme-outpacing-large",
        title: "MSME outpacing large industry",
        body:  "Micro & Small grew +31.2% YoY and Medium +22.3% — against Large at just +5.5%. " +
               "The credit opportunity has shifted decisively to mid-market origination.",
        implication: "MSME-focused NBFCs have structural runway. The data confirms the gap at scale, not just in the narrative.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small", "Medium"] },
      },
    ],
    gaps: [
      {
        id:    "msme-formalisation-base-effect",
        title: "MSME growth includes formalisation lift",
        body:  "Part of Micro & Small's elevated YoY growth reflects previously informal businesses entering formal credit for the first time " +
               "after UDYAM registration and GST filing, not purely new borrowing. " +
               "The stock figure conflates credit deepening with genuine demand expansion.",
        implication: "MSME credit growth overstates organic credit demand. Lenders entering this segment should build for borrower acquisition, not just share capture — many high-growth customers are genuinely first-time borrowers without credit history to underwrite against.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"], dash: ["Micro and Small"] },
      },
    ],
    opportunities: [
      {
        id:    "msme-formalisation-cohort",
        title: "MSME formalisation cohort: first-mover window",
        body:  "The UDYAM+GST registration wave (2022–2025) has produced a cohort of first-time borrowers with 2–3 years of " +
               "verifiable cash-flow data but no formal credit history. Micro & Small +43.8% and Medium +44.8% over two years confirm the cohort is converting.",
        implication: "Lenders with cash-flow underwriting models (GST returns, UPI transaction data, TReDS invoice history) have a durable edge over collateral-first incumbents in this segment. The window before this cohort becomes fully banked is 3–5 years.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small", "Medium"] },
      },
    ],
  },

  services: {
    insights: [],
    gaps: [
      {
        id:    "nbfc-wholesale-invisible",
        title: "NBFC credit is not end-borrower data",
        body:  "NBFCs represent 33% of Services credit (₹19.1L Cr) — but this is bank-to-NBFC wholesale lending, not credit reaching the end borrower. " +
               "The actual segments being funded (unsecured consumer, MSME, microfinance) are invisible in this data.",
        implication: "Co-lending and NBFC-bank partnerships are the mechanism through which banks access high-growth consumer and MSME segments. Direct origination in these segments is underrepresented in bank books.",
        effect: { highlight: ["Non-Banking Financial Companies (NBFCs)"], dash: ["Non-Banking Financial Companies (NBFCs)"] },
      },
      {
        id:    "trade-wholesale-not-sme",
        title: "Trade credit is mostly wholesale",
        body:  "Trade at ₹13.1L Cr (+40.3% over 2 years) appears to signal an SME trade-finance boom. " +
               "However, the RBI Services classification aggregates large wholesale trading entities alongside retail and SME trade credit. " +
               "True end-SME trade finance is largely channelled through NBFC and supply-chain platforms, not directly visible here.",
        implication: "Trade credit growth is real but the beneficiary profile is unclear. Lenders building SME trade products should validate demand through NBFC channel data rather than treating this SIBC line as a direct SME credit signal.",
        preferredMode: "yoy",
        effect: { highlight: ["Trade"], dash: ["Trade"] },
      },
    ],
    opportunities: [
      {
        id:    "software-it-working-capital",
        title: "IT sector credit: massively underserved",
        body:  "Computer Software grew +54.7% over 2 years to only ₹0.41L Cr — India's largest export sector (>$200B/yr) " +
               "has essentially no bank credit penetration. IT firms have predictable receivables, TDS-verified income, and zero physical collateral.",
        implication: "Receivables-backed working capital for IT service exporters is a high-yield, low-risk product with no current bank-scale incumbent. The combination of NOSTRO data, GST invoices, and export receivables provides a fully digital underwriting chain.",
        preferredMode: "yoy",
        effect: { highlight: ["Computer Software"] },
      },
    ],
  },

  personalLoans: {
    insights: [
      {
        id:    "gold-system-signal",
        title: "Gold loans: a system-level signal",
        body:  "₹0.92L Cr → ₹4.01L Cr in 24 months (+337.9%). Gold prices rose ~25–30% but credit grew 4.4×. " +
               "This is volume expansion — more borrowers pledging gold — not collateral appreciation.",
        implication: "This pace of gold-secured credit growth is a leading indicator of household financial stress. It also signals a competitive window before larger banks saturate the category.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"] },
      },
      {
        id:    "credit-cards-stalled",
        title: "Credit cards have effectively stalled",
        body:  "+1.5% YoY after a historical trend of 25–30% growth. RBI's risk-weight intervention (Nov 2023) is the structural cause. " +
               "The plateau is regulatory, not cyclical.",
        implication: "Lenders with heavy revolving unsecured exposure should evaluate rotation into secured retail — vehicle, gold, and housing are all growing faster.",
        preferredMode: "yoy",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
      },
    ],
    gaps: [
      {
        id:    "gold-risk-uncontextualised",
        title: "Gold growth hides a risk dimension",
        body:  "The +337.9% in gold loans is reported as a product category statistic without contextualising the RBI's 2024 intervention — " +
               "the regulator flagged LTV compliance breaches and mandated corrections at multiple lenders. " +
               "Some portion of reported growth may reflect loan re-structuring or re-classification, not purely new origination.",
        implication: "Gold loan portfolios built during 2024–25 carry an embedded regulatory risk event. Lenders should separately track pre- and post-RBI-intervention cohorts to isolate true portfolio quality from the aggregate growth figure.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"], dash: ["Loans against gold jewellery"] },
      },
    ],
    opportunities: [
      {
        id:    "gold-income-overlay-pricing",
        title: "Gold loans: income overlay = better pricing",
        body:  "The gold loan market is priced on LTV alone. A lender adding an income overlay (ITR, GST turnover, salary credits) " +
               "can segment the same LTV band into high-quality and stress-driven borrowers — and offer competitive rates to the former " +
               "while avoiding the latter.",
        implication: "Risk-adjusted returns improve without changing collateral requirements. The income-overlay cohort will also have structurally lower renewal failure rates, reducing auction risk exposure in the 2026–27 cycle.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"] },
      },
      {
        id:    "vehicle-ev-product-layer",
        title: "Vehicle loans meet the EV transition",
        body:  "Vehicle Loans +17.1% YoY (₹7.21L Cr) is steady growth, but the product is undifferentiated. " +
               "EV financing requires a distinct structure: residual value curves, charging infrastructure dependency, " +
               "and FAME subsidy integration — none of which fit standard auto loan templates.",
        implication: "Lenders who build EV-specific loan products now will own the customer relationship through the transition rather than ceding the segment to OEM-captive finance arms. The EV transition compresses the window — OEM captive finance is already scaling.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicle Loans"] },
      },
    ],
  },

  prioritySector: {
    insights: [
      {
        id:    "psl-housing-3x",
        title: "PSL Housing growing at 3× commercial",
        body:  "PSL Housing +37.9% YoY (₹10.31L Cr) vs commercial housing loans +11.1%. " +
               "PSL Housing now represents 31.5% of total housing credit and is the fastest-growing PSL category.",
        implication: "Regulatory incentive and market growth are aligned. Efficient origination in the affordable housing segment provides both a subsidised cost of funds and a structural demand floor.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"] },
      },
    ],
    gaps: [
      {
        id:    "psl-cross-classification",
        title: "PSL totals are cross-classifications",
        body:  "PSL categories are not additive — the same loan appears in multiple PSL buckets simultaneously. " +
               "A Micro & Small Enterprise loan in Agriculture is counted under both MSE and Agriculture. " +
               "Summing PSL line items produces double-counting; only the aggregate PSL target (40% of ANBC) has legal meaning.",
        implication: "Any model that sums PSL sub-categories to estimate addressable market will overstate the true unduplicated pool. Use the aggregate PSL figure as the reference, not the sum of sub-categories.",
        preferredMode: "absolute",
        effect: {
          highlight: ["Micro and Small Enterprises", "Housing"],
          dim: ["Others"],
        },
      },
    ],
    opportunities: [
      {
        id:    "psl-housing-tier3-origination",
        title: "PSL Housing: build Tier 3/4 infrastructure",
        body:  "PSL Housing +37.9% is the strongest risk-adjusted opportunity in this dataset: regulatory demand floor (PMAY), " +
               "lower LTV at affordable ticket sizes, and strong repayment culture in target geographies. " +
               "But origination infrastructure in Tier 3/4 cities — where most demand sits — remains sparse.",
        implication: "Lenders who build low-cost, tech-enabled origination networks (DSA/BC, co-lending with HFCs) in 50 target semi-urban clusters capture both PSL certificate value and structural demand that urban-only distribution models cannot reach.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"] },
      },
      {
        id:    "renewable-energy-psl-window",
        title: "Renewable Energy PSL: pre-scale window",
        body:  "Renewable Energy PSL +126.9% over 2 years — but from a tiny base. This is a confirmed-but-nascent category: " +
               "the PSL classification is settled, solar/wind project pipelines are real, yet lender product infrastructure is still being built.",
        implication: "First-mover advantage in structured renewable energy PSL products (rooftop solar for MSMEs, small wind assets) is still available. The regulatory tailwind and demand pipeline are both visible; the product-infrastructure gap is the entry point.",
        preferredMode: "yoy",
        effect: { highlight: ["Renewable Energy"] },
      },
    ],
  },

  industryByType: {
    insights: [
      {
        id:    "engineering-fastest",
        title: "Engineering is the fastest grower",
        body:  "All Engineering grew +35.9% YoY to ₹3.11L Cr — highest growth of any sub-sector above ₹1L Cr. " +
               "+60.3% over two years. PLI-linked supply-chain reshoring is the primary driver.",
        implication: "Manufacturing supply-chain finance — working capital, machinery loans, export credit — is the highest-velocity opportunity in the corporate credit segment today.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id:    "infrastructure-power-masks",
        title: "Infrastructure: Power masks collapse",
        body:  "The +6.4% Infrastructure aggregate hides severe divergence: Power +17.5% while Telecom −17.2%, Roads +0.2%, Railways −24.2%. " +
               "Remove Power and infrastructure credit is declining.",
        implication: "Power project finance is the only live infrastructure credit opportunity at scale. All other infrastructure sub-sectors are in deleveraging or capex pause mode.",
        effect: { highlight: ["Infrastructure"] },
      },
    ],
    gaps: [
      {
        id:    "infrastructure-aggregate-misleading",
        title: "Infrastructure +6.4% is one-sector story",
        body:  "The Infrastructure aggregate is the most misleading number in this dataset. Power (55% of the total, +17.5%) " +
               "is the sole driver of the positive headline. Remove Power and the remaining 45% of infrastructure credit — " +
               "Telecom, Roads, Railways, Ports — is contracting on aggregate at approximately −3.7% YoY.",
        implication: "Lenders with infrastructure mandates built on the composite headline are mispricing risk. The only live infrastructure credit opportunity is Power and renewables. All other sub-sectors are in capex pause or active deleveraging — correct underwriting should reflect this bifurcation.",
        preferredMode: "yoy",
        effect: { highlight: ["Infrastructure"], dash: ["Infrastructure"] },
      },
    ],
    opportunities: [
      {
        id:    "engineering-supply-chain-finance",
        title: "Engineering SCF via GST and TReDS",
        body:  "Engineering's +35.9% YoY is PLI-linked, meaning anchor buyers (large OEMs receiving PLI incentives) have validated supply chains. " +
               "This creates a high-quality supply-chain finance opportunity: anchor-buyer-backed receivables from Tier 1–2 suppliers, " +
               "underwritten via GST invoice data and TReDS transaction history.",
        implication: "Lower credit risk than unsecured MSME lending at comparable yield. The PLI anchor-buyer structure provides de facto credit enhancement — suppliers who lose their anchor lose their PLI eligibility, creating a powerful repayment incentive.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id:    "gems-jewellery-gold-cycle-hedge",
        title: "Gems and Jewellery: gold price hedge play",
        body:  "Gems and Jewellery credit +35.6% YoY (₹1.17L Cr) is collateral-sensitive to gold prices, " +
               "creating a natural portfolio hedge when paired with retail gold loans. " +
               "Trade credit performance correlates positively with gold prices; retail gold loan default risk correlates inversely.",
        implication: "Lenders with both a Gems & Jewellery working capital book and a gold loan retail book can manage gold-price concentration risk across the cycle. This cross-product diversification reduces tail risk that single-product gold lenders carry.",
        preferredMode: "yoy",
        effect: { highlight: ["Gems and Jewellery"] },
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
  const seriesNames:  string[]     = codes.map((c) => labels[c] ?? c);

  return {
    id,
    title,
    icon,
    accentIndex,
    absoluteData,
    growthData,
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
