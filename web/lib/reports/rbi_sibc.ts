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
    gaps: [],
    opportunities: [],
  },

  industryBySize: {
    insights: [
      {
        id:    "msme-outpacing-large",
        title: "MSME outpacing large industry",
        body:  "Micro & Small grew +31.2% YoY and Medium +22.3% — against Large at just +5.5%. " +
               "The credit opportunity has shifted decisively to mid-market origination.",
        implication: "MSME-focused NBFCs have structural runway. The data confirms the gap at scale, not just in the narrative.",
        effect: { highlight: ["Micro and Small", "Medium"] },
      },
    ],
    gaps: [],
    opportunities: [],
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
    ],
    opportunities: [],
  },

  personalLoans: {
    insights: [
      {
        id:    "gold-system-signal",
        title: "Gold loans: a system-level signal",
        body:  "₹0.92L Cr → ₹4.01L Cr in 24 months (+337.9%). Gold prices rose ~25–30% but credit grew 4.4×. " +
               "This is volume expansion — more borrowers pledging gold — not collateral appreciation.",
        implication: "This pace of gold-secured credit growth is a leading indicator of household financial stress. It also signals a competitive window before larger banks saturate the category.",
        effect: { highlight: ["Loans against gold jewellery"] },
      },
      {
        id:    "credit-cards-stalled",
        title: "Credit cards have effectively stalled",
        body:  "+1.5% YoY after a historical trend of 25–30% growth. RBI's risk-weight intervention (Nov 2023) is the structural cause. " +
               "The plateau is regulatory, not cyclical.",
        implication: "Lenders with heavy revolving unsecured exposure should evaluate rotation into secured retail — vehicle, gold, and housing are all growing faster.",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
      },
    ],
    gaps: [],
    opportunities: [],
  },

  prioritySector: {
    insights: [
      {
        id:    "psl-housing-3x",
        title: "PSL Housing growing at 3× commercial",
        body:  "PSL Housing +37.9% YoY (₹10.31L Cr) vs commercial housing loans +11.1%. " +
               "PSL Housing now represents 31.5% of total housing credit and is the fastest-growing PSL category.",
        implication: "Regulatory incentive and market growth are aligned. Efficient origination in the affordable housing segment provides both a subsidised cost of funds and a structural demand floor.",
        effect: { highlight: ["Housing"] },
      },
    ],
    gaps: [],
    opportunities: [],
  },

  industryByType: {
    insights: [
      {
        id:    "engineering-fastest",
        title: "Engineering is the fastest grower",
        body:  "All Engineering grew +35.9% YoY to ₹3.11L Cr — highest growth of any sub-sector above ₹1L Cr. " +
               "+60.3% over two years. PLI-linked supply-chain reshoring is the primary driver.",
        implication: "Manufacturing supply-chain finance — working capital, machinery loans, export credit — is the highest-velocity opportunity in the corporate credit segment today.",
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
    gaps: [],
    opportunities: [],
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

  // 3 — Industry by Size (children of code "2", Statement 1)
  const sec3 = childrenOf(rows, "2");
  sections.push(makeSection(
    rows,
    "industryBySize", "Industry by Size", "🏭", 2,
    sec3.codes, sec3.labels, "% of Industry"
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
