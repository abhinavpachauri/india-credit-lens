// The Layer 1 cut table (DASHBOARD_SPEC §17, reshaped by §20) — loader + types.
//
// Every number arrives ALREADY RENDERED. `display` is drawn; `sort` orders and is never
// shown. The browser formats nothing, for the same reason the state band ships strings:
// a surface that formats its own numbers is a publishing surface no validator can see.
//
// A cell is the LATEST READING of a stored series, which is what makes §20 possible: the
// cell can open its own chart, so the sparkline column disappears (it was one series
// printed as text) and so does the Numbers/Chart toggle.

export interface Cell {
  display: string;
  sort: number | null;
  /** The whole stored history, aligned to the column's period list; null where a part has
   *  no reading that period, so a late arrival never slides its history a month left. */
  series?: (number | null)[] | null;
  /** The same readings, rendered in Python — what the panel quotes. */
  series_display?: (string | null)[] | null;
}

/** The columns a row carries, in the order the table draws them. */
export const COLUMNS = ["size", "of_cut", "of_book", "growth", "pace", "new"] as const;
export type ColKey = typeof COLUMNS[number];

export interface CutRow {
  entity:  string | null;      // null = the cut's own row
  size:    Cell | null;
  of_cut:  Cell | null;        // null on the total row — a whole is not a share of itself
  of_book: Cell | null;
  growth:  Cell | null;
  pace:    Cell | null;
  new:     Cell | null;
  /** The cut this part decomposes into, when it has one (§19) — resolved in Python. */
  sub_cut?: string | null;
}

export interface CutTable {
  cut: string;
  /** "New" or "Of fall" — a share of the NET, and the net can be negative. */
  flow_label: string;
  parts: CutRow[];
  total: CutRow;
  /** Axis labels per column: a column's depth is its OWN (payments stores 31 readings of a
   *  level and 19 of its YoY, because a rate cannot exist until a year has passed). */
  periods?: Partial<Record<ColKey, string[]>>;
  parent_periods?: Partial<Record<ColKey, string[]>>;
  /** Which signal each column is — declared, so the gate can scope a cell to its column. */
  columns?: Partial<Record<ColKey, string>>;
  /** The CSV metric a payments cut measures, declared in Python. The adapter matches on THIS
   *  rather than reconstructing a stem from the metric name — a spelling that was right for
   *  23 cuts and wrong for the three group anchors, which reached no surface at all. */
  metric?: string;
  source_signals: string[];
}

export type CutTables = Record<string, CutTable>;

export async function loadCutTables(pipeline: "sibc" | "atm_pos"): Promise<CutTables> {
  try {
    const res = await fetch(`/data/${pipeline}_table.json`);
    if (!res.ok) return {};
    return ((await res.json()) as { cuts?: CutTables }).cuts ?? {};
  } catch {
    return {};                 // a missing sidecar hides the table; it never breaks the page
  }
}

export type SortKey = ColKey;
export type SortDir = "desc" | "asc";

/** Sorting is free: `sort` already exists on every cell for exactly this, so the only
 *  decision left is what a missing value does. It SINKS, in both directions — a column the
 *  data cannot fill must never lead the table (Infrastructure's whole flow column is "—"
 *  because its mix is contested, and a table led by dashes says nothing). */
export function sortParts(parts: CutRow[], key: SortKey, dir: SortDir = "desc"): CutRow[] {
  const sign = dir === "desc" ? 1 : -1;
  return [...parts].sort((a, b) => {
    const av = a[key]?.sort, bv = b[key]?.sort;
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return (bv - av) * sign;
  });
}

/** The readings behind one cell, paired with their axis labels — what the side panel draws. */
export function cellSeries(table: CutTable, row: CutRow, col: ColKey):
    { label: string; value: number | null; display: string | null }[] {
  const cell = row[col];
  const labels = (row.entity === null ? table.parent_periods : table.periods)?.[col];
  if (!cell?.series || !labels || labels.length !== cell.series.length) return [];
  return cell.series.map((v, i) => ({
    label: labels[i], value: v, display: cell.series_display?.[i] ?? null,
  }));
}
