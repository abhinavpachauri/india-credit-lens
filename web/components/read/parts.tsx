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

export function DimensionCard({ dim, state = [], topRead, tables = 0, onClick }:
  { dim: RMDimension; state?: StateBlock[]; topRead?: RMRead | null; tables?: number; onClick: () => void }) {
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
              {tileMix(b)
                ? <div style={{ color: "var(--font-muted)" }}>⇢ {tileMix(b)}</div>
                : !b.speed_short && <div style={{ color: "var(--font-muted)" }}>⇢ no mix at this level</div>}
            </div>
          ))}
        </div>
      )}
      {/* §20 — the ONE new thing, where it can be acted on. A pooled grid of five reads above
          seven tiles was the same news twice, ranked by a score the reader cannot see; a tile
          that carries its own says which dimension is worth opening this month. */}
      {topRead && (
        <div className="mt-2.5 flex items-baseline gap-1.5" style={{ fontSize: FS.note, lineHeight: 1.45 }}>
          <span style={{ color: col }}>{glyph(topRead.direction)}</span>
          <span style={{ color: "var(--font)" }}>{topRead.title}</span>
        </div>
      )}
      <div className="flex items-center gap-2 mt-auto pt-3">
        {tables > 0 && (
          <span style={{ fontSize: FS.note, color: "var(--font-muted)" }}>
            {tables} table{tables > 1 ? "s" : ""}
          </span>
        )}
        {dim.cardCount > 0 && (
          <span style={{ fontSize: FS.note, fontWeight: dim.moved > 0 ? 600 : 400,
                         color: dim.moved > 0 ? col : "var(--font-muted)" }}>
            {dim.cardCount} notable
          </span>
        )}
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

/**
 * The chart behind a cell (§20). Every cell is the latest reading of a stored series, so a
 * cell opens into its own history — which is why the sparkline column and the Numbers/Chart
 * toggle are both gone: one was this series printed as text, the other asked the reader to
 * leave the table to see it.
 *
 * `compare` overlays a sibling from the same cut and the same column — the one thing a table
 * genuinely cannot do, and the only overlay where the units and the depth match.
 */
function CellPanel({ table, row, col, color, onClose }: {
  table: import("@/lib/table").CutTable;
  row: import("@/lib/table").CutRow;
  col: ColKey; color: string; onClose: () => void;
}) {
  const [compare, setCompare] = React.useState<string[]>([]);
  const own = cellSeries(table, row, col);
  const who = row.entity ?? "the cut";
  const siblings = table.parts.filter((p) => p.entity && p.entity !== row.entity && p[col]?.series);

  // One row per period; one key per compared entity. Labels come from the sidecar, so the
  // axis is a published string like everything else here.
  const data = own.map((pt, i) => {
    const point: Record<string, string | number | null> = { label: pt.label, [who]: pt.value };
    for (const name of compare) {
      const s = cellSeries(table, siblings.find((p) => p.entity === name)!, col);
      point[name!] = s[i]?.label === pt.label ? s[i].value : null;
    }
    return point;
  });
  const lines = [who, ...compare];

  React.useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);

  return (
    <div className="fixed z-40 inset-x-0 bottom-0 lg:top-[68px] lg:bottom-0 lg:inset-x-auto lg:right-0 lg:w-[440px]"
         style={{ background: "var(--bg-card)", borderTop: "1px solid var(--border-card)",
                  borderLeft: "1px solid var(--border-card)", boxShadow: "0 -6px 24px var(--shadow)",
                  maxHeight: "82vh", overflowY: "auto", padding: 18 }}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div style={{ ...EYEBROW, color }}>{COL_LABEL[col]}</div>
          <div style={{ fontSize: FS.card, fontWeight: 700, color: "var(--font)", lineHeight: 1.25 }}>{who}</div>
        </div>
        <button onClick={onClose} className="rm-link" aria-label="close"
                style={{ fontSize: GLYPH.arrow, color: "var(--font-muted)", lineHeight: 1 }}>✕</button>
      </div>

      <div style={{ height: 200, marginTop: 14 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-card)" />
            <XAxis dataKey="label" tick={{ fontSize: FS.micro, fill: "var(--font-muted)" }}
                   interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: FS.micro, fill: "var(--font-muted)" }} width={52} />
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

