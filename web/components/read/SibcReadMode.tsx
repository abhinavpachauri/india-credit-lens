"use client";

// SIBC adapter — maps the credit Report + planes sidecar onto the shared RMModel, and renders the
// SIBC chart (TrendChart / DistributionChart). Dimension = section; subject = effect.highlight[0].

import { useMemo } from "react";
import type { Report, Annotation, ReportSection } from "@/lib/types";
import { organizeReadMode, type PlanesMap } from "@/lib/planes";
import { hasDeepReading } from "@/lib/opportunities";
import DeepReading from "./DeepReading";
import { SEC_COLORS } from "@/lib/theme";
import SectionCard from "@/components/SectionCard";
import TrendChart from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";
import ReadModeShell from "./ReadModeShell";
import { EYEBROW, type RMModel, type RMCard, type RMDimension } from "./parts";

const modeLabel = (pm?: string | null) =>
  pm === "share" ? "Share" : pm === "yoy" ? "YoY" : pm === "fy" ? "FY" : "Absolute";

export default function SibcReadMode({ report, planes }: { report: Report; planes: PlanesMap }) {
  const { model, annById, sectionById } = useMemo(() => {
    const org = organizeReadMode(report, planes);
    const readIds = new Set(org.reads.map((r) => r.card.id));
    const movedByDim = new Map<string, number>();
    for (const r of org.reads) movedByDim.set(r.section.id, (movedByDim.get(r.section.id) ?? 0) + 1);

    const annById = new Map<string, Annotation>();
    const sectionById = new Map<string, ReportSection>();

    const toCard = (a: Annotation, dimId: string): RMCard => {
      annById.set(a.id, a);
      return { id: a.id, title: a.title, body: a.body, implication: a.implication, chain: a.basis?.inferences, dimId, isRead: readIds.has(a.id) };
    };
    const dimensions: RMDimension[] = org.sections.map((sv) => {
      sectionById.set(sv.section.id, sv.section);
      return {
        id: sv.section.id, title: sv.section.title, icon: sv.section.icon,
        color: SEC_COLORS[sv.section.accentIndex] ?? "#4e8ef7",
        cardCount: sv.cardCount, moved: movedByDim.get(sv.section.id) ?? 0,
        subjects: sv.subjects.map((s) => ({ name: s.name, cards: s.cards.map((a) => toCard(a, sv.section.id)) })),
        compositionTitles: sv.compositionCards.map((c) => c.title),
      };
    });
    const reads = org.reads.map((r) => ({
      id: r.card.id, title: r.card.title, dimId: r.section.id, dimTitle: r.section.title,
      color: SEC_COLORS[r.section.accentIndex] ?? "#4e8ef7", reason: r.reason, direction: r.direction,
      mode: modeLabel(r.card.preferredMode),
    }));
    const model: RMModel = { reads, dimensions };
    return { model, annById, sectionById };
  }, [report, planes]);

  function renderChart(card: RMCard, dim: RMDimension) {
    const ann = annById.get(card.id);
    const section = sectionById.get(dim.id);
    if (!section) return null;
    const pm = ann?.preferredMode ?? null;
    const isDist = pm === "share";
    const trendMode: "absolute" | "yoy" | "fy" = pm === "yoy" || pm === "fy" ? pm : "absolute";
    const label = isDist ? "📊 Distribution · % share"
      : `📈 Trend · ${trendMode === "yoy" ? "YoY %" : trendMode === "fy" ? "FY cumulative" : "₹ absolute"}`;
    return (
      <>
        <div className="mb-3" style={{ fontSize: 13, fontWeight: 600, color: "var(--font-muted)" }}>{label}</div>
        <SectionCard accentColor={dim.color} bare>
          {isDist ? (
            <DistributionChart absoluteData={section.absoluteData}
              seriesNames={section.distributionSeriesNames ?? section.seriesNames}
              pctLabel={section.pctLabel} mode="pct" highlightConfig={ann?.effect ?? null} preferredMode={pm} />
          ) : (
            <TrendChart absoluteData={section.absoluteData} growthData={section.growthData}
              fyData={section.fyData} seriesNames={section.seriesNames} pctLabel={section.pctLabel}
              mode={trendMode} initialHidden={section.defaultHiddenSeries}
              highlightConfig={ann?.effect ?? null} preferredMode={pm} />
          )}
        </SectionCard>
      </>
    );
  }

  const dimTitle = (dimId: string) => model.dimensions.find((d) => d.id === dimId)?.title ?? "";
  const hasDeep = (dimId: string) => hasDeepReading("sibc", dimId, dimTitle(dimId));
  function renderDeep(dimId: string, color: string) {
    return (
      <DeepReading pipeline="sibc" sectionId={dimId} sectionTitle={dimTitle(dimId)}
                   color={color} otherLabel="payments" />
    );
  }

  const period = report.latestDate?.split(" ")[0] ?? "period";
  return (
    <ReadModeShell model={model} homeLabel="Credit dashboard" period={period}
                   renderChart={renderChart} hasDeep={hasDeep} renderDeep={renderDeep} />
  );
}
