// The type and radius ladders — the one place a size is decided.
//
// A scale lived in globals.css from the beginning, said "use these semantic levels in ALL
// dashboards", and had no consumers: every component picked its own number instead. That is how
// fifteen font sizes accumulated, five of them half-points, on a surface tuned by eye. The scale
// is here now rather than in CSS because a size has two destinations — an inline style, which
// takes a string or a number, and a Recharts prop, which takes only a number. CSS custom
// properties can serve the first and not the second, so a CSS-only scale could never cover the
// charts, and a size the scale cannot express is a size someone will hardcode.
//
// Steps are semantic, not numeric: reach for the ROLE the text plays, not the pixel value you
// want. Adding a step is a design decision — make it here, in the open, or not at all.
// A test (tests/tokens.test.ts) fails on any raw fontSize/borderRadius number outside this file.

/** Font sizes, in px. Ordered smallest to largest; names describe the job, not the size. */
export const FS = {
  /** Uppercase role labels, disclosure carets, tiny badges. */
  micro: 10,
  /** Coverage lines, chart axis ticks, depth hints — present but receding. */
  meta: 11,
  /** Uppercase group headers, chain markers, chart legends. */
  label: 12,
  /** Card meta, chip labels, eyebrows, chart tooltips — the read-mode workhorse. */
  note: 13,
  /** Body text, controls, breadcrumbs, rail rows. */
  body: 14,
  /** Read-card titles and chain steps — a notch above body, below a card title. */
  lead: 15,
  /** Dimension titles, detail body, CTA strip. */
  card: 16,
  /** Section headers in explore mode. */
  section: 18,
  /** The detail pane's title. One per screen. */
  title: 24,
} as const;

/** Corner radii, in px. `full` stays Tailwind's `rounded-full`. */
export const R = {
  /** Badges and the smallest chips. */
  sm: 4,
  /** Cards, chips, tooltips, buttons — the default. */
  md: 8,
  /** Panels and anything that frames other cards. */
  lg: 12,
} as const;

export type FontSize = (typeof FS)[keyof typeof FS];
export type Radius = (typeof R)[keyof typeof R];

// Glyph sizes are a separate axis from type: an arrow or an emoji is sized to sit right next to
// text, not to be read as text. Keeping them out of FS is what stops the type ladder growing a
// step that no sentence will ever use.
export const GLYPH = {
  /** The ‹ › chip-strip scroll arrows. */
  arrow: 20,
  /** The emoji standing in for a dimension on its tile. */
  dimension: 24,
} as const;

// ── The information hierarchy (DASHBOARD_SPEC §22) ──────────────────────────────
// Five levels, the same on every surface: a reader learns them once and every screen reads the
// same way. A component reaches for the LEVEL a piece of text plays, never a size and a weight
// picked separately — that pairing, chosen by eye per component, is how the landing tiles, the
// rail and the row chart each grew their own hierarchy.
type TextRole = { fontSize: number; fontWeight?: number; lineHeight: number; color: string };

export const TEXT = {
  /** L1 — the page or open pane. One per screen. */
  title:   { fontSize: FS.title,   fontWeight: 700, lineHeight: 1.2,  color: "var(--font)" },
  /** L2 — a section inside the pane ("How it moved", "What's notable"); peers share it. */
  section: { fontSize: FS.section, fontWeight: 700, lineHeight: 1.3,  color: "var(--font)" },
  /** L3 — one item: a tile, a notable, a chart's own title. */
  item:    { fontSize: FS.card,    fontWeight: 600, lineHeight: 1.35, color: "var(--font)" },
  /** A section's lead paragraph — the one sentence block a reader should not skip. */
  lead:    { fontSize: FS.card,                     lineHeight: 1.6,  color: "var(--font)" },
  /** Sentences. */
  body:    { fontSize: FS.body,                     lineHeight: 1.55, color: "var(--font)" },
  /** Counts, view labels, footers, sublines — present but receding. */
  meta:    { fontSize: FS.note,                     lineHeight: 1.45, color: "var(--font-muted)" },
} as const satisfies Record<string, TextRole>;
