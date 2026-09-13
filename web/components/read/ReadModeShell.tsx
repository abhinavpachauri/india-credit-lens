"use client";

// The read-mode SHELL — pipeline-agnostic (DASHBOARD_SPEC.md §14, reshaped by §20). Owns the
// grid front door, the chip strip, the depth ladder, and all state. A pipeline supplies: its
// RMModel, its cuts, a chart renderer for the dimensions that have no table, and its deep.
//
// §20 turned the detail pane inside out. It used to be a rail of cards driving a pane that
// REDREW THE SAME TABLE with different prose beside it — the table was the constant and the
// cards the variable, and the layout had that backwards. Now the dimension is one table, the
// insights are a list beneath it, and a measure is a filter rather than another table.

import { useEffect, useMemo, useRef, useState } from "react";
import { usePersistent } from "@/hooks/usePersistent";
import {
  chipStyle,
  STYLE, PANEL, EYEBROW, READS_COLOR, glyph, REASON,
  DimensionCard, ChipStrip, DepthLadder, CutTable, StateBand,
  type RMModel, type RMCard, type RMDimension, type Depth, type ChipItem,
} from "./parts";
import { FS, R } from "@/lib/tokens";
import type { CutTables } from "@/lib/table";
import type { StateMap } from "@/lib/state";

const READS = "reads";

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
}