export interface CutTableProps {
  table: import("@/lib/table").CutTable;
  /** All tables, so a row can open into the cut it decomposes into (§19). */
  all?: import("@/lib/table").CutTables;
  depth?: number;
  title: string;               // the cut's own name, for the total row
  color: string;
  /** Named because a share is meaningless without it (§15). Omitted when the cut has none. */
  bookLabel?: string;
  footer?: string;             // e.g. the main-sectors residual
}

export function CutTable({ table, title, color, bookLabel, footer, all, depth = 0 }: CutTableProps) {
  // Default size, descending: the reader's model is "biggest first", and a growth-sorted
  // table opens with the smallest book on the page.
  const [sort, setSort] = React.useState<{ key: SortKey; dir: SortDir }>({ key: "size", dir: "desc" });
  const [open, setOpen] = React.useState<string | null>(null);
  const [cell, setCell] = React.useState<{ entity: string | null; col: ColKey } | null>(null);
  const parts = sortPartsMemo(table.parts, sort.key, sort.dir);
  const cols = COLUMNS.filter((c) => c !== "of_book" || table.parts.some((p) => p.of_book));
  const label = (c: ColKey) => (c === "new" ? (table.flow_label ?? "New") : COL_LABEL[c]);

  function pickSort(key: SortKey) {
    setSort((s) => s.key === key ? { key, dir: s.dir === "desc" ? "asc" : "desc" } : { key, dir: "desc" });
  }
  const openRow = cell && (cell.entity === null ? table.total
                                                : table.parts.find((p) => p.entity === cell.entity));

  function numeric(row: import("@/lib/table").CutRow, c: ColKey) {
    const v = row[c];
    if (!v) return <td key={c} style={NUM}>{DASH}</td>;
    const live = v.series && v.series.length > 1;
    const on = cell?.entity === row.entity && cell?.col === c;
    return (
      <td key={c} style={{ ...NUM, cursor: live ? "pointer" : "default",
                           background: on ? tint(color, 0.16) : undefined,
                           borderRadius: on ? R.sm : undefined,
                           textDecoration: live ? "underline" : undefined,
                           textDecorationColor: live ? tint(color, 0.4) : undefined,
                           textUnderlineOffset: 3 }}
          onClick={live ? (e) => { e.stopPropagation(); setCell(on ? null : { entity: row.entity, col: c }); } : undefined}>
        {v.display}
      </td>
    );
  }

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
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
          <tr style={{ borderTop: `2px solid ${color}`, borderBottom: "1px solid var(--border-card)" }}>
            <td style={{ ...NUM, textAlign: "left", fontWeight: 700 }}>{title}</td>
            {cols.map((c) => numeric(table.total, c))}
          </tr>
          {parts.map((p) => {
            const nested = p.sub_cut && all?.[p.sub_cut] && depth === 0 ? all[p.sub_cut] : null;
            const isOpen = open === p.entity;
            return (
              <React.Fragment key={p.entity ?? "_"}>
                <tr style={{ ...vars(color, tint(color, 0.07)),
                             background: isOpen ? tint(color, 0.07) : undefined }}>
                  <td style={{ ...NUM, textAlign: "left" }}>
                    {nested ? (
                      <button onClick={() => setOpen(isOpen ? null : p.entity)} className="rm-link"
                              style={{ font: "inherit", color: "inherit" }}>
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
                                  all={all} depth={depth + 1} />
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
        {table.parts.length} parts · every underlined number opens its own chart · sort by any column
      </p>
      {footer && (
        <p style={{ fontSize: FS.note, color: "var(--font-muted)", marginTop: 6, lineHeight: 1.5 }}>
          {footer}
        </p>
      )}
      {cell && openRow && (
        <CellPanel table={table} row={openRow} col={cell.col} color={color}
                   onClose={() => setCell(null)} />
      )}
    </div>
  );
}
