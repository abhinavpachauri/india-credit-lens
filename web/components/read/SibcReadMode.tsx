"use client";

// SIBC adapter — maps the credit Report + planes sidecar onto the shared RMModel, and renders the
// SIBC chart (TrendChart / DistributionChart). Dimension = section; subject = effect.highlight[0].

import { useMemo } from "react";
import type { Report, Annotation, ReportSection } from "@/lib/types";
import { organizeReadMode, type PlanesMap } from "@/lib/planes";
import type { StateMap } from "@/lib/state";
import { hasDeepReading } from "@/lib/opportunities";
import DeepReading from "./DeepReading";
import { SEC_COLORS } from "@/lib/theme";
import SectionCard from "@/components/SectionCard";
import TrendChart from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";
import ReadModeShell from "./ReadModeShell";
import { EYEBROW, type RMModel, type RMCard, type RMDimension } from "./parts";
import { FS } from "@/lib/tokens";

/** The last non-null value of one series in a ChartPoint[]. */
function lastValue(points: { date: string; [k: string]: string | number | null }[], name: string): number | null {
  for (let i = points.length - 1; i >= 0; i--) {
    const v = points[i]?.[name];
    if (typeof v === "number" && Number.isFinite(v)) return v;
  }
  return null;
}

/**
 * The parent's own numbers, kept — §15.6(a). Charting the sub-cut answers the card, but the
 * figures the reader had before (the parent's share of its section, and its growth) are real
 * and were the only thing on screen until now. They belong underneath as context, not gone.
 */
function ParentContext(
  { section, sub, color }: { section: ReportSection; sub: ReportSection; color: string },
) {
  const name = sub.parentLabel ?? "";
  const share = lastValue(section.absoluteData, name);
  // Out of the section's OWN total — the same denominator the chart above it uses, which
  // for a section built from childrenOf() is the sum of its children, not a separate row.
  const total = section.seriesNames.reduce(
    (t, n) => t + (n === "Total" ? 0 : (lastValue(section.absoluteData, n) ?? 0)), 0);
  const yoy = lastValue(section.growthData, name);
  if (share == null || !total) return null;
  return (
    <div className="mt-2" style={{ fontSize: FS.note, color: "var(--font-muted)" }}>
      <span style={{ color }}>{name}</span>{" is "}
      <strong>{((share / total) * 100).toFixed(1)}%</strong>{" of "}
      {section.pctLabel.replace(/^%\s*(of\s*)?/i, "") || section.title}
      {yoy != null && <>{", growing "}<strong>{yoy.toFixed(1)}%</strong>{" YoY"}</>}
      {" — the level above this chart."}
    </div>
  );
}

const modeLabel = (pm?: string | null) =>
  pm === "share" ? "Share" : pm === "yoy" ? "YoY" : pm === "fy" ? "FY" : "Absolute";

export default function SibcReadMode(
  { report, planes, state }: { report: Report; planes: PlanesMap; state: StateMap },
) {
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

  /**
   * The chart for one card — DASHBOARD_SPEC §15.6(a).
   *
   * A card computed over a sub-cut (the children of one industry, one service line) is charted
   * on that cut, not on its parent's level. The parent's own figures move to a footer line, so
   * the number the reader sees today is kept as context instead of being replaced by a rival.
   */
  function renderChart(card: RMCard, dim: RMDimension) {
    const ann = annById.get(card.id);
    const section = sectionById.get(dim.id);
    if (!section) return null;

    // §15.5: resolve, or render the section as it is. Never quietly substitute an ancestor
    // and present it as the card's evidence — that silent fallback is the whole defect.
    const cut = ann?.effect?.cut;
    const sub = cut?.parent_code ? section.subCuts?.[cut.parent_code] : undefined;
    const chart = sub ?? section;

    const pm = ann?.preferredMode ?? null;
    const isDist = pm === "share";
    const trendMode: "absolute" | "yoy" | "fy" = pm === "yoy" || pm === "fy" ? pm : "absolute";
    const denom = sub ? `% of ${sub.parentLabel}` : "% share";
    const label = isDist ? `📊 Distribution · ${denom}`
      : `📈 Trend · ${trendMode === "yoy" ? "YoY %" : trendMode === "fy" ? "FY cumulative" : "₹ absolute"}`;

    // On a sub-cut the card names its own children, not the parent the generator had to
    // fall back to while no chart could draw them (§15.4).
    const effect = sub ? { ...(ann?.effect ?? {}), highlight: undefined } : (ann?.effect ?? null);

    return (
      <>
        <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1"
             style={{ fontSize: FS.note, fontWeight: 600, color: "var(--font-muted)" }}>
          <span>{label}</span>
          {sub && (
            <span style={{ fontWeight: 500, color: dim.color }}>
              {sub.parentLabel} · {sub.seriesNames.length - 1} sub-types
            </span>
          )}
        </div>
        <SectionCard accentColor={dim.color} bare>
          {/*
            Keyed by the chart's own id: a sub-cut is a different set of series, and
            TrendChart seeds its hidden-series state once via useState, so without a
            remount the sub-cut inherits whichever toggles the parent chart was left
            in — which is how its "Total" line came back after being defaulted off.
            Same id within a section, so switching cards still keeps the reader's own
            legend toggles.
          */}
          {isDist ? (
            <DistributionChart key={chart.id} absoluteData={chart.absoluteData}
              seriesNames={chart.distributionSeriesNames ?? chart.seriesNames}
              pctLabel={chart.pctLabel} mode="pct" highlightConfig={effect} preferredMode={pm} />
          ) : (
            <TrendChart key={chart.id} absoluteData={chart.absoluteData} growthData={chart.growthData}
              fyData={chart.fyData} seriesNames={chart.seriesNames} pctLabel={chart.pctLabel}
              mode={trendMode} initialHidden={chart.defaultHiddenSeries}
              highlightConfig={effect} preferredMode={pm} />
          )}
        </SectionCard>
        {sub && <ParentContext section={section} sub={sub} color={dim.color} />}
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
    <ReadModeShell model={model} homeLabel="Credit dashboard" period={period} state={state}
                   renderChart={renderChart} hasDeep={hasDeep} renderDeep={renderDeep} />
  );
}
