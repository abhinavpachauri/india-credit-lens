"use client";

import { useState, useMemo, useEffect } from "react";
import {
  SECTION_DEFS,
  GROUP_LABELS,
  GROUP_ICONS,
  GROUP_ACCENT,
  getAllBanks,
  getTopNBanks,
} from "@/lib/atm_pos_data";
import type { AtmPosSeries, FilterState } from "@/lib/atm_pos_data";
import {
  loadAtmPosInsights,
  filterInsights,
} from "@/lib/atm_pos_insights";
import type { AtmPosInsight } from "@/lib/atm_pos_insights";
import { pickColor } from "@/lib/theme";
import InsightCard   from "@/components/dls/InsightCard";
import InsightCTAStrip from "@/components/dls/InsightCTAStrip";
import OpportunityTeaser from "@/components/dls/OpportunityTeaser";
import { opportunitiesFor } from "@/lib/opportunities";
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
  series:  AtmPosSeries;
}

const BTN = (active: boolean): React.CSSProperties => ({
  background: active ? "#4e8ef7" : "var(--bg-page)",
  color:      active ? "#fff"    : "var(--font-muted)",
  border:     `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`,
});

const DIVIDER_STYLE: React.CSSProperties = {
  width: 1, height: 20, background: "var(--border-card)", flexShrink: 0,
};

export default function AtmPosGroupSection({ group, series }: AtmPosGroupSectionProps) {
  const sections = useMemo(
    () => SECTION_DEFS.filter((d) => d.group === group),
    [group],
  );
  const allBanks = useMemo(() => getAllBanks(series), [series]);

  const [mode,          setMode]          = useState<GroupMode>("top_n");
  const [selectedBanks, setSelectedBanks] = useState<string[]>([]);
  const [topN,          setTopN]          = useState<number>(5);
  const [hiddenSeries,  setHiddenSeries]  = useState<Set<string>>(new Set(["Total"]));
  const [tab,           setTab]           = useState<TabId>("trend");
  const [trendMode,     setTrendMode]     = useState<"absolute" | "mom" | "yoy">("absolute");
  const [distMode,      setDistMode]      = useState<"absolute" | "pct">("absolute");
  const [bankSearch,    setBankSearch]    = useState("");
  const [activeInsight, setActiveInsight] = useState<AtmPosInsight | null>(null);
  const [allInsights,   setAllInsights]   = useState<AtmPosInsight[]>([]);
  const [insightsMode,  setInsightsMode]  = useState(false);

  // Load insights once
  useEffect(() => {
    loadAtmPosInsights().then(setAllInsights).catch(() => setAllInsights([]));
  }, []);

  // Pre-compute top N banks at group level for consistent chips across all cards
  const topNBanks = useMemo(() => {
    if (mode !== "top_n") return [];
    return getTopNBanks(series, GROUP_PRIMARY[group] ?? "pos_terminals", topN);
  }, [mode, topN, series, group]);

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
      return;
    }
    setActiveInsight(ins);

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
      <div className="flex items-center gap-2" style={{ marginTop: 32, marginBottom: 12 }}>
        <span className="text-lg leading-none">{GROUP_ICONS[group]}</span>
        <h2
          className="text-sm font-bold leading-snug"
          style={{ color: "var(--font)" }}
        >
          {GROUP_LABELS[group]}
        </h2>
      </div>

      {/* ── Insights CTA / exit strip (DLS) ────────────────────────────────── */}
      {visibleInsights.length > 0 && (
        <InsightCTAStrip
          items={visibleInsights.map((i) => ({ type: i.type, title: i.title }))}
          counts={{
            insight:     insightCount,
            gap:         gapCount,
            opportunity: opportunitiesFor("atm_pos", group).length,
          }}
          isActive={insightsMode}
          activeIdx={activeIdx}
          total={visibleInsights.length}
          onEnter={enterInsightsMode}
          onExit={exitInsightsMode}
        />
      )}

      {/* ── Opportunity teaser (DLS) — feed-sourced, deep-links to /opportunities */}
      <OpportunityTeaser pipeline="atm_pos" sectionId={group} />

      {/* ── Insight card (DLS) — key resets internal chain-expand on navigation */}
      {insightsMode && activeInsight && (
        <InsightCard
          key={activeIdx}
          type={activeInsight.type}
          title={activeInsight.title}
          body={activeInsight.body}
          implication={activeInsight.implication}
          chain={activeInsight.basis?.inferences ?? activeInsight.reasoning?.chain}
          activeIndex={activeIdx}
          total={visibleInsights.length}
          onNext={goNext}
          onPrev={goPrev}
        />
      )}

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
        {/* Tighter vertical gap when the row wraps on mobile; full gap from sm up. */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 sm:gap-3">
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
              ? (["absolute", "mom", "yoy"] as const).map((m) => (
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
                    {m === "absolute" ? "Absolute" : m === "mom" ? "MoM %" : "YoY %"}
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
          <div className="flex flex-wrap gap-1.5 mt-2 sm:mt-3">
            {seriesNames.map((name, i) => {
              const color    = pickColor(name, i);
              const isHidden = hiddenSeries.has(name);
              return (
                <button
                  key={name}
                  onClick={() => toggleSeries(name)}
                  className="text-xs sm:text-sm font-medium px-2.5 sm:px-3 py-1 rounded-full transition-all"
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
              series={series}
              filter={cardFilter}
              tab={tab}
              hiddenSeries={hiddenSeries}
              trendMode={trendMode}
              distMode={distMode}
              accentColor={GROUP_ACCENT[group] ?? "#4e8ef7"}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
