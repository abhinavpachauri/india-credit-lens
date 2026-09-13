"use client";

// The read-mode SHELL — pipeline-agnostic (DASHBOARD_SPEC.md §14, reshaped by §20). Owns the
// three states, the rail, the depth ladder, and which cell has a chart open. A pipeline
// supplies its RMModel, its cuts, a chart renderer for dimensions that own no table, and its
// deep reading.
//
// THREE STATES, AND EACH CLOSE POPS EXACTLY ONE LEVEL:
//
//   A  every dimension as a tile, each carrying its own news
//   B  click a tile — the tiles compress into a rail, the dimension opens beside it
//   C  click a row  — the rail collapses to ☰ and the chart takes the width it gave up
//
// The chart is a COLUMN, not an overlay: it occupies exactly the space the rail released, so
// nothing is hidden behind it and the table it was opened from stays readable.

import { useEffect, useMemo, useRef, useState } from "react";
import { usePersistent } from "@/hooks/usePersistent";
import {
  chipStyle,
  STYLE, PANEL, EYEBROW, READS_COLOR, tint, glyph, REASON,
  DimensionCard, RailItem, DepthLadder, CutTable, CellPanel, StateBand,
  type RMModel, type RMCard, type RMDimension, type RMRead, type Depth, type CellRef,
} from "./parts";
import { FS, R, GLYPH } from "@/lib/tokens";
import type { CutTables, ColKey } from "@/lib/table";
import type { StateMap } from "@/lib/state";

/** How many of a dimension's own reads its tile carries. Three, because the tile has to say
 *  what happened without becoming the pooled read grid it replaced. */
const TILE_READS = 3;

export interface ReadModeShellProps {
  model: RMModel;
  homeLabel: string;
  period: string;                                             // e.g. "May"
  /** render the view label + chart for a card — used by dimensions that own no table. */
  renderChart: (card: RMCard, dim: RMDimension) => React.ReactNode;
  hasDeep: (dimId: string) => boolean;
  renderDeep: (dimId: string, color: string) => React.ReactNode;
  /** dimension id → its standing state blocks (§16). Absent dimensions simply show none. */
  state?: StateMap;
  /** §17 — the Layer 1 tables keyed by cut stem, and the cuts a dimension owns. */
  tables?: CutTables;
  cutsFor?: (dimId: string) => CutRef[];
}

export interface CutRef {
  stem: string;
  title: string;
  /** §20 — a payments group is many MEASURES over one entity set, so the measure is a filter
   *  on one table rather than a second table. A credit dimension leaves both blank: it is one
   *  measure over a hierarchy, and its depth comes from a row opening into its own cut. */
  measure?: string;
  axis?: "value" | "volume";
  /** Named because a share is meaningless without it (§15). Omitted when the cut has none. */
  bookLabel?: string;
  footer?: string;
  /** Why this dimension has no table at all, in its own words. Bank Credit is the top level:
   *  its only split is food vs non-food, which is an accounting line and not a mix. A pane
   *  that simply omits the table reads as broken. */
  noTableNote?: string;
}

