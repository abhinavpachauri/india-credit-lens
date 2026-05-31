"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSectionInsights }   from "@/hooks/useSectionInsights";
import { SEC_COLORS }           from "@/lib/theme";
import SectionCard              from "./SectionCard";
import InsightCTAStrip          from "./dls/InsightCTAStrip";
import InsightCard              from "./dls/InsightCard";
import TrendChart               from "./TrendChart";
import DistributionChart        from "./DistributionChart";
import IndustryFilter           from "./IndustryFilter";
import type { ReportSection }   from "@/lib/types";
import type { TabId }           from "./TabBar";

interface Props {
  section: ReportSection;
  tab:     TabId;
}

export default function SectionWithAnnotations({ section, tab }: Props) {
  const ins = useSectionInsights(section);

  // Reset insights mode when tab changes
  const prevTab = useRef<TabId | null>(null);
  useEffect(() => {
    if (prevTab.current !== null && prevTab.current !== tab) ins.exit();
    prevTab.current = tab;
  }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  // Series filter — only in explore (non-active) mode
  const [visibleSeries, setVisibleSeries] = useState<string[]>([]);
  const onFilteredSeries = useCallback((names: string[]) => setVisibleSeries(names), []);

  function renderChart(visible?: string[]) {
    return tab === "trend" ? (
      <TrendChart
        absoluteData={section.absoluteData}
        growthData={section.growthData}
        fyData={section.fyData}
        seriesNames={section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visible}
        highlightConfig={ins.highlightConfig}
        preferredMode={ins.current?.preferredMode ?? null}
      />
    ) : (
      <DistributionChart
        absoluteData={section.absoluteData}
        seriesNames={section.distributionSeriesNames ?? section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visible}
        highlightConfig={ins.highlightConfig}
        preferredMode={ins.current?.preferredMode ?? null}
      />
    );
  }

  const isExploreMode = !ins.isActive;

  const accentColor = SEC_COLORS[section.accentIndex];

  return (
    <div className="mb-8">
      {/* Section heading — matches payments group heading pattern */}
      <div className="flex items-center gap-2" style={{ marginTop: 32, marginBottom: 12 }}>
        <span className="text-lg leading-none">{section.icon}</span>
        <h2
          className="text-sm font-bold leading-snug"
          style={{ color: "var(--font)" }}
        >
          {section.title}
        </h2>
      </div>

      {/* CTA / exit strip — outside the card, above it */}
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

      {/* Insight card — key resets internal chain-expand state on navigation */}
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

      {/* Chart card — bare (no duplicate title header) */}
      <SectionCard accentColor={accentColor} bare>
        {section.filterable ? (
          <>
            {isExploreMode && (
              <IndustryFilter
                absoluteData={section.absoluteData}
                seriesNames={section.seriesNames}
                onFilteredSeries={onFilteredSeries}
              />
            )}
            {(!isExploreMode || visibleSeries.length > 0) && renderChart(isExploreMode ? visibleSeries : undefined)}
          </>
        ) : (
          renderChart()
        )}
      </SectionCard>
    </div>
  );
}
