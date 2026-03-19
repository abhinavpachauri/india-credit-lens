"use client";

import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { CreditRow, buildSeries, buildGrowthSeries, formatCr, formatGrowth } from "@/lib/data";
import { pickColor } from "@/lib/theme";
import ChartLegend from "./ChartLegend";

interface TrendChartProps {
  rows: CreditRow[];
  codes: string[];
  labels: Record<string, string>;
  pctLabel?: string;
  dataOpts?: { psl?: boolean; stmt?: string };
}

type ViewMode = "absolute" | "yoy" | "fy";

export default function TrendChart({
  rows, codes, labels, pctLabel = "% of Total", dataOpts = {}
}: TrendChartProps) {
  const [mode, setMode] = useState<ViewMode>("absolute");
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const seriesData = useMemo(() => {
    if (mode === "absolute") return buildSeries(rows, codes, labels, dataOpts);
    return buildGrowthSeries(rows, codes, labels, mode === "yoy" ? "yoy" : "fy", dataOpts);
  }, [rows, codes, labels, mode, dataOpts]);

  const seriesKeys = codes.map((c) => labels[c] ?? c);

  const legendItems = seriesKeys.map((label, i) => ({
    label,
    color: pickColor(label, i),
    active: !hidden.has(label),
  }));

  const toggleSeries = (label: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(label) ? next.delete(label) : next.add(label);
      return next;
    });
  };

  const formatY = (v: number) =>
    mode === "absolute" ? formatCr(v, 1) : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] =>
    mode === "absolute"
      ? [formatCr(Number(value) || 0), String(name ?? "")]
      : [formatGrowth(Number(value) || 0), String(name ?? "")];

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-3 text-xs">
        <div className="flex items-center gap-2">
          {(["absolute", "yoy", "fy"] as ViewMode[]).map((m) => (
            <label key={m} className="flex items-center gap-1 cursor-pointer" style={{ color: "var(--font)" }}>
              <input
                type="radio"
                name={`mode-${codes[0]}`}
                value={m}
                checked={mode === m}
                onChange={() => setMode(m)}
                className="accent-blue-500"
              />
              {m === "absolute" ? "Absolute" : m === "yoy" ? "YoY Growth" : "FY Growth"}
            </label>
          ))}
        </div>
      </div>

      <ChartLegend items={legendItems} onToggle={toggleSeries} />

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={seriesData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "var(--font-muted)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatY}
            tick={{ fontSize: 10, fill: "var(--font-muted)" }}
            tickLine={false}
            axisLine={false}
            width={90}
          />
          <Tooltip
            formatter={tooltipFormatter}
            contentStyle={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-card)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--font)",
            }}
          />
          {seriesKeys.map((key, i) => (
            hidden.has(key) ? null : (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={pickColor(key, i)}
                strokeWidth={2}
                dot={{ r: 4, strokeWidth: 1 }}
                activeDot={{ r: 6 }}
                connectNulls
              />
            )
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
