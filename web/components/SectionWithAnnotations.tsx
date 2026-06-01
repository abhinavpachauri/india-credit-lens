"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSectionInsights }   from "@/hooks/useSectionInsights";
import { SEC_COLORS }           from "@/lib/theme";
import SectionCard              from "./SectionCard";
import InsightCTAStrip          from "./dls/InsightCTAStrip";
import InsightCard              from "./dls/InsightCard";
import OpportunityTeaser        from "./dls/OpportunityTeaser";
import TrendChart               from "./TrendChart";
import DistributionChart        from "./DistributionChart";
import IndustryFilter           from "./IndustryFilter";
import type { ReportSection }   from "@/lib/types";

type TabId      = "trend" | "distribution";
type TrendMode  = "absolute" | "yoy" | "fy";
type DistMode   = "absolute" | "pct";

interface Props {
  section: ReportSection;
}

// Matches the payments controls card style exactly
const CONTROLS_CARD: React.CSSProperties = {
  background:   "var(--bg-card)",
  border:       "1px solid var(--border-card)",
  borderRadius: 10,
  padding:      "12px 16px",
  marginBottom: 16,
};

const DIVIDER: React.CSSProperties = {
  width: 1, height: 20, background: "var(--border-card)", flexShrink: 0,
};

const BTN = (active: boolean): React.CSSProperties => ({
  background: active ? "#4e8ef7" : "var(--bg-page)",
  color:      active ? "#fff"    : "var(--font-muted)",
  border:     `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`,
});

export default function SectionWithAnnotations({ section }: Props) {
  const ins = useSectionInsights(section);

  // Per-section tab and chart-mode state — mirrors payments per-group controls
  const [tab,       setTab]       = useState<TabId>("trend");
  const [trendMode, setTrendMode] = useState<TrendMode>("absolute");
  const [distMode,  setDistMode]  = useState<DistMode>("absolute");

  // Exit insights when the local tab changes (user navigating away mid-insight)
  const prevTab = useRef<TabId | null>(null);
  useEffect(() => {
    if (prevTab.current !== null && prevTab.current !== tab) ins.exit();
    prevTab.current = tab;
  }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  // Series filter — only used in explore (non-insights) mode for filterable sections
  const [visibleSeries, setVisibleSeries] = useState<string[]>([]);
  const onFilteredSeries = useCallback((names: string[]) => setVisibleSeries(names), []);

  const isExploreMode = !ins.isActive;
  const accentColor   = SEC_COLORS[section.accentIndex];

  function renderChart(visible?: string[]) {
    return tab === "trend" ? (
      <TrendChart
        absoluteData={section.absoluteData}
        growthData={section.growthData}
        fyData={section.fyData}
        seriesNames={section.seriesNames}
        pctLabel={section.pctLabel}
        mode={trendMode}
        visibleSeries={visible}
        highlightConfig={ins.highlightConfig}
        preferredMode={ins.current?.preferredMode ?? null}
      />
    ) : (
      <DistributionChart
        absoluteData={section.absoluteData}
        seriesNames={section.distributionSeriesNames ?? section.seriesNames}
        pctLabel={section.pctLabel}
        mode={distMode}
        visibleSeries={visible}
        highlightConfig={ins.highlightConfig}
        preferredMode={ins.current?.preferredMode ?? null}
      />
    );
  }

  return (
    <div className="mb-8">
      {/* Section heading */}
      <div className="flex items-center gap-2" style={{ marginTop: 32, marginBottom: 12 }}>
        <span className="text-lg leading-none">{section.icon}</span>
        <h2
          className="text-sm font-bold leading-snug"
          style={{ color: "var(--font)" }}
        >
          {section.title}
        </h2>
      </div>

      {/* Opportunity teaser — gated, separate from carousel */}
      <OpportunityTeaser opps={ins.opps} sectionId={section.id} />

      {/* CTA / exit strip */}
      {ins.flat.length > 0 && (
        <InsightCTAStrip
          items={ins.flat.map((a) => ({ type: a._type, title: a.title }))}
          counts={ins.counts}
          isActive={ins.isActive}
          activeIdx={ins.activeIdx}
          total={ins.total}
          onEnter={ins.enter}
          onExit={ins.exit}
        />
      )}

      {/* Insight card */}
      {ins.isActive && ins.current && (
        <InsightCard
          key={ins.activeIdx}
          type={ins.current._type}
          title={ins.current.title}
          body={ins.current.body}
          implication={ins.current.implication}
          chain={ins.current.basis?.inferences}
          activeIndex={ins.activeIdx}
          total={ins.total}
          onNext={ins.next}
          onPrev={ins.prev}
        />
      )}

      {/* ── Controls card — hidden in insights mode (same as payments) ─────── */}
      {!ins.isActive && (
        <div style={CONTROLS_CARD}>
          {/* Tab + chart-mode row */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Tab buttons */}
            <div className="flex gap-1">
              {([
                ["trend",        "📈 Trend"],
                ["distribution", "📊 Distribution"],
              ] as const).map(([t, label]) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className="text-sm font-medium px-3 py-1.5 rounded-full transition-colors"
                  style={BTN(tab === t)}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="hidden sm:block" style={DIVIDER} />

            {/* Chart-mode radios — change with active tab */}
            <div className="flex items-center gap-3 text-sm">
              {tab === "trend"
                ? (["absolute", "yoy", "fy"] as const).map((m) => (
                    <label
                      key={m}
                      className="flex items-center gap-1.5 cursor-pointer"
                      style={{ color: "var(--font)" }}
                    >
                      <input
                        type="radio"
                        name={`trend-${section.id}`}
                        value={m}
                        checked={trendMode === m}
                        onChange={() => setTrendMode(m)}
                        className="accent-blue-500"
                      />
                      {m === "absolute" ? "Absolute" : m === "yoy" ? "YoY %" : "FY Cumul."}
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
                        name={`dist-${section.id}`}
                        value={m}
                        checked={distMode === m}
                        onChange={() => setDistMode(m)}
                        className="accent-blue-500"
                      />
                      {m === "absolute" ? "₹ Crore" : "% Share"}
                    </label>
                  ))}
            </div>
          </div>

          {/* Industry filter — only for filterable sections */}
          {section.filterable && (
            <div className="mt-3">
              <IndustryFilter
                absoluteData={section.absoluteData}
                seriesNames={section.seriesNames}
                onFilteredSeries={onFilteredSeries}
              />
            </div>
          )}
        </div>
      )}

      {/* Chart card */}
      <SectionCard accentColor={accentColor} bare>
        {section.filterable
          ? ((!isExploreMode || visibleSeries.length > 0) &&
              renderChart(isExploreMode ? visibleSeries : undefined))
          : renderChart()
        }
      </SectionCard>
    </div>
  );
}
