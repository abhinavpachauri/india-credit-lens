// ── India Credit Lens — Data Layer ────────────────────────────────────────────
// Parses RBI SIBC consolidated CSV and exposes typed helpers

import Papa from "papaparse";

export interface CreditRow {
  report_date:             string;
  statement:               string;   // "Statement 1" | "Statement 2"
  code:                    string;   // hierarchical code e.g. "1", "2.1", "I"
  sector:                  string;
  level:                   number;   // -1 / 0 / 1 / 2 / 3
  is_priority_sector_memo: boolean;
  parent_code:             string;
  parent_statement:        string;
  date:                    string;   // observation date YYYY-MM-DD (may be relabelled)
  outstanding_cr:          number | null;
  source_date:             string;   // original publication date if relabelled, else ""
}

// ── Fetch + parse the public CSV ──────────────────────────────────────────────
let _cache: CreditRow[] | null = null;

export async function loadData(): Promise<CreditRow[]> {
  if (_cache) return _cache;

  const res = await fetch("/data/rbi_sibc_consolidated.csv");
  const text = await res.text();

  const result = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: true,
  });

  _cache = result.data.map((r) => ({
    report_date:             r.report_date ?? "",
    statement:               r.statement   ?? "",
    code:                    String(r.code ?? ""),
    sector:                  r.sector      ?? "",
    level:                   Number(r.level ?? 0),
    is_priority_sector_memo: r.is_priority_sector_memo === "True" || r.is_priority_sector_memo === "true",
    parent_code:             String(r.parent_code ?? ""),
    parent_statement:        r.parent_statement ?? "",
    date:                    r.date         ?? "",
    outstanding_cr:          r.outstanding_cr === "" || r.outstanding_cr == null
                               ? null
                               : Number(r.outstanding_cr),
    source_date:             r.source_date ?? "",
  }));

  return _cache;
}

// ── Sorted unique observation dates ──────────────────────────────────────────
export function uniqueDates(rows: CreditRow[]): string[] {
  return [...new Set(rows.map((r) => r.date))].sort();
}

// ── Filter rows by codes (Statement 1, non-PSL by default) ───────────────────
export function rowsForCodes(
  rows: CreditRow[],
  codes: string[],
  opts: { psl?: boolean; stmt?: string } = {}
): CreditRow[] {
  return rows.filter(
    (r) =>
      codes.includes(r.code) &&
      r.is_priority_sector_memo === (opts.psl ?? false) &&
      (opts.stmt ? r.statement === opts.stmt : true)
  );
}

// ── Get children of a parent code ─────────────────────────────────────────────
export function childrenOf(
  rows: CreditRow[],
  parentCode: string,
  opts: { stmt?: string; psl?: boolean } = {}
): { codes: string[]; labels: Record<string, string> } {
  const children = rows.filter(
    (r) =>
      r.parent_code === parentCode &&
      r.is_priority_sector_memo === (opts.psl ?? false) &&
      (opts.stmt ? r.statement === opts.stmt : true)
  );
  const codes = [...new Set(children.map((r) => r.code))];
  const labels: Record<string, string> = {};
  children.forEach((r) => { labels[r.code] = r.sector; });
  return { codes, labels };
}

// ── Build chart-friendly series: [{date, [code]: value}] ─────────────────────
export interface ChartPoint {
  date: string;
  [code: string]: string | number | null;
}

export function buildSeries(
  rows: CreditRow[],
  codes: string[],
  labels: Record<string, string>,
  opts: { psl?: boolean; stmt?: string } = {}
): ChartPoint[] {
  const filtered = rowsForCodes(rows, codes, opts);
  // Use only dates where this section has actual data — avoids phantom null
  // points from other sections (e.g. Statement 2 Feb dates appearing in a
  // Statement 1 section's timeline and breaking connectNulls behaviour).
  const dates = uniqueDates(filtered);

  return dates.map((date) => {
    // Check if any row for this date has a source_date (delayed-publication relabelling)
    const sourceRow = filtered.find((r) => r.date === date && r.source_date);
    const isDelayed = !!sourceRow?.source_date;
    const displayDate = formatDate(date) + (isDelayed ? "*" : "");
    const point: ChartPoint = {
      date:        displayDate,
      _ts:         new Date(date).getTime(),
      ...(isDelayed ? { _sourceDate: formatDate(sourceRow!.source_date) } : {}),
    };
    codes.forEach((code) => {
      const row = filtered.find((r) => r.code === code && r.date === date);
      point[labels[code] ?? code] = row?.outstanding_cr ?? null;
    });
    return point;
  });
}

