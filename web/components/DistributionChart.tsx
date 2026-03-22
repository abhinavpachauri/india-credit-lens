"use client";

import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Label,
} from "recharts";
import { CreditRow, buildSeries, formatCr, uniqueDates } from "@/lib/data";
import { pickColor } from "@/lib/theme";
import ChartLegend from "./ChartLegend";
import type { ChartAnnotation } from "@/lib/insights";

interface DistributionChartProps {
  rows: CreditRow[];
  codes: string[];
  labels: Record<string, string>;
  pctLabel?: string;
  dataOpts?: { psl?: boolean; stmt?: string };
  distAnnotations?: ChartAnnotation[];
}

export default function DistributionChart({
  rows, codes, labels, pctLabel = "% Share", dataOpts = {}, distAnnotations = []
}: DistributionChartProps) {
  const [mode, setMode] = useState<"absolute" | "pct">("absolute");
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const seriesKeys = codes.map((c) => labels[c] ?? c);

  const rawData = useMemo(() =>
    buildSeries(rows, codes, labels, dataOpts),
    [rows, codes, labels, dataOpts]
  );

  const chartData = useMemo(() => {
    if (mode === "absolute") return rawData;
    return rawData.map((point) => {
      const total = seriesKeys.reduce((s, k) => s + (Number(point[k]) || 0), 0);
      const pct: typeof point = { date: point.date };
      seriesKeys.forEach((k) => {
        pct[k] = total > 0 ? +((Number(point[k]) || 0) / total * 100).toFixed(1) : 0;
      });
      return pct;
    });
  }, [rawData, seriesKeys, mode]);

  // Latest date breakdown table
  const latestDates = uniqueDates(rows);
  const latestDate  = latestDates[latestDates.length - 1];

  const latestRow = rawData[rawData.length - 1];
  const latestTotal = seriesKeys.reduce((s, k) => s + (Number(latestRow?.[k]) || 0), 0);

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
    mode === "absolute" ? formatCr(v, 1) : `${v}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] =>
    mode === "absolute"
      ? [formatCr(Number(value) || 0), String(name ?? "")]
      : [`${Number(value || 0).toFixed(1)}%`, String(name ?? "")];

  // Show pct annotations only in pct mode, absolute annotations only in absolute mode
  const activeAnnotations = distAnnotations.filter((a) =>
    a.type === "hLine" && (
      (mode === "pct"      && (a.value ?? 0) <= 100) ||
      (mode === "absolute" && (a.value ?? 0) > 100)
    )
  );

  return (
    <div>
      {/* Controls */}
      <div className="flex gap-4 mb-3 text-xs">
        {(["absolute", "pct"] as const).map((m) => (
          <label key={m} className="flex items-center gap-1 cursor-pointer" style={{ color: "var(--font)" }}>
            <input
              type="radio"
              name={`dist-${codes[0]}`}
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
              background: "var(--bg-card)",
              border: "1px solid var(--border-card)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--font)",
            }}
          />

          {/* Reference line annotations */}
          {activeAnnotations.map((ann, i) => (
            <ReferenceLine
              key={i}
              y={ann.value}
              stroke={ann.color}
              strokeDasharray="5 4"
              strokeWidth={1.5}
            >
              <Label
                value={ann.label}
                position={ann.position ?? "right"}
                style={{ fontSize: 10, fill: ann.color, fontWeight: 500 }}
              />
            </ReferenceLine>
          ))}

          {seriesKeys.map((key, i) =>
            hidden.has(key) ? null : (
              <Bar key={key} dataKey={key} stackId="a" fill={pickColor(key, i)} />
            )
          )}
        </BarChart>
      </ResponsiveContainer>

      {/* Summary table at latest date */}
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
              {seriesKeys.map((key, i) => {
                const val = Number(latestRow[key]) || 0;
                const share = latestTotal > 0 ? (val / latestTotal * 100).toFixed(1) : "—";
                return (
                  <tr key={key} style={{ borderBottom: "1px solid var(--border-card)" }}>
                    <td className="py-1.5 px-2 flex items-center gap-1.5">
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-sm flex-shrink-0"
                        style={{ background: pickColor(key, i) }}
                      />
                      {key}
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
