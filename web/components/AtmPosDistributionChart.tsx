"use client";

import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { pickColor } from "@/lib/theme";
import { formatAtmValue } from "@/lib/atm_pos_data";
import type { ChartPoint } from "@/lib/atm_pos_data";

interface AtmPosDistributionChartProps {
  absoluteData: ChartPoint[];
  seriesNames:  string[];
  unit:         string;
  hiddenSeries: Set<string>;
  chartId:      string;
}

export default function AtmPosDistributionChart({
  absoluteData,
  seriesNames,
  unit,
  hiddenSeries,
  chartId,
}: AtmPosDistributionChartProps) {
  const [mode, setMode] = useState<"absolute" | "pct">("absolute");

  const visibleNames = useMemo(
    () => seriesNames.filter((n) => !hiddenSeries.has(n)),
    [seriesNames, hiddenSeries],
  );

  const chartData = useMemo(() => {
    if (mode === "absolute") return absoluteData;
    return absoluteData.map((point) => {
      const total = seriesNames.reduce((s, k) => s + (Number(point[k]) || 0), 0);
      const pct: ChartPoint = { date: point.date, _ts: point._ts };
      seriesNames.forEach((k) => {
        pct[k] = total > 0 ? +((Number(point[k]) || 0) / total * 100).toFixed(1) : 0;
      });
      return pct;
    });
  }, [absoluteData, seriesNames, mode]);

  const formatY = (v: number) =>
    mode === "absolute" ? formatAtmValue(v, unit) : `${v}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] =>
    mode === "absolute"
      ? [formatAtmValue(Number(value) || 0, unit), String(name ?? "")]
      : [`${Number(value || 0).toFixed(1)}%`, String(name ?? "")];

  // Summary table — latest data point
  const latestRow   = absoluteData[absoluteData.length - 1];
  const latestTotal = seriesNames.reduce((s, k) => s + (Number(latestRow?.[k]) || 0), 0);

  return (
    <div>
      {/* Toggle */}
      <div className="flex items-center gap-4 mb-3 text-sm">
        {(["absolute", "pct"] as const).map((m) => (
          <label
            key={m}
            className="flex items-center gap-1.5 cursor-pointer"
            style={{ color: "var(--font)" }}
          >
            <input
              type="radio"
              name={`dist-mode-${chartId}`}
              value={m}
              checked={mode === m}
              onChange={() => setMode(m)}
              className="accent-blue-500"
            />
            {m === "absolute" ? "Absolute" : "% Share"}
          </label>
        ))}
      </div>

      <div style={{ minWidth: 0, overflow: "hidden" }}>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: "var(--font-muted)" }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatY}
              domain={mode === "pct" ? [0, 100] : undefined}
              tick={{ fontSize: 12, fill: "var(--font-muted)" }}
              tickLine={false}
              axisLine={false}
              width={80}
            />
            <Tooltip
              formatter={tooltipFormatter}
              contentStyle={{
                background:   "var(--bg-card)",
                border:       "1px solid var(--border-card)",
                borderRadius: 8,
                fontSize:     13,
                color:        "var(--font)",
              }}
            />
            {seriesNames.map((name, i) =>
              hiddenSeries.has(name) ? null : (
                <Bar
                  key={name}
                  dataKey={name}
                  stackId="a"
                  fill={pickColor(name, i)}
                  isAnimationActive={false}
                />
              ),
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Summary table */}
      {latestRow && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-card)" }}>
                <th
                  className="text-left py-2 px-2 text-xs font-semibold uppercase tracking-wide"
                  style={{ color: "var(--font-muted)" }}
                >
                  Segment
                </th>
                <th
                  className="text-right py-2 px-2 text-xs font-semibold uppercase tracking-wide"
                  style={{ color: "var(--font-muted)" }}
                >
                  Latest Value
                </th>
                <th
                  className="text-right py-2 px-2 text-xs font-semibold uppercase tracking-wide"
                  style={{ color: "var(--font-muted)" }}
                >
                  Share
                </th>
              </tr>
            </thead>
            <tbody>
              {visibleNames.map((name, i) => {
                const val   = Number(latestRow[name]) || 0;
                const share = latestTotal > 0 ? (val / latestTotal * 100).toFixed(1) : "—";
                return (
                  <tr key={name} style={{ borderBottom: "1px solid var(--border-card)" }}>
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
                          style={{ background: pickColor(name, seriesNames.indexOf(name) === -1 ? i : seriesNames.indexOf(name)) }}
                        />
                        {name}
                      </div>
                    </td>
                    <td className="py-2 px-2 text-right font-mono">{formatAtmValue(val, unit)}</td>
                    <td className="py-2 px-2 text-right font-mono">{share}%</td>
                  </tr>
                );
              })}
              <tr className="font-semibold" style={{ borderTop: "2px solid var(--border-card)" }}>
                <td className="py-2 px-2">Total</td>
                <td className="py-2 px-2 text-right font-mono">{formatAtmValue(latestTotal, unit)}</td>
                <td className="py-2 px-2 text-right">100%</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
