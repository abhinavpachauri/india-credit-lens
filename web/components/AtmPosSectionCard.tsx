"use client";

import { useState, useMemo } from "react";
import { buildSectionData } from "@/lib/atm_pos_data";
import type { SectionDef, AtmPosRow, FilterState, VolVal } from "@/lib/atm_pos_data";
import AtmPosTrendChart from "@/components/AtmPosTrendChart";
import AtmPosDistributionChart from "@/components/AtmPosDistributionChart";

interface AtmPosSectionCardProps {
  def:          SectionDef;
  rows:         AtmPosRow[];
  filter:       FilterState;
  tab:          "trend" | "distribution";
  hiddenSeries: Set<string>;
  trendMode:    "absolute" | "mom";
  distMode:     "absolute" | "pct";
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
  rows,
  filter,
  tab,
  hiddenSeries,
  trendMode,
  distMode,
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

  const { absoluteData, momData, seriesNames } = useMemo(
    () => buildSectionData(rows, activeMetric, filter),
    [rows, activeMetric, filter],
  );


  return (
    <div
      style={{
        background:   "var(--bg-card)",
        border:       "1px solid var(--border-card)",
        borderRadius: 10,
        boxShadow:    "0 1px 4px var(--shadow)",
        padding:      "14px 16px",
      }}
    >
      {/* Card header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm flex-shrink-0">{def.icon}</span>
        <h3 className="text-sm font-semibold min-w-0" style={{ color: "var(--font)" }}>
          {def.title}
        </h3>


        {/* Vol / Val toggle */}
        {hasVolVal && (
          <div className="flex items-center gap-1 flex-shrink-0">
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
    </div>
  );
}
