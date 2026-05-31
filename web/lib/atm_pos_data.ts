"use client";

import Papa from "papaparse";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface AtmPosRow {
  report_date:   string;
  bank_name:     string;
  bank_category: string;
  record_type:   "bank" | "total";
  metric:        string;
  value:         number;
  unit:          string;
  data_status:   string;
}

export type FilterMode = "all" | "by_type" | "individual" | "top_n";

export interface FilterState {
  mode:          FilterMode;
  selectedTypes: string[];   // for by_type — default all 5
  selectedBanks: string[];   // for individual — default []
  topN:          number;     // for top_n — default 10
}

export interface ChartPoint {
  date: string;          // "Oct 2025"
  _ts:  number;          // timestamp for sorting
  [seriesName: string]: string | number | null;
}

export interface SectionData {
  absoluteData: ChartPoint[];
  momData:      ChartPoint[];   // MoM % — null for first date
  seriesNames:  string[];
}

// ── CSV cache ──────────────────────────────────────────────────────────────────

let _cache: AtmPosRow[] | null = null;

export async function loadAtmPosData(): Promise<AtmPosRow[]> {
  if (_cache) return _cache;
  return new Promise((resolve, reject) => {
    Papa.parse("/data/atm_pos_consolidated.csv", {
      download:      true,
      header:        true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (result) => {
        _cache = result.data as AtmPosRow[];
        resolve(_cache);
      },
      error: reject,
    });
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────────

export function getAllBanks(rows: AtmPosRow[]): string[] {
  const set = new Set<string>();
  rows.forEach((r) => {
    if (r.record_type === "bank") set.add(r.bank_name);
  });
  return Array.from(set).sort();
}

export function getAvailableDates(rows: AtmPosRow[]): string[] {
  const set = new Set<string>();
  rows.forEach((r) => set.add(r.report_date));
  return Array.from(set).sort();
}

export function formatAtmDate(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-IN", { month: "short", year: "numeric", timeZone: "UTC" });
}

export function formatAtmValue(value: number, unit: string): string {
  if (unit === "rs_thousands") {
    const crore = value / 100; // rs_thousands → crore: 1 crore = 100 thousands? No: 1 crore = 10,000 thousands
    // rs_thousands: divide by 10000 to get crore
    const cr = value / 10000;
    if (cr >= 100000) return `₹${(cr / 100000).toFixed(1)} L Cr`;
    if (cr >= 1000)   return `₹${cr.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
    return `₹${cr.toFixed(1)} Cr`;
  }
  // count or transactions
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return String(value);
}

// ── Category mapping ───────────────────────────────────────────────────────────

export const CATEGORY_SHORT_TO_FULL: Record<string, string> = {
  PSB:      "Public Sector Banks",
  Private:  "Private Sector Banks",
  Foreign:  "Foreign Banks",
  SFB:      "Small Finance Banks",
  Payments: "Payment Banks",
};

export const CATEGORY_FULL_TO_SHORT: Record<string, string> = {
  "Public Sector Banks":  "PSB",
  "Private Sector Banks": "Private",
  "Foreign Banks":        "Foreign",
  "Small Finance Banks":  "SFB",
  "Payment Banks":        "Payments",
};

// ── buildSectionData ───────────────────────────────────────────────────────────

export function buildSectionData(
  rows:   AtmPosRow[],
  metric: string | string[],
  filter: FilterState,
): SectionData {
  const metrics    = Array.isArray(metric) ? metric : [metric];
  const sortedDates = getAvailableDates(rows);

  // Determine series names and how to aggregate
  type SeriesAgg = { name: string; getValue: (date: string) => number };
  const series: SeriesAgg[] = [];

  // Total series — used as the first chip in every mode
  const totalSeries: SeriesAgg = {
    name: "Total",
    getValue: (date) =>
      rows
        .filter((r) => r.report_date === date && r.record_type === "total" && metrics.includes(r.metric))
        .reduce((s, r) => s + (r.value || 0), 0),
  };

  if (filter.mode === "all") {
    series.push(totalSeries);
  } else if (filter.mode === "by_type") {
    series.push(totalSeries);
    for (const shortLabel of ["PSB", "Private", "Foreign", "SFB", "Payments"]) {
      const fullCat = CATEGORY_SHORT_TO_FULL[shortLabel] ?? shortLabel;
      series.push({
        name: shortLabel,
        getValue: (date) =>
          rows
            .filter(
              (r) =>
                r.report_date === date &&
                r.record_type === "bank" &&
                r.bank_category === fullCat &&
                metrics.includes(r.metric),
            )
            .reduce((s, r) => s + (r.value || 0), 0),
      });
    }
  } else if (filter.mode === "individual") {
    series.push(totalSeries);
    for (const bank of filter.selectedBanks) {
      series.push({
        name: bank,
        getValue: (date) =>
          rows
            .filter(
              (r) =>
                r.report_date === date &&
                r.record_type === "bank" &&
                r.bank_name === bank &&
                metrics.includes(r.metric),
            )
            .reduce((s, r) => s + (r.value || 0), 0),
      });
    }
  } else if (filter.mode === "top_n") {
    series.push(totalSeries);
    // Rank banks by latest date total value
    const latestDate = sortedDates[sortedDates.length - 1];
    const bankTotals: Map<string, number> = new Map();
    rows
      .filter((r) => r.report_date === latestDate && r.record_type === "bank" && metrics.includes(r.metric))
      .forEach((r) => {
        bankTotals.set(r.bank_name, (bankTotals.get(r.bank_name) ?? 0) + (r.value || 0));
      });
    const topBanks = Array.from(bankTotals.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, filter.topN)
      .map(([name]) => name);
    for (const bank of topBanks) {
      series.push({
        name: bank,
        getValue: (date) =>
          rows
            .filter(
              (r) =>
                r.report_date === date &&
                r.record_type === "bank" &&
                r.bank_name === bank &&
                metrics.includes(r.metric),
            )
            .reduce((s, r) => s + (r.value || 0), 0),
      });
    }
  }

  // Build per-date values map: seriesName → date → value
  const valMap: Map<string, Map<string, number>> = new Map();
  for (const s of series) {
    const dateMap = new Map<string, number>();
    for (const date of sortedDates) {
      dateMap.set(date, s.getValue(date));
    }
    valMap.set(s.name, dateMap);
  }

  const seriesNames = series.map((s) => s.name);

  // absoluteData
  const absoluteData: ChartPoint[] = sortedDates.map((iso) => {
    const point: ChartPoint = {
      date: formatAtmDate(iso),
      _ts:  new Date(iso + "T00:00:00Z").getTime(),
    };
    for (const name of seriesNames) {
      point[name] = valMap.get(name)?.get(iso) ?? null;
    }
    return point;
  });

  // momData
  const momData: ChartPoint[] = sortedDates.map((iso, i) => {
    const point: ChartPoint = {
      date: formatAtmDate(iso),
      _ts:  new Date(iso + "T00:00:00Z").getTime(),
    };
    for (const name of seriesNames) {
      if (i === 0) {
        point[name] = null;
      } else {
        const prevIso = sortedDates[i - 1];
        const curr    = valMap.get(name)?.get(iso) ?? 0;
        const prev    = valMap.get(name)?.get(prevIso) ?? 0;
        point[name]   = prev !== 0 ? +((curr - prev) / prev * 100).toFixed(2) : null;
      }
    }
    return point;
  });

  return { absoluteData, momData, seriesNames };
}

// ── QoQ computation ────────────────────────────────────────────────────────────

function getQuarterKey(ts: number): string {
  const d = new Date(ts);
  const month = d.getUTCMonth() + 1;
  const year  = d.getUTCFullYear();
  let fy: number, q: number;
  if (month >= 4) {
    fy = year;
    q  = month <= 6 ? 1 : month <= 9 ? 2 : 3;
  } else {
    fy = year - 1;
    q  = 4;
  }
  return `${fy}-Q${q}`;
}

/**
 * Computes QoQ % change for the "Total" series in absoluteData.
 * Stock units (count): end-of-quarter value.
 * Flow units (transactions / rs_thousands): sum of quarter.
 */
export function buildQoQValue(absoluteData: ChartPoint[], unit: string): number | null {
  if (!absoluteData.length) return null;

  const quarterMap = new Map<string, ChartPoint[]>();
  for (const point of absoluteData) {
    const key = getQuarterKey(point._ts as number);
    if (!quarterMap.has(key)) quarterMap.set(key, []);
    quarterMap.get(key)!.push(point);
  }

  const sortedKeys = Array.from(quarterMap.keys()).sort((a, b) => {
    const [afy, aq] = a.split("-Q").map(Number);
    const [bfy, bq] = b.split("-Q").map(Number);
    return afy !== bfy ? afy - bfy : aq - bq;
  });

  if (sortedKeys.length < 2) return null;

  const prevPts = quarterMap.get(sortedKeys[sortedKeys.length - 2])!
    .sort((a, b) => (a._ts as number) - (b._ts as number));
  const currPts = quarterMap.get(sortedKeys[sortedKeys.length - 1])!
    .sort((a, b) => (a._ts as number) - (b._ts as number));

  const isFlow  = unit === "transactions" || unit === "rs_thousands";
  const qVal    = (pts: ChartPoint[]) =>
    isFlow
      ? pts.reduce((s, p) => s + (Number(p["Total"]) || 0), 0)
      : Number(pts[pts.length - 1]["Total"]) || 0;

  const prev = qVal(prevPts);
  const curr = qVal(currPts);
  if (prev === 0) return null;
  return +((curr - prev) / prev * 100).toFixed(1);
}

// ── Section definitions ────────────────────────────────────────────────────────

export type VolVal = "vol" | "val";

export interface SectionDef {
  id:    string;
  title: string;
  icon:  string;
  group: "cc" | "dc" | "infra";
  // simple metric (no vol/val)
  metric?: string | string[];
  unit?:   string;
  // vol+val toggle
  volMetric?: string;
  valMetric?: string;
  volUnit?:   string;
  valUnit?:   string;
}

export const SECTION_DEFS: SectionDef[] = [
  { id: "credit_cards",  title: "Cards Outstanding",      icon: "💳", group: "cc",    metric: "credit_cards",             unit: "count"          },
  { id: "cc_pos",        title: "POS Transactions",        icon: "🏪", group: "cc",    volMetric: "cc_pos_txn_vol",         valMetric: "cc_pos_txn_val",         volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "cc_ecom",       title: "eCommerce Transactions",  icon: "🛒", group: "cc",    volMetric: "cc_ecom_txn_vol",        valMetric: "cc_ecom_txn_val",        volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "cc_atm",        title: "ATM Cash Withdrawals",    icon: "🏧", group: "cc",    volMetric: "cc_atm_withdrawal_vol",  valMetric: "cc_atm_withdrawal_val",  volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "cc_other",      title: "Other Transactions",      icon: "💳", group: "cc",    volMetric: "cc_other_txn_vol",       valMetric: "cc_other_txn_val",       volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "debit_cards",   title: "Cards Outstanding",       icon: "💳", group: "dc",    metric: "debit_cards",              unit: "count"          },
  { id: "dc_atm",        title: "ATM Cash Withdrawals",    icon: "🏧", group: "dc",    volMetric: "dc_atm_withdrawal_vol",  valMetric: "dc_atm_withdrawal_val",  volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "dc_pos",        title: "POS Transactions",        icon: "🏪", group: "dc",    volMetric: "dc_pos_txn_vol",         valMetric: "dc_pos_txn_val",         volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "dc_ecom",       title: "eCommerce Transactions",  icon: "🛒", group: "dc",    volMetric: "dc_ecom_txn_vol",        valMetric: "dc_ecom_txn_val",        volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "dc_pos_wd",     title: "POS Cash Withdrawals",    icon: "💳", group: "dc",    volMetric: "dc_pos_withdrawal_vol",  valMetric: "dc_pos_withdrawal_val",  volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "dc_other",      title: "Other Transactions",      icon: "💳", group: "dc",    volMetric: "dc_other_txn_vol",       valMetric: "dc_other_txn_val",       volUnit: "transactions", valUnit: "rs_thousands" },
  { id: "pos_terminals", title: "POS Terminals",           icon: "🏪", group: "infra", metric: "pos_terminals",             unit: "count"          },
  { id: "upi_qr",        title: "UPI QR Codes",            icon: "📱", group: "infra", metric: "upi_qr",                   unit: "count"          },
  { id: "atms",          title: "ATMs (On-site + Off-site)", icon: "🏧", group: "infra", metric: ["atm_onsite", "atm_offsite"], unit: "count"      },
  { id: "micro_atms",    title: "Micro ATMs",              icon: "📱", group: "infra", metric: "micro_atms",               unit: "count"          },
  { id: "bharat_qr",     title: "Bharat QR Codes",         icon: "📱", group: "infra", metric: "bharat_qr",                unit: "count"          },
];

export const GROUP_LABELS: Record<string, string> = {
  cc:    "CREDIT CARD",
  dc:    "DEBIT CARD",
  infra: "DIGITAL INFRASTRUCTURE",
};

export const GROUP_ICONS: Record<string, string> = {
  cc:    "💳",
  dc:    "🏧",
  infra: "📡",
};

// ── getTopNBanks ───────────────────────────────────────────────────────────────

export function getTopNBanks(rows: AtmPosRow[], metric: string | string[], n: number): string[] {
  const metrics    = Array.isArray(metric) ? metric : [metric];
  const latestDate = getAvailableDates(rows).slice(-1)[0];
  if (!latestDate) return [];
  const bankTotals = new Map<string, number>();
  rows
    .filter((r) => r.report_date === latestDate && r.record_type === "bank" && metrics.includes(r.metric))
    .forEach((r) => { bankTotals.set(r.bank_name, (bankTotals.get(r.bank_name) ?? 0) + (r.value || 0)); });
  return Array.from(bankTotals.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([name]) => name);
}
