// ── New Report Template ───────────────────────────────────────────────────────
// Copy this file, rename it to your report id (e.g. crif_women.ts),
// fill in every TODO, then register in lib/reports/index.ts.
//
// Steps:
//   1. cp _template.ts crif_women.ts
//   2. Add your CSV to public/data/
//   3. Implement loadRows() — parse your CSV into your report-specific row type
//   4. Implement buildSections() — produce ReportSection[] from your rows
//   5. Register: REPORTS["crif_women"] = loadReport in lib/reports/index.ts
//   6. Run `npm run dev` — TypeScript will tell you if anything is wrong

import type { Report, ReportSection, ChartPoint } from "@/lib/types";

// ── 1. Define your report-specific row type ───────────────────────────────────

interface TemplateRow {
  date:    string;
  segment: string;  // TODO: replace with your actual column names
  value:   number | null;
}

// ── 2. Load and parse your CSV ────────────────────────────────────────────────

async function loadRows(): Promise<TemplateRow[]> {
  // TODO: fetch your CSV from /data/your_file.csv
  // TODO: parse with PapaParse (see lib/data.ts for example)
  return [];
}

// ── 3. Build chart-ready sections ─────────────────────────────────────────────

export function buildSections(_rows: TemplateRow[]): ReportSection[] {
  // TODO: group rows by segment, build ChartPoint[] for each section

  const exampleSection: ReportSection = {
    id:          "TODO_section_id",
    title:       "TODO Section Title",
    icon:        "📊",
    accentIndex: 0,
    absoluteData: [],   // TODO: ChartPoint[] — [{date, "Series A": value, ...}]
    growthData:   [],   // TODO: ChartPoint[] — [{date, "Series A": yoyPct, ...}]
    fyData:       [],   // TODO: ChartPoint[] — [{date, "Series A": fyPct, ...}]
    seriesNames:  [],   // TODO: ["Series A", "Series B", ...]
    pctLabel:    "% Share",
    annotations: { insights: [], gaps: [], opportunities: [] },
  };

  return [exampleSection].filter((s) => s.absoluteData.length > 0);
}

// ── 4. Export loadReport — this is the only public API ───────────────────────

export async function loadReport(): Promise<Report> {
  const rows     = await loadRows();
  // TODO: derive the latest date from your rows
  const dataDate = "TODO_YYYY-MM-DD";

  return {
    id:              "TODO_report_id",      // e.g. "crif_women_jan2026"
    title:           "TODO Report Title",
    source:          "TODO Source Name",
    dataDate,
    latestDate:      "TODO formatted date", // e.g. "Jan 2026"
    totalBankCredit: null,                  // null if not applicable to this report
    sections:        buildSections(rows),
  };
}
