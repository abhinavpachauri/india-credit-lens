// The standing state band's data layer (DASHBOARD_SPEC.md §16).
//
// The read tier answers "what is news". This answers "what is happening", which is a
// different question and had no answer on the dashboard: in a good month 29 of 96 SIBC
// cards score as reads, in a quiet one none do, and a reader arriving between events was
// handed a directory.
//
// The SENTENCES are rendered in Python (analysis/core/state_lines.py) and shipped as
// strings — this module formats nothing. That is deliberate: a browser that formats
// numbers is a publishing surface no validator can see, and the band is the first place
// the dashboard publishes a Layer-2 reading. Every number in these strings has already
// been traced to a stored signals.db row by gate stage 5.9b.

export type MixState = "steered" | "drifting" | "contested" | "reallocating";

export interface StateBlock {
  dimension:      string;
  cut:            string;        // a dimension can carry two (industry by size AND by type)
  subject:        string;        // the block heading, shown only when a dimension has >1 cut
  speed:          string | null; // Layer 1 — how fast the parent is growing
  speed_short:    string | null; // the same reading, tile-sized — also rendered in Python
  speed_dir:      "up" | "down" | null;  // the tile glyph, from the sign of the rate
  mix:            string | null; // Layer 2 — whether the mix is being steered
  // Why a row is empty, when it is. The band always renders both lines: a standing element
  // that silently loses a row is indistinguishable from a broken one, and "priority sector
  // has no published total" is a fact about the data worth stating once a month.
  no_speed_note:  string | null;
  no_mix_note:    string | null;
  mix_state:      MixState | null;
  toward:         string | null;
  toward_entity:  string | null;
  source_signals: string[];
}

export type StateMap = Record<string, StateBlock[]>;

export async function loadStateBands(pipeline: "sibc" | "atm_pos"): Promise<StateMap> {
  const res = await fetch(`/data/${pipeline}_state.json`);
  if (!res.ok) return {};
  const doc = await res.json();
  return (doc?.dimensions ?? {}) as StateMap;
}

/** The tile form of the mix: two labels, no number — so this one is safe to compose here. */
export function tileMix(block: StateBlock): string | null {
  if (!block.mix_state) return null;
  return block.toward ? `${block.mix_state} → ${block.toward}` : block.mix_state;
}
