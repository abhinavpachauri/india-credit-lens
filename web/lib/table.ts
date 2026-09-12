// The Layer 1 cut table (DASHBOARD_SPEC §17) — loader + types.
//
// Every number arrives ALREADY RENDERED. `display` is drawn; `sort` orders and is never
// shown. The browser formats nothing, for the same reason the state band ships strings:
// a surface that formats its own numbers is a publishing surface no validator can see.

export interface Cell { display: string; sort: number | null }

export interface CutRow {
  entity:  string | null;      // null = the cut's own row
  size:    Cell | null;
  of_cut:  Cell | null;        // null on the total row — a whole is not a share of itself
  of_book: Cell | null;
  growth:  Cell | null;
  pace:    Cell | null;
  new:     Cell | null;
  run:     number[];           // trailing growth readings, oldest first
}

export interface CutTable {
  cut: string;
  /** "New" or "Of fall" — a share of the NET, and the net can be negative. */
  flow_label: string;
  parts: CutRow[];
  total: CutRow;
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

/** Sort keys, in the order the header offers them. Size first: the reader's model is
 *  "biggest first", and a growth-sorted table leads with the smallest book on the page. */
export type SortKey = "size" | "growth" | "new";

export function sortParts(parts: CutRow[], key: SortKey): CutRow[] {
  return [...parts].sort((a, b) => {
    const av = a[key]?.sort, bv = b[key]?.sort;
    if (av == null && bv == null) return 0;
    if (av == null) return 1;              // a part with no value sinks, never leads
    if (bv == null) return -1;
    return bv - av;
  });
}
