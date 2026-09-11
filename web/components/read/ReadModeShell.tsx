"use client";

// The read-mode SHELL — pipeline-agnostic (DASHBOARD_SPEC.md §14). Owns the grid front door, the
// three-nav chrome (chip strip / single-list rail / breadcrumb), depth ladder, and all state.
// A pipeline supplies: its RMModel, a chart renderer, and its deep (opportunities) — nothing else.

import { useEffect, useMemo, useRef, useState } from "react";
import { usePersistent } from "@/hooks/usePersistent";
import {
  STYLE, PANEL, EYEBROW, READS_COLOR, tint, vars, glyph, REASON,
  ReadCard, DimensionCard, ChipStrip, DepthLadder, StateBand,
  type RMModel, type RMCard, type RMDimension, type Depth, type ChipItem,
} from "./parts";
import { FS, R } from "@/lib/tokens";
import type { StateMap } from "@/lib/state";

const READS = "reads";
const READ_CAP = 5;

export interface ReadModeShellProps {
  model: RMModel;
  homeLabel: string;
  period: string;                                             // e.g. "May"
  /** render the view label + chart for the selected card (the adapter owns chart state). */
  renderChart: (card: RMCard, dim: RMDimension) => React.ReactNode;
  hasDeep: (dimId: string) => boolean;
  renderDeep: (dimId: string, color: string) => React.ReactNode;
  /** dimension id → its standing state blocks (§16). Absent dimensions simply show none. */
  state?: StateMap;
}

