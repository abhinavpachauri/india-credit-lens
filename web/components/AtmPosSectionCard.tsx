"use client";

import { useState, useMemo } from "react";
import { buildSectionData } from "@/lib/atm_pos_data";
import type { SectionDef, AtmPosSeries, FilterState, VolVal } from "@/lib/atm_pos_data";
import SectionCard          from "@/components/SectionCard";
import AtmPosTrendChart     from "@/components/AtmPosTrendChart";
import AtmPosDistributionChart from "@/components/AtmPosDistributionChart";

interface AtmPosSectionCardProps {
  def:          SectionDef;
  series:         AtmPosSeries;
  filter:       FilterState;
  tab:          "trend" | "distribution";
  hiddenSeries: Set<string>;
  trendMode:    "absolute" | "mom" | "yoy";
  distMode:     "absolute" | "pct";
  accentColor:  string;
}

const ACTIVE_VOL_VAL: React.CSSProperties = {
  background: "#4e8ef7",
  color:      "#fff",
  border:     "1px solid #4e8ef7",
};

const INACTIVE_VOL_VAL: React.CSSProperties = {
  background: "var(--bg-page)",
  color:      "var(--font-muted)",
  border:     "1px solid var(--border-card)",
};

export default function AtmPosSectionCard({
  def,
  series,
  filter,
  tab,
  hiddenSeries,
  trendMode,
  distMode,
  accentColor,
}: AtmPosSectionCardProps) {
  const [volVal, setVolVal] = useState<VolVal>("vol");

  const hasVolVal = !!(def.volMetric && def.valMetric);

  const { activeMetric, activeUnit } = useMemo(() => {
    if (def.metric) {
      return { activeMetric: def.metric, activeUnit: def.unit ?? "count" };
    }
    if (volVal === "vol") {
      return { activeMetric: def.volMetric!, activeUnit: def.volUnit ?? "transactions" };
    }
    return { activeMetric: def.valMetric!, activeUnit: def.valUnit ?? "rs_thousands" };
  }, [def, volVal]);

  const { absoluteData, momData, yoyData, seriesNames } = useMemo(
    () => buildSectionData(series, activeMetric, filter),
    [series, activeMetric, filter],
  );

  return (
    <SectionCard accentColor={accentColor} bare>
      {/* Card header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm flex-shrink-0">{def.icon}</span>
        <h3 className="text-sm font-semibold min-w-0" style={{ color: "var(--font)" }}>
          {def.title}
        </h3>

        {/* Vol / Val toggle */}
        {hasVolVal && (
          <div className="flex items-center gap-1 ml-auto flex-shrink-0">
            {(["vol", "val"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setVolVal(v)}
                className="text-sm font-medium px-2 py-0.5 rounded-full transition-colors"
                style={volVal === v ? ACTIVE_VOL_VAL : INACTIVE_VOL_VAL}
              >
                {v === "vol" ? "Vol" : "Val"}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Chart */}
      {tab === "trend" ? (
        <AtmPosTrendChart
          absoluteData={absoluteData}
          momData={momData}
          yoyData={yoyData}
          seriesNames={seriesNames}
          unit={activeUnit}
          hiddenSeries={hiddenSeries}
          chartId={def.id}
          chartMode={trendMode}
        />
      ) : (
        <AtmPosDistributionChart
          absoluteData={absoluteData}
          seriesNames={seriesNames}
          unit={activeUnit}
          hiddenSeries={hiddenSeries}
          chartId={def.id}
          chartMode={distMode}
        />
      )}
    </SectionCard>
  );
}
