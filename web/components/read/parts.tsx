"use client";

// Shared read-mode primitives (DASHBOARD_SPEC.md §14). The design lives HERE, once — SIBC and
// payments both render these; only the data model (below) + the chart/deep renderers differ per
// pipeline. Colour = section/group (a card's colour is also its chart-line colour).

import React from "react";
import {
  sortParts as sortPartsMemo, cellSeries, COLUMNS,
  type ColKey, type SortKey, type SortDir,
} from "@/lib/table";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { pickColor } from "@/lib/theme";
import { FS, R, GLYPH } from "@/lib/tokens";
import { tileMix, type StateBlock } from "@/lib/state";

export type ReadReason = "record" | "reversal" | "surge" | "shift";
export type Direction = "up" | "down" | "flat";

// ── the pipeline-agnostic model an adapter builds ──────────────────────────────
export interface RMCard {
  id: string;
  title: string;
  body?: string;
  implication?: string;
  chain?: string[];
  dimId: string;          // which dimension this card belongs to
  isRead: boolean;        // a "mover" — gets the ▲ marker in the rail
}
export interface RMSubject { name: string; cards: RMCard[] }
export interface RMDimension {
  id: string;
  title: string;
  icon: string;
  color: string;
  cardCount: number;
  moved: number;
  subjects: RMSubject[];
  compositionTitles: string[];   // structural cards → the composition caption
}
export interface RMRead {
  id: string;             // card id
  title: string;
  dimId: string;
  dimTitle: string;
  color: string;
  reason: ReadReason | null;
  direction: Direction | null;
  mode: string;           // display label of the card's chart view (e.g. "YoY")
}
export interface RMModel { reads: RMRead[]; dimensions: RMDimension[] }

// ── styling ────────────────────────────────────────────────────────────────────
// Card visuals live in CSS so :hover applies (inline border/box-shadow win specificity and kill it).
// Dynamic bits come in as the --sec (section colour) / --sel (selected tint) custom props.
// The colour spine is drawn INSIDE the card's box, so a card that wants even optical padding
// has to add the spine's width back on the left. Naming it keeps that arithmetic legible.
export const SPINE = 3;

export const STYLE = `
@keyframes rmfade{from{opacity:0}to{opacity:1}}
.rm-card{border:1px solid var(--border-card);box-shadow:inset 3px 0 0 var(--sec);background:var(--bg-card);transition:box-shadow .12s ease,border-color .12s ease,transform .12s ease}
.rm-card:hover{border-color:var(--sec);box-shadow:inset 3px 0 0 var(--sec),0 4px 14px var(--shadow)}
.rm-card.sel{border-color:var(--sec);background:var(--sel)}
.rm-tile:hover{transform:translateY(-2px)}
.rm-flat{border:1px solid var(--border-card);background:transparent;transition:box-shadow .12s ease,border-color .12s ease}
.rm-flat:hover{border-color:var(--sec);box-shadow:0 2px 8px var(--shadow)}
.rm-flat.sel{border-color:var(--sec);background:var(--sel)}
.rm-chip{border:1px solid var(--sec);background:var(--bg-card);color:var(--font);transition:background .12s ease,color .12s ease}
.rm-chip:hover{background:var(--sel)}
.rm-chip.on{background:var(--sec);color:#fff}
.rm-chip.on:hover{background:var(--sec)}
.rm-strip{scrollbar-width:none}
.rm-strip::-webkit-scrollbar{display:none}
.rm-link{transition:color .12s ease}
.rm-link:hover{color:var(--font)}
.rm-row:hover{background:var(--sel)}
`;

export const PANEL: React.CSSProperties = {
  background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: R.lg, padding: 18,
};
export const EYEBROW: React.CSSProperties = {
  fontSize: FS.note, fontWeight: 600, letterSpacing: "0.06em", color: "var(--font-muted)", textTransform: "uppercase",
};
export const READS_COLOR = "#4e8ef7";

