"use client";

/**
 * DLS — SectionSparkline
 *
 * Compact 80px trend line for opportunity cards.
 * Shows the FIRST series (total / main metric) from absoluteData.
 * No axes, no grid, no tooltip text — just the trend shape.
 *
 * Intentionally minimal: pure evidence, not interactive.
 */

import { useMemo } from "react";
import {
  AreaChart, Area, YAxis, ResponsiveContainer, Tooltip,
} from "recharts";
import type { SectionChartSlice } from "@/lib/section-chart-data";

const OPP_COLOR = "#16A34A";
const AREA_FILL = `${OPP_COLOR}18`;

interface Props {
  slice:      SectionChartSlice;
  /** Label shown in the minimal tooltip (e.g. "₹ Crore"). Defaults to "₹ Crore" */
  valueLabel?: string;
}

// Minimal tooltip — just the value, no clutter
function SparkTooltip({ active, payload, label }: {
  active?:  boolean;
  payload?: { value: number | null }[];
  label?:   string;
}) {
  if (!active || !payload?.length) return null;
  const val = payload[0]?.value;
  if (val == null) return null;
  return (
    <div
      style={{
        background:   "var(--bg-card)",
        border:       "1px solid var(--border-card)",
        borderRadius: 4,
        padding:      "3px 8px",
        fontSize:     11,
        color:        "var(--font)",
        boxShadow:    "0 1px 4px var(--shadow)",
      }}
    >
      <span style={{ color: "var(--font-muted)", marginRight: 4 }}>{label}</span>
      <strong>₹{(val / 100000).toFixed(1)}L Cr</strong>
    </div>
  );
}

export default function SectionSparkline({ slice }: Props) {
  const mainSeries = slice.seriesNames[0];

  // Keep only the last 24 data points (2 years) — enough to show the trend
  // without making the sparkline too dense for a card-sized render
  const data = useMemo(() => {
    const pts = slice.absoluteData.filter(
      (p) => p[mainSeries] != null
    );
    return pts.slice(-24);
  }, [slice.absoluteData, mainSeries]);

  if (!data.length || !mainSeries) return null;

  return (
    <div style={{ width: "100%", height: 80, marginTop: 12 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          {/* Hidden Y axis just to auto-scale */}
          <YAxis domain={["auto", "auto"]} hide />

          <Tooltip
            content={<SparkTooltip />}
            cursor={{ stroke: OPP_COLOR, strokeWidth: 1, strokeDasharray: "3 3" }}
          />

          <Area
            type="monotone"
            dataKey={mainSeries}
            stroke={OPP_COLOR}
            strokeWidth={1.5}
            fill={AREA_FILL}
            dot={false}
            activeDot={{ r: 3, fill: OPP_COLOR, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
