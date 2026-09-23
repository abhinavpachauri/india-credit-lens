"use client";

// The read-mode SHELL — pipeline-agnostic (DASHBOARD_SPEC.md §14, reshaped by §20). Owns the
// three states, the rail, and which cell has a chart open. A pipeline
// supplies its RMModel, its cuts, a chart renderer for dimensions that own no table, and its
// deep reading.
//
// THREE PANES, NEVER MORE THAN TWO AT ONCE, AND EACH CLOSE POPS EXACTLY ONE LEVEL:
//
//   A  dimensions            every dimension as a tile, each carrying its own news
//   B  dimensions + table    the tiles compress into a rail; the table is the child
//   C  table + chart         the table compresses into a row list; the chart is the child
//
// THE CHILD ALWAYS TAKES THE LARGER SHARE, and the parent compresses into a list of its own
// children — which is the one compression that loses nothing the reader was using, because
// what a parent pane is FOR at that moment is changing their mind about which child they
// wanted. Three panes at once was the version that had a hamburger; the hamburger existed
// only to hide a pane that should not have been open.

import { useEffect, useMemo, useRef, useState } from "react";
import { usePersistent } from "@/hooks/usePersistent";
import {
  chipStyle,
  STYLE, PANEL, EYEBROW, READS_COLOR, tint, glyph, REASON,
  DimensionCard, RailItem, CutTable, CutRowList, CellPanel, StateBand,
  type RMModel, type RMCard, type RMDimension, type RMRead, type CellRef,
} from "./parts";
import { FS, R, GLYPH } from "@/lib/tokens";
import { loadBankTable, type CutTables, type CutTable as CutTableData,
         type BankIndex, type ColKey } from "@/lib/table";
import type { StateMap } from "@/lib/state";

/** Every read a dimension has, on its own tile. It was capped at three with the rest behind a
 *  count — but a count is not the news, and a reader deciding which dimension to open needs the
 *  items, not their number. The grid drops to two columns to give them the width; nine lines on
 *  a wide tile reads, nine lines squeezed into a third of the screen does not. */
const TILE_READS = Infinity;

/** The deeper reading (Layer 2/3) is OFF while Layer 1 is being got right: the causal layer is
 *  a different argument and it competes for the same attention. Display only — the opportunities
 *  feed is still built, still gated, still on /opportunities. Reversed by flipping this. */
const DEEP_ENABLED = false;

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
  /** §20 — which measures have a bank breakout, and where to fetch it (metric → entry). */
  bankIndex?: BankIndex;
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
  /** The CSV metric this cut measures — how a bank breakout is found for it (§20). */
  metricKey?: string;
  /** Named because a share is meaningless without it (§15). Omitted when the cut has none. */
  bookLabel?: string;
  footer?: string;
  /** Why this dimension has no table at all, in its own words. Bank Credit is the top level:
   *  its only split is food vs non-food, which is an accounting line and not a mix. A pane
   *  that simply omits the table reads as broken. */
  noTableNote?: string;
}

