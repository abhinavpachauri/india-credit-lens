"use client";

import { useCallback, useState } from "react";
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

  // Only used for filterable sections (Industry by Type)
  const [visibleSeries, setVisibleSeries] = useState<string[]>([]);
  const onFilteredSeries = useCallback((names: string[]) => setVisibleSeries(names), []);

  function renderChart(visible?: string[]) {
    return tab === "trend" ? (
      <TrendChart
        absoluteData={section.absoluteData}
        growthData={section.growthData}
        seriesNames={section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visible}
        highlightConfig={ann.highlightConfig}
        preferredMode={ann.activeAnnotation?.preferredMode ?? null}
      />
    ) : (
      <DistributionChart
        absoluteData={section.absoluteData}
        seriesNames={section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visible}
        highlightConfig={ann.highlightConfig}
      />
    );
  }

  return (
    <SectionCard
      title={section.title}
      icon={section.icon}
      accentColor={SEC_COLORS[section.accentIndex]}
    >
      {/* Annotation lens buttons — shown below card title */}
      <AnnotationControls
        counts={ann.counts}
        activeLens={ann.activeLens}
        setLens={ann.setLens}
      />

      {/* Chart — filterable or standard */}
      {section.filterable ? (
        <>
          <IndustryFilter
            absoluteData={section.absoluteData}
            seriesNames={section.seriesNames}
            onFilteredSeries={onFilteredSeries}
          />
          {visibleSeries.length > 0 && renderChart(visibleSeries)}
        </>
      ) : (
        renderChart()
      )}

      {/* Annotation text panel — below the chart */}
      <AnnotationPanel
        activeLens={ann.activeLens}
        activeAnnotation={ann.activeAnnotation}
        activeIndex={ann.activeIndex}
        total={ann.total}
        next={ann.next}
        prev={ann.prev}
        setLens={ann.setLens}
      />
    </SectionCard>
  );
}
