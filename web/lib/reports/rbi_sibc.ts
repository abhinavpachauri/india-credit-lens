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
        body:  "Food credit spikes every January because that's when the government buys kharif crops from farmers. By March, it drops back by 35–50%. " +
               "Jan 2025: ₹0.56L Cr → Mar 2025: ₹0.37L Cr. The +58.9% figure for Jan 2026 is that seasonal spike — it will disappear by next quarter.",
        implication: "If you're comparing your portfolio growth to 'bank credit grew X%' — check which month that figure is from. January bank credit includes this spike and makes the headline look better than it is.",
        preferredMode: "yoy",
        effect: { highlight: ["Food Credit"], dash: ["Food Credit"] },
      },
    ],
    opportunities: [
      {
        id:    "non-food-structural-engine",
        title: "Non-food credit is the real benchmark",
        body:  "Strip out food credit and what remains — ₹203.9L Cr growing +14.4% YoY — is the number that actually tells you how the credit system is doing. " +
               "It has grown at roughly 13% a year, in line with nominal GDP plus more people accessing formal credit for the first time.",
        implication: "Use non-food credit growth as your benchmark, not the headline total. If your portfolio is growing slower than 13–14% a year, you are losing ground — even if the headline numbers make the sector look healthy.",
        preferredMode: "absolute",
        effect: { highlight: ["Non-food Credit"], dim: ["Food Credit"] },
      },
    ],
  },

  mainSectors: {
    insights: [
      {
        id:    "retail-overtook-corporate",
        title: "Retail lending is now bigger than corporate",
        body:  "Personal loans (₹67.2L Cr, 33% of bank credit) now exceed industry and corporate credit (₹43.9L Cr, 21%). " +
               "This has been happening gradually for a decade, but the gap has now become impossible to ignore.",
        implication: "If your strategy is built around large corporate clients, you are in the slower-growing part of the market. The volume and the growth are in retail and small business lending.",
        effect: { highlight: ["Personal Loans"] },
      },
    ],
    gaps: [
      {
        id:    "jan-vs-march-distorts",
        title: "Agriculture YoY depends on which month you pick",
        body:  "January captures peak kharif crop procurement; March captures the post-harvest position. The same sector can look very different depending on whether you're comparing Jan-to-Jan or Mar-to-Mar. " +
               "Agriculture and food credit can swing 30–40% just because of the calendar.",
        implication: "Agriculture growth rates in this dataset are directional, not precise. Services and personal loans are stable across months and are more reliable to compare. Always check which month is being used before quoting agriculture credit growth.",
        preferredMode: "yoy",
        effect: { highlight: ["Agriculture"], dash: ["Agriculture"] },
      },
    ],
    opportunities: [
      {
        id:    "services-personal-dual-engine",
        title: "Two sectors are carrying the credit system",
        body:  "Services (₹57.2L Cr, +15.5% YoY) and personal loans (₹67.2L Cr, +14.9% YoY) together account for 61% of non-food bank credit " +
               "and are both growing faster than the system average. Industry and agriculture are below average and losing share year on year.",
        implication: "Credit growth over the next few years will be driven by services and retail — trade, housing, vehicle loans, gold. If your team is spending most of its time on corporate or agriculture credit, the data says the opportunity is elsewhere.",
        preferredMode: "absolute",
        effect: { highlight: ["Services", "Personal Loans"] },
      },
    ],
  },

  industryBySize: {
    insights: [
      {
        id:    "msme-outpacing-large",
        title: "Small businesses growing 6x faster than large",
        body:  "Micro & Small enterprises grew +31.2% YoY and Medium +22.3% — compared to Large industry at just +5.5%. " +
               "Small business credit is growing roughly 5–6 times faster than large corporate credit.",
        implication: "The lending opportunity in industry has shifted to smaller businesses. Large corporate credit is slow-growing and already competitive. MSME is where the volume growth is happening.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small", "Medium"] },
      },
    ],
    gaps: [
      {
        id:    "msme-formalisation-base-effect",
        title: "Some of this growth is businesses newly visible, not new borrowing",
        body:  "A lot of Micro & Small's growth isn't businesses borrowing more — it's businesses that always existed, " +
               "now showing up in bank data for the first time after GST registration and UDYAM enrolment. " +
               "The economy hasn't grown 31%; the formally visible part of it has.",
        implication: "Many of these new borrowers have no credit history — bureau checks will come back thin or blank. If you're entering MSME lending, your ability to assess creditworthiness without a credit score matters more than how many leads you can generate.",
        preferredMode: "yoy",
        effect: { highlight: ["Micro and Small"], dash: ["Micro and Small"] },
      },
    ],
    opportunities: [
      {
        id:    "msme-formalisation-cohort",
        title: "First-time MSME borrowers: a 3–5 year window",
        body:  "GST and UDYAM registrations from 2022 onwards created a large group of businesses with 2–3 years of verifiable income data but no formal loan history. " +
               "Micro & Small grew +43.8% and Medium +44.8% over two years — this group is actively converting to formal credit right now.",
        implication: "Lenders who can use GST returns, UPI transaction history, or TReDS invoice data — rather than requiring 3 years of ITR and property as collateral — have a real edge here. The window before these businesses build a bureau history and become accessible to every lender is roughly 3–5 years.",
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
        title: "NBFC figure here is bank-to-NBFC lending, not end borrowers",
        body:  "NBFCs are the largest services sub-sector at ₹19.1L Cr — but this is money banks lent to NBFCs, not money those NBFCs then lent to their customers. " +
               "The real end-borrowers (small businesses, consumers, microfinance customers) are further down the chain and aren't visible here at all.",
        implication: "Banks aren't directly reaching those segments — they're lending wholesale to NBFCs who then lend retail. The risk for banks is concentrated in a small number of large NBFC counterparties, not spread across millions of borrowers as this chart might suggest.",
        effect: { highlight: ["Non-Banking Financial Companies (NBFCs)"], dash: ["Non-Banking Financial Companies (NBFCs)"] },
      },
      {
        id:    "trade-wholesale-not-sme",
        title: "Trade credit is mostly large companies, not small traders",
        body:  "₹13.1L Cr in trade credit growing +40.3% over two years sounds like an SME trade finance boom. " +
               "But the RBI groups large wholesale traders alongside small retailers and SMEs in this category. " +
               "The bulk of this is large-value wholesale trade, not the small trader credit the headline implies.",
        implication: "If you are considering entering SME trade finance based on this number, check actual demand through NBFC and invoice discounting platforms first. The headline overstates the small-business opportunity.",
        preferredMode: "yoy",
        effect: { highlight: ["Trade"], dash: ["Trade"] },
      },
    ],
    opportunities: [
      {
        id:    "software-it-working-capital",
        title: "IT sector: big revenue, almost no bank credit",
        body:  "India's IT sector earns over $200 billion a year in exports but has only ₹0.41L Cr in bank credit. " +
               "Banks historically avoided this sector because IT firms have no land or machinery to pledge as security. " +
               "But IT firms have something more reliable: predictable export invoices, TDS-verified income, and long-term client contracts.",
        implication: "There is no dominant lender here yet. The product — working capital against export invoices — exists. It just hasn't been built specifically for IT exporters at scale. No physical security is needed; you underwrite against the invoice and the client.",
        preferredMode: "yoy",
        effect: { highlight: ["Computer Software"] },
      },
    ],
  },

  personalLoans: {
    insights: [
      {
        id:    "gold-system-signal",
        title: "Gold loans: the biggest signal in this data",
        body:  "Gold loan credit went from ₹0.92L Cr to ₹4.01L Cr in just 24 months — up 337.9%. Gold prices rose about 25–30% in the same period. " +
               "Credit grew 4.4 times while the value of the gold barely moved. That means far more people are pledging their gold, not just the same people pledging more valuable gold.",
        implication: "When large numbers of people pledge their gold, it usually means they need money urgently and this is the quickest way to get it. That is a household stress signal. The business opportunity is real, but the quality of borrowers entering now is different from those who built this market three years ago.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"] },
      },
      {
        id:    "credit-cards-stalled",
        title: "Credit cards have stopped growing",
        body:  "+1.5% YoY — after years of 25–30% annual growth. This is not because people want credit cards less. " +
               "In November 2023, RBI increased the risk weight on unsecured credit from 100% to 125%, making it more expensive for banks to issue cards. That one change cut growth from 25%+ to near zero.",
        implication: "If your book is heavy on credit cards, this is not a temporary slowdown — it is a policy ceiling. The banks growing fastest right now are rotating into secured products: vehicle loans, gold, and housing. The regulatory environment is friendlier there.",
        preferredMode: "yoy",
        effect: { highlight: ["Credit Card Outstanding"], dash: ["Credit Card Outstanding"] },
      },
    ],
    gaps: [
      {
        id:    "gold-risk-uncontextualised",
        title: "Gold growth includes a regulatory event that isn't visible here",
        body:  "The 337.9% growth figure does not mention that RBI stepped in during 2024 to flag loan-to-value compliance problems at multiple gold lenders. " +
               "Lenders were giving loans at higher LTV ratios than permitted. The regulator required corrections. " +
               "Some of the reported growth may be restructured loans, not purely new lending.",
        implication: "Gold loan portfolios built during 2024–25 carry a regulatory risk event baked in. Track your pre- and post-RBI-intervention lending separately. If you cannot tell them apart in your data, that is worth fixing before you scale further.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"], dash: ["Loans against gold jewellery"] },
      },
    ],
    opportunities: [
      {
        id:    "gold-income-overlay-pricing",
        title: "Gold loans: add income check, price better",
        body:  "Almost all gold loan pricing today is based on one thing: how much the gold is worth versus the loan amount. " +
               "A lender that also checks the borrower's income — ITR, GST turnover, salary credits — can separate lower-risk borrowers from stress-driven ones within the same LTV band, and offer better rates to the former.",
        implication: "You get better returns without changing your security requirements. And income-verified borrowers are less likely to miss payments and trigger gold auctions — which is the situation the whole industry is trying to avoid in 2026–27.",
        preferredMode: "yoy",
        effect: { highlight: ["Loans against gold jewellery"] },
      },
      {
        id:    "vehicle-ev-product-layer",
        title: "Vehicle loans meet the EV shift",
        body:  "Vehicle loans are growing steadily at +17.1% YoY (₹7.21L Cr). But the product is mostly unchanged — the same structure used for petrol and diesel vehicles for decades. " +
               "Electric vehicles are different: the resale value curve is different, FAME government subsidies need to be built into the loan, and buyer concerns about charging availability affect decisions.",
        implication: "OEM finance companies (Tata Motors, Ola Electric, etc.) are already building EV-specific products. If banks do not develop their own EV loan structure before volumes hit scale, they will lose that segment to captive lenders and it will be difficult to win back.",
        preferredMode: "yoy",
        effect: { highlight: ["Vehicle Loans"] },
      },
    ],
  },

  prioritySector: {
    insights: [
      {
        id:    "psl-housing-3x",
        title: "Affordable housing growing 3x faster than regular housing",
        body:  "Priority Sector housing loans — for lower-income borrowers under government schemes — grew +37.9% YoY to ₹10.31L Cr. " +
               "Regular commercial housing loans grew only +11.1%. Affordable housing now accounts for nearly a third of all housing credit in the country.",
        implication: "The government's affordable housing push is creating real credit demand at the bottom of the market — and it's growing much faster than the premium segment. The risk profile is also better: smaller loans, government demand support (PMAY scheme), and strong repayment track records in target areas.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"] },
      },
    ],
    gaps: [
      {
        id:    "psl-cross-classification",
        title: "These PSL numbers cannot be added up — they overlap",
        body:  "Priority Sector (PSL) categories are not separate buckets. The same loan can appear in multiple PSL lines at once — " +
               "an MSME loan in agriculture is counted under both MSE and Agriculture. PSL Housing is a portion of total housing credit, not additional to it. " +
               "Add up all the PSL lines and you will count many loans twice.",
        implication: "Only the overall PSL target (40% of net bank credit) has legal meaning. Never add up the PSL sub-categories to estimate the total opportunity — the number you get will be much larger than the real pool.",
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
        title: "Affordable housing opportunity is in smaller cities",
        body:  "PSL housing growing +37.9% is the strongest combination in this data: government demand support via PMAY, small loan sizes meaning lower loss if something goes wrong, " +
               "and strong repayment behaviour in the towns where most of this demand sits. The constraint isn't demand — it is distribution. " +
               "Very few lenders have origination infrastructure in Tier 3 and 4 cities.",
        implication: "Building or partnering for origination in 50 targeted semi-urban clusters — through agents, business correspondents, or co-lending with housing finance companies — gets you to where the demand is. You earn both the business and PSL credit certificates.",
        preferredMode: "yoy",
        effect: { highlight: ["Housing"] },
      },
      {
        id:    "renewable-energy-psl-window",
        title: "Renewable energy PSL: early mover window still open",
        body:  "Renewable Energy PSL grew +126.9% over two years — but from a very small base of ₹0.12L Cr. " +
               "Solar and wind projects are being built at scale. The PSL classification is settled. " +
               "But most banks still don't have standard products for rooftop solar for small businesses or small renewable assets.",
        implication: "The regulatory support and project pipeline are both confirmed. What's missing is a bank with a simple, repeatable product for this category. That gap will not stay open more than 2–3 years before the space becomes crowded.",
        preferredMode: "yoy",
        effect: { highlight: ["Renewable Energy"] },
      },
    ],
  },

  industryByType: {
    insights: [
      {
        id:    "engineering-fastest",
        title: "Engineering credit is the fastest growing large sector",
        body:  "All Engineering grew +35.9% YoY to ₹3.11L Cr — the highest growth of any industry sub-sector above ₹1L Cr, and +60.3% over two years. " +
               "The main driver is India's Production Linked Incentive (PLI) scheme — manufacturers who qualify get government incentives, which is spurring new factories, machinery purchases, and supply chain expansion.",
        implication: "This is real, policy-backed demand, not a one-off project. Companies in engineering supply chains need working capital and equipment financing. The segment is growing, tends to be creditworthy, and is not yet crowded with lenders.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id:    "infrastructure-power-masks",
        title: "Infrastructure is growing — but only because of power",
        body:  "Infrastructure credit looks stable at +6.4% YoY. But take out Power (which grew +17.5%), and everything else is actually shrinking: " +
               "Telecom −17.2%, Roads flat at +0.2%, Railways −24.2%, Airports −26.1%. Power is 55% of infrastructure credit and is the only sub-sector keeping the overall number positive.",
        implication: "Infrastructure credit is not broadly recovering. Power and renewables have active project pipelines. Roads, telecom, and railways are in a quiet period with very little new lending happening.",
        effect: { highlight: ["Infrastructure"] },
      },
    ],
    gaps: [
      {
        id:    "infrastructure-aggregate-misleading",
        title: "The infrastructure headline hides a split story",
        body:  "Power (₹7.89L Cr, +17.5%) is 55% of total infrastructure credit. Remove it, and the remaining 45% — roads, telecom, railways, airports — " +
               "is shrinking at roughly −3.7% on aggregate. Four of six sub-sectors are nominally declining. " +
               "The headline makes infrastructure sound stable; the breakdown shows most of it is quietly contracting.",
        implication: "If you are in infrastructure lending, where you sit within it matters enormously. Lenders still putting money into telecom or roads based on the composite growth rate are working from a misleading number. Power and renewables are the only live opportunity.",
        preferredMode: "yoy",
        effect: { highlight: ["Infrastructure"], dash: ["Infrastructure"] },
      },
    ],
    opportunities: [
      {
        id:    "engineering-supply-chain-finance",
        title: "Engineering supply chains: well-secured lending opportunity",
        body:  "Engineering's +35.9% growth is linked to PLI scheme anchor buyers — large manufacturers receiving government incentives with verified supply chains. " +
               "Their Tier 1 and 2 suppliers need working capital to fulfil orders. These invoices are backed by a large, creditworthy buyer and can be verified through GST data and TReDS (the government's digital invoice discounting platform).",
        implication: "This is lower risk than unsecured MSME lending at similar yields. The anchor buyer provides a natural backstop — suppliers are unlikely to default on loans tied to orders from their main customer. The whole chain is digitally verifiable.",
        preferredMode: "yoy",
        effect: { highlight: ["All Engineering"] },
      },
      {
        id:    "gems-jewellery-gold-cycle-hedge",
        title: "Gems and Jewellery: a natural offset to gold loan risk",
        body:  "Gems and Jewellery credit grew +35.6% YoY (₹1.17L Cr). This sector does well when gold prices are high — the trade is more profitable, working capital needs are larger. " +
               "Retail gold loans work the other way: when gold prices are high, some borrowers over-borrow against expensive gold and struggle to repay.",
        implication: "A lender with both a Gems & Jewellery working capital book and a retail gold loan book has a natural offset. When gold prices rise, one book does better while the other faces more stress — and vice versa. Lenders with only a gold loan book don't have this cushion.",
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
