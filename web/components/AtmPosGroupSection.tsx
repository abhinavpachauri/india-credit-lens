"use client";

import { useState, useMemo, useEffect } from "react";
import {
  SECTION_DEFS,
  GROUP_LABELS,
  getAllBanks,
  getTopNBanks,
} from "@/lib/atm_pos_data";
import type { AtmPosRow, FilterState } from "@/lib/atm_pos_data";
import {
  loadAtmPosInsights,
  filterInsights,
} from "@/lib/atm_pos_insights";
import type { AtmPosInsight } from "@/lib/atm_pos_insights";
import { pickColor } from "@/lib/theme";
import AtmPosSectionCard from "@/components/AtmPosSectionCard";

// Primary metric per group — used to rank banks for Top N
const GROUP_PRIMARY: Record<string, string> = {
  cc:    "credit_cards",
  dc:    "debit_cards",
  infra: "pos_terminals",
};

const ALL_TYPES      = ["PSB", "Private", "Foreign", "SFB", "Payments"];
const TOP_N_OPTIONS  = [5, 10, 20] as const;
const BY_TYPE_SERIES = ["Total", "PSB", "Private", "Foreign", "SFB", "Payments"];

type GroupMode = "by_type" | "individual" | "top_n";
type TabId     = "trend" | "distribution";

interface AtmPosGroupSectionProps {
  group: "cc" | "dc" | "infra";
  rows:  AtmPosRow[];
}

const BTN = (active: boolean): React.CSSProperties => ({
  background: active ? "#4e8ef7" : "var(--bg-page)",
  color:      active ? "#fff"    : "var(--font-muted)",
  border:     `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`,
});

const DIVIDER_STYLE: React.CSSProperties = {
  width: 1, height: 20, background: "var(--border-card)", flexShrink: 0,
};

