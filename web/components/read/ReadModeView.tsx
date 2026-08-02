"use client";

// Read mode — Option A + grid front-door + chip navigation (DASHBOARD_SPEC.md §14).
// Three navigations, three controls (the rail used to do all three at once → overload):
//   nav 1 · between items in a list  → the left rail (ONE dimension's cards, or the reads)
//   nav 2 · switch list              → the horizontal DIMENSION CHIP strip (★ What moved + N dims)
//   nav 3 · to the dashboard         → the ‹ home breadcrumb (back to the grid front door)
// Colour = section (SEC_COLORS): a card's colour is also its chart-line colour. Mobile = one column.

import { useEffect, useMemo, useRef, useState } from "react";
import type { Report, Annotation } from "@/lib/types";
import {
  organizeReadMode, type PlanesMap, type ReadEntry, type ReadReason, type Direction, type SectionView,
} from "@/lib/planes";
import { opportunitiesFor } from "@/lib/opportunities";
import { SEC_COLORS } from "@/lib/theme";
import { usePersistent } from "@/hooks/usePersistent";
import SectionCard from "@/components/SectionCard";
import TrendChart from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";

type Depth = "brief" | "full" | "deep";
type View = "grid" | "detail";
const READS = "reads";              // the id of the "★ What moved" pseudo-list

const READ_CAP = 5;

