"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAnnotation }    from "@/hooks/useAnnotation";
import { SEC_COLORS }       from "@/lib/theme";
import SectionCard          from "./SectionCard";
import AnnotationControls   from "./AnnotationControls";
import AnnotationPanel      from "./AnnotationPanel";
import TrendChart           from "./TrendChart";
import DistributionChart    from "./DistributionChart";
import IndustryFilter       from "./IndustryFilter";
import type { ReportSection } from "@/lib/types";
import type { TabId }         from "./TabBar";

interface Props {
  section: ReportSection;
  tab:     TabId;
}

export default function SectionWithAnnotations({ section, tab }: Props) {
  const ann = useAnnotation(section);

  // Reset lens only when tab actually changes — not on initial mount
  const prevTab = useRef<TabId | null>(null);
  useEffect(() => {
    if (prevTab.current !== null && prevTab.current !== tab) ann.reset();
    prevTab.current = tab;
  }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  // Series filter state — only active in explore mode
  const [visibleSeries, setVisibleSeries] = useState<string[]>([]);
  const onFilteredSeries = useCallback((names: string[]) => setVisibleSeries(names), []);

  const isExploreMode = ann.activeLens === null;

  function renderChart(visible?: string[]) {
    return tab === "trend" ? (
      <TrendChart
        absoluteData={section.absoluteData}
        growthData={section.growthData}
        fyData={section.fyData}
        seriesNames={section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visible}
        highlightConfig={ann.highlightConfig}
        preferredMode={ann.activeAnnotation?.preferredMode ?? null}
      />
    ) : (
      <DistributionChart
        absoluteData={section.absoluteData}
        seriesNames={section.distributionSeriesNames ?? section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visible}
        highlightConfig={ann.highlightConfig}
        preferredMode={ann.activeAnnotation?.preferredMode ?? null}
      />
    );
  }

  return (
    <SectionCard
      title={section.title}
      icon={section.icon}
      accentColor={SEC_COLORS[section.accentIndex]}
    >
      {/* Lens switcher */}
      <AnnotationControls
        counts={ann.counts}
        activeLens={ann.activeLens}
        setLens={ann.setLens}
        onExplore={ann.reset}
      />

      {/* Annotation card — above chart in intelligence mode */}
      <AnnotationPanel
        activeLens={ann.activeLens}
        activeAnnotation={ann.activeAnnotation}
        activeIndex={ann.activeIndex}
        total={ann.total}
        next={ann.next}
        prev={ann.prev}
      />

      {/* Chart — series filter only available in explore mode */}
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
