"use client";

import { useState, useMemo } from "react";
import { buildSectionData } from "@/lib/atm_pos_data";
import type { SectionDef, AtmPosRow, FilterState, VolVal } from "@/lib/atm_pos_data";
import { pickColor } from "@/lib/theme";
import AtmPosTrendChart from "@/components/AtmPosTrendChart";
import AtmPosDistributionChart from "@/components/AtmPosDistributionChart";

interface AtmPosSectionCardProps {
  def:             SectionDef;
  rows:            AtmPosRow[];
  filter:          FilterState;
  tab:             "trend" | "distribution";
  hiddenSeries:    Set<string>;
  onToggleSeries:  (name: string) => void;
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

export default function AtmPosSectionCard({ def, rows, filter, tab, hiddenSeries, onToggleSeries }: AtmPosSectionCardProps) {
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
        padding:      "16px 20px",
        marginBottom: 16,
      }}
    >
      {/* Card header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">{def.icon}</span>
          <h3 className="text-sm font-semibold" style={{ color: "var(--font)" }}>
            {def.title}
          </h3>
        </div>

        {/* Vol / Val toggle */}
        {hasVolVal && (
          <div className="flex items-center gap-1">
            {(["vol", "val"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setVolVal(v)}
                className="text-xs font-medium px-2.5 py-1 rounded-full transition-colors"
                style={volVal === v ? ACTIVE_VOL_VAL : INACTIVE_VOL_VAL}
              >
                {v === "vol" ? "Vol" : "Val"}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Series chips */}
      {seriesNames.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {seriesNames.map((name, i) => {
            const color    = pickColor(name, i);
            const isHidden = hiddenSeries.has(name);
            return (
              <button
                key={name}
                onClick={() => onToggleSeries(name)}
                className="text-xs font-medium px-3 py-1 rounded-full transition-all"
                style={{
                  background: isHidden ? "transparent" : color,
                  border:     `1.5px solid ${color}`,
                  color:      isHidden ? color          : "#fff",
                  opacity:    isHidden ? 0.65            : 1,
                }}
              >
                {name}
              </button>
            );
          })}
        </div>
      )}

      {/* Chart */}
      {tab === "trend" ? (
        <AtmPosTrendChart
          absoluteData={absoluteData}
          momData={momData}
          seriesNames={seriesNames}
          unit={activeUnit}
          hiddenSeries={hiddenSeries}
          chartId={def.id}
        />
      ) : (
        <AtmPosDistributionChart
          absoluteData={absoluteData}
          seriesNames={seriesNames}
          unit={activeUnit}
          hiddenSeries={hiddenSeries}
          chartId={def.id}
        />
      )}
    </div>
  );
}