// Card visuals live in CSS so :hover applies — inline border/box-shadow win specificity over :hover
// and silently kill it. Dynamic bits come in as the --sec (section colour) / --sel (selected tint) props.
const STYLE = `
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

const REASON: Record<ReadReason, string> = { record: "record", reversal: "reversal", surge: "surge", shift: "shift" };
const glyph = (d: Direction | null) => (d === "up" ? "▲" : d === "down" ? "▼" : "•");

function tint(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}
function vars(col: string, sel?: string): React.CSSProperties {
  return { ["--sec" as string]: col, ["--sel" as string]: sel ?? "transparent" } as React.CSSProperties;
}

const PANEL: React.CSSProperties = {
  background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: 12, padding: 18,
};
const EYEBROW: React.CSSProperties = {
  fontSize: 13, fontWeight: 600, letterSpacing: "0.06em", color: "var(--font-muted)", textTransform: "uppercase",
};
const READS_COLOR = "#4e8ef7";

export default function ReadModeView(
  { report, planes, homeLabel = "Dashboard" }: { report: Report; planes: PlanesMap; homeLabel?: string },
) {
  const model = useMemo(() => organizeReadMode(report, planes), [report, planes]);

  const firstId = model.reads[0]?.card.id ?? model.sections[0]?.subjects[0]?.cards[0]?.id ?? "";
  const [view, setView] = useState<View>("grid");
  const [selId, setSelId] = useState(firstId);
  const [activeList, setActiveList] = useState<string>(READS);   // "reads" or a section id
  const [depth, setDepth] = usePersistent<Depth>("icl-depth", "full");
  const [showAll, setShowAll] = useState(false);

  const detailRef = useRef<HTMLDivElement>(null);
  const stripRef = useRef<HTMLDivElement>(null);
  const whyRef = useRef<HTMLDivElement>(null);
  const deepRef = useRef<HTMLDivElement>(null);
  const prevDepth = useRef<Depth>(depth);

  const selected = useMemo(() => findCard(model.sections, selId), [model, selId]);
  const section = selected?.section ?? report.sections[0];
  const card = selected?.card ?? null;
  const secColor = SEC_COLORS[section.accentIndex] ?? "#4e8ef7";

  // Deep is only offered where there's actually an opportunity to open into. Elsewhere the ladder
  // shows Brief/Full only, and a sticky "deep" preference falls back to Full for rendering.
  const opps = useMemo(() => opportunitiesFor("sibc", section.id), [section.id]);
  const hasOpps = opps.length > 0;
  const effDepth: Depth = depth === "deep" && !hasOpps ? "full" : depth;
  const DEPTH_HINT: Record<Depth, string> = {
    brief: "chart only", full: "with the reasoning", deep: "with what it opens",
  };

  const shownReads = showAll ? model.reads : model.reads.slice(0, READ_CAP);
  const overflow = model.reads.length - shownReads.length;
  const period = report.latestDate?.split(" ")[0] ?? "period";

  const movedBySection = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of model.reads) m.set(r.section.id, (m.get(r.section.id) ?? 0) + 1);
    return m;
  }, [model.reads]);
  const readIds = useMemo(() => new Set(model.reads.map((r) => r.card.id)), [model.reads]);
  const totalInsights = model.sections.reduce((n, sv) => n + sv.cardCount, 0);

  // The chip strip: ★ What moved, then every dimension.
  const chips = useMemo(() => [
    { id: READS, title: "What moved", icon: "★", color: READS_COLOR, moved: model.reads.length },
    ...model.sections.map((sv) => ({
      id: sv.section.id, title: sv.section.title, icon: sv.section.icon,
      color: SEC_COLORS[sv.section.accentIndex] ?? "#4e8ef7", moved: movedBySection.get(sv.section.id) ?? 0,
    })),
  ], [model.sections, model.reads.length, movedBySection]);

  // Keep the active chip in view when the list changes (it may be off-screen after a grid entry).
  useEffect(() => {
    if (view !== "detail") return;
    stripRef.current?.querySelector<HTMLElement>('[data-on="true"]')
      ?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  }, [activeList, view]);

  // When the depth increases, bring the newly-revealed block into view and flash it — so it's
  // obvious what each level added (the whole point of the ladder was invisible otherwise).
  useEffect(() => {
    const order = { brief: 0, full: 1, deep: 2 };
    const grew = order[effDepth] > order[prevDepth.current];
    prevDepth.current = effDepth;
    if (!grew || view !== "detail") return;
    const target = effDepth === "deep" ? deepRef.current : whyRef.current;
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.animate?.(
      [{ backgroundColor: tint(secColor, 0.2) }, { backgroundColor: "transparent" }],
      { duration: 900, easing: "ease-out" },
    );
  }, [effDepth, view, secColor]);

  function firstOfList(listId: string) {
    if (listId === READS) return model.reads[0]?.card.id ?? firstId;
    const sv = model.sections.find((s) => s.section.id === listId);
    const readInSec = model.reads.find((r) => r.section.id === listId);
    return readInSec?.card.id ?? sv?.subjects[0]?.cards[0]?.id ?? firstId;
  }
  function scrollChartIntoView() {
    if (typeof window !== "undefined") {
      setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    }
  }
  function enterDetail(listId: string, cardId?: string) {
    setActiveList(listId);
    setSelId(cardId ?? firstOfList(listId));
    setView("detail");
    if (typeof window !== "undefined") {
      window.innerWidth < 1024 ? scrollChartIntoView() : requestAnimationFrame(() => window.scrollTo({ top: 0 }));
    }
  }
  function pickList(listId: string) {          // nav 2 — a chip: switch which list the rail shows
    setActiveList(listId);
    setSelId(firstOfList(listId));
    setShowAll(false);
  }
  function selectCard(cardId: string) {        // nav 1 — a rail item: change the detail, stay in the list
    setSelId(cardId);
    scrollChartIntoView();
  }

  const pm = card?.preferredMode ?? null;
  const isDist = pm === "share";
  const trendMode: "absolute" | "yoy" | "fy" = pm === "yoy" || pm === "fy" ? pm : "absolute";
  const viewLabel = isDist
    ? "📊 Distribution · % share"
    : `📈 Trend · ${trendMode === "yoy" ? "YoY %" : trendMode === "fy" ? "FY cumulative" : "₹ absolute"}`;

  // ── GRID front door ──────────────────────────────────────────────────────
  if (view === "grid") {
    return (
      <>
        <style>{STYLE}</style>
        <div key="grid" style={{ animation: "rmfade 220ms ease" }}>
          <h2 style={{ ...EYEBROW, marginBottom: 14 }}>The read · {model.reads.length} moved this {period}</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {shownReads.length === 0 && (
              <p style={{ ...PANEL, fontSize: 15, color: "var(--font-muted)" }}>
                Nothing crossed the news threshold this {period} — a quiet month. Browse dimensions below.
              </p>
            )}
            {shownReads.map((r) => (
              <ReadCard key={r.card.id} entry={r} selected={false} onClick={() => enterDetail(READS, r.card.id)} />
            ))}
          </div>
          {overflow > 0 && !showAll && (
            <button className="py-1 mt-2" style={{ fontSize: 14, fontWeight: 600, color: READS_COLOR }}
                    onClick={() => setShowAll(true)}>+{overflow} more moved →</button>
          )}

          <h2 style={{ ...EYEBROW, margin: "34px 0 14px" }}>
            Browse · {model.sections.length} dimensions · {totalInsights} insights
          </h2>
          <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {model.sections.map((sv) => (
              <DimensionCard key={sv.section.id} sv={sv} moved={movedBySection.get(sv.section.id) ?? 0}
                             onClick={() => enterDetail(sv.section.id)} />
            ))}
          </div>
        </div>
      </>
    );
  }

  // ── DETAIL view ──────────────────────────────────────────────────────────
  const activeSV = activeList === READS ? null : model.sections.find((s) => s.section.id === activeList);

  return (
    <>
      <style>{STYLE}</style>
      <div key="detail" style={{ animation: "rmfade 220ms ease" }}>
        {/* breadcrumb: home (nav 3) + depth */}
        <div className="flex items-center justify-between mb-3">
          <button onClick={() => { setShowAll(false); setView("grid"); }} className="rm-link"
                  style={{ fontSize: 14, fontWeight: 600, color: "var(--font-muted)" }}>
            ‹ {homeLabel}
          </button>
          <div className="flex flex-col items-end">
            <DepthLadder depth={effDepth} setDepth={setDepth} deepAvailable={hasOpps} />
            <span style={{ fontSize: 11.5, color: "var(--font-muted)", marginTop: 4 }}>Detail: {DEPTH_HINT[effDepth]}</span>
          </div>
        </div>

        {/* dimension chips (nav 2) */}
        <ChipStrip chips={chips} active={activeList} stripRef={stripRef} onPick={pickList} />

        <div className="mt-5 lg:grid lg:grid-cols-[360px_minmax(0,1fr)] lg:gap-7 lg:items-start">
          {/* LEFT · the active list (nav 1) */}
          <div className="lg:col-start-1">
            {activeList === READS ? (
              <>
                <h2 style={{ ...EYEBROW, marginBottom: 12 }}>What moved · {model.reads.length} this {period}</h2>
                <div className="flex flex-col gap-2.5">
                  {shownReads.map((r) => (
                    <ReadCard key={r.card.id} entry={r} selected={r.card.id === selId}
                              onClick={() => selectCard(r.card.id)} />
                  ))}
                  {overflow > 0 && !showAll && (
                    <button className="text-left py-1" style={{ fontSize: 14, fontWeight: 600, color: READS_COLOR }}
                            onClick={() => setShowAll(true)}>+{overflow} more moved →</button>
                  )}
                </div>
              </>
            ) : activeSV ? (
              <>
                <h2 style={{ ...EYEBROW, marginBottom: 12 }}>
                  {activeSV.section.title} · {activeSV.cardCount} insights
                  {(movedBySection.get(activeList) ?? 0) > 0 && ` · ▲ ${movedBySection.get(activeList)} moved`}
                </h2>
                <div className="flex flex-col gap-1.5">
                  {activeSV.subjects.map((sub) => {
                    const col = SEC_COLORS[activeSV.section.accentIndex] ?? "#4e8ef7";
                    return (
                      <div key={sub.name || "_"} className="mb-1">
                        {sub.name && (
                          <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--font-muted)", margin: "6px 0 5px 2px" }}>{sub.name}</div>
                        )}
                        {sub.cards.map((c) => {
                          const isMoved = readIds.has(c.id);
                          const isSel = c.id === selId;
                          return (
                            <button key={c.id} onClick={() => selectCard(c.id)}
                                    className={`rm-flat w-full text-left rounded-md px-3 py-2 mb-1.5 flex items-start gap-2${isSel ? " sel" : ""}`}
                                    style={{ ...vars(col, tint(col, 0.1)), fontSize: 14.5, fontWeight: isSel || isMoved ? 600 : 400, color: "var(--font)" }}>
                              {isMoved && <span style={{ color: col, fontSize: 12, lineHeight: 1.6 }}>▲</span>}
                              <span>{c.title}</span>
                            </button>
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
              </>
            ) : null}
          </div>

          {/* RIGHT · DETAIL */}
          <div ref={detailRef} className="mt-6 lg:mt-0 lg:col-start-2">
            <div style={{ ...PANEL, padding: 20, borderTop: `3px solid ${secColor}` }}>
              <div style={{ ...EYEBROW, color: secColor, letterSpacing: "0.05em" }}>{section.icon} {section.title}</div>
              <h3 style={{ fontSize: 24, fontWeight: 700, lineHeight: 1.25, color: "var(--font)", margin: "6px 0 14px" }}>
                {card?.title ?? "Select a read"}
              </h3>

              <div className="mb-3" style={{ fontSize: 13, fontWeight: 600, color: "var(--font-muted)" }}>{viewLabel}</div>

              <SectionCard accentColor={secColor} bare>
                {isDist ? (
                  <DistributionChart absoluteData={section.absoluteData}
                    seriesNames={section.distributionSeriesNames ?? section.seriesNames}
                    pctLabel={section.pctLabel} mode="pct" highlightConfig={card?.effect ?? null} preferredMode={pm} />
                ) : (
                  <TrendChart absoluteData={section.absoluteData} growthData={section.growthData}
                    fyData={section.fyData} seriesNames={section.seriesNames} pctLabel={section.pctLabel}
                    mode={trendMode} initialHidden={section.defaultHiddenSeries}
                    highlightConfig={card?.effect ?? null} preferredMode={pm} />
                )}
              </SectionCard>

              <CompositionCaption cards={selected?.sectionView.compositionCards ?? []} />

              {effDepth !== "brief" && card && (
                <div ref={whyRef} style={{ borderRadius: 8 }}>
                  <p style={{ fontSize: 16, lineHeight: 1.65, color: "var(--font)", marginTop: 16 }}>{card.body}</p>
                  {card.implication && (
                    <p style={{ fontSize: 14.5, lineHeight: 1.6, color: "var(--font-muted)", marginTop: 10 }}>{card.implication}</p>
                  )}
                  {card.basis?.inferences?.length ? (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ ...EYEBROW, letterSpacing: "0.05em" }}>Why this reads</div>
                      <ol style={{ marginTop: 6 }}>
                        {card.basis.inferences.map((s, i) => (
                          <li key={i} className="flex gap-2.5" style={{ fontSize: 15, lineHeight: 1.55, color: "var(--font)", marginTop: 6 }}>
                            <span style={{ color: secColor, fontWeight: 700 }}>{i + 1}.</span><span>{s}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
                </div>
              )}
              {effDepth === "deep" && (
                <div ref={deepRef} style={{ borderRadius: 8 }}><DeepBlock opps={opps} color={secColor} /></div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── pieces ────────────────────────────────────────────────────────────────────

function findCard(sections: ReturnType<typeof organizeReadMode>["sections"], id: string) {
  for (const sv of sections)
    for (const sub of sv.subjects)
      for (const c of sub.cards)
        if (c.id === id) return { card: c, section: sv.section, sectionView: sv };
  return null;
}

interface Chip { id: string; title: string; icon: string; color: string; moved: number }

function ChipStrip({ chips, active, stripRef, onPick }: {
  chips: Chip[]; active: string; stripRef: React.RefObject<HTMLDivElement | null>; onPick: (id: string) => void;
}) {
  const scroll = (dir: number) => stripRef.current?.scrollBy({ left: dir * 260, behavior: "smooth" });
  return (
    <div className="flex items-center gap-1">
      <button onClick={() => scroll(-1)} className="rm-link px-1 shrink-0"
              style={{ fontSize: 20, color: "var(--font-muted)" }} aria-label="scroll left">‹</button>
      <div ref={stripRef} className="rm-strip flex gap-2 overflow-x-auto py-1">
        {chips.map((c) => {
          const on = c.id === active;
          return (
            <button key={c.id} data-on={on} onClick={() => onPick(c.id)}
                    className={`rm-chip whitespace-nowrap rounded-full shrink-0${on ? " on" : ""}`}
                    style={{ ...vars(c.color, tint(c.color, 0.14)), fontSize: 13.5, fontWeight: 600, padding: "6px 14px" }}>
              {c.icon} {c.title}{c.moved > 0 ? ` · ▲ ${c.moved}` : ""}
            </button>
          );
        })}
      </div>
      <button onClick={() => scroll(1)} className="rm-link px-1 shrink-0"
              style={{ fontSize: 20, color: "var(--font-muted)" }} aria-label="scroll right">›</button>
    </div>
  );
}

function DimensionCard({ sv, moved, onClick }: { sv: SectionView; moved: number; onClick: () => void }) {
  const col = SEC_COLORS[sv.section.accentIndex] ?? "#4e8ef7";
  return (
    <button onClick={onClick} className="rm-card rm-tile text-left rounded-xl"
            style={{ ...vars(col), padding: "16px 18px" }}>
      <div style={{ fontSize: 24, lineHeight: 1 }}>{sv.section.icon}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: "var(--font)", marginTop: 10, lineHeight: 1.25 }}>{sv.section.title}</div>
      <div className="flex items-center gap-2 mt-2">
        <span style={{ fontSize: 13, color: "var(--font-muted)" }}>{sv.cardCount} insights</span>
        {moved > 0 && <span style={{ fontSize: 13, fontWeight: 600, color: col }}>▲ {moved} moved</span>}
      </div>
    </button>
  );
}

function ReadCard({ entry, selected, onClick }: { entry: ReadEntry; selected: boolean; onClick: () => void }) {
  const col = SEC_COLORS[entry.section.accentIndex] ?? "#4e8ef7";
  const mode = entry.card.preferredMode === "share" ? "Share"
    : entry.card.preferredMode === "yoy" ? "YoY" : entry.card.preferredMode === "fy" ? "FY" : "Absolute";
  return (
    <button onClick={onClick} className={`rm-card w-full h-full text-left rounded-xl${selected ? " sel" : ""}`}
            style={{ ...vars(col, tint(col, 0.08)), padding: "12px 15px 12px 17px" }}>
      <div style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.35, color: "var(--font)" }}>{entry.card.title}</div>
      <div className="flex items-center gap-1.5 mt-1.5" style={{ fontSize: 13, color: "var(--font-muted)" }}>
        <span style={{ color: col }}>{glyph(entry.direction)}</span>
        {entry.reason && <span>{REASON[entry.reason]}</span>}
        <span>·</span><span>{mode}</span>
        <span className="ml-auto" style={{ color: col, fontWeight: 600 }}>{entry.section.title}</span>
      </div>
    </button>
  );
}

function DepthLadder({ depth, setDepth, deepAvailable }: { depth: Depth; setDepth: (d: Depth) => void; deepAvailable: boolean }) {
  const levels: Depth[] = deepAvailable ? ["brief", "full", "deep"] : ["brief", "full"];
  return (
    <div className="flex gap-1">
      {levels.map((d) => (
        <button key={d} onClick={() => setDepth(d)} className="rounded-full transition-colors"
                style={{ fontSize: 12.5, padding: "5px 11px", ...chip(depth === d) }}>
          {d === "brief" ? "Brief" : d === "full" ? "Full" : "Deep ⌁"}
        </button>
      ))}
    </div>
  );
}

function CompositionCaption({ cards }: { cards: Annotation[] }) {
  if (!cards.length) return null;
  return (
    <p style={{ fontSize: 13.5, lineHeight: 1.55, color: "var(--font-muted)", marginTop: 12 }}>
      <span style={{ fontWeight: 600 }}>Composition: </span>{cards.map((c) => c.title).join(" · ")}
    </p>
  );
}

function DeepBlock({ opps, color }: { opps: ReturnType<typeof opportunitiesFor>; color: string }) {
  if (!opps.length) return null;
  return (
    <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border-card)" }}>
      <div style={{ ...EYEBROW, letterSpacing: "0.05em" }}>⌁ What this opens</div>
      {opps.map((o) => (
        <a key={o.id} href={`/opportunities#${o.id}`} className="rm-link block mt-1.5" style={{ fontSize: 15, fontWeight: 600, color }}>
          {o.title} <span style={{ color: "var(--font-muted)", fontWeight: 400 }}>· {o.status}</span>
        </a>
      ))}
    </div>
  );
}

function chip(active: boolean): React.CSSProperties {
  return {
    background: active ? "#4e8ef7" : "var(--bg-page)",
    color: active ? "#fff" : "var(--font-muted)",
    border: `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`,
  };
}
