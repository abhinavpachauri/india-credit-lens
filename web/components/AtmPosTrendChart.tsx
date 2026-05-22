"use client";

import { useState } from "react";
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
}

export default function AtmPosTrendChart({
  absoluteData,
  momData,
  seriesNames,
  unit,
  hiddenSeries,
  chartId,
}: AtmPosTrendChartProps) {
  const [mode, setMode] = useState<"absolute" | "mom">("absolute");

  const chartData = mode === "absolute" ? absoluteData : momData;

  const formatY = (v: number) =>
    mode === "absolute" ? formatAtmValue(v, unit) : `${v.toFixed(1)}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div
        style={{
          background:   "var(--bg-card)",
          border:       "1px solid var(--border-card)",
          borderRadius: 8,
          fontSize:     13,
          color:        "var(--font)",
          padding:      "10px 14px",
        }}
      >
        <p style={{ marginBottom: 4, fontWeight: 600 }}>{label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} style={{ color: p.color, margin: "2px 0" }}>
            {p.name}:{" "}
            {mode === "absolute"
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
    <div>
      {/* Toggle */}
      <div className="flex items-center gap-4 mb-3 text-sm">
        {(["absolute", "mom"] as const).map((m) => (
          <label
            key={m}
            className="flex items-center gap-1.5 cursor-pointer"
            style={{ color: "var(--font)" }}
          >
            <input
              type="radio"
              name={`trend-mode-${chartId}`}
              value={m}
              checked={mode === m}
              onChange={() => setMode(m)}
              className="accent-blue-500"
            />
            {m === "absolute" ? "Absolute" : "MoM %"}
          </label>
        ))}
      </div>

      <div style={{ minWidth: 0, overflow: "hidden" }}>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
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
              width={80}
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
    </div>
  );
}
