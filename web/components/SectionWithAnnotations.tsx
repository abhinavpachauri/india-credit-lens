"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSectionInsights }   from "@/hooks/useSectionInsights";
import { SEC_COLORS }           from "@/lib/theme";
import { TYPE_COLOR }           from "@/components/dls/InsightCard";
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

  // Newsletter CTA footer — shows remaining count + Substack link
  const remaining = ins.total - 1 - ins.activeIdx;
  const currentType = ins.current?._type ?? "insight";
  const newsletterFooter = remaining > 0 ? (
    <p className="text-xs" style={{ color: "var(--font-muted)" }}>
      {remaining} more {currentType}{remaining !== 1 ? "s" : ""} in this section.{" "}
      <a
        href="https://indiacreditlens.substack.com"
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: TYPE_COLOR[currentType], textDecoration: "underline" }}
      >
        Get all 45 free →
      </a>
    </p>
  ) : null;

  const isExploreMode = !ins.isActive;

  return (
    <SectionCard
      title={section.title}
      icon={section.icon}
      accentColor={SEC_COLORS[section.accentIndex]}
    >
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
          footerSlot={newsletterFooter}
        />
      )}

      {/* Chart — series filter only in explore mode */}
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
  );
}