export default function ReadModeShell({ model, homeLabel, period, renderChart, hasDeep, renderDeep,
                                       state = {}, tables, cutsFor }: ReadModeShellProps) {
  const dimById = useMemo(() => new Map(model.dimensions.map((d) => [d.id, d])), [model]);
  const [view, setView] = useState<"grid" | "detail">("grid");
  const [activeList, setActiveList] = useState<string>(model.dimensions[0]?.id ?? READS);
  const [openCard, setOpenCard] = useState<string | null>(null);
  const [depth, setDepth] = usePersistent<Depth>("icl-depth", "full");
  const [showIndex, setShowIndex] = useState(false);
  // The measure filter's two axes, per dimension — a group's measures and the value/volume
  // choice are the reader's, and they should survive switching between dimensions.
  const [measure, setMeasure] = useState<string | null>(null);
  const [axis, setAxis] = usePersistent<"value" | "volume">("icl-axis", "value");

  const detailRef = useRef<HTMLDivElement>(null);
  const stripRef = useRef<HTMLDivElement>(null);
  const deepRef = useRef<HTMLDivElement>(null);

  const activeDim = activeList === READS ? null : dimById.get(activeList) ?? model.dimensions[0];
  const secColor = activeDim?.color ?? READS_COLOR;

  /** The cuts this dimension owns that the sidecar actually carries. */
  const cuts = useMemo(
    () => (activeDim && cutsFor ? cutsFor(activeDim.id).filter((c) => tables?.[c.stem]) : []),
    [activeDim, cutsFor, tables]);
  const measures = useMemo(() => {
    const seen: string[] = [];
    for (const c of cuts) { const m = c.measure ?? c.title; if (!seen.includes(m)) seen.push(m); }
    return seen;
  }, [cuts]);
  const activeMeasure = measure && measures.includes(measure) ? measure : measures[0];
  const forMeasure = cuts.filter((c) => (c.measure ?? c.title) === activeMeasure);
  const axes = forMeasure.map((c) => c.axis).filter(Boolean) as ("value" | "volume")[];
  const cut = forMeasure.find((c) => !c.axis || c.axis === axis) ?? forMeasure[0];

  const deepAvailable = activeDim ? hasDeep(activeDim.id) : false;
  const effDepth: Depth = depth === "deep" && !deepAvailable ? "full" : depth;
  const DEPTH_HINT: Record<Depth, string> = {
    brief: "the table only", full: "with the reasoning", deep: "the deeper reading" };

  /** The cards a dimension still renders (§18): its reads, gaps and FY step-ups — the
   *  judgements about a SERIES that a table structurally cannot make. */
  const notable = (dim: RMDimension) => dim.subjects.flatMap((s) => s.cards);
  const topRead = (dimId: string) => model.reads.find((r) => r.dimId === dimId) ?? null;
  const tableCount = (dimId: string) => (cutsFor ? cutsFor(dimId).filter((c) => tables?.[c.stem]).length : 0);

  const chips: ChipItem[] = useMemo(() => [
    ...model.dimensions.map((d) => ({ id: d.id, title: d.title, icon: d.icon, color: d.color, moved: d.moved })),
    { id: READS, title: "Everything that moved", icon: "★", color: READS_COLOR, moved: model.reads.length },
  ], [model]);

  useEffect(() => {
    if (view !== "detail") return;
    stripRef.current?.querySelector<HTMLElement>('[data-on="true"]')
      ?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  }, [activeList, view]);

  function enterDetail(listId: string, cardId?: string) {
    setActiveList(listId);
    setMeasure(null);
    setOpenCard(cardId ?? null);
    setView("detail");
    if (typeof window !== "undefined") requestAnimationFrame(() => window.scrollTo({ top: 0 }));
  }

  // ── GRID front door ──────────────────────────────────────────────────────
  // The read grid used to sit on top as five fat cards. After §20 every notable card lives
  // under its own table, so a pooled grid of five of them was the same news twice, picked by
  // a score the reader cannot see. The news is now IN the tiles — one line each, where it can
  // be acted on — and the pool survives as an index for the reader coming back after a month.
  if (view === "grid") {
    return (
      <>
        <style>{STYLE}</style>
        <div key="grid" style={{ animation: "rmfade 220ms ease" }}>
          <h2 style={{ ...EYEBROW, marginBottom: 14 }}>
            {model.dimensions.length} dimensions · {model.dimensions.reduce((n, d) => n + tableCount(d.id), 0)} tables
            {" · "}{model.reads.length} moved this {period}
          </h2>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {model.dimensions.map((d) => (
              <DimensionCard key={d.id} dim={d} state={state[d.id]} topRead={topRead(d.id)}
                             tables={tableCount(d.id)} onClick={() => enterDetail(d.id)} />
            ))}
          </div>

          <button onClick={() => setShowIndex(!showIndex)} className="rm-link mt-6"
                  style={{ fontSize: FS.body, fontWeight: 600, color: READS_COLOR }}>
            {showIndex ? "▾" : "▸"} everything that moved this {period} · {model.reads.length}
          </button>
          {showIndex && (
            <div className="mt-3 flex flex-col gap-1.5">
              {model.reads.map((r) => (
                <button key={r.id} onClick={() => enterDetail(r.dimId, r.id)}
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

  // ── DETAIL view — one table, insights below ──────────────────────────────
  return (
    <>
      <style>{STYLE}</style>
      <div key="detail" style={{ animation: "rmfade 220ms ease" }}>
        <div className="flex items-center justify-between mb-3">
          <button onClick={() => setView("grid")} className="rm-link"
                  style={{ fontSize: FS.body, fontWeight: 600, color: "var(--font-muted)" }}>‹ {homeLabel}</button>
          <div className="flex flex-col items-end">
            <DepthLadder depth={effDepth} setDepth={setDepth} deepAvailable={deepAvailable} />
            <span style={{ fontSize: FS.meta, color: "var(--font-muted)", marginTop: 4 }}>Detail: {DEPTH_HINT[effDepth]}</span>
          </div>
        </div>

        <ChipStrip chips={chips} active={activeList} stripRef={stripRef}
                   onPick={(id) => { setActiveList(id); setMeasure(null); setOpenCard(null); }} />

        {activeList === READS ? (
          <div className="mt-5" style={{ ...PANEL, padding: 20 }}>
            <div style={{ ...EYEBROW, color: READS_COLOR }}>Everything that moved · {model.reads.length} this {period}</div>
            <div className="mt-3 flex flex-col gap-2">
              {model.reads.map((r) => (
                <button key={r.id} onClick={() => enterDetail(r.dimId, r.id)}
                        className="rm-link text-left flex items-baseline gap-2"
                        style={{ fontSize: FS.lead, color: "var(--font)" }}>
                  <span style={{ color: r.color }}>{glyph(r.direction)}</span>
                  <span>{r.title}</span>
                  <span style={{ fontSize: FS.meta, color: "var(--font-muted)" }}>
                    {r.reason ? REASON[r.reason] : ""} · {r.dimTitle}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : activeDim && (
          <div ref={detailRef} className="mt-5" style={{ ...PANEL, padding: 20, borderTop: `3px solid ${secColor}` }}>
            <div style={{ ...EYEBROW, color: secColor, letterSpacing: "0.05em", marginBottom: 12 }}>
              {activeDim.icon} {activeDim.title}
            </div>

            {/* §16 — the dimension's standing state. It belongs to the dimension, not to any
                card or measure, and every sentence names its own subject, so it cannot be
                misread as describing whichever measure the filter is on. */}
            <StateBand blocks={state[activeDim.id] ?? []} color={secColor} />

            {/* §20 — the measure is a FILTER. A credit dimension has one measure and shows no
                strip; a payments group has five to eleven and used to stack them as tables. */}
            {measures.length > 1 && (
              <div className="mb-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span style={{ ...EYEBROW, marginRight: 4 }}>Measure</span>
                  {measures.map((m) => (
                    <button key={m} onClick={() => setMeasure(m)} className="rounded-full transition-colors"
                            style={{ fontSize: FS.note, padding: "5px 11px", ...chipStyle(m === activeMeasure) }}>
                      {m}
                    </button>
                  ))}
                </div>
                {axes.length > 1 && (
                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    <span style={{ ...EYEBROW, marginRight: 4 }}>Showing</span>
                    {(["value", "volume"] as const).map((a) => (
                      <button key={a} onClick={() => setAxis(a)} className="rounded-full transition-colors"
                              style={{ fontSize: FS.note, padding: "5px 11px", ...chipStyle(a === axis) }}>
                        {a}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {cut && tables?.[cut.stem] ? (
              <CutTable table={tables[cut.stem]} title={cut.title} color={secColor}
                        bookLabel={cut.bookLabel} footer={cut.footer} all={tables} />
            ) : (
              // A dimension that owns no cut keeps the chart: Bank Credit IS the top level,
              // so there is nothing to decompose and nothing for a table to say.
              (() => {
                const first = notable(activeDim)[0];
                return first ? renderChart(first, activeDim) : null;
              })()
            )}

            {/* §18 — the cards that survive: judgements about a SERIES ("highest on record",
                "first growth in 11 periods"), gaps, and FY step-ups. None has a column to
                live in, which is exactly why they are still cards. */}
            {notable(activeDim).length > 0 && (
              <div style={{ marginTop: 22, borderTop: "1px solid var(--border-card)", paddingTop: 16 }}>
                <div style={{ ...EYEBROW }}>What's notable · {notable(activeDim).length}</div>
                <div className="mt-3 flex flex-col gap-1">
                  {notable(activeDim).map((c) => {
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

            {effDepth === "deep" && <div ref={deepRef} style={{ borderRadius: R.md }}>{renderDeep(activeDim.id, secColor)}</div>}
          </div>
        )}
      </div>
    </>
  );
}
