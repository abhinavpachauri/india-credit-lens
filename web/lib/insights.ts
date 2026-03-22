// ─── Insight / Gap / Opportunity content per dashboard section ──────────────
// Source: rbi_sibc_jan2026_summary.md, gaps.md, opportunities.md
// Each entry maps 1:1 to a SectionCard on the dashboard.

export interface SectionInsight {
  insight:     string   // what the data shows       → blue dot
  gap:         string   // what the data cannot show → grey hollow dot
  opportunity: string   // what a lender can act on  → green dot
}

export interface ChartAnnotation {
  type:  "hLine" | "vLine" | "dot"
  // hLine: horizontal reference line at y=value
  // vLine: vertical reference line at x=dateKey
  // dot:   reference dot at specific (x, y)
  value?: number          // y-value for hLine; ignored for vLine
  dateKey?: string        // x-value (raw date string) for vLine / dot
  dotY?: number           // y-value for dot type
  label:  string
  color:  string
  position?: "top" | "right" | "left" | "bottom"
}

export interface SectionMeta {
  insights:           SectionInsight
  trendAnnotations?:  ChartAnnotation[]
  distAnnotations?:   ChartAnnotation[]
}

// ─── Section content ─────────────────────────────────────────────────────────

export const SECTION_META: Record<string, SectionMeta> = {

  bankCredit: {
    insights: {
      insight:     "Non-food credit drives 99.6% of all growth. Total bank credit up +14.6% YoY to ₹204.7L Cr.",
      gap:         "Food Credit's +58.9% YoY is a seasonal artefact — January is procurement peak; it reverses sharply by March.",
      opportunity: "Retail and MSME now outpace corporate credit growth. The structural shift from balance-sheet lending to origination-led products is confirmed.",
    },
    trendAnnotations: [
      {
        type:     "hLine",
        value:    160.5,
        label:    "₹160.5L Cr  Jan '24 baseline",
        color:    "#9CA3AF",
        position: "right",
      },
    ],
  },

  mainSectors: {
    insights: {
      insight:     "Personal Loans (₹67.2L Cr, 33%) is now the single largest credit sector — overtaking Services for the first time.",
      gap:         "NBFC's ₹19.1L Cr within Services is bank-to-NBFC wholesale funding. End-borrower exposure in consumer and MSME is invisible here.",
      opportunity: "Micro & Small credit grew +31.2% YoY — fastest-growing large segment in the dataset. The MSME pipeline is real and data-confirmed.",
    },
    trendAnnotations: [
      {
        type:     "hLine",
        value:    67.2,
        label:    "Personal Loans ₹67.2L Cr",
        color:    "#EA580C",
        position: "right",
      },
    ],
  },

  industryBySize: {
    insights: {
      insight:     "MSME massively outpaces large industry: Micro & Small +31.2%, Medium +22.3% YoY vs Large industry only +5.5%.",
      gap:         "No NPA or delinquency overlay. Can't distinguish genuine MSME expansion from evergreening in large-industry books.",
      opportunity: "GST + UPI history makes the 2022–25 MSME formalisation cohort creditworthy for the first time. Cash-flow underwriting unlocks this without collateral.",
    },
  },

  services: {
    insights: {
      insight:     "NBFCs are the largest Services sub-sector at ₹19.1L Cr (33.3%) — but this is wholesale bank-to-NBFC funding, not retail credit deployment.",
      gap:         "Services is a catch-all. Trade, transport, professional services, and NBFCs are all aggregated — end-use of credit is indistinguishable.",
      opportunity: "Trade finance grew +32.9% over 2 years. Digital invoice discounting on GST-validated trades is structurally underbuilt at scale.",
    },
    trendAnnotations: [
      {
        type:     "hLine",
        value:    19.05,
        label:    "NBFC wholesale ₹19.1L Cr",
        color:    "#9CA3AF",
        position: "right",
      },
    ],
  },

  personalLoans: {
    insights: {
      insight:     "Gold Jewellery loans grew 337.9% in 2 years (₹0.92L Cr → ₹4.01L Cr). Volume grew 4.4× while collateral value grew only 1.3×.",
      gap:         "No borrower-level data. Rising gold loan volumes could signal productive working-capital use or household financial distress — this dataset cannot distinguish them.",
      opportunity: "Income-overlaid gold loan underwriting separates productive-use from distress cohorts. Accurate pricing here is a first-mover advantage before the category consolidates.",
    },
    trendAnnotations: [
      {
        type:     "hLine",
        value:    4.01,
        label:    "Gold: +129% YoY",
        color:    "#B45309",
        position: "right",
      },
    ],
  },

  prioritySector: {
    insights: {
      insight:     "PSL Housing grew +37.9% YoY — nearly 3× the rate of commercial housing (+11.1%). PSL now represents 31.5% of total housing credit.",
      gap:         "PSL targets appear met on paper, but PSLC certificate trading means the originating bank and the target-claiming bank may not be the same entity.",
      opportunity: "Tier 3/4 affordable housing combines regulatory tailwind, structural demand depth, and underserved geography — best risk-adjusted PSL opportunity in the data.",
    },
    distAnnotations: [
      {
        type:     "hLine",
        value:    40,
        label:    "PSL target 40%",
        color:    "#16A34A",
        position: "right",
      },
    ],
  },

  industryByType: {
    insights: {
      insight:     "All Engineering grew +35.9% YoY (+60.3% in 2yr) — fastest large industry segment. Telecom −17.2%, Railways −24.2%, Airports −26.1% YoY.",
      gap:         "Infrastructure's +6.4% headline hides sub-sector collapse. Ex-Power, infrastructure credit is declining ~3.7% — 5 of 6 sub-sectors are contracting.",
      opportunity: "PLI-linked manufacturing (engineering, electronics) has government revenue visibility and export linkages. Risk is mispriced against the outdated 2014-era infra NPA lens.",
    },
  },

}
