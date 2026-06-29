/**
 * Section chart data layer — full chart slice for opportunity cards.
 *
 * Returns a Map<pipeline:sectionId, SectionChartSlice> for any pipeline.
 * SIBC: loads from rbi_sibc.ts (full report, CSV fetch — browser-cached after
 *       first dashboard visit)
 * ATM/POS: stub returning empty map — extend when ATM/POS opportunities exist
 *
 * Usage:
 *   const charts = await loadSectionChartMap();
 *   const slice  = charts.get(chartKey("sibc", "bankCredit"));
 */

import type { ChartPoint } from "@/lib/types";

// ── Public types ──────────────────────────────────────────────────────────────

export interface SectionChartSlice {
  absoluteData:             ChartPoint[];
  growthData:               ChartPoint[];
  fyData:                   ChartPoint[];
  seriesNames:              string[];
  distributionSeriesNames?: string[];   // subset used by distribution chart
  pctLabel:                 string;
  variant?:                 "sibc" | "atm_pos";   // atm_pos: growthData is MoM, no FY
}

/** Keyed by pipeline:sectionId — avoids collisions across pipelines. */
export type SectionChartMap = Map<string, SectionChartSlice>;

/** Canonical lookup key for a given opportunity. */
export function chartKey(pipeline: string, sectionId: string): string {
  return `${pipeline}:${sectionId}`;
}

// ── SIBC loader ───────────────────────────────────────────────────────────────

async function loadSibcChartMap(): Promise<SectionChartMap> {
  const { loadReport } = await import("@/lib/reports/rbi_sibc");
  const report = await loadReport();
  const map: SectionChartMap = new Map();
  for (const section of report.sections) {
    map.set(chartKey("sibc", section.id), {
      absoluteData:            section.absoluteData,
      growthData:              section.growthData,
      fyData:                  section.fyData,
      seriesNames:             section.seriesNames,
      distributionSeriesNames: section.distributionSeriesNames,
      pctLabel:                section.pctLabel,
    });
  }
  return map;
}

// ── ATM/POS loader (stub — extend when ATM/POS opportunities are authored) ───

async function loadAtmPosChartMap(): Promise<SectionChartMap> {
  const { loadAtmPosData, buildSectionData } = await import("@/lib/atm_pos_data");
  const series = await loadAtmPosData();
  const map: SectionChartMap = new Map();
  // headline metric per opportunity group; charted as Total + by bank-type over time
  const GROUP_METRIC: Record<string, string> = {
    cc: "credit_cards", dc: "debit_cards", infra: "pos_terminals",
  };
  const filter = {
    mode: "by_type" as const,
    selectedTypes: ["PSB", "Private", "Foreign", "SFB", "Payments"],
    selectedBanks: [] as string[],
    topN: 5,
  };
  for (const [group, metric] of Object.entries(GROUP_METRIC)) {
    const sd = buildSectionData(series, metric, filter);
    map.set(chartKey("atm_pos", group), {
      absoluteData:            sd.absoluteData,
      growthData:              sd.momData,   // MoM % (no YoY/FY for the payments slice)
      fyData:                  [],
      seriesNames:             sd.seriesNames,
      distributionSeriesNames: sd.seriesNames,
      pctLabel:                "% of Total",
      variant:                 "atm_pos",
    });
  }
  return map;
}

// ── Public API ────────────────────────────────────────────────────────────────

let _cache: SectionChartMap | null = null;

/**
 * Load all section chart data across both pipelines.
 * Result is cached for the page lifetime — safe to call multiple times.
 */
export async function loadSectionChartMap(): Promise<SectionChartMap> {
  if (_cache) return _cache;
  const [sibc, atmPos] = await Promise.all([
    loadSibcChartMap(),
    loadAtmPosChartMap(),
  ]);
  _cache = new Map([...sibc, ...atmPos]);
  return _cache;
}