export default function ReadModeShell({ model, homeLabel, period, renderChart, hasDeep, renderDeep, state = {} }: ReadModeShellProps) {
  const cardById = useMemo(() => {
    const m = new Map<string, { card: RMCard; dim: RMDimension }>();
    for (const dim of model.dimensions)
      for (const sub of dim.subjects)
        for (const card of sub.cards) m.set(card.id, { card, dim });
    return m;
  }, [model]);
  const dimById = useMemo(() => new Map(model.dimensions.map((d) => [d.id, d])), [model]);

  const firstId = model.reads[0]?.id ?? model.dimensions[0]?.subjects[0]?.cards[0]?.id ?? "";
  const [view, setView] = useState<"grid" | "detail">("grid");
  const [selId, setSelId] = useState(firstId);
  const [activeList, setActiveList] = useState<string>(READS);
  const [depth, setDepth] = usePersistent<Depth>("icl-depth", "full");
  const [showAll, setShowAll] = useState(false);

  const detailRef = useRef<HTMLDivElement>(null);
  const stripRef = useRef<HTMLDivElement>(null);
  const whyRef = useRef<HTMLDivElement>(null);
  const deepRef = useRef<HTMLDivElement>(null);
  const prevDepth = useRef<Depth>(depth);

  const sel = cardById.get(selId);
  const selCard = sel?.card ?? null;
  const selDim = sel?.dim ?? model.dimensions[0];
  const secColor = selDim?.color ?? READS_COLOR;

  const shownReads = showAll ? model.reads : model.reads.slice(0, READ_CAP);
  const overflow = model.reads.length - shownReads.length;
  const totalInsights = model.dimensions.reduce((n, d) => n + d.cardCount, 0);

  const chips: ChipItem[] = useMemo(() => [
    { id: READS, title: "What moved", icon: "★", color: READS_COLOR, moved: model.reads.length },
    ...model.dimensions.map((d) => ({ id: d.id, title: d.title, icon: d.icon, color: d.color, moved: d.moved })),
  ], [model]);

  const deepAvailable = selDim ? hasDeep(selDim.id) : false;
  const effDepth: Depth = depth === "deep" && !deepAvailable ? "full" : depth;
  const DEPTH_HINT: Record<Depth, string> = { brief: "chart only", full: "with the reasoning", deep: "the deeper reading" };

  useEffect(() => {
    if (view !== "detail") return;
    stripRef.current?.querySelector<HTMLElement>('[data-on="true"]')
      ?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  }, [activeList, view]);

  useEffect(() => {
    const order = { brief: 0, full: 1, deep: 2 };
    const grew = order[effDepth] > order[prevDepth.current];
    prevDepth.current = effDepth;
    if (!grew || view !== "detail") return;
    const target = effDepth === "deep" ? deepRef.current : whyRef.current;
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.animate?.([{ backgroundColor: tint(secColor, 0.2) }, { backgroundColor: "transparent" }],
      { duration: 900, easing: "ease-out" });
  }, [effDepth, view, secColor]);

  function firstOfList(listId: string) {
    if (listId === READS) return model.reads[0]?.id ?? firstId;
    const d = dimById.get(listId);
    const readInDim = model.reads.find((r) => r.dimId === listId);
    return readInDim?.id ?? d?.subjects[0]?.cards[0]?.id ?? firstId;
  }
  function scrollChartIntoView() {
    if (typeof window !== "undefined") setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  }
  function enterDetail(listId: string, cardId?: string) {
    setActiveList(listId);
    setSelId(cardId ?? firstOfList(listId));
    setView("detail");
    if (typeof window !== "undefined") window.innerWidth < 1024 ? scrollChartIntoView() : requestAnimationFrame(() => window.scrollTo({ top: 0 }));
  }
  function pickList(listId: string) { setActiveList(listId); setSelId(firstOfList(listId)); setShowAll(false); }
  function selectCard(cardId: string) { setSelId(cardId); scrollChartIntoView(); }

  // ── GRID front door ──────────────────────────────────────────────────────
  if (view === "grid") {
    return (
      <>
        <style>{STYLE}</style>
        <div key="grid" style={{ animation: "rmfade 220ms ease" }}>
          <h2 style={{ ...EYEBROW, marginBottom: 14 }}>The read · {model.reads.length} moved this {period}</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {shownReads.length === 0 && (
              <p style={{ ...PANEL, fontSize: FS.lead, color: "var(--font-muted)" }}>
                Nothing crossed the news threshold this {period} — a quiet month. Browse dimensions below.
              </p>
            )}
            {shownReads.map((r) => <ReadCard key={r.id} read={r} selected={false} onClick={() => enterDetail(READS, r.id)} />)}
          </div>
          {overflow > 0 && !showAll && (
            <button className="py-1 mt-2" style={{ fontSize: FS.body, fontWeight: 600, color: READS_COLOR }}
                    onClick={() => setShowAll(true)}>+{overflow} more moved →</button>
          )}

          <h2 style={{ ...EYEBROW, margin: "34px 0 14px" }}>Browse · {model.dimensions.length} dimensions · {totalInsights} insights</h2>
          <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {model.dimensions.map((d) => (
              <DimensionCard key={d.id} dim={d} state={state[d.id]} onClick={() => enterDetail(d.id)} />
            ))}
          </div>
        </div>
      </>
    );
  }

  // ── DETAIL view ──────────────────────────────────────────────────────────
  const activeDim = activeList === READS ? null : dimById.get(activeList);

  return (
    <>
      <style>{STYLE}</style>
      <div key="detail" style={{ animation: "rmfade 220ms ease" }}>
        <div className="flex items-center justify-between mb-3">
          <button onClick={() => { setShowAll(false); setView("grid"); }} className="rm-link"
                  style={{ fontSize: FS.body, fontWeight: 600, color: "var(--font-muted)" }}>‹ {homeLabel}</button>
          <div className="flex flex-col items-end">
            <DepthLadder depth={effDepth} setDepth={setDepth} deepAvailable={deepAvailable} />
            <span style={{ fontSize: FS.meta, color: "var(--font-muted)", marginTop: 4 }}>Detail: {DEPTH_HINT[effDepth]}</span>
          </div>
        </div>

        <ChipStrip chips={chips} active={activeList} stripRef={stripRef} onPick={pickList} />

        <div className="mt-5 lg:grid lg:grid-cols-[360px_minmax(0,1fr)] lg:gap-7 lg:items-start">
          {/* LEFT · the active list */}
          <div className="lg:col-start-1">
            {activeList === READS ? (
              <>
                <h2 style={{ ...EYEBROW, marginBottom: 12 }}>What moved · {model.reads.length} this {period}</h2>
                <div className="flex flex-col gap-2.5">
                  {shownReads.map((r) => <ReadCard key={r.id} read={r} selected={r.id === selId} onClick={() => selectCard(r.id)} />)}
                  {overflow > 0 && !showAll && (
                    <button className="text-left py-1" style={{ fontSize: FS.body, fontWeight: 600, color: READS_COLOR }}
                            onClick={() => setShowAll(true)}>+{overflow} more moved →</button>
                  )}
                </div>
              </>
            ) : activeDim ? (
              <>
                <h2 style={{ ...EYEBROW, marginBottom: 12 }}>
                  {activeDim.title} · {activeDim.cardCount} insights{activeDim.moved > 0 && ` · ▲ ${activeDim.moved} moved`}
                </h2>
                <div className="flex flex-col gap-1.5">
                  {activeDim.subjects.map((sub) => (
                    <div key={sub.name || "_"} className="mb-1">
                      {sub.name && <div style={{ fontSize: FS.label, fontWeight: 600, color: "var(--font-muted)", margin: "6px 0 5px 2px" }}>{sub.name}</div>}
                      {sub.cards.map((c) => {
                        const isSel = c.id === selId;
                        return (
                          <button key={c.id} onClick={() => selectCard(c.id)}
                                  className={`rm-flat w-full text-left rounded-md px-3 py-2 mb-1.5 flex items-start gap-2${isSel ? " sel" : ""}`}
                                  style={{ ...vars(activeDim.color, tint(activeDim.color, 0.1)), fontSize: FS.body, fontWeight: isSel || c.isRead ? 600 : 400, color: "var(--font)" }}>
                            {c.isRead && <span style={{ color: activeDim.color, fontSize: FS.label, lineHeight: 1.6 }}>▲</span>}
                            <span>{c.title}</span>
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </div>

          {/* RIGHT · DETAIL */}
          <div ref={detailRef} className="mt-6 lg:mt-0 lg:col-start-2">
            <div style={{ ...PANEL, padding: 20, borderTop: `3px solid ${secColor}` }}>
              <div style={{ ...EYEBROW, color: secColor, letterSpacing: "0.05em", marginBottom: 12 }}>{selDim?.icon} {selDim?.title}</div>

              {/* §16 — the dimension's standing state, above the card it frames. Rendered at
                  every depth including Brief: chart + state is the fastest honest answer. */}
              <StateBand blocks={selDim ? (state[selDim.id] ?? []) : []} color={secColor} />

              <h3 style={{ fontSize: FS.title, fontWeight: 700, lineHeight: 1.25, color: "var(--font)", margin: "6px 0 14px" }}>
                {selCard?.title ?? "Select a read"}
              </h3>

              {selCard && selDim && renderChart(selCard, selDim)}

              {selDim && selDim.compositionTitles.length > 0 && (
                <p style={{ fontSize: FS.note, lineHeight: 1.55, color: "var(--font-muted)", marginTop: 12 }}>
                  <span style={{ fontWeight: 600 }}>Composition: </span>{selDim.compositionTitles.join(" · ")}
                </p>
              )}

              {effDepth !== "brief" && selCard && (
                <div ref={whyRef} style={{ borderRadius: R.md }}>
                  {selCard.body && <p style={{ fontSize: FS.card, lineHeight: 1.65, color: "var(--font)", marginTop: 16 }}>{selCard.body}</p>}
                  {selCard.implication && <p style={{ fontSize: FS.body, lineHeight: 1.6, color: "var(--font-muted)", marginTop: 10 }}>{selCard.implication}</p>}
                  {selCard.chain?.length ? (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ ...EYEBROW, letterSpacing: "0.05em" }}>Why this reads</div>
                      <ol style={{ marginTop: 6 }}>
                        {selCard.chain.map((s, i) => (
                          <li key={i} className="flex gap-2.5" style={{ fontSize: FS.lead, lineHeight: 1.55, color: "var(--font)", marginTop: 6 }}>
                            <span style={{ color: secColor, fontWeight: 700 }}>{i + 1}.</span><span>{s}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
                </div>
              )}
              {effDepth === "deep" && selDim && <div ref={deepRef} style={{ borderRadius: R.md }}>{renderDeep(selDim.id, secColor)}</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
