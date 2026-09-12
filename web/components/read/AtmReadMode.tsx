"use client";

// Payments adapter — maps the flat ATM/POS insights + planes sidecar onto the shared RMModel, and
// renders the payments chart via buildSectionData. Dimension = group (cc/dc/infra); subject =
// effect.focusCard (its SectionDef title). Same shell, same §14 design — only the data + chart differ.

import { useMemo } from "react";
import {
  buildSectionData, buildPairData, buildShareData, metricLabel,
  SECTION_DEFS, GROUP_LABELS, GROUP_ICONS, GROUP_ACCENT,
  type AtmPosSeries, type FilterState, type SectionDef,
} from "@/lib/atm_pos_data";
import type { AtmPosInsight } from "@/lib/atm_pos_insights";
import type { PlanesMap } from "@/lib/planes";
import type { StateMap } from "@/lib/state";
import { hasDeepReading } from "@/lib/opportunities";
import DeepReading from "./DeepReading";
import SectionCard from "@/components/SectionCard";
import AtmPosTrendChart from "@/components/AtmPosTrendChart";
import AtmPosDistributionChart from "@/components/AtmPosDistributionChart";
import ReadModeShell, { type CutRef } from "./ReadModeShell";
import type { CutTables } from "@/lib/table";
import { EYEBROW, type RMModel, type RMCard, type RMDimension } from "./parts";
import { FS } from "@/lib/tokens";

const GROUPS = ["cc", "dc", "infra"] as const;
const TOP_N: FilterState = { mode: "top_n", selectedTypes: [], selectedBanks: [], topN: 5 };

function modeLabelShort(ins: AtmPosInsight) {
  if (ins.effect.tab === "distribution") return "Share";
  return ins.effect.trendMode === "yoy" ? "YoY" : ins.effect.trendMode === "mom" ? "MoM" : "Absolute";
}
function defFor(ins: AtmPosInsight, group: string): SectionDef | undefined {
  return SECTION_DEFS.find((d) => d.id === ins.effect.focusCard) ?? SECTION_DEFS.find((d) => d.group === group);
}

/** A payments group owns one cut per MEASURE — a credit dimension is one measure over a
 *  hierarchy, a payments group is many measures over the same bank categories. Derived from
 *  SECTION_DEFS so a new section cannot be forgotten here, and filtered by what the sidecar
 *  actually carries, so a measure with no cut simply does not appear.
 */
const atmCutsFor = (group: string): CutRef[] =>
  SECTION_DEFS.filter((d) => d.group === group).flatMap((d) => {
    const metrics = d.metric
      ? (Array.isArray(d.metric) ? d.metric : [d.metric])
      : [d.valMetric, d.volMetric].filter(Boolean) as string[];
    return metrics.map((m) => ({
      stem: `${m.replace(/_/g, "-")}-category`,
      title: metrics.length > 1 ? `${d.title} — ${m.endsWith("_val") ? "value" : "volume"}` : d.title,
    }));
  });