export const REASON: Record<ReadReason, string> = { record: "record", reversal: "reversal", surge: "surge", shift: "shift" };
export const glyph = (d: Direction | null) => (d === "up" ? "▲" : d === "down" ? "▼" : "•");

export function tint(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}
export function vars(col: string, sel?: string): React.CSSProperties {
  return { ["--sec" as string]: col, ["--sel" as string]: sel ?? "transparent" } as React.CSSProperties;
}
export function chipStyle(active: boolean): React.CSSProperties {
  return {
    background: active ? "#4e8ef7" : "var(--bg-page)",
    color: active ? "#fff" : "var(--font-muted)",
    border: `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`,
  };
}

// ── presentational components ──────────────────────────────────────────────────

export function ReadCard({ read, selected, onClick }: { read: RMRead; selected: boolean; onClick: () => void }) {
  const col = read.color;
  return (
    <button onClick={onClick} className={`rm-card w-full h-full text-left rounded-xl${selected ? " sel" : ""}`}
            style={{ ...vars(col, tint(col, 0.08)), padding: `12px 16px 12px ${16 + SPINE}px` }}>
      <div style={{ fontSize: FS.lead, fontWeight: 600, lineHeight: 1.35, color: "var(--font)" }}>{read.title}</div>
      <div className="flex items-center gap-1.5 mt-1.5" style={{ fontSize: FS.note, color: "var(--font-muted)" }}>
        <span style={{ color: col }}>{glyph(read.direction)}</span>
        {read.reason && <span>{REASON[read.reason]}</span>}
        <span>·</span><span>{read.mode}</span>
        <span className="ml-auto" style={{ color: col, fontWeight: 600 }}>{read.dimTitle}</span>
      </div>
    </button>
  );
}