export default function AtmPosGroupSection({ group, rows }: AtmPosGroupSectionProps) {
  const sections = useMemo(
    () => SECTION_DEFS.filter((d) => d.group === group),
    [group],
  );
  const allBanks = useMemo(() => getAllBanks(rows), [rows]);

  const [mode,          setMode]          = useState<GroupMode>("top_n");
  const [selectedBanks, setSelectedBanks] = useState<string[]>([]);
  const [topN,          setTopN]          = useState<number>(5);
  const [hiddenSeries,  setHiddenSeries]  = useState<Set<string>>(new Set(["Total"]));
  const [tab,           setTab]           = useState<TabId>("trend");
  const [trendMode,     setTrendMode]     = useState<"absolute" | "mom">("absolute");
  const [distMode,      setDistMode]      = useState<"absolute" | "pct">("absolute");
  const [bankSearch,    setBankSearch]    = useState("");
  const [activeInsight,  setActiveInsight]  = useState<AtmPosInsight | null>(null);
  const [allInsights,    setAllInsights]    = useState<AtmPosInsight[]>([]);
  const [insightsMode,   setInsightsMode]   = useState(false);
  const [showReasoning,  setShowReasoning]  = useState(false);
  const [tickerIdx,      setTickerIdx]     = useState(0);
  const [tickerVisible,  setTickerVisible] = useState(true);

  // Load insights once
  useEffect(() => {
    loadAtmPosInsights().then(setAllInsights).catch(() => setAllInsights([]));
  }, []);

  // Pre-compute top N banks at group level for consistent chips across all cards
  const topNBanks = useMemo(() => {
    if (mode !== "top_n") return [];
    return getTopNBanks(rows, GROUP_PRIMARY[group] ?? "pos_terminals", topN);
  }, [mode, topN, rows, group]);

  // Series names that drive the chip row
  const seriesNames = useMemo<string[]>(() => {
    if (mode === "by_type")    return BY_TYPE_SERIES;
    if (mode === "individual") return ["Total", ...selectedBanks];
    return ["Total", ...topNBanks];
  }, [mode, selectedBanks, topNBanks]);

  // Filter passed to every card in this group
  const cardFilter = useMemo<FilterState>(() => {
    if (mode === "by_type") {
      return { mode: "by_type", selectedTypes: ALL_TYPES, selectedBanks: [], topN };
    }
    if (mode === "individual") {
      return { mode: "individual", selectedTypes: [], selectedBanks, topN };
    }
    return { mode: "individual", selectedTypes: [], selectedBanks: topNBanks, topN };
  }, [mode, selectedBanks, topNBanks, topN]);

  // In insights mode, show only the card the active insight is about
  const sectionsToShow = useMemo(() => {
    if (!insightsMode || !activeInsight?.effect.focusCard) return sections;
    const focused = sections.filter((s) => s.id === activeInsight.effect.focusCard);
    return focused.length > 0 ? focused : sections;
  }, [insightsMode, activeInsight, sections]);

  // Insights visible for current group + mode
  const visibleInsights = useMemo(
    () => filterInsights(allInsights, group, mode),
    [allInsights, group, mode],
  );

  const insightCount = visibleInsights.filter((i) => i.type === "insight").length;
  const gapCount     = visibleInsights.filter((i) => i.type === "gap").length;

  // Reset ticker when mode changes
  useEffect(() => {
    setTickerIdx(0);
    setTickerVisible(true);
  }, [mode]);

  // Cycle through headlines on the CTA strip (pause in insights mode)
  useEffect(() => {
    if (insightsMode || visibleInsights.length <= 1) return;
    const id = setInterval(() => {
      setTickerVisible(false);
      setTimeout(() => {
        setTickerIdx((prev) => (prev + 1) % visibleInsights.length);
        setTickerVisible(true);
      }, 350);
    }, 3200);
    return () => clearInterval(id);
  }, [insightsMode, visibleInsights.length]);

  const handleModeChange = (m: GroupMode) => {
    setMode(m);
    setHiddenSeries(m === "by_type" ? new Set() : new Set(["Total"]));
    setActiveInsight(null);
  };

  const toggleSeries = (name: string) => {
    setHiddenSeries((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const toggleBank = (bank: string) => {
    setSelectedBanks((prev) =>
      prev.includes(bank) ? prev.filter((b) => b !== bank) : [...prev, bank],
    );
  };

  // Apply insight effect: dim all series except highlight, switch tab/mode
  const applyInsight = (ins: AtmPosInsight) => {
    if (activeInsight?.id === ins.id) {
      setActiveInsight(null);
      setHiddenSeries(new Set());
      setShowReasoning(false);
      return;
    }
    setActiveInsight(ins);
    setShowReasoning(false);

    const highlighted = new Set(ins.effect.highlight);
    const toHide = new Set(seriesNames.filter((n) => !highlighted.has(n)));
    setHiddenSeries(toHide);

    setTab(ins.effect.tab);
    if (ins.effect.trendMode) setTrendMode(ins.effect.trendMode);
    if (ins.effect.distMode)  setDistMode(ins.effect.distMode);
  };

  // Enter insights mode — auto-activate first insight immediately
  const enterInsightsMode = () => {
    setInsightsMode(true);
    if (visibleInsights.length > 0) applyInsight(visibleInsights[0]);
  };

  // Exit insights mode: reset chart state
  const exitInsightsMode = () => {
    setInsightsMode(false);
    setActiveInsight(null);
    setHiddenSeries(mode === "by_type" ? new Set() : new Set(["Total"]));
    setTab("trend");
    setTrendMode("absolute");
    setDistMode("absolute");
  };

  const filteredBanks = bankSearch
    ? allBanks.filter((b) => b.toLowerCase().includes(bankSearch.toLowerCase()))
    : allBanks;

  // Active insight index (for nav)
  const activeIdx = activeInsight
    ? visibleInsights.findIndex((i) => i.id === activeInsight.id)
    : -1;

  const goNext = () => {
    const next = visibleInsights[activeIdx + 1];
    if (next) applyInsight(next);
  };
  const goPrev = () => {
    const prev = visibleInsights[activeIdx - 1];
    if (prev) applyInsight(prev);
  };

  return (
    <div className="mb-12">
      {/* Group label */}
      <h2
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--font-muted)", marginTop: 32, marginBottom: 12 }}
      >
        {GROUP_LABELS[group]}
      </h2>

      {/* ── Insights CTA strip / Back-to-explore strip ──────────────────────── */}
      {visibleInsights.length > 0 && (
        !insightsMode ? (
          /* EXPLORE MODE → prominent CTA */
          <div
            onClick={enterInsightsMode}
            className="cursor-pointer mb-4 flex items-center justify-between gap-4"
            style={{
              background:   "#4e8ef712",
              border:       "1.5px solid #4e8ef740",
              borderLeft:   "5px solid #4e8ef7",
              borderRadius: "0 10px 10px 0",
              padding:      "16px 20px",
            }}
          >
            <div className="min-w-0">
              {/* Static count line */}
              <p className="text-base font-bold leading-snug" style={{ color: "var(--font)" }}>
                {insightCount > 0 && `💡 ${insightCount} insight${insightCount !== 1 ? "s" : ""}`}
                {insightCount > 0 && gapCount > 0 && (
                  <span style={{ color: "var(--font-muted)", fontWeight: 400 }}> · </span>
                )}
                {gapCount > 0 && (
                  <span style={{ color: "#D97706" }}>
                    {`⚠️ ${gapCount} gap${gapCount !== 1 ? "s" : ""}`}
                  </span>
                )}
                <span style={{ color: "var(--font-muted)", fontWeight: 400 }}> in this view</span>
              </p>

              {/* Animated ticker — cycles through headlines */}
              {visibleInsights.length > 0 && (
                <div style={{ minHeight: 26, overflow: "hidden", marginTop: 6, marginBottom: 4 }}>
                  <p
                    className="text-sm font-medium leading-snug truncate"
                    style={{
                      color:      visibleInsights[tickerIdx]?.type === "gap" ? "#D97706" : "var(--font)",
                      opacity:    tickerVisible ? 1 : 0,
                      transform:  tickerVisible ? "translateY(0)" : "translateY(-7px)",
                      transition: "opacity 0.35s ease, transform 0.35s ease",
                    }}
                  >
                    {visibleInsights[tickerIdx]?.type === "gap" ? "⚠️" : "💡"}{" "}
                    {visibleInsights[tickerIdx]?.title}
                  </p>
                </div>
              )}

              {/* Static CTA line */}
              <p className="text-sm" style={{ color: "#4e8ef7", fontWeight: 500 }}>
                What they mean for lenders — click to explore →
              </p>
            </div>
            <div
              className="flex-shrink-0 flex items-center justify-center rounded-full font-bold"
              style={{
                width:      38,
                height:     38,
                background: "#4e8ef7",
                color:      "#fff",
                fontSize:   18,
              }}
            >
              →
            </div>
          </div>
        ) : (
          /* INSIGHTS MODE → back strip (same size as CTA, full div clickable) */
          <div
            onClick={exitInsightsMode}
            className="cursor-pointer mb-4 flex items-center justify-between gap-4"
            style={{
              background:   "#4e8ef712",
              border:       "1.5px solid #4e8ef740",
              borderLeft:   "5px solid #4e8ef7",
              borderRadius: "0 10px 10px 0",
              padding:      "16px 20px",
            }}
          >
            <div className="min-w-0">
              <p className="text-base font-bold leading-snug" style={{ color: "#4e8ef7" }}>
                ← Exit insights
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--font-muted)", fontWeight: 500 }}>
                {activeIdx >= 0 ? `${activeIdx + 1} of ${visibleInsights.length}` : visibleInsights.length} · Insights mode active
              </p>
            </div>
            <div
              className="flex-shrink-0 flex items-center justify-center rounded-full font-bold"
              style={{
                width:      38,
                height:     38,
                background: "#4e8ef7",
                color:      "#fff",
                fontSize:   18,
              }}
            >
              ×
            </div>
          </div>
        )
      )}

      {/* ── Insight card (one at a time, SIBC style) ────────────────────────── */}
      {insightsMode && activeInsight && (() => {
        const ins       = activeInsight;
        const isGap     = ins.type === "gap";
        const color     = isGap ? "#D97706" : "#4e8ef7";
        const typeLabel = isGap ? "Gap" : "Insight";
        const total     = visibleInsights.length;

        return (
          <div
            className="mb-4"
            style={{
              background:   "var(--bg-card)",
              border:       "1px solid var(--border-card)",
              borderLeft:   `4px solid ${color}`,
              borderRadius: "0 10px 10px 0",
              padding:      "18px 20px",
            }}
          >
            {/* Type badge + progress dots */}
            <div className="flex items-center justify-between mb-3">
              <span
                className="text-xs font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full"
                style={{ color, background: `${color}18` }}
              >
                {typeLabel}
              </span>
              {total > 1 && (
                <div className="flex items-center gap-1.5">
                  {visibleInsights.map((_, i) => (
                    <span
                      key={i}
                      className="inline-block rounded-full transition-all duration-200"
                      style={{
                        width:      i === activeIdx ? "18px" : "6px",
                        height:     "6px",
                        background: i === activeIdx ? color : `${color}35`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Title */}
            <p className="text-base font-bold leading-snug mb-2" style={{ color: "var(--font)" }}>
              {ins.title}
            </p>

            {/* Body */}
            <p className="text-sm leading-relaxed" style={{ color: "var(--font-muted)" }}>
              {ins.body}
            </p>

            {/* For lenders */}
            {ins.implication && (
              <div className="mt-4 pt-4" style={{ borderTop: `1px solid ${color}20` }}>
                <p
                  className="text-xs font-bold uppercase tracking-widest mb-1.5"
                  style={{ color }}
                >
                  For lenders
                </p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--font)" }}>
                  {ins.implication}
                </p>

                {/* Reasoning expand — Stage 4d sourced claims */}
                {ins.reasoning && (
                  <div className="mt-3">
                    <button
                      onClick={() => setShowReasoning((s) => !s)}
                      className="flex items-center gap-1.5 text-xs font-semibold"
                      style={{ color: "var(--font-muted)", background: "none", border: "none", padding: 0, cursor: "pointer" }}
                    >
                      <span
                        style={{
                          display:    "inline-block",
                          transition: "transform 0.2s",
                          transform:  showReasoning ? "rotate(90deg)" : "rotate(0deg)",
                          fontSize:   9,
                        }}
                      >
                        ▶
                      </span>
                      {showReasoning ? "Hide inference" : "Inference chain"}
                    </button>

                    {showReasoning && (
                      <div
                        className="mt-2 rounded-lg text-xs"
                        style={{
                          background: `${color}08`,
                          border:     `1px solid ${color}25`,
                          padding:    "10px 12px",
                        }}
                      >
                        <ol className="flex flex-col gap-1.5" style={{ paddingLeft: 0, listStyle: "none", margin: 0 }}>
                          {ins.reasoning.chain.map((step, i) => (
                            <li key={i} className="flex gap-2" style={{ lineHeight: 1.5 }}>
                              <span className="flex-shrink-0 font-bold" style={{ color, minWidth: 14 }}>
                                {i + 1}.
                              </span>
                              <span style={{ color: "var(--font)" }}>{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Footer: prev/next */}
            <div
              className="flex items-center gap-3 mt-4 pt-3"
              style={{ borderTop: "1px solid var(--border-card)" }}
            >
              <button
                onClick={goPrev}
                disabled={activeIdx === 0}
                className="px-4 py-1.5 rounded-lg text-sm font-semibold disabled:opacity-25 transition-opacity"
                style={{ border: `1.5px solid ${color}`, color }}
              >
                ←
              </button>
              <span className="text-xs tabular-nums" style={{ color: "var(--font-muted)" }}>
                {activeIdx + 1} of {total}
              </span>
              <button
                onClick={goNext}
                disabled={activeIdx === total - 1}
                className="px-4 py-1.5 rounded-lg text-sm font-semibold disabled:opacity-25 transition-opacity"
                style={{ border: `1.5px solid ${color}`, color }}
              >
                →
              </button>
            </div>
          </div>
        );
      })()}

      {/* ── Controls panel (hidden in insights mode) ────────────────────────── */}
      {!insightsMode && <div
        style={{
          background:   "var(--bg-card)",
          border:       "1px solid var(--border-card)",
          borderRadius: 10,
          padding:      "12px 16px",
          marginBottom: 16,
        }}
      >
        {/* Top row: mode | tab | chart-mode | top-N selector */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Mode buttons */}
          <div className="flex gap-1">
            {([["by_type", "By Type"], ["individual", "Individual"], ["top_n", "Top N"]] as const).map(
              ([m, label]) => (
                <button
                  key={m}
                  onClick={() => handleModeChange(m)}
                  className="text-sm font-medium px-3 py-1.5 rounded-full transition-colors"
                  style={BTN(mode === m)}
                >
                  {label}
                </button>
              ),
            )}
          </div>

          <div className="hidden sm:block" style={DIVIDER_STYLE} />

          {/* Tab buttons */}
          <div className="flex gap-1">
            {([["trend", "📈 Trend"], ["distribution", "📊 Distribution"]] as const).map(
              ([t, label]) => (
                <button
                  key={t}
                  onClick={() => setTab(t as TabId)}
                  className="text-sm font-medium px-3 py-1.5 rounded-full transition-colors"
                  style={BTN(tab === t)}
                >
                  {label}
                </button>
              ),
            )}
          </div>

          <div className="hidden sm:block" style={DIVIDER_STYLE} />

          {/* Chart mode radios */}
          <div className="flex items-center gap-3 text-sm">
            {tab === "trend"
              ? (["absolute", "mom"] as const).map((m) => (
                  <label
                    key={m}
                    className="flex items-center gap-1.5 cursor-pointer"
                    style={{ color: "var(--font)" }}
                  >
                    <input
                      type="radio"
                      name={`trend-${group}`}
                      value={m}
                      checked={trendMode === m}
                      onChange={() => setTrendMode(m)}
                      className="accent-blue-500"
                    />
                    {m === "absolute" ? "Absolute" : "MoM %"}
                  </label>
                ))
              : (["absolute", "pct"] as const).map((m) => (
                  <label
                    key={m}
                    className="flex items-center gap-1.5 cursor-pointer"
                    style={{ color: "var(--font)" }}
                  >
                    <input
                      type="radio"
                      name={`dist-${group}`}
                      value={m}
                      checked={distMode === m}
                      onChange={() => setDistMode(m)}
                      className="accent-blue-500"
                    />
                    {m === "absolute" ? "Absolute" : "% Share"}
                  </label>
                ))}
          </div>

          {/* Top N selector */}
          {mode === "top_n" && (
            <>
              <div className="hidden sm:block" style={DIVIDER_STYLE} />
              <div className="flex items-center gap-1">
                <span className="text-sm mr-1" style={{ color: "var(--font-muted)" }}>Top:</span>
                {TOP_N_OPTIONS.map((n) => (
                  <button
                    key={n}
                    onClick={() => setTopN(n)}
                    className="text-sm font-medium px-2.5 py-1 rounded-full transition-colors"
                    style={BTN(topN === n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Chips row */}
        {seriesNames.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {seriesNames.map((name, i) => {
              const color    = pickColor(name, i);
              const isHidden = hiddenSeries.has(name);
              return (
                <button
                  key={name}
                  onClick={() => toggleSeries(name)}
                  className="text-sm font-medium px-3 py-1 rounded-full transition-all"
                  style={{
                    background: isHidden ? "transparent" : color,
                    border:     `1.5px solid ${color}`,
                    color:      isHidden ? color : "#fff",
                    opacity:    isHidden ? 0.65 : 1,
                  }}
                >
                  {name}
                </button>
              );
            })}
          </div>
        )}

        {/* Individual bank selector */}
        {mode === "individual" && (
          <div className="mt-3">
            <input
              type="text"
              placeholder="Search banks…"
              value={bankSearch}
              onChange={(e) => setBankSearch(e.target.value)}
              className="w-full text-sm px-3 py-1.5 rounded mb-2"
              style={{
                border:     "1px solid var(--border-card)",
                background: "var(--bg-page)",
                color:      "var(--font)",
                outline:    "none",
              }}
            />
            <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
              {filteredBanks.map((bank) => {
                const sel = selectedBanks.includes(bank);
                return (
                  <button
                    key={bank}
                    onClick={() => toggleBank(bank)}
                    className="text-sm px-2.5 py-1 rounded-full transition-colors"
                    style={BTN(sel)}
                  >
                    {bank}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>}

      {/* Card grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {sectionsToShow.map((def) => (
          <div key={def.id} data-card-id={def.id}>
            <AtmPosSectionCard
              def={def}
              rows={rows}
              filter={cardFilter}
              tab={tab}
              hiddenSeries={hiddenSeries}
              trendMode={trendMode}
              distMode={distMode}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
