"use client";

// ── Types ──────────────────────────────────────────────────────────────────────

// Compact precomputed chart series (compute-once, ship-compact). Replaces the
// 4.6 MB raw CSV + client-side PapaParse + 47k-row per-series filtering. Built by
// analysis/generate_chart_series.py → web/public/data/atm_pos_chart_series.json.
export interface AtmPosSeries {
  _meta: { pipeline: string; periods: string[]; entity_count: number; metric_count: number };
  entities: { name: string; category: string }[];
  // metric → { total: [v per period], entity: [[v per period] aligned with entities] }
  series: Record<string, { total: number[]; entity: number[][] }>;
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
  yoyData:      ChartPoint[];   // YoY % — null when no same-month year-ago point
  seriesNames:  string[];
}

// ── CSV cache ──────────────────────────────────────────────────────────────────

let _cache: AtmPosSeries | null = null;

export async function loadAtmPosData(): Promise<AtmPosSeries> {
  if (_cache) return _cache;
  const res = await fetch("/data/atm_pos_chart_series.json");
  _cache = (await res.json()) as AtmPosSeries;
  return _cache;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

export function getAllBanks(series: AtmPosSeries): string[] {
  return series.entities.map((e) => e.name).sort();
}

export function getAvailableDates(series: AtmPosSeries): string[] {
  return series._meta.periods;   // already sorted by the generator
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
  s:      AtmPosSeries,
  metric: string | string[],
  filter: FilterState,
): SectionData {
  const metrics     = Array.isArray(metric) ? metric : [metric];
  const sortedDates = s._meta.periods;            // already sorted
  const np          = sortedDates.length;
  const nE          = s.entities.length;

  // Sum the requested metric(s) into a Total array + per-entity matrix — cheap
  // index math over the precomputed series, no row filtering.
  const total: number[]    = new Array(np).fill(0);
  const entity: number[][] = s.entities.map(() => new Array(np).fill(0));
  for (const m of metrics) {
    const ms = s.series[m];
    if (!ms) continue;
    for (let p = 0; p < np; p++) total[p] += ms.total[p] || 0;
    for (let e = 0; e < nE; e++) {
      const row = ms.entity[e];
      if (!row) continue;
      for (let p = 0; p < np; p++) entity[e][p] += row[p] || 0;
    }
  }

  // Pick which series to plot by filter mode → {name, values[]}.
  const picked: { name: string; values: number[] }[] = [{ name: "Total", values: total }];

  if (filter.mode === "by_type") {
    for (const shortLabel of ["PSB", "Private", "Foreign", "SFB", "Payments"]) {
      const fullCat = CATEGORY_SHORT_TO_FULL[shortLabel] ?? shortLabel;
      const vals = new Array(np).fill(0);
      s.entities.forEach((ent, e) => {
        if (ent.category === fullCat) for (let p = 0; p < np; p++) vals[p] += entity[e][p];
      });
      picked.push({ name: shortLabel, values: vals });
    }
  } else if (filter.mode === "individual") {
    for (const bank of filter.selectedBanks) {
      const e = s.entities.findIndex((x) => x.name === bank);
      picked.push({ name: bank, values: e >= 0 ? entity[e] : new Array(np).fill(0) });
    }
  } else if (filter.mode === "top_n") {
    const latest = np - 1;
    s.entities
      .map((ent, e) => ({ name: ent.name, e, v: entity[e][latest] }))
      .sort((a, b) => b.v - a.v)
      .slice(0, filter.topN)
      .forEach((r) => picked.push({ name: r.name, values: entity[r.e] }));
  }
  // mode "all" → Total only (already pushed)

  // Per-date value map (preserves the downstream chart builders verbatim).
  const valMap: Map<string, Map<string, number>> = new Map();
  for (const ser of picked) {
    const dateMap = new Map<string, number>();
    sortedDates.forEach((d, p) => dateMap.set(d, ser.values[p]));
    valMap.set(ser.name, dateMap);
  }

  const seriesNames = picked.map((p) => p.name);

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

  // yoyData — same month one year earlier (seasonally clean)
  // Index sortedDates by "YYYY-MM" so we can resolve the year-ago period even
  // when month-end days differ (28/29/30/31) or a month is missing.
  const isoByMonth = new Map<string, string>();
  for (const iso of sortedDates) isoByMonth.set(iso.slice(0, 7), iso);

  const yoyData: ChartPoint[] = sortedDates.map((iso) => {
    const point: ChartPoint = {
      date: formatAtmDate(iso),
      _ts:  new Date(iso + "T00:00:00Z").getTime(),
    };
    const [y, m]    = iso.slice(0, 7).split("-");
    const priorKey  = `${Number(y) - 1}-${m}`;
    const priorIso  = isoByMonth.get(priorKey);
    for (const name of seriesNames) {
      if (!priorIso) {
        point[name] = null;
      } else {
        const curr = valMap.get(name)?.get(iso) ?? 0;
        const prev = valMap.get(name)?.get(priorIso) ?? 0;
        point[name] = prev !== 0 ? +((curr - prev) / prev * 100).toFixed(2) : null;
      }
    }
    return point;
  });

  return { absoluteData, momData, yoyData, seriesNames };
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

// Left-border accent colour per group — mirrors SectionCard accent pattern
export const GROUP_ACCENT: Record<string, string> = {
  cc:    "#4e8ef7",   // blue
  dc:    "#2ca02c",   // green
  infra: "#f0912a",   // orange
};

// ── getTopNBanks ───────────────────────────────────────────────────────────────

export function getTopNBanks(s: AtmPosSeries, metric: string | string[], n: number): string[] {
  const metrics = Array.isArray(metric) ? metric : [metric];
  const latest  = s._meta.periods.length - 1;
  if (latest < 0) return [];
  return s.entities
    .map((ent, e) => {
      let v = 0;
      for (const m of metrics) v += s.series[m]?.entity[e]?.[latest] || 0;
      return { name: ent.name, v };
    })
    .sort((a, b) => b.v - a.v)
    .slice(0, n)
    .map((x) => x.name);
}