export default function ReadModeShell({ model, homeLabel, period, renderChart, hasDeep, renderDeep,
                                       state = {}, tables, cutsFor }: ReadModeShellProps) {
  const dimById = useMemo(() => new Map(model.dimensions.map((d) => [d.id, d])), [model]);

  const [openDim, setOpenDim] = useState<string | null>(null);       // null = state A
  const [cell, setCell] = useState<CellRef | null>(null);            // non-null = state C
  const [railOver, setRailOver] = useState(false);                   // ☰ in state C
  const [openCard, setOpenCard] = useState<string | null>(null);
  const [depth, setDepth] = usePersistent<Depth>("icl-depth", "full");
  const [showIndex, setShowIndex] = useState(false);
  const [measure, setMeasure] = useState<string | null>(null);
  const [axis, setAxis] = usePersistent<"value" | "volume">("icl-axis", "value");

  const detailRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const deepRef = useRef<HTMLDivElement>(null);

  const dim = openDim ? dimById.get(openDim) ?? null : null;
  const secColor = dim?.color ?? READS_COLOR;

  /** The cuts this dimension owns that the sidecar actually carries. */
  const cuts = useMemo(
    () => (dim && cutsFor ? cutsFor(dim.id).filter((c) => tables?.[c.stem] || c.noTableNote) : []),
    [dim, cutsFor, tables]);
  const measures = useMemo(() => {
    const seen: string[] = [];
    for (const c of cuts) { const m = c.measure ?? c.title; if (!seen.includes(m)) seen.push(m); }
    return seen;
  }, [cuts]);
  const activeMeasure = measure && measures.includes(measure) ? measure : measures[0];
  const forMeasure = cuts.filter((c) => (c.measure ?? c.title) === activeMeasure);
  const axes = forMeasure.map((c) => c.axis).filter(Boolean) as ("value" | "volume")[];
  const cut = forMeasure.find((c) => !c.axis || c.axis === axis) ?? forMeasure[0];
  const table = cut && tables?.[cut.stem];

  const deepAvailable = dim ? hasDeep(dim.id) : false;
  const effDepth: Depth = depth === "deep" && !deepAvailable ? "full" : depth;
  const DEPTH_HINT: Record<Depth, string> = {
    brief: "the table only", full: "with the reasoning", deep: "the deeper reading" };

  const notable = (d: RMDimension) => d.subjects.flatMap((s) => s.cards);
  const readsOf = (dimId: string) => model.reads.filter((r) => r.dimId === dimId);
  const tableCount = (dimId: string) =>
    (cutsFor ? cutsFor(dimId).filter((c) => tables?.[c.stem]).length : 0);

  // On a phone the chart cannot sit beside the table, so it stacks under it — and a chart
  // the reader has to go looking for is a chart that did not open. Desktop leaves the scroll
  // alone: there the panel is already in view, beside the row that was clicked.
  useEffect(() => {
    if (!cell || typeof window === "undefined" || window.innerWidth >= 1024) return;
    const id = setTimeout(() => chartRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    return () => clearTimeout(id);
  }, [cell]);

  // Esc pops one level, exactly like the ✕ on each pane — C → B → A.
  useEffect(() => {
    const esc = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (railOver) setRailOver(false);
      else if (cell) setCell(null);
      else if (openDim) setOpenDim(null);
    };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [cell, openDim, railOver]);

  function enter(dimId: string, cardId?: string) {
    setOpenDim(dimId);
    setMeasure(null);
    setCell(null);
    setOpenCard(cardId ?? null);
    if (typeof window !== "undefined") requestAnimationFrame(() => window.scrollTo({ top: 0 }));
  }
  function pickDim(dimId: string) {
    setOpenDim(dimId); setMeasure(null); setCell(null); setOpenCard(null); setRailOver(false);
  }

  // ── STATE A · the landing grid ───────────────────────────────────────────
  if (!dim) {
    return (
      <>
        <style>{STYLE}</style>
        <div key="grid" style={{ animation: "rmfade 220ms ease" }}>
          <h2 style={{ ...EYEBROW, marginBottom: 14 }}>
            {model.dimensions.length} dimensions ·{" "}
            {model.dimensions.reduce((n, d) => n + tableCount(d.id), 0)} tables ·{" "}
            {model.reads.length} moved this {period}
          </h2>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 items-stretch">
            {model.dimensions.map((d) => (
              <DimensionCard key={d.id} dim={d} state={state[d.id]}
                             reads={readsOf(d.id).slice(0, TILE_READS)}
                             tables={tableCount(d.id)} onClick={() => enter(d.id)} />
            ))}
          </div>

          <button onClick={() => setShowIndex(!showIndex)} className="rm-link mt-6"
                  style={{ fontSize: FS.body, fontWeight: 600, color: READS_COLOR }}>
            {showIndex ? "▾" : "▸"} everything that moved this {period} · {model.reads.length}
          </button>
          {showIndex && (
            <div className="mt-3 flex flex-col gap-1.5">
              {model.reads.map((r) => (
                <button key={r.id} onClick={() => enter(r.dimId, r.id)}
                        className="rm-link text-left flex items-baseline gap-2"
                        style={{ fontSize: FS.body, color: "var(--font)" }}>
                  <span style={{ color: r.color }}>{glyph(r.direction)}</span>
                  <span>{r.title}</span>
                  <span style={{ fontSize: FS.meta, color: r.color, fontWeight: 600 }}>{r.dimTitle}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </>
    );
  }

  // ── STATES B and C ───────────────────────────────────────────────────────
  const rail = (
    <div className="flex flex-col gap-1.5">
      <div style={{ ...EYEBROW, marginBottom: 4 }}>{homeLabel}</div>
      {model.dimensions.map((d) => (
        <RailItem key={d.id} dim={d} state={state[d.id]} selected={d.id === dim.id}
                  onClick={() => pickDim(d.id)} />
      ))}
      <button onClick={() => { setOpenDim(null); setRailOver(false); }} className="rm-link text-left mt-1.5"
              style={{ fontSize: FS.note, fontWeight: 600, color: READS_COLOR }}>
        ‹ all dimensions
      </button>
    </div>
  );

  return (
    <>
      <style>{STYLE}</style>
      <div key="detail" style={{ animation: "rmfade 220ms ease" }}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            {/* ☰ only exists in state C — in state B the rail is already there, and a control
                that hides what is already visible is a control with nothing to do. */}
            {cell && (
              <button onClick={() => setRailOver(!railOver)} className="rm-link lg:block hidden"
                      aria-label="dimensions" style={{ fontSize: GLYPH.arrow, color: "var(--font-muted)" }}>☰</button>
            )}
            <button onClick={() => (cell ? setCell(null) : setOpenDim(null))} className="rm-link"
                    style={{ fontSize: FS.body, fontWeight: 600, color: "var(--font-muted)" }}>
              ‹ {cell ? dim.title : homeLabel}
            </button>
          </div>
          <div className="flex flex-col items-end">
            <DepthLadder depth={effDepth} setDepth={setDepth} deepAvailable={deepAvailable} />
            <span style={{ fontSize: FS.meta, color: "var(--font-muted)", marginTop: 4 }}>Detail: {DEPTH_HINT[effDepth]}</span>
          </div>
        </div>

        <div className={`lg:grid lg:gap-6 lg:items-start ${
          cell ? "lg:grid-cols-[minmax(0,1fr)_430px]" : "lg:grid-cols-[300px_minmax(0,1fr)]"}`}>
          {/* LEFT · the rail, which state C hands to the chart */}
          {!cell && <div className="hidden lg:block lg:col-start-1">{rail}</div>}

          {/* CENTRE · the dimension */}
          <div ref={detailRef} className={cell ? "lg:col-start-1" : "lg:col-start-2 mt-5 lg:mt-0"}>
            <div style={{ ...PANEL, padding: 20, borderTop: `3px solid ${secColor}` }}>
              <div className="flex items-start justify-between gap-3">
                <div style={{ ...EYEBROW, color: secColor, letterSpacing: "0.05em", marginBottom: 12 }}>
                  {dim.icon} {dim.title}
                </div>
                <button onClick={() => setOpenDim(null)} className="rm-link shrink-0" aria-label="close dimension"
                        style={{ fontSize: GLYPH.arrow, color: "var(--font-muted)", lineHeight: 1 }}>✕</button>
              </div>

              {/* §16 — the dimension's standing state. It belongs to the dimension, not to any
                  card or measure, and every sentence names its own subject, so it cannot be
                  misread as describing whichever measure the filter is on. */}
              <StateBand blocks={state[dim.id] ?? []} color={secColor} />

              {/* §20 — the measure is a FILTER. A credit dimension has one measure and shows no
                  strip; a payments group has five to eleven and used to stack them as tables. */}
              {measures.length > 1 && (
                <div className="mb-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span style={{ ...EYEBROW, marginRight: 4 }}>Measure</span>
                    {measures.map((m) => (
                      <button key={m} onClick={() => { setMeasure(m); setCell(null); }}
                              className="rounded-full transition-colors"
                              style={{ fontSize: FS.note, padding: "5px 11px", ...chipStyle(m === activeMeasure) }}>
                        {m}
                      </button>
                    ))}
                  </div>
                  {axes.length > 1 && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      <span style={{ ...EYEBROW, marginRight: 4 }}>Showing</span>
                      {(["value", "volume"] as const).map((a) => (
                        <button key={a} onClick={() => { setAxis(a); setCell(null); }}
                                className="rounded-full transition-colors"
                                style={{ fontSize: FS.note, padding: "5px 11px", ...chipStyle(a === axis) }}>
                          {a}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {table ? (
                <CutTable table={table} title={cut!.title} color={secColor}
                          bookLabel={cut!.bookLabel} footer={cut!.footer} all={tables}
                          active={cell} onPickCell={setCell} />
              ) : (
                // A dimension that owns no cut says so, and shows the series itself. Bank
                // Credit IS the top level: its only split is food vs non-food, an accounting
                // line rather than a mix, so there is nothing for a table to decompose.
                <>
                  {cut?.noTableNote && (
                    <p style={{ fontSize: FS.note, color: "var(--font-muted)", lineHeight: 1.55, marginBottom: 10 }}>
                      {cut.noTableNote}
                    </p>
                  )}
                  {(() => {
                    const first = notable(dim)[0];
                    return first ? renderChart(first, dim) : null;
                  })()}
                </>
              )}

              {/* §18 — the cards that survive: judgements about a SERIES ("highest on record",
                  "first growth in 11 periods"), gaps, and FY step-ups. None has a column to
                  live in, which is exactly why they are still cards. */}
              {notable(dim).length > 0 && (
                <div style={{ marginTop: 22, borderTop: "1px solid var(--border-card)", paddingTop: 16 }}>
                  <div style={{ ...EYEBROW }}>What&apos;s notable · {notable(dim).length}</div>
                  <div className="mt-3 flex flex-col gap-1">
                    {notable(dim).map((c) => {
                      const on = openCard === c.id;
                      return (
                        <div key={c.id}>
                          <button onClick={() => setOpenCard(on ? null : c.id)}
                                  className="rm-link text-left flex items-baseline gap-2 w-full py-1"
                                  style={{ fontSize: FS.lead, lineHeight: 1.45,
                                           fontWeight: c.isRead ? 600 : 400, color: "var(--font)" }}>
                            <span style={{ color: c.isRead ? secColor : "var(--font-muted)" }}>
                              {c.isRead ? "▲" : "○"}
                            </span>
                            <span>{c.title}</span>
                          </button>
                          {on && effDepth !== "brief" && (
                            <div style={{ padding: "4px 0 12px 22px" }}>
                              {c.body && <p style={{ fontSize: FS.body, lineHeight: 1.65, color: "var(--font)" }}>{c.body}</p>}
                              {c.implication && <p style={{ fontSize: FS.body, lineHeight: 1.6, color: "var(--font-muted)", marginTop: 8 }}>{c.implication}</p>}
                              {c.chain?.length ? (
                                <ol style={{ marginTop: 10 }}>
                                  {c.chain.map((s, i) => (
                                    <li key={i} className="flex gap-2.5" style={{ fontSize: FS.body, lineHeight: 1.55, color: "var(--font)", marginTop: 5 }}>
                                      <span style={{ color: secColor, fontWeight: 700 }}>{i + 1}.</span><span>{s}</span>
                                    </li>
                                  ))}
                                </ol>
                              ) : null}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {effDepth === "deep" && <div ref={deepRef} style={{ borderRadius: R.md }}>{renderDeep(dim.id, secColor)}</div>}
            </div>
          </div>

          {/* RIGHT · STATE C — the chart, in the width the rail released */}
          {cell && table && (
            <div ref={chartRef} className="mt-5 lg:mt-0 lg:col-start-2">
              <CellPanel table={tables?.[cell.stem] ?? table} cell={cell} color={secColor}
                         flowLabel={(tables?.[cell.stem] ?? table).flow_label}
                         onPick={(col: ColKey) => setCell({ ...cell, col })}
                         onClose={() => setCell(null)} />
            </div>
          )}
        </div>

        {/* ☰ — the rail slides back over, so a reader can change dimension without giving up
            the chart they opened. */}
        {railOver && (
          <>
            <div className="fixed inset-0 z-30" style={{ background: "var(--shadow)" }}
                 onClick={() => setRailOver(false)} />
            <div className="fixed z-40 top-0 bottom-0 left-0 w-[300px] overflow-y-auto"
                 style={{ ...PANEL, borderRadius: 0, paddingTop: 20 }}>{rail}</div>
          </>
        )}
      </div>
    </>
  );
}
