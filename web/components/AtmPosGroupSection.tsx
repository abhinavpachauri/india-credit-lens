"use client";

import { useState, useMemo, useEffect, useRef } from "react";
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

const ALL_TYPES     = ["PSB", "Private", "Foreign", "SFB", "Payments"];
const TOP_N_OPTIONS = [5, 10, 20] as const;
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

  const [mode,           setMode]           = useState<GroupMode>("by_type");
  const [selectedBanks,  setSelectedBanks]  = useState<string[]>([]);
  const [topN,           setTopN]           = useState<number>(10);
  const [hiddenSeries,   setHiddenSeries]   = useState<Set<string>>(new Set());
  const [tab,            setTab]            = useState<TabId>("trend");
  const [trendMode,      setTrendMode]      = useState<"absolute" | "mom">("absolute");
  const [distMode,       setDistMode]       = useState<"absolute" | "pct">("absolute");
  const [bankSearch,     setBankSearch]     = useState("");
  const [activeInsight,  setActiveInsight]  = useState<AtmPosInsight | null>(null);
  const [allInsights,    setAllInsights]    = useState<AtmPosInsight[]>([]);
  const cardsRef = useRef<HTMLDivElement>(null);

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

  // Insights visible for current group + mode
  const visibleInsights = useMemo(
    () => filterInsights(allInsights, group, mode),
    [allInsights, group, mode],
  );

  const handleModeChange = (m: GroupMode) => {
    setMode(m);
    setHiddenSeries(new Set());
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
      // Clicking active insight resets everything
      setActiveInsight(null);
      setHiddenSeries(new Set());
      return;
    }
    setActiveInsight(ins);

    // Dim all series not in highlight
    const highlighted = new Set(ins.effect.highlight);
    const toHide = new Set(seriesNames.filter((n) => !highlighted.has(n)));
    setHiddenSeries(toHide);

    // Switch tab and chart mode
    setTab(ins.effect.tab);
    if (ins.effect.trendMode) setTrendMode(ins.effect.trendMode);
    if (ins.effect.distMode)  setDistMode(ins.effect.distMode);

    // Scroll to focus card if specified
    if (ins.effect.focusCard && cardsRef.current) {
      const el = cardsRef.current.querySelector(`[data-card-id="${ins.effect.focusCard}"]`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  // Explore action: switch mode then re-apply insight
  const applyExplore = (ins: AtmPosInsight) => {
    if (!ins.exploreAction) return;
    handleModeChange(ins.exploreAction.mode);
    if (ins.exploreAction.topN) setTopN(ins.exploreAction.topN);
  };

  const filteredBanks = bankSearch
    ? allBanks.filter((b) => b.toLowerCase().includes(bankSearch.toLowerCase()))
    : allBanks;

  return (
    <div className="mb-12">
      {/* Group label */}
      <h2
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--font-muted)", marginTop: 32, marginBottom: 12 }}
      >
        {GROUP_LABELS[group]}
      </h2>

      {/* Controls panel */}
      <div
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
                    opacity:    isHidden ? 0.65  : 1,
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
      </div>

      {/* ── Insights panel ──────────────────────────────────────────────────── */}
      {visibleInsights.length > 0 && (
        <div
          className="mb-4"
          style={{
            background:   "var(--bg-card)",
            border:       "1px solid var(--border-card)",
            borderLeft:   "3px solid #4e8ef7",
            borderRadius: "0 8px 8px 0",
            overflow:     "hidden",
          }}
        >
          {visibleInsights.map((ins, idx) => {
            const isActive  = activeInsight?.id === ins.id;
            const cutLabel  = ins.cut === "by_type" ? "By Type" : ins.cut === "top_n" ? "Top N" : "Total";
            return (
              <div
                key={ins.id}
                onClick={() => applyInsight(ins)}
                className="cursor-pointer transition-colors"
                style={{
                  padding:    "10px 14px",
                  borderTop:  idx > 0 ? "1px solid var(--border-card)" : "none",
                  background: isActive ? "#4e8ef710" : "transparent",
                }}
              >
                <div className="flex items-start gap-2">
                  <span className="flex-shrink-0 mt-0.5" style={{ fontSize: 13 }}>💡</span>
                  <p
                    className="text-sm font-medium leading-snug flex-1 min-w-0"
                    style={{ color: isActive ? "#4e8ef7" : "var(--font)" }}
                  >
                    {ins.title}
                  </p>
                  <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                    <span
                      style={{
                        fontSize:     11,
                        color:        "var(--font-muted)",
                        background:   "var(--bg-page)",
                        border:       "1px solid var(--border-card)",
                        borderRadius: 4,
                        padding:      "1px 6px",
                      }}
                    >
                      {cutLabel}
                    </span>
                    {isActive && ins.exploreAction && (
                      <button
                        onClick={(e) => { e.stopPropagation(); applyExplore(ins); }}
                        className="text-sm font-medium px-2.5 py-0.5 rounded transition-colors"
                        style={{ background: "#4e8ef7", color: "#fff", border: "none" }}
                      >
                        Explore →
                      </button>
                    )}
                  </div>
                </div>
                {isActive && (
                  <p
                    className="text-sm leading-relaxed mt-2"
                    style={{ color: "var(--font-muted)", paddingLeft: 22 }}
                  >
                    {ins.body}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Card grid */}
      <div ref={cardsRef} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {sections.map((def) => (
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
