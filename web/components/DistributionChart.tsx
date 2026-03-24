"use client";

import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { formatCr } from "@/lib/data";
import { pickColor } from "@/lib/theme";
import ChartLegend from "./ChartLegend";
import type { ChartPoint } from "@/lib/types";

interface DistributionChartProps {
  absoluteData: ChartPoint[];
  seriesNames:  string[];
  pctLabel?:    string;
  visibleSeries?: string[];   // optional subset — used by IndustryFilter
}

export default function DistributionChart({
  absoluteData, seriesNames, pctLabel = "% Share", visibleSeries,
}: DistributionChartProps) {
  const [mode, setMode]     = useState<"absolute" | "pct">("absolute");
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  // Which series to actually render
  const activeNames = useMemo(
    () => (visibleSeries ? seriesNames.filter((n) => visibleSeries.includes(n)) : seriesNames),
    [seriesNames, visibleSeries]
  );

  const chartData = useMemo(() => {
    if (mode === "absolute") return absoluteData;
    return absoluteData.map((point) => {
      const total = activeNames.reduce((s, k) => s + (Number(point[k]) || 0), 0);
      const pct: ChartPoint = { date: point.date };
      activeNames.forEach((k) => {
        pct[k] = total > 0 ? +((Number(point[k]) || 0) / total * 100).toFixed(1) : 0;
      });
      return pct;
    });
  }, [absoluteData, activeNames, mode]);

  // Summary table — latest data point
  const latestRow   = absoluteData[absoluteData.length - 1];
  const latestTotal = activeNames.reduce((s, k) => s + (Number(latestRow?.[k]) || 0), 0);

  const legendItems = activeNames.map((name, i) => ({
    label:  name,
    color:  pickColor(name, i),
    active: !hidden.has(name),
  }));

  const toggleSeries = (name: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });

  const formatY = (v: number) =>
    mode === "absolute" ? formatCr(v, 1) : `${v}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] =>
    mode === "absolute"
      ? [formatCr(Number(value) || 0), String(name ?? "")]
      : [`${Number(value || 0).toFixed(1)}%`, String(name ?? "")];

  return (
    <div>
      {/* Mode toggle */}
      <div className="flex gap-4 mb-3 text-xs">
        {(["absolute", "pct"] as const).map((m) => (
          <label key={m} className="flex items-center gap-1 cursor-pointer" style={{ color: "var(--font)" }}>
            <input
              type="radio"
              name={`dist-${activeNames[0] ?? "chart"}`}
              value={m}
              checked={mode === m}
              onChange={() => setMode(m)}
              className="accent-blue-500"
            />
            {m === "absolute" ? "₹ Crore" : pctLabel}
          </label>
        ))}
      </div>

      <ChartLegend items={legendItems} onToggle={toggleSeries} />

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
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
              background:   "var(--bg-card)",
              border:       "1px solid var(--border-card)",
              borderRadius: 8,
              fontSize:     12,
              color:        "var(--font)",
            }}
          />
          {activeNames.map((name, i) =>
            hidden.has(name) ? null : (
              <Bar key={name} dataKey={name} stackId="a" fill={pickColor(name, i)} />
            )
          )}
        </BarChart>
      </ResponsiveContainer>

      {/* Summary table */}
      {latestRow && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-card)" }}>
                <th className="text-left py-1.5 px-2 font-medium" style={{ color: "var(--font-muted)" }}>Segment</th>
                <th className="text-right py-1.5 px-2 font-medium" style={{ color: "var(--font-muted)" }}>Outstanding</th>
                <th className="text-right py-1.5 px-2 font-medium" style={{ color: "var(--font-muted)" }}>Share</th>
              </tr>
            </thead>
            <tbody>
              {activeNames.map((name, i) => {
                const val   = Number(latestRow[name]) || 0;
                const share = latestTotal > 0 ? (val / latestTotal * 100).toFixed(1) : "—";
                return (
                  <tr key={name} style={{ borderBottom: "1px solid var(--border-card)" }}>
                    <td className="py-1.5 px-2 flex items-center gap-1.5">
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-sm flex-shrink-0"
                        style={{ background: pickColor(name, i) }}
                      />
                      {name}
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono">{formatCr(val)}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{share}%</td>
                  </tr>
                );
              })}
              <tr className="font-semibold">
                <td className="py-1.5 px-2">Total</td>
                <td className="py-1.5 px-2 text-right font-mono">{formatCr(latestTotal)}</td>
                <td className="py-1.5 px-2 text-right">100%</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
