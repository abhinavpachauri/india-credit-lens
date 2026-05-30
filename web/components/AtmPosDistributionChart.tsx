"use client";

import { useMemo } from "react";
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
  chartMode:    "absolute" | "pct";
}

export default function AtmPosDistributionChart({
  absoluteData,
  seriesNames,
  unit,
  hiddenSeries,
  chartMode,
}: AtmPosDistributionChartProps) {
  const visibleNames = useMemo(
    () => seriesNames.filter((n) => !hiddenSeries.has(n)),
    [seriesNames, hiddenSeries],
  );

  // When "Total" is a series, use it as the 100% denominator so individual
  // banks/types show their true share. Summing all series would double-count
  // (Total already contains all sub-series).
  const getPctDenominator = (point: ChartPoint): number => {
    if (seriesNames.includes("Total")) return Number(point["Total"]) || 0;
    return seriesNames.reduce((s, k) => s + (Number(point[k]) || 0), 0);
  };

  const chartData = useMemo(() => {
    if (chartMode === "absolute") return absoluteData;
    return absoluteData.map((point) => {
      const denom = getPctDenominator(point);
      const pct: ChartPoint = { date: point.date, _ts: point._ts };
      seriesNames.forEach((k) => {
        pct[k] = denom > 0 ? +((Number(point[k]) || 0) / denom * 100).toFixed(1) : 0;
      });
      return pct;
    });
  }, [absoluteData, seriesNames, chartMode]);

  const formatY = (v: number) =>
    chartMode === "absolute" ? formatAtmValue(v, unit) : `${v}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] =>
    chartMode === "absolute"
      ? [formatAtmValue(Number(value) || 0, unit), String(name ?? "")]
      : [`${Number(value || 0).toFixed(1)}%`, String(name ?? "")];

  const latestRow   = absoluteData[absoluteData.length - 1];
  const latestTotal = latestRow ? getPctDenominator(latestRow) : 0;

  return (
    <div>
      <div style={{ minWidth: 0, overflow: "hidden" }}>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: "var(--font-muted)" }}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatY}
              domain={chartMode === "pct" ? [0, 100] : undefined}
              tick={{ fontSize: 12, fill: "var(--font-muted)" }}
              tickLine={false}
              axisLine={false}
              width={72}
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
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-card)" }}>
                <th
                  className="text-left py-1.5 px-2 font-semibold uppercase tracking-wide"
                  style={{ color: "var(--font-muted)" }}
                >
                  Segment
                </th>
                <th
                  className="text-right py-1.5 px-2 font-semibold uppercase tracking-wide"
                  style={{ color: "var(--font-muted)" }}
                >
                  Latest
                </th>
                <th
                  className="text-right py-1.5 px-2 font-semibold uppercase tracking-wide"
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
                    <td className="py-1.5 px-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="inline-block w-2.5 h-2.5 rounded-sm flex-shrink-0"
                          style={{ background: pickColor(name, seriesNames.indexOf(name) === -1 ? i : seriesNames.indexOf(name)) }}
                        />
                        {name}
                      </div>
                    </td>
                    <td className="py-1.5 px-2 text-right font-mono">{formatAtmValue(val, unit)}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{share}%</td>
                  </tr>
                );
              })}
              <tr className="font-semibold" style={{ borderTop: "2px solid var(--border-card)" }}>
                <td className="py-1.5 px-2">Total</td>
                <td className="py-1.5 px-2 text-right font-mono">{formatAtmValue(latestTotal, unit)}</td>
                <td className="py-1.5 px-2 text-right">100%</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
