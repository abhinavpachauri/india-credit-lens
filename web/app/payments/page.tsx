"use client";

import { useEffect, useState, useMemo } from "react";
import {
  loadAtmPosData,
  getAllBanks,
  SECTION_DEFS,
  GROUP_LABELS,
} from "@/lib/atm_pos_data";
import type { AtmPosRow, FilterState } from "@/lib/atm_pos_data";
import Header           from "@/components/Header";
import AtmPosFilterBar  from "@/components/AtmPosFilterBar";
import AtmPosSectionCard from "@/components/AtmPosSectionCard";

const ALL_TYPES = ["PSB", "Private", "Foreign", "SFB", "Payments"];

const DEFAULT_FILTER: FilterState = {
  mode:          "by_type",
  selectedTypes: ALL_TYPES,
  selectedBanks: [],
  topN:          10,
};

// Stable empty set — avoids new Set() on every render causing unnecessary re-renders
const EMPTY_HIDDEN = new Set<string>();

const GROUPS = ["cards", "cc", "dc", "infra"] as const;

type TabId = "trend" | "distribution";

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "trend",        label: "Trend",        icon: "📈" },
  { id: "distribution", label: "Distribution", icon: "📊" },
];

export default function PaymentsPage() {
  const [rows,         setRows]         = useState<AtmPosRow[] | null>(null);
  const [filter,       setFilter]       = useState<FilterState>(DEFAULT_FILTER);
  const [tab,          setTab]          = useState<TabId>("trend");
  const [dark,         setDark]         = useState(false);
  const [hiddenSeries, setHiddenSeries] = useState<Map<string, Set<string>>>(new Map());

  // Dark mode sync
  useEffect(() => {
    const saved = localStorage.getItem("icl-dark");
    if (saved === "true") setDark(true);
  }, []);

  const toggleDark = () =>
    setDark((d) => {
      localStorage.setItem("icl-dark", String(!d));
      return !d;
    });

  // Load data
  useEffect(() => {
    loadAtmPosData().then(setRows);
  }, []);

  const allBanks = useMemo(
    () => (rows ? getAllBanks(rows) : []),
    [rows],
  );

  const handleFilterChange = (newFilter: FilterState) => {
    // Reset per-section chip visibility whenever the global mode changes
    if (newFilter.mode !== filter.mode) {
      setHiddenSeries(new Map());
    }
    setFilter(newFilter);
  };

  const handleToggleSeries = (sectionId: string, seriesName: string) => {
    setHiddenSeries((prev) => {
      const next    = new Map(prev);
      const current = new Set(next.get(sectionId) ?? []);
      current.has(seriesName) ? current.delete(seriesName) : current.add(seriesName);
      next.set(sectionId, current);
      return next;
    });
  };

  if (!rows) {
    return (
      <div
        data-dark={dark}
        className="flex items-center justify-center min-h-screen text-sm"
        style={{ background: "var(--bg-page)", color: "var(--font-muted)" }}
      >
        Loading data…
      </div>
    );
  }

  return (
    <div data-dark={dark} style={{ background: "var(--bg-page)", minHeight: "100vh" }}>
      <Header
        totalBankCredit={null}
        latestDate="Mar 2026"
        darkMode={dark}
        onToggleDark={toggleDark}
      />

      <AtmPosFilterBar filter={filter} onChange={handleFilterChange} allBanks={allBanks} />

      {/* Tab bar */}
      <div style={{ borderBottom: "1px solid var(--border-card)" }}>
        <div className="flex gap-1 px-6 pt-4 pb-0">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="px-5 py-2 text-sm font-medium rounded-t-lg transition-colors"
              style={{
                background:   tab === t.id ? "var(--bg-card)"       : "transparent",
                color:        tab === t.id ? "#4e8ef7"               : "var(--font-muted)",
                borderBottom: tab === t.id ? "2px solid #4e8ef7"     : "2px solid transparent",
              }}
            >
              {t.icon}  {t.label}
            </button>
          ))}
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 py-6">

        {/* Substack embed — top */}
        <div className="mb-8 flex flex-col items-center gap-2">
          <p className="text-sm font-medium" style={{ color: "var(--font-muted)" }}>
            Monthly credit intelligence, free — get it in your inbox
          </p>
          <iframe
            src="https://indiacreditlens.substack.com/embed"
            width="100%"
            height="320"
            style={{
              maxWidth:     "480px",
              border:       "1px solid #EEE",
              background:   "white",
              borderRadius: "0.5rem",
            }}
            frameBorder={0}
            scrolling="no"
          />
        </div>

        {GROUPS.map((group) => {
          const groupSections = SECTION_DEFS.filter((d) => d.group === group);
          return (
            <div key={group}>
              <h2
                className="text-xs font-semibold uppercase tracking-wider"
                style={{
                  color:       "var(--font-muted)",
                  marginTop:   32,
                  marginBottom: 12,
                }}
              >
                {GROUP_LABELS[group]}
              </h2>
              {groupSections.map((def) => (
                <AtmPosSectionCard
                  key={def.id}
                  def={def}
                  rows={rows}
                  filter={filter}
                  tab={tab}
                  hiddenSeries={hiddenSeries.get(def.id) ?? EMPTY_HIDDEN}
                  onToggleSeries={(name) => handleToggleSeries(def.id, name)}
                />
              ))}
            </div>
          );
        })}

        {/* Substack embed — bottom */}
        <div className="mt-10 mb-2 flex flex-col items-center gap-2">
          <p className="text-sm font-medium" style={{ color: "var(--font-muted)" }}>
            Enjoyed the data? Get the analysis behind it in your inbox
          </p>
          <iframe
            src="https://indiacreditlens.substack.com/embed"
            width="100%"
            height="320"
            style={{
              maxWidth:     "480px",
              border:       "1px solid #EEE",
              background:   "white",
              borderRadius: "0.5rem",
            }}
            frameBorder={0}
            scrolling="no"
          />
        </div>

        <footer
          className="mt-6 pb-8 text-center text-xs"
          style={{ color: "var(--font-muted)" }}
        >
          Source: Reserve Bank of India · ATM / POS Card Statistics · Latest: Mar 2026
        </footer>
      </main>
    </div>
  );
}
