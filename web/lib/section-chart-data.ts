/**
 * Section chart data layer — lightweight slice of report data for sparklines.
 *
 * Returns a Map<sectionId, SectionChartSlice> for any pipeline.
 * SIBC: loads from rbi_sibc.ts (full report, CSV fetch — browser-cached after
 *       first dashboard visit)
 * ATM/POS: stub returning empty map — extend when ATM/POS opportunities exist
 *
 * Usage:
 *   const charts = await loadSectionChartMap();
 *   const slice  = charts.get("bankCredit");   // → { absoluteData, seriesNames }
 */

import type { ChartPoint } from "@/lib/types";

// ── Public types ──────────────────────────────────────────────────────────────

export interface SectionChartSlice {
  absoluteData: ChartPoint[];
  seriesNames:  string[];
}

/** Keyed by pipeline:sectionId — avoids collisions when ATM/POS opps land. */
export type SectionChartMap = Map<string, SectionChartSlice>;

/** Canonical key for a given opportunity. */
export function chartKey(pipeline: string, sectionId: string): string {
  return `${pipeline}:${sectionId}`;
}

// ── SIBC loader ───────────────────────────────────────────────────────────────

async function loadSibcChartMap(): Promise<SectionChartMap> {
  // Dynamic import avoids pulling the full rbi_sibc module into the initial
  // bundle for pages that don't need it.
  const { loadReport } = await import("@/lib/reports/rbi_sibc");
  const report = await loadReport();
  const map: SectionChartMap = new Map();
  for (const section of report.sections) {
    map.set(chartKey("sibc", section.id), {
      absoluteData: section.absoluteData,
      seriesNames:  section.seriesNames,
    });
  }
  return map;
}

// ── ATM/POS loader (stub — extend when ATM/POS opportunities are authored) ───

async function loadAtmPosChartMap(): Promise<SectionChartMap> {
  // When ATM/POS opportunities land, import the ATM/POS report loader here
  // and build the map the same way as SIBC.
  return new Map();
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
