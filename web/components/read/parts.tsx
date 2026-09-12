"use client";

// Shared read-mode primitives (DASHBOARD_SPEC.md §14). The design lives HERE, once — SIBC and
// payments both render these; only the data model (below) + the chart/deep renderers differ per
// pipeline. Colour = section/group (a card's colour is also its chart-line colour).

import React from "react";
import { sortParts as sortPartsMemo } from "@/lib/table";
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

export function DimensionCard({ dim, state = [], onClick }:
  { dim: RMDimension; state?: StateBlock[]; onClick: () => void }) {
  const col = dim.color;
  return (
    <button onClick={onClick} className="rm-card rm-tile text-left rounded-xl"
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
              {tileMix(b)
                ? <div style={{ color: "var(--font-muted)" }}>⇢ {tileMix(b)}</div>
                : !b.speed_short && <div style={{ color: "var(--font-muted)" }}>⇢ no mix at this level</div>}
            </div>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 mt-2">
        <span style={{ fontSize: FS.note, color: "var(--font-muted)" }}>{dim.cardCount} insights</span>
        {dim.moved > 0 && <span style={{ fontSize: FS.note, fontWeight: 600, color: col }}>▲ {dim.moved} moved</span>}
      </div>
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

/** A run of readings as a sparkline. Bars, not a line: eight monthly readings are eight
 *  discrete observations, and a line implies we know what happened between them. */
function Run({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <span style={{ color: "var(--font-muted)" }}>—</span>;
  const lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
  return (
    <span className="inline-flex items-end gap-px" style={{ height: 16 }} aria-hidden>
      {values.map((v, i) => (
        <span key={i} style={{
          width: 3, height: Math.max(2, ((v - lo) / span) * 14 + 2),
          // Square, deliberately. The radius ladder starts at 4, which on a 3px bar is a
          // circle; and adding a 1px rung for one sparkline would dilute a ladder that
          // exists to stop exactly that. A 3px bar needs no corner.
          background: color, opacity: 0.35 + 0.65 * (i / (values.length - 1)),
        }} />
      ))}
    </span>
  );
}

const NUM: React.CSSProperties = {
  textAlign: "right", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap",
  padding: "7px 10px", fontSize: FS.body, color: "var(--font)",
};
const HEAD: React.CSSProperties = {
  ...NUM, fontSize: FS.meta, fontWeight: 600, color: "var(--font-muted)",
  textTransform: "uppercase", letterSpacing: "0.05em", padding: "4px 10px 8px",
};

function cell(c: { display: string } | null) {
  return c ? c.display : <span style={{ color: "var(--font-muted)" }}>—</span>;
}

export interface CutTableProps {
  table: import("@/lib/table").CutTable;
  title: string;               // the cut's own name, for the total row
  color: string;
  /** Named because a share is meaningless without it (§15). Omitted when the cut has none. */
  bookLabel?: string;
  footer?: string;             // e.g. the main-sectors residual
  openLabel?: (entity: string) => string;
}

export function CutTable({ table, title, color, bookLabel, footer }: CutTableProps) {
  const [sort, setSort] = React.useState<import("@/lib/table").SortKey>("size");
  const [open, setOpen] = React.useState<string | null>(null);
  const parts = sortPartsMemo(table.parts, sort);
  const hasBook = table.parts.some((p) => p.of_book);

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
        <thead>
          <tr>
            <th style={{ ...HEAD, textAlign: "left" }}>Part</th>
            <th style={HEAD}>Size</th>
            <th style={HEAD}>of cut</th>
            {hasBook && <th style={HEAD}>{bookLabel ?? "of book"}</th>}
            <th style={HEAD}>Growth</th>
            <th style={HEAD}>Pace</th>
            <th style={HEAD}>Run</th>
            <th style={HEAD}>{table.flow_label ?? "New"}</th>
          </tr>
        </thead>
        <tbody>
          {/* the cut's own row — pinned, never sorted */}
          <tr style={{ borderTop: `2px solid ${color}`, borderBottom: "1px solid var(--border-card)" }}>
            <td style={{ ...NUM, textAlign: "left", fontWeight: 700 }}>{title}</td>
            <td style={{ ...NUM, fontWeight: 700 }}>{cell(table.total.size)}</td>
            <td style={NUM}>{cell(table.total.of_cut)}</td>
            {hasBook && <td style={NUM}>{cell(table.total.of_book)}</td>}
            <td style={NUM}>{cell(table.total.growth)}</td>
            <td style={NUM}>{cell(table.total.pace)}</td>
            <td style={NUM} /><td style={NUM} />
          </tr>
          {parts.map((p) => {
            const isOpen = open === p.entity;
            return (
              <React.Fragment key={p.entity ?? "_"}>
                <tr className="rm-row" onClick={() => setOpen(isOpen ? null : p.entity)}
                    style={{ ...vars(color, tint(color, 0.07)), cursor: "pointer",
                             background: isOpen ? tint(color, 0.07) : undefined }}>
                  <td style={{ ...NUM, textAlign: "left" }}>{p.entity}</td>
                  <td style={NUM}>{cell(p.size)}</td>
                  <td style={NUM}>{cell(p.of_cut)}</td>
                  {hasBook && <td style={NUM}>{cell(p.of_book)}</td>}
                  <td style={NUM}>{cell(p.growth)}</td>
                  <td style={NUM}>{cell(p.pace)}</td>
                  <td style={{ ...NUM, textAlign: "center" }}><Run values={p.run} color={color} /></td>
                  <td style={NUM}>{cell(p.new)}</td>
                </tr>
                {isOpen && p.run.length > 1 && (
                  <tr>
                    <td colSpan={hasBook ? 8 : 7}
                        style={{ ...NUM, textAlign: "left", fontSize: FS.note,
                                 color: "var(--font-muted)", paddingTop: 0, paddingBottom: 12 }}>
                      {/* The readings themselves — the sparkline shows the shape, this shows
                          the argument. Eight numbers per row would be a spreadsheet; eight
                          numbers in the row you opened is the point. */}
                      Growth, last {p.run.length} readings:{" "}
                      <span style={{ color: "var(--font)" }}>
                        {p.run.map((v) => `${v.toFixed(1)}%`).join("  →  ")}
                      </span>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>

      <div className="flex items-center justify-between flex-wrap gap-2" style={{ marginTop: 8 }}>
        <span style={{ fontSize: FS.note, color: "var(--font-muted)" }}>
          {table.parts.length} parts · sort by{" "}
          {(["size", "growth", "new"] as const).map((k) => (
            <button key={k} onClick={() => setSort(k)}
                    style={{ fontWeight: sort === k ? 700 : 400,
                             color: sort === k ? color : "var(--font-muted)", marginRight: 10 }}>
              {k === "new" ? "new money" : k}
            </button>
          ))}
        </span>
      </div>
      {footer && (
        <p style={{ fontSize: FS.note, color: "var(--font-muted)", marginTop: 6, lineHeight: 1.5 }}>
          {footer}
        </p>
      )}
    </div>
  );
}