// ── Build growth series (YoY) ─────────────────────────────────────────────────
export function buildGrowthSeries(
  rows: CreditRow[],
  codes: string[],
  labels: Record<string, string>,
  mode: "yoy" | "fy",
  opts: { psl?: boolean; stmt?: string } = {}
): ChartPoint[] {
  const filtered = rowsForCodes(rows, codes, opts);
  // Use only dates where this section has actual data — same reason as buildSeries.
  // This prevents null growth points from other sections' dates (e.g. Statement 2
  // Feb 23rd appearing between Statement 1's Feb* and Mar, breaking the line).
  const dates = uniqueDates(filtered);
  if (dates.length < 2) return [];

  // For YoY: pair each date with the date 12 months prior (or nearest)
  const points: ChartPoint[] = [];

  for (let i = 1; i < dates.length; i++) {
    const currDate = dates[i];
    const currYear  = new Date(currDate).getFullYear();
    const currMonth = new Date(currDate).getMonth();

    let prevDate: string | undefined;
    if (mode === "yoy") {
      // Exact same month, previous calendar year — no fallback
      prevDate = dates.find((d) => {
        const dy = new Date(d).getFullYear();
        const dm = new Date(d).getMonth();
        return dy === currYear - 1 && dm === currMonth;
      });
    } else {
      // FY growth = growth since the most recent March-end (start of current fiscal year).
      // Previous March-end year:
      //   - currMonth >= Apr (3): we're mid-FY, previous March = this calendar year (currYear)
      //   - currMonth < Apr (0,1,2): we're in the Jan–Mar tail, previous March = currYear - 1
      // e.g. Jan 2025 → Mar 2024; Mar 2025 → Mar 2024; Jan 2026 → Mar 2025
      const prevMarchYear = currMonth >= 3 ? currYear : currYear - 1;
      prevDate = dates.find((d) => {
        const dy = new Date(d).getFullYear();
        const dm = new Date(d).getMonth();
        return dy === prevMarchYear && dm === 2; // March = month 2
      });
    }

    // Skip if no valid comparison period exists — emit null rather than a wrong number
    if (!prevDate || prevDate === currDate) continue;

    const sourceRow2 = filtered.find((r) => r.date === currDate && r.source_date);
    const isDelayed2 = !!sourceRow2?.source_date;
    const point: ChartPoint = {
      date: formatDate(currDate) + (isDelayed2 ? "*" : ""),
      _ts:  new Date(currDate).getTime(),
      ...(isDelayed2 ? { _sourceDate: formatDate(sourceRow2!.source_date) } : {}),
    };
    codes.forEach((code) => {
      const curr = filtered.find((r) => r.code === code && r.date === currDate)?.outstanding_cr;
      const prev = filtered.find((r) => r.code === code && r.date === prevDate)?.outstanding_cr;
      if (curr != null && prev != null && prev !== 0) {
        point[labels[code] ?? code] = +((curr / prev - 1) * 100).toFixed(1);
      } else {
        point[labels[code] ?? code] = null;
      }
    });
    points.push(point);
  }
  return points;
}

// ── Priority sector rows ──────────────────────────────────────────────────────
export function prioritySectorCodes(rows: CreditRow[]): { codes: string[]; labels: Record<string, string> } {
  const pslRows = rows.filter((r) => r.is_priority_sector_memo);
  const codes = [...new Set(pslRows.map((r) => r.code))].sort();
  const labels: Record<string, string> = {};
  pslRows.forEach((r) => { labels[r.code] = r.sector; });
  return { codes, labels };
}

// ── Get latest single value for a code ───────────────────────────────────────
export function latestValue(rows: CreditRow[], code: string): number | null {
  const dates = uniqueDates(rows);
  const latest = dates[dates.length - 1];
  const row = rows.find((r) => r.code === code && r.date === latest && !r.is_priority_sector_memo);
  return row?.outstanding_cr ?? null;
}

// ── Format ₹ Crore values ─────────────────────────────────────────────────────
export function formatCr(value: number | null, decimals = 2): string {
  if (value == null) return "—";
  if (Math.abs(value) >= 1e5)  return `₹${(value / 1e5).toFixed(decimals)} L Cr`;
  if (Math.abs(value) >= 1e3)  return `₹${(value / 1e3).toFixed(decimals)} Th Cr`;
  return `₹${value.toFixed(0)} Cr`;
}

export function formatGrowth(value: number | null): string {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

// ── Date display ──────────────────────────────────────────────────────────────
export function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}
