"use client";

import { useState, useMemo } from "react";
import {
  SECTION_DEFS,
  GROUP_LABELS,
  getAllBanks,
  getTopNBanks,
} from "@/lib/atm_pos_data";
import type { AtmPosRow, FilterState } from "@/lib/atm_pos_data";
import { pickColor } from "@/lib/theme";
import AtmPosSectionCard from "@/components/AtmPosSectionCard";

// Primary metric per group — used to rank banks for Top N
const GROUP_PRIMARY: Record<string, string> = {
  cc:    "credit_cards",
  dc:    "debit_cards",
  infra: "pos_terminals",
};

const ALL_TYPES = ["PSB", "Private", "Foreign", "SFB", "Payments"];
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

  const [mode,          setMode]          = useState<GroupMode>("by_type");
  const [selectedBanks, setSelectedBanks] = useState<string[]>([]);
  const [topN,          setTopN]          = useState<number>(10);
  const [hiddenSeries,  setHiddenSeries]  = useState<Set<string>>(new Set());
  const [tab,           setTab]           = useState<TabId>("trend");
  const [trendMode,     setTrendMode]     = useState<"absolute" | "mom">("absolute");
  const [distMode,      setDistMode]      = useState<"absolute" | "pct">("absolute");
  const [bankSearch,    setBankSearch]    = useState("");

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
    // top_n: forward as individual with pre-computed banks so all cards share same set
    return { mode: "individual", selectedTypes: [], selectedBanks: topNBanks, topN };
  }, [mode, selectedBanks, topNBanks, topN]);

  const handleModeChange = (m: GroupMode) => {
    setMode(m);
    setHiddenSeries(new Set()); // reset chip visibility on mode switch
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
                  className="text-xs font-medium px-3 py-1.5 rounded-full transition-colors"
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
                  className="text-xs font-medium px-3 py-1.5 rounded-full transition-colors"
                  style={BTN(tab === t)}
                >
                  {label}
                </button>
              ),
            )}
          </div>

          <div className="hidden sm:block" style={DIVIDER_STYLE} />

          {/* Chart mode radios */}
          <div className="flex items-center gap-3 text-xs">
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
                <span className="text-xs mr-1" style={{ color: "var(--font-muted)" }}>Top:</span>
                {TOP_N_OPTIONS.map((n) => (
                  <button
                    key={n}
                    onClick={() => setTopN(n)}
                    className="text-xs font-medium px-2.5 py-1 rounded-full transition-colors"
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
                  className="text-xs font-medium px-3 py-1 rounded-full transition-all"
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
              className="w-full text-xs px-3 py-1.5 rounded mb-2"
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
                    className="text-xs px-2.5 py-1 rounded-full transition-colors"
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

      {/* 3-column card grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {sections.map((def) => (
          <AtmPosSectionCard
            key={def.id}
            def={def}
            rows={rows}
            filter={cardFilter}
            tab={tab}
            hiddenSeries={hiddenSeries}
            trendMode={trendMode}
            distMode={distMode}
          />
        ))}
      </div>
    </div>
  );
}
