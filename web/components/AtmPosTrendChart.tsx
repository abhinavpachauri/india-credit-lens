"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { pickColor } from "@/lib/theme";
import { formatAtmValue } from "@/lib/atm_pos_data";
import type { ChartPoint } from "@/lib/atm_pos_data";

interface AtmPosTrendChartProps {
  absoluteData: ChartPoint[];
  momData:      ChartPoint[];
  seriesNames:  string[];
  unit:         string;
  hiddenSeries: Set<string>;
  chartId:      string;
  chartMode:    "absolute" | "mom";
}

export default function AtmPosTrendChart({
  absoluteData,
  momData,
  seriesNames,
  unit,
  hiddenSeries,
  chartMode,
}: AtmPosTrendChartProps) {
  const chartData = chartMode === "absolute" ? absoluteData : momData;

  const formatY = (v: number) =>
    chartMode === "absolute" ? formatAtmValue(v, unit) : `${v.toFixed(1)}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div
        style={{
          background:   "var(--bg-card)",
          border:       "1px solid var(--border-card)",
          borderRadius: 8,
          fontSize:     13,  // --chart-tooltip-size
          color:        "var(--font)",
          padding:      "10px 14px",
        }}
      >
        <p style={{ marginBottom: 4, fontWeight: 600 }}>{label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} style={{ color: p.color, margin: "2px 0" }}>
            {p.name}:{" "}
            {chartMode === "absolute"
              ? formatAtmValue(Number(p.value) || 0, unit)
              : p.value == null
              ? "—"
              : `${Number(p.value).toFixed(1)}%`}
          </p>
        ))}
      </div>
    );
  };

  return (
    <div style={{ minWidth: 0, overflow: "hidden" }}>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: "var(--font-muted)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatY}
            tick={{ fontSize: 12, fill: "var(--font-muted)" }}
            tickLine={false}
            axisLine={false}
            width={72}
          />
          <Tooltip content={<CustomTooltip />} />
          {seriesNames.map((name, i) =>
            hiddenSeries.has(name) ? null : (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                name={name}
                stroke={pickColor(name, i)}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            ),
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