export default function AtmReadMode(
  { series, insights, planes, state, tables }:
    { series: AtmPosSeries; insights: AtmPosInsight[]; planes: PlanesMap; state: StateMap;
      tables: CutTables },
) {
  const { model, insById } = useMemo(() => {
    const plane = (id: string) => planes[id]?.plane ?? "subject";
    const insById = new Map(insights.map((i) => [i.id, i]));

    const toCard = (i: AtmPosInsight): RMCard => ({
      id: i.id, title: i.title, body: i.body, implication: i.implication,
      chain: i.basis?.inferences ?? i.reasoning?.chain, dimId: i.group, isRead: plane(i.id) === "read",
    });

    const dimensions: RMDimension[] = GROUPS.map((g) => {
      const gi = insights.filter((i) => i.group === g);
      // group by focusCard → subject (its SectionDef title), preserving feed order
      const order: string[] = [];
      const bySubject = new Map<string, RMCard[]>();
      for (const i of gi) {
        const name = SECTION_DEFS.find((d) => d.id === i.effect.focusCard)?.title ?? "";
        if (!bySubject.has(name)) { bySubject.set(name, []); order.push(name); }
        bySubject.get(name)!.push(toCard(i));
      }
      return {
        id: g, title: GROUP_LABELS[g], icon: GROUP_ICONS[g], color: GROUP_ACCENT[g],
        cardCount: gi.length, moved: gi.filter((i) => plane(i.id) === "read").length,
        subjects: order.map((name) => ({ name, cards: bySubject.get(name)! })),
        compositionTitles: gi.filter((i) => plane(i.id) === "composition").map((i) => i.title),
      };
    });

    const reads = insights
      .filter((i) => plane(i.id) === "read")
      .sort((a, b) => (planes[b.id]?.news_score ?? 0) - (planes[a.id]?.news_score ?? 0) || a.id.localeCompare(b.id))
      .map((i) => ({
        id: i.id, title: i.title, dimId: i.group, dimTitle: GROUP_LABELS[i.group],
        color: GROUP_ACCENT[i.group], reason: planes[i.id]?.reason ?? null, direction: planes[i.id]?.direction ?? null,
        mode: modeLabelShort(i),
      }));

    const model: RMModel = { reads, dimensions };
    return { model, insById };
  }, [series, insights, planes]);

  /**
   * The chart for one card — DASHBOARD_SPEC §15.6 (b) share_of and (c) pair.
   *
   * A `share_of` card's number IS a percentage and a `pair` card's number IS the distance
   * between two lines. Charted through the section builder, the first plotted the numerator's
   * raw count (the percentage appeared nowhere) and the second plotted one side and dropped
   * the other. Both now render what the card actually claims, per-bank detail giving way to
   * the metrics the claim is made of.
   */
  function renderChart(card: RMCard, dim: RMDimension) {
    const ins = insById.get(card.id);
    if (!ins) return null;
    const def = defFor(ins, dim.id);
    const metric = def?.metric ?? def?.volMetric;
    if (!def || !metric) return null;

    const cut = ins.effect.cut;
    const sectionMetrics = new Set([def.metric, def.volMetric, def.valMetric].flat().filter(Boolean) as string[]);
    // Only take over the chart when the claim reaches OUTSIDE what this section draws.
    // A share whose denominator is already on screen needs no second chart.
    const beyond = (cut?.metrics ?? []).filter((m: string) => !sectionMetrics.has(m));
    const isShare = cut?.shape === "share_of" && beyond.length > 0;
    const isPair  = cut?.shape === "pair" && beyond.length > 0 && !!cut?.sides?.length;

    const chartMode = ins.effect.trendMode ?? "absolute";
    if (isShare || isPair) {
      const metrics = cut!.metrics!;
      const sides = cut!.sides ?? [];
      const data = isShare ? buildShareData(series, metrics) : buildPairData(series, sides);
      // A share is already a percentage — growth modes would be a rate of a rate.
      const mode = isShare ? "absolute" : chartMode;

      const label = isShare
        ? `📊 Share · % of ${GROUP_LABELS[dim.id] ?? dim.title} volume`
        : `📈 Trend · ${mode === "yoy" ? "YoY %" : mode === "mom" ? "MoM %" : "Absolute"} · both sides`;
      const sideNames = data.seriesNames;
      return (
        <>
          <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1"
               style={{ fontSize: FS.note, fontWeight: 600, color: "var(--font-muted)" }}>
            <span>{label}</span>
            <span style={{ fontWeight: 500, color: dim.color }}>
              {isShare ? `${metrics.length} components` : sideNames.join(" vs ")}
            </span>
          </div>
          <SectionCard accentColor={dim.color} bare>
            <AtmPosTrendChart key={`${card.id}:cut`} absoluteData={data.absoluteData}
              momData={data.momData} yoyData={data.yoyData} seriesNames={data.seriesNames}
              unit={isShare ? "pct" : (def.unit ?? def.volUnit ?? "count")}
              hiddenSeries={new Set()} chartId={`${card.id}:cut`} chartMode={mode} />
          </SectionCard>
          <div className="mt-2" style={{ fontSize: FS.note, color: "var(--font-muted)" }}>
            {isShare
              ? <>Out of <span style={{ color: dim.color }}>{metrics.map(metricLabel).join(" + ")}</span> — the whole this share is measured against.</>
              : <>The card quotes the gap between these two lines.</>}
          </div>
        </>
      );
    }

    const unit = def.unit ?? def.volUnit ?? "count";
    const data = buildSectionData(series, metric, TOP_N);
    const highlighted = new Set(ins.effect.highlight ?? []);
    const hidden = new Set(data.seriesNames.filter((n) => highlighted.size > 0 && !highlighted.has(n)));
    const isDist = ins.effect.tab === "distribution";
    const label = isDist ? "📊 Distribution · % share"
      : `📈 Trend · ${chartMode === "yoy" ? "YoY %" : chartMode === "mom" ? "MoM %" : "Absolute"}`;
    return (
      <>
        <div className="mb-3" style={{ fontSize: FS.note, fontWeight: 600, color: "var(--font-muted)" }}>{label}</div>
        <SectionCard accentColor={dim.color} bare>
          {isDist ? (
            <AtmPosDistributionChart absoluteData={data.absoluteData} seriesNames={data.seriesNames}
              unit={unit} hiddenSeries={hidden} chartId={card.id} chartMode="pct" />
          ) : (
            <AtmPosTrendChart absoluteData={data.absoluteData} momData={data.momData} yoyData={data.yoyData}
              seriesNames={data.seriesNames} unit={unit} hiddenSeries={hidden} chartId={card.id} chartMode={chartMode} />
          )}
        </SectionCard>
      </>
    );
  }

  const dimTitle = (dimId: string) => model.dimensions.find((d) => d.id === dimId)?.title ?? "";
  const hasDeep = (dimId: string) => hasDeepReading("atm_pos", dimId, dimTitle(dimId));
  function renderDeep(dimId: string, color: string) {
    return (
      <DeepReading pipeline="atm_pos" sectionId={dimId} sectionTitle={dimTitle(dimId)}
                   color={color} otherLabel="credit" />
    );
  }

  const iso = series._meta.periods[series._meta.periods.length - 1];
  const period = iso ? new Date(`${iso}T00:00:00Z`).toLocaleString("en-US", { month: "short", timeZone: "UTC" }) : "period";

  return (
    <ReadModeShell model={model} homeLabel="Payments dashboard" period={period} state={state}
                   tables={tables} cutsFor={atmCutsFor}
                   renderChart={renderChart} hasDeep={hasDeep} renderDeep={renderDeep} />
  );
}
