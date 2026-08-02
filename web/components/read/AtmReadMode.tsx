"use client";

// Payments adapter — maps the flat ATM/POS insights + planes sidecar onto the shared RMModel, and
// renders the payments chart via buildSectionData. Dimension = group (cc/dc/infra); subject =
// effect.focusCard (its SectionDef title). Same shell, same §14 design — only the data + chart differ.

import { useMemo } from "react";
import {
  buildSectionData, SECTION_DEFS, GROUP_LABELS, GROUP_ICONS, GROUP_ACCENT,
  type AtmPosSeries, type FilterState, type SectionDef,
} from "@/lib/atm_pos_data";
import type { AtmPosInsight } from "@/lib/atm_pos_insights";
import type { PlanesMap } from "@/lib/planes";
import { opportunitiesFor } from "@/lib/opportunities";
import SectionCard from "@/components/SectionCard";
import AtmPosTrendChart from "@/components/AtmPosTrendChart";
import AtmPosDistributionChart from "@/components/AtmPosDistributionChart";
import ReadModeShell from "./ReadModeShell";
import { EYEBROW, type RMModel, type RMCard, type RMDimension } from "./parts";

const GROUPS = ["cc", "dc", "infra"] as const;
const TOP_N: FilterState = { mode: "top_n", selectedTypes: [], selectedBanks: [], topN: 5 };

function modeLabelShort(ins: AtmPosInsight) {
  if (ins.effect.tab === "distribution") return "Share";
  return ins.effect.trendMode === "yoy" ? "YoY" : ins.effect.trendMode === "mom" ? "MoM" : "Absolute";
}
function defFor(ins: AtmPosInsight, group: string): SectionDef | undefined {
  return SECTION_DEFS.find((d) => d.id === ins.effect.focusCard) ?? SECTION_DEFS.find((d) => d.group === group);
}

export default function AtmReadMode(
  { series, insights, planes }: { series: AtmPosSeries; insights: AtmPosInsight[]; planes: PlanesMap },
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

  function renderChart(card: RMCard, dim: RMDimension) {
    const ins = insById.get(card.id);
    if (!ins) return null;
    const def = defFor(ins, dim.id);
    const metric = def?.metric ?? def?.volMetric;
    if (!def || !metric) return null;
    const unit = def.unit ?? def.volUnit ?? "count";
    const data = buildSectionData(series, metric, TOP_N);
    const highlighted = new Set(ins.effect.highlight ?? []);
    const hidden = new Set(data.seriesNames.filter((n) => highlighted.size > 0 && !highlighted.has(n)));
    const isDist = ins.effect.tab === "distribution";
    const chartMode = ins.effect.trendMode ?? "absolute";
    const label = isDist ? "📊 Distribution · % share"
      : `📈 Trend · ${chartMode === "yoy" ? "YoY %" : chartMode === "mom" ? "MoM %" : "Absolute"}`;
    return (
      <>
        <div className="mb-3" style={{ fontSize: 13, fontWeight: 600, color: "var(--font-muted)" }}>{label}</div>
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

  const hasDeep = (dimId: string) => opportunitiesFor("atm_pos", dimId).length > 0;
  function renderDeep(dimId: string, color: string) {
    const opps = opportunitiesFor("atm_pos", dimId);
    if (!opps.length) return null;
    return (
      <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--border-card)" }}>
        <div style={{ ...EYEBROW, letterSpacing: "0.05em" }}>⌁ What this opens</div>
        {opps.map((o) => (
          <a key={o.id} href={`/opportunities#${o.id}`} className="rm-link block mt-1.5" style={{ fontSize: 15, fontWeight: 600, color }}>
            {o.title} <span style={{ color: "var(--font-muted)", fontWeight: 400 }}>· {o.status}</span>
          </a>
        ))}
      </div>
    );
  }

  const iso = series._meta.periods[series._meta.periods.length - 1];
  const period = iso ? new Date(`${iso}T00:00:00Z`).toLocaleString("en-US", { month: "short", timeZone: "UTC" }) : "period";

  return (
    <ReadModeShell model={model} homeLabel="Payments dashboard" period={period}
                   renderChart={renderChart} hasDeep={hasDeep} renderDeep={renderDeep} />
  );
}