export default function ReadModeShell({ model, homeLabel, period, renderChart, hasDeep, renderDeep,
                                       state = {}, tables, bankIndex = {}, cutsFor }: ReadModeShellProps) {
  const dimById = useMemo(() => new Map(model.dimensions.map((d) => [d.id, d])), [model]);

  const [openDim, setOpenDim] = useState<string | null>(null);       // null = state A
  const [cell, setCell] = useState<CellRef | null>(null);            // non-null = state C
  const [openCard, setOpenCard] = useState<string | null>(null);
  const [deepOpen, setDeepOpen] = useState(false);
  // Which sub-cut a row has opened (SIBC §19). The band stacks that cut's own state under
  // the parent's, because the parent table is still on screen above it.
  const [subCut, setSubCut] = useState<string | null>(null);
  const [showIndex, setShowIndex] = useState(false);
  const [measure, setMeasure] = useState<string | null>(null);
  const [byBank, setByBank] = useState(false);
  // The fetched breakout, if the reader has asked for one. Held here rather than in the table
  // so that closing and reopening a measure does not re-fetch what is already in hand.
  const [bankTable, setBankTable] = useState<CutTableData | null>(null);
  const [axis, setAxis] = usePersistent<"value" | "volume">("icl-axis", "value");

  const detailRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const deepRef = useRef<HTMLDivElement>(null);

  // Does this pipeline HAVE a news layer? NBFC generates no cards by design, so every
  // card-shaped affordance — the moved count, the index of everything that moved — would be
  // offering a reader something that was never written.
  const hasCardLayer = model.dimensions.some((d) => d.cardCount > 0) || model.reads.length > 0;

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
  // A bank breakout is the same table at a different LEVEL, so it replaces the table rather
  // than nesting inside a row: the 63 banks are not children of the five categories on screen,
  // they are what those categories are made of.
  const bankEntry = cut?.metricKey ? bankIndex[cut.metricKey] : undefined;
  const table = byBank && bankTable ? bankTable : (cut && tables?.[cut.stem]);

  // Fetch the breakout the first time it is asked for, and drop it when the reader moves to a
  // measure that has a different one — a stale table under a new heading is the worst outcome.
  useEffect(() => {
    if (!byBank || !bankEntry) { setBankTable(null); return; }
    let live = true;
    loadBankTable(bankEntry).then((t) => { if (live) setBankTable(t); });
    return () => { live = false; };
  }, [byBank, bankEntry]);

  const deepAvailable = DEEP_ENABLED && dim ? hasDeep(dim.id) : false;

  /** The state blocks to show: the cut on screen, plus an expanded sub-cut's own. Falls back
   *  to whatever the dimension declares, so a dimension whose cut has no state (or no table at
   *  all, like Bank Credit) still renders its band rather than going quiet. */
  const dimBlocks = (dim && state[dim.id]) || [];
  const onScreen = dimBlocks.filter((b) => b.stem === (byBank && bankEntry ? bankEntry.cut : cut?.stem));
  const stacked = subCut ? dimBlocks.filter((b) => b.stem === subCut) : [];
  const bandBlocks = [...(onScreen.length ? onScreen : dimBlocks.filter((b) => b.anchor)),
                      ...stacked];

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
      if (cell) setCell(null);
      else if (openDim) setOpenDim(null);
    };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [cell, openDim]);

  function enter(dimId: string, cardId?: string) {
    setOpenDim(dimId);
    setMeasure(null);
    setCell(null);
    setOpenCard(cardId ?? null);
    setDeepOpen(false);
    setSubCut(null);
    if (typeof window !== "undefined") requestAnimationFrame(() => window.scrollTo({ top: 0 }));
  }
  function pickDim(dimId: string) {
    setOpenDim(dimId); setMeasure(null); setCell(null); setOpenCard(null);
    setByBank(false); setDeepOpen(false); setSubCut(null);
  }

  // ── STATE A · the landing grid ───────────────────────────────────────────
  if (!dim) {
    return (
      <>
        <style>{STYLE}</style>
        <div key="grid" style={{ animation: "rmfade 220ms ease" }}>
          {/* "0 moved this Jul 2026" is what a QUIET month looks like. A pipeline with no card
              layer at all has not had a quiet month — it has never been asked the question —
              and the two must not render the same. Same rule as the tile footer. */}
          <h2 style={{ ...EYEBROW, marginBottom: 14 }}>
            {model.dimensions.length} dimensions ·{" "}
            {model.dimensions.reduce((n, d) => n + tableCount(d.id), 0)} tables
            {hasCardLayer && <> · {model.reads.length} moved this {period}</>}
          </h2>
          <div className="grid gap-4 grid-cols-1 lg:grid-cols-2 items-stretch">
            {model.dimensions.map((d) => (
              <DimensionCard key={d.id} dim={d} state={(state[d.id] ?? []).filter((b) => b.anchor)}
                             reads={readsOf(d.id).slice(0, TILE_READS)}
                             period={period}
                             tables={tableCount(d.id)} onClick={() => enter(d.id)} />
            ))}
          </div>

          {hasCardLayer && (
            <button onClick={() => setShowIndex(!showIndex)} className="rm-link mt-6"
                    style={{ fontSize: FS.body, fontWeight: 600, color: READS_COLOR }}>
              {showIndex ? "▾" : "▸"} everything that moved this {period} · {model.reads.length}
            </button>
          )}
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
        <RailItem key={d.id} dim={d} state={(state[d.id] ?? []).filter((b) => b.anchor)}
                  selected={d.id === dim.id}
                  onClick={() => pickDim(d.id)} />
      ))}
    </div>
  );

  return (
    <>
      <style>{STYLE}</style>
      <div key="detail" style={{ animation: "rmfade 220ms ease" }}>
        <div className={`lg:grid lg:gap-6 lg:items-start ${
          cell ? "lg:grid-cols-[260px_minmax(0,1fr)]" : "lg:grid-cols-[300px_minmax(0,1fr)]"}`}>
          {/* LEFT · the PARENT, compressed. In B that is the dimensions; in C it is this
              dimension's own rows. Never both — two panes, and the child gets the width. */}
          <div className="hidden lg:block lg:col-start-1">
            {cell && table
              ? <div style={{ ...PANEL, padding: 14, position: "sticky", top: 12 }}>
                  <CutRowList table={tables?.[cell.stem] ?? table} title={cut?.title ?? dim.title}
                              cell={cell} color={secColor} onPick={setCell} />
                </div>
              : rail}
          </div>

          {/* RIGHT · the CHILD — the table in B, the chart in C */}
          {!cell && (
          <div ref={detailRef} className="lg:col-start-2 mt-5 lg:mt-0">
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
              {/* §16 — the standing state OF THE CUT ON SCREEN. It was the dimension's anchor
                  always, so switching to eCommerce Transactions left a band describing cards in
                  force: not wrong, since every sentence names its own subject, but the right
                  state existed and was withheld. Layer 2 computes 40 mix states and ten reached
                  a browser.

                  A measure SWAPS the band (the table is fully replaced); an expanded row STACKS
                  a second block (the parent table is still above it). */}
              <StateBand blocks={bandBlocks} color={secColor} />

              {/* §18 — the cards that survive: judgements about a SERIES ("highest on record",
                  "first growth in 11 periods"), gaps, and FY step-ups. None has a column to
                  live in, which is exactly why they are still cards. */}
              {notable(dim).length > 0 && (
                <div style={{ marginBottom: 20, paddingBottom: 16,
                              borderBottom: "1px solid var(--border-card)" }}>
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
                          {on && (
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


              {/* §20 — the measure is a FILTER. A credit dimension has one measure and shows no
                  strip; a payments group has five to eleven and used to stack them as tables. */}
              {measures.length > 1 && (
                <div className="mb-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span style={{ ...EYEBROW, marginRight: 4 }}>Measure</span>
                    {measures.map((m) => (
                      <button key={m} onClick={() => { setMeasure(m); setCell(null); setByBank(false); setSubCut(null); }}
                              className="rounded-full transition-colors"
                              style={{ fontSize: FS.note, padding: "5px 11px", ...chipStyle(m === activeMeasure) }}>
                        {m}
                      </button>
                    ))}
                  </div>
                  {bankEntry && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      <span style={{ ...EYEBROW, marginRight: 4 }}>Break out by</span>
                      {([false, true] as const).map((b) => (
                        <button key={String(b)} onClick={() => { setByBank(b); setCell(null); }}
                                className="rounded-full transition-colors"
                                style={{ fontSize: FS.note, padding: "5px 11px", ...chipStyle(b === byBank) }}>
                          {b ? `bank (${bankEntry.parts})` : "bank category"}
                        </button>
                      ))}
                    </div>
                  )}
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
                          active={cell} onPickCell={setCell} onExpand={setSubCut} />
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

              {/* The deeper reading, where one exists. It used to be the third rung of a
                  Brief/Full/Deep ladder — but the notable list expands on click, so two of
                  those rungs controlled nothing a click did not already control, and a
                  three-way switch for one real choice is a control explaining itself. */}
              {deepAvailable && (
                <div ref={deepRef} style={{ marginTop: 20, borderTop: "1px solid var(--border-card)", paddingTop: 14 }}>
                  <button onClick={() => setDeepOpen(!deepOpen)} className="rm-link"
                          style={{ ...EYEBROW, color: secColor }}>
                    {deepOpen ? "▾" : "▸"} The deeper reading ⌁
                  </button>
                  {deepOpen && <div style={{ borderRadius: R.md, marginTop: 10 }}>{renderDeep(dim.id, secColor)}</div>}
                </div>
              )}
            </div>
          </div>
          )}

          {/* STATE C · the chart is the child, so it takes the column the table was in */}
          {cell && table && (
            <div ref={chartRef} className="mt-5 lg:mt-0 lg:col-start-2 lg:row-start-1">
              <CellPanel table={tables?.[cell.stem] ?? table} cell={cell} color={secColor}
                         flowLabel={(tables?.[cell.stem] ?? table).flow_label}
                         onPick={(col: ColKey) => setCell({ ...cell, col })}
                         onClose={() => setCell(null)} />
            </div>
          )}
        </div>

      </div>
    </>
  );
}