export function DimensionCard({ dim, state = [], reads = [], tables = 0, onClick }:
  { dim: RMDimension; state?: StateBlock[]; reads?: RMRead[]; tables?: number; onClick: () => void }) {
  const col = dim.color;
  return (
    <button onClick={onClick} className="rm-card rm-tile text-left rounded-xl h-full flex flex-col"
            style={{ ...vars(col), padding: "16px 18px" }}>
      <div style={{ fontSize: GLYPH.dimension, lineHeight: 1 }}>{dim.icon}</div>
      <div style={{ fontSize: FS.card, fontWeight: 600, color: "var(--font)", marginTop: 10, lineHeight: 1.25 }}>{dim.title}</div>
      {/* The standing state (§16). A dimension with no movement cut shows NOTHING here —
          an absence, not an empty row: Bank Credit is the top level and has no mix to state. */}
      {state.length > 0 && (
        <div className="mt-2.5 flex flex-col gap-1">
          {state.map((b) => (
            <div key={b.cut} style={{ fontSize: FS.note, lineHeight: 1.4 }}>
              {b.speed_short && (
                <div style={{ color: "var(--font)" }}>
                  <span style={{ color: col }}>{b.speed_dir === "down" ? "▼" : "▲"} </span>{b.speed_short}
                </div>
              )}
              {/* The mix, or the DECLARED reason there is none (§16): a tile that quietly
                  drops the line makes a dimension with nothing to steer look like one that
                  failed to load. */}
              {tileMix(b)
                ? <div style={{ color: "var(--font-muted)" }}>⇢ {tileMix(b)}</div>
                : <div style={{ color: "var(--font-muted)", fontStyle: "italic" }}>
                    — {b.no_mix_note ?? "no mix at this level"}
                  </div>}
            </div>
          ))}
        </div>
      )}
      {/* §20 — this dimension's OWN news, up to three, where it can be acted on. A pooled
          grid of five reads above seven tiles was the same news twice, ranked by a score the
          reader cannot see. A dimension with one read shows one and says so: a padded tile and
          a quiet month look identical otherwise, and Services being quiet IS the news when its
          mix is the one being steered hardest. */}
      {reads.length > 0 && (
        <div className="mt-3 flex flex-col gap-1.5">
          {reads.map((r) => (
            <div key={r.id} className="flex items-baseline gap-1.5" style={{ fontSize: FS.note, lineHeight: 1.45 }}>
              <span style={{ color: col }}>{glyph(r.direction)}</span>
              <span style={{ color: "var(--font)" }}>{r.title}</span>
            </div>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 mt-auto pt-3">
        {tables > 0 && (
          <span style={{ fontSize: FS.note, color: "var(--font-muted)" }}>
            {tables} table{tables > 1 ? "s" : ""} ·
          </span>
        )}
        <span style={{ fontSize: FS.note, fontWeight: dim.moved > 0 ? 600 : 400,
                       color: dim.moved > 0 ? col : "var(--font-muted)" }}>
          {dim.cardCount} notable →
        </span>
      </div>
    </button>
  );
}

/** The same dimension, compressed (§20 state B). The tile's grid becomes a rail, so the rail
 *  IS the dimension switcher and the chip strip is gone — two switchers for one nav was the
 *  §14.8 mistake, re-made. */
export function RailItem({ dim, state = [], selected, onClick }:
  { dim: RMDimension; state?: StateBlock[]; selected: boolean; onClick: () => void }) {
  const col = dim.color;
  const b = state[0];
  return (
    <button onClick={onClick} className={`rm-flat w-full text-left rounded-lg${selected ? " sel" : ""}`}
            style={{ ...vars(col, tint(col, 0.1)), padding: "10px 12px",
                     borderLeft: `3px solid ${selected ? col : "transparent"}` }}>
      <div className="flex items-baseline gap-2">
        <span style={{ fontSize: FS.body }}>{dim.icon}</span>
        <span style={{ fontSize: FS.body, fontWeight: selected ? 700 : 600, color: "var(--font)" }}>{dim.title}</span>
        {dim.moved > 0 && (
          <span className="ml-auto" style={{ fontSize: FS.meta, fontWeight: 600, color: col }}>▲ {dim.moved}</span>
        )}
      </div>
      {b?.speed_short && (
        <div style={{ fontSize: FS.meta, color: "var(--font-muted)", marginTop: 3 }}>
          {b.speed_dir === "down" ? "▼" : "▲"} {b.speed_short}
        </div>
      )}
      {!b?.speed_short && b?.no_speed_note && (
        <div style={{ fontSize: FS.meta, color: "var(--font-muted)", marginTop: 3, fontStyle: "italic" }}>
          — {b.no_speed_note}
        </div>
      )}
    </button>
  );
}

export interface ChipItem { id: string; title: string; icon: string; color: string; moved: number }

export function ChipStrip({ chips, active, stripRef, onPick }: {
  chips: ChipItem[]; active: string; stripRef: React.RefObject<HTMLDivElement | null>; onPick: (id: string) => void;
}) {
  const scroll = (dir: number) => stripRef.current?.scrollBy({ left: dir * 260, behavior: "smooth" });
  return (
    <div className="flex items-center gap-1">
      <button onClick={() => scroll(-1)} className="rm-link px-1 shrink-0"
              style={{ fontSize: GLYPH.arrow, color: "var(--font-muted)" }} aria-label="scroll left">‹</button>
      <div ref={stripRef} className="rm-strip flex gap-2 overflow-x-auto py-1">
        {chips.map((c) => (
          <button key={c.id} data-on={c.id === active} onClick={() => onPick(c.id)}
                  className={`rm-chip whitespace-nowrap rounded-full shrink-0${c.id === active ? " on" : ""}`}
                  style={{ ...vars(c.color, tint(c.color, 0.14)), fontSize: FS.note, fontWeight: 600, padding: "6px 14px" }}>
            {c.icon} {c.title}{c.moved > 0 ? ` · ▲ ${c.moved}` : ""}
          </button>
        ))}
      </div>
      <button onClick={() => scroll(1)} className="rm-link px-1 shrink-0"
              style={{ fontSize: GLYPH.arrow, color: "var(--font-muted)" }} aria-label="scroll right">›</button>
    </div>
  );
}

export type Depth = "brief" | "full" | "deep";

export function DepthLadder({ depth, setDepth, deepAvailable }: { depth: Depth; setDepth: (d: Depth) => void; deepAvailable: boolean }) {
  const levels: Depth[] = deepAvailable ? ["brief", "full", "deep"] : ["brief", "full"];
  return (
    <div className="flex gap-1">
      {levels.map((d) => (
        <button key={d} onClick={() => setDepth(d)} className="rounded-full transition-colors"
                style={{ fontSize: FS.note, padding: "6px 12px", ...chipStyle(depth === d) }}>
          {d === "brief" ? "Brief" : d === "full" ? "Full" : "Deep ⌁"}
        </button>
      ))}
    </div>
  );
}

/**
 * The standing state band (DASHBOARD_SPEC §16) — the tier above the reads.
 *
 * It belongs to the DIMENSION, not the selected card, so it does not change as the reader
 * clicks between the cards beneath it. Two labelled lines: `speed` is Layer 1 (how fast the
 * parent is growing) and `mix` is Layer 2 (whether anyone is steering the mix). Read together
 * they separate where the money went from whether that changed the shape of the book — the
 * distinction no single card can carry, and the reason this tier exists.
 *
 * Every sentence arrives pre-rendered from `analysis/core/state_lines.py` and gate-checked by
 * stage 5.9b. Nothing here formats a number; a missing line is simply absent.
 */
export function StateBand({ blocks, color }: { blocks: StateBlock[]; color: string }) {
  if (blocks.length === 0) return null;
  const named = blocks.length > 1;   // two cuts on one dimension need telling apart
  return (
    <div className="mb-4" style={{
      background: tint(color, 0.06), border: `1px solid ${tint(color, 0.22)}`,
      borderRadius: R.md, padding: "14px 16px",
    }}>
      <div style={{ ...EYEBROW, color, letterSpacing: "0.05em" }}>
        The state · every month, news or not
      </div>
      {blocks.map((b, i) => (
        <div key={b.cut} style={{ marginTop: i === 0 ? 10 : 12,
                                  borderTop: i === 0 ? undefined : `1px solid ${tint(color, 0.22)}`,
                                  paddingTop: i === 0 ? undefined : 12 }}>
          {named && (
            <div style={{ fontSize: FS.label, fontWeight: 600, color: "var(--font)", marginBottom: 6 }}>
              {b.subject}
            </div>
          )}
          {/* BOTH rows, always. Where a reading does not exist the row carries the reason
              instead of a number — a standing element that silently loses a line reads as
              broken, and "priority sector has no published total" is worth saying. */}
          {([["speed", b.speed, b.no_speed_note],
             ["mix", b.mix, b.no_mix_note]] as const).map(([label, text, note]) =>
            text || note ? (
              <div key={label} className="flex flex-col sm:flex-row sm:gap-3" style={{ marginTop: 4 }}>
                <span className="shrink-0" style={{
                  fontSize: FS.meta, fontWeight: 600, color: "var(--font-muted)",
                  textTransform: "uppercase", letterSpacing: "0.06em",
                  width: 44, lineHeight: 1.9,
                }}>{label}</span>
                {text
                  ? <span style={{ fontSize: FS.body, lineHeight: 1.55, color: "var(--font)" }}>{text}</span>
                  : <span style={{ fontSize: FS.body, lineHeight: 1.55, color: "var(--font-muted)",
                                   fontStyle: "italic" }}>— {note}</span>}
              </div>
            ) : null)}
        </div>
      ))}
    </div>
  );
}

// ── the Layer 1 cut table (DASHBOARD_SPEC §17) ─────────────────────────────────
// One cut's parts, side by side. The table makes the pairing rule STRUCTURAL: a share of
// new money cannot be drawn without that part's speed and acceleration, because they are
// cells in the same row. Every number arrives rendered; this draws strings.

const NUM: React.CSSProperties = {
  textAlign: "right", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap",
  padding: "7px 10px", fontSize: FS.body, color: "var(--font)",
};
const HEAD: React.CSSProperties = {
  ...NUM, fontSize: FS.meta, fontWeight: 600, color: "var(--font-muted)",
  textTransform: "uppercase", letterSpacing: "0.05em", padding: "4px 10px 8px",
};

const DASH = <span style={{ color: "var(--font-muted)" }}>—</span>;

/** What each column is called, and what a chart of it is called. `new` takes the cut's own
 *  flow label, because a share of the net reads as "New" only while the net is positive. */
const COL_LABEL: Record<ColKey, string> = {
  size: "Size", of_cut: "of cut", of_book: "of book",
  growth: "Growth", pace: "Pace", new: "New",
};

/** Which cell a chart is open on. The table no longer owns this: the chart is a COLUMN of
 *  the page (§20 state C), not an overlay on the table, so the shell holds it and the table
 *  is told what is lit. `stem` because a nested sub-cut is its own table. */
export interface CellRef { stem: string; entity: string | null; col: ColKey }

/**
 * The chart behind a cell (§20). Every cell is the latest reading of a stored series, so a
 * cell opens into its own history — which is why the sparkline column and the Numbers/Chart
 * toggle are both gone: one was this series printed as text, the other asked the reader to
 * leave the table to see it.
 *
 * It takes the width the RAIL gave up when the reader opened a row, so nothing is hidden
 * behind it. The columns are tabs inside it, which is what makes "click a row" and "click a
 * number" the same gesture landing on different tabs.
 *
 * `compare` overlays a sibling from the same cut and the same column — the one thing a table
 * genuinely cannot do, and the only overlay where the units and the depth match.
 */
export function CellPanel({ table, cell, color, flowLabel, onPick, onClose }: {
  table: import("@/lib/table").CutTable;
  cell: CellRef; color: string; flowLabel?: string;
  onPick: (col: ColKey) => void;
  onClose: () => void;
}) {
  const [compare, setCompare] = React.useState<string[]>([]);
  React.useEffect(() => setCompare([]), [cell.entity, cell.stem]);

  const row = cell.entity === null ? table.total : table.parts.find((p) => p.entity === cell.entity);
  const own = row ? cellSeries(table, row, cell.col) : [];
  const who = cell.entity ?? table.cut;
  const siblings = table.parts.filter((p) => p.entity && p.entity !== cell.entity && p[cell.col]?.series);
  const cols = COLUMNS.filter((c) => row?.[c]?.series && (row[c]!.series as unknown[]).length > 1);

  const data = own.map((pt, i) => {
    const point: Record<string, string | number | null> = { label: pt.label, [who]: pt.value };
    for (const name of compare) {
      const sib = siblings.find((p) => p.entity === name);
      const s = sib ? cellSeries(table, sib, cell.col) : [];
      point[name] = s[i]?.label === pt.label ? s[i].value : null;
    }
    return point;
  });
  const lines = [who, ...compare];

  // NB no Escape handler here. The SHELL owns the state stack (A/B/C) and pops exactly one
  // level per press; a second listener in this panel meant one Esc popped two levels, which
  // is what a reader experiences as the page jumping.

  return (
    <div style={{ ...PANEL, padding: 16, position: "sticky", top: 12 }}>
      <div className="flex items-start justify-between gap-3">
        <div style={{ fontSize: FS.card, fontWeight: 700, color: "var(--font)", lineHeight: 1.25 }}>{who}</div>
        <button onClick={onClose} className="rm-link shrink-0" aria-label="close chart"
                style={{ fontSize: GLYPH.arrow, color: "var(--font-muted)", lineHeight: 1 }}>✕</button>
      </div>

      {/* The columns as tabs — so clicking a ROW and clicking a NUMBER are one gesture that
          lands on different tabs. A column this row has no history for is simply not offered. */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        {cols.map((c) => (
          <button key={c} onClick={() => onPick(c)} className="rounded-full transition-colors"
                  style={{ fontSize: FS.meta, padding: "4px 10px", ...chipStyle(c === cell.col) }}>
            {c === "new" ? (flowLabel ?? "New") : COL_LABEL[c]}
          </button>
        ))}
      </div>

      <div style={{ height: 190, marginTop: 12 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 8, left: -14, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-card)" />
            <XAxis dataKey="label" tick={{ fontSize: FS.micro, fill: "var(--font-muted)" }}
                   interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: FS.micro, fill: "var(--font-muted)" }} width={50} />
            <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border-card)",
                                     borderRadius: R.sm, fontSize: FS.note }} />
            {lines.map((name, i) => (
              // Linear with a dot per reading, not a smoothed curve: the readings are monthly
              // observations and SIBC's own period set has a gap in it (eleven ingested
              // periods, not eleven consecutive months). A spline through them would draw a
              // confident shape across months nobody measured.
              <Line key={name} type="linear" dataKey={name} stroke={i === 0 ? color : pickColor(name, i + 2)}
                    strokeWidth={i === 0 ? 2.5 : 1.5} dot={{ r: 2 }} connectNulls={false}
                    isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* The readings themselves, as rendered in Python. The line shows the shape; these are
          the argument, and they are the numbers the gate checked. */}
      <p style={{ fontSize: FS.note, lineHeight: 1.7, color: "var(--font)", marginTop: 10 }}>
        {own.filter((p) => p.display).map((p) => p.display).join("  →  ")}
      </p>
      <p style={{ fontSize: FS.meta, color: "var(--font-muted)", marginTop: 4 }}>
        {own.filter((p) => p.value !== null).length} readings · {own[0]?.label} to {own[own.length - 1]?.label}
      </p>

      {siblings.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ ...EYEBROW, marginBottom: 6 }}>Compare</div>
          <div className="flex flex-wrap gap-1.5">
            {siblings.map((p) => {
              const on = compare.includes(p.entity!);
              return (
                <button key={p.entity} onClick={() => setCompare(on
                          ? compare.filter((x) => x !== p.entity)
                          : [...compare, p.entity!])}
                        className={`rm-chip rounded-full${on ? " on" : ""}`}
                        style={{ ...vars(color, tint(color, 0.14)), fontSize: FS.meta, padding: "4px 10px" }}>
                  {p.entity}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * The table, COMPRESSED into a navigator (§20 state C). The parent pane never disappears and
 * never stays full width: two panes at a time, and the child — the chart the reader just
 * asked for — takes the larger share. What survives the compression is exactly what is needed
 * to change the reader's mind about which row they wanted: the part's name and the number
 * they clicked.
 *
 * The same shape the rail has in state B, one level down. A parent pane that shrinks into a
 * list of its children is the one compression that loses nothing the reader was using.
 */
export function CutRowList({ table, title, cell, color, onPick }: {
  table: import("@/lib/table").CutTable;
  title: string; cell: CellRef; color: string;
  onPick: (ref: CellRef) => void;
}) {
  const rows = [table.total, ...sortPartsMemo(table.parts, "size", "desc")];
  const label = cell.col === "new" ? (table.flow_label ?? "New") : COL_LABEL[cell.col];
  return (
    <div>
      <div style={{ ...EYEBROW, color, marginBottom: 2 }}>{title}</div>
      <div style={{ ...EYEBROW, marginBottom: 8 }}>{label}</div>
      <div className="flex flex-col gap-0.5">
        {rows.map((r) => {
          const v = r[cell.col];
          const on = r.entity === cell.entity;
          const live = (v?.series?.length ?? 0) > 1;
          return (
            <button key={r.entity ?? "_total"} disabled={!live}
                    onClick={() => live && onPick({ stem: table.cut, entity: r.entity, col: cell.col })}
                    className="rm-flat text-left rounded-md flex items-baseline gap-2"
                    style={{ ...vars(color, tint(color, 0.12)), border: "none",
                             background: on ? tint(color, 0.14) : "transparent",
                             padding: "6px 8px", cursor: live ? "pointer" : "default",
                             opacity: live ? 1 : 0.45 }}>
              <span style={{ fontSize: FS.note, fontWeight: r.entity === null || on ? 700 : 400,
                             color: "var(--font)", lineHeight: 1.35 }}>
                {r.entity ?? title}
              </span>
              <span className="ml-auto" style={{ fontSize: FS.note, fontVariantNumeric: "tabular-nums",
                                                 color: on ? color : "var(--font-muted)" }}>
                {v?.display ?? "—"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export interface CutTableProps {
  table: import("@/lib/table").CutTable;
  /** All tables, so a row can open into the cut it decomposes into (§19). */
  all?: import("@/lib/table").CutTables;
  depth?: number;
  title: string;               // the cut's own name, for the total row
  color: string;
  /** Named because a share is meaningless without it (§15). Omitted when the cut has none. */
  bookLabel?: string;
  footer?: string;
  /** The chart lives in the shell, so the table reports clicks and is told what is lit. */
  active?: CellRef | null;
  onPickCell?: (ref: CellRef) => void;
}

/** What a row opens on when the reader clicks the ROW rather than one of its numbers.
 *  Growth, because that is the question a reader is asking when they click a sector — the
 *  size is already on the line in front of them. */
const ROW_DEFAULT: ColKey[] = ["growth", "size", "of_cut", "new", "pace", "of_book"];

export function CutTable({ table, title, color, bookLabel, footer, all, depth = 0,
                          active, onPickCell }: CutTableProps) {
  // Default size, descending: the reader's model is "biggest first", and a growth-sorted
  // table opens with the smallest book on the page.
  const [sort, setSort] = React.useState<{ key: SortKey; dir: SortDir }>({ key: "size", dir: "desc" });
  const [open, setOpen] = React.useState<string | null>(null);
  const parts = sortPartsMemo(table.parts, sort.key, sort.dir);
  // The columns this cut ACTUALLY has, declared in Python. A bank breakout stores no pace and
  // no share of the new money, and six columns of dashes would say it does — the same argument
  // that keeps `of book` off the payments tables rather than dashing it.
  const cols = COLUMNS.filter((c) => table.columns
    ? c in table.columns
    : c !== "of_book" || table.parts.some((p) => p.of_book));
  const label = (c: ColKey) => (c === "new" ? (table.flow_label ?? "New") : COL_LABEL[c]);
  const lit = (row: import("@/lib/table").CutRow, c?: ColKey) =>
    active?.stem === table.cut && active.entity === row.entity && (!c || active.col === c);

  function pickSort(key: SortKey) {
    setSort((s) => s.key === key ? { key, dir: s.dir === "desc" ? "asc" : "desc" } : { key, dir: "desc" });
  }
  function pickRow(row: import("@/lib/table").CutRow, col?: ColKey) {
    const has = (c: ColKey) => (row[c]?.series?.length ?? 0) > 1;
    const c = col && has(col) ? col : ROW_DEFAULT.find(has);
    if (c && onPickCell) onPickCell({ stem: table.cut, entity: row.entity, col: c });
  }

  function numeric(row: import("@/lib/table").CutRow, c: ColKey) {
    const v = row[c];
    if (!v) return <td key={c} style={NUM}>{DASH}</td>;
    const live = (v.series?.length ?? 0) > 1;
    return (
      <td key={c} style={{ ...NUM, cursor: live ? "pointer" : "default",
                           background: lit(row, c) ? tint(color, 0.18) : undefined,
                           borderRadius: lit(row, c) ? R.sm : undefined,
                           textDecoration: live ? "underline" : undefined,
                           textDecorationColor: live ? tint(color, 0.4) : undefined,
                           textUnderlineOffset: 3 }}
          onClick={live ? (e) => { e.stopPropagation(); pickRow(row, c); } : undefined}>
        {v.display}
      </td>
    );
  }

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 520 }}>
        <thead>
          <tr>
            <th style={{ ...HEAD, textAlign: "left" }}>Part</th>
            {cols.map((c) => (
              <th key={c} style={HEAD}>
                <button onClick={() => pickSort(c)} className="rm-link"
                        style={{ font: "inherit", letterSpacing: "inherit", textTransform: "inherit",
                                 color: sort.key === c ? color : "inherit" }}>
                  {c === "of_book" ? (bookLabel ?? label(c)) : label(c)}
                  {sort.key === c ? (sort.dir === "desc" ? " ↓" : " ↑") : ""}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* the cut's own row — pinned, never sorted: it is the denominator, not a competitor */}
          <tr className="rm-row" onClick={() => pickRow(table.total)}
              style={{ borderTop: `2px solid ${color}`, borderBottom: "1px solid var(--border-card)",
                       cursor: "pointer", background: lit(table.total) ? tint(color, 0.07) : undefined }}>
            <td style={{ ...NUM, textAlign: "left", fontWeight: 700 }}>{title}</td>
            {cols.map((c) => numeric(table.total, c))}
          </tr>
          {parts.map((p) => {
            const nested = p.sub_cut && all?.[p.sub_cut] && depth === 0 ? all[p.sub_cut] : null;
            const isOpen = open === p.entity;
            return (
              <React.Fragment key={p.entity ?? "_"}>
                <tr className="rm-row" onClick={() => pickRow(p)}
                    style={{ ...vars(color, tint(color, 0.07)), cursor: "pointer",
                             background: lit(p) ? tint(color, 0.12) : isOpen ? tint(color, 0.07) : undefined }}>
                  <td style={{ ...NUM, textAlign: "left" }}>
                    {nested ? (
                      <button onClick={(e) => { e.stopPropagation(); setOpen(isOpen ? null : p.entity); }}
                              className="rm-link" style={{ font: "inherit", color: "inherit" }}>
                        <span style={{ color, fontWeight: 700 }}>{isOpen ? "▾" : "▸"}</span> {p.entity}
                      </button>
                    ) : p.entity}
                  </td>
                  {cols.map((c) => numeric(p, c))}
                </tr>
                {/* §19 — the part decomposes further, so it opens into its own table. One level:
                    RBI publishes no fourth. This is also the answer to §15's founding defect —
                    the card said "Iron and Steel holds 69.0% of basic-metals credit" above a
                    chart of "Basic Metal 11.2% of industry"; now both are on screen, nested,
                    with the denominator stated rather than implied. */}
                {isOpen && nested && (
                  <tr>
                    <td colSpan={cols.length + 1} style={{ padding: "0 10px 14px" }}>
                      <div style={{ paddingLeft: 14, borderLeft: `2px solid ${tint(color, 0.4)}` }}>
                        <div style={{ ...EYEBROW, margin: "8px 0 6px" }}>
                          Inside {p.entity} · shares below are of {p.entity}
                        </div>
                        <CutTable table={nested} title={p.entity ?? ""} color={color}
                                  all={all} depth={depth + 1} active={active} onPickCell={onPickCell} />
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
      </div>

      <p style={{ fontSize: FS.note, color: "var(--font-muted)", marginTop: 8 }}>
        {table.parts.length} parts · click any row to chart it · sort by any column
      </p>
      {footer && (
        <p style={{ fontSize: FS.note, color: "var(--font-muted)", marginTop: 6, lineHeight: 1.5 }}>
          {footer}
        </p>
      )}
    </div>
  );
}
