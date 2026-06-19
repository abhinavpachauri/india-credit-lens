"use client";

import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { formatCr } from "@/lib/data";
import { pickColor } from "@/lib/theme";
import ChartLegend from "./ChartLegend";
import type { ChartPoint, AnnotationEffect } from "@/lib/types";

interface DistributionChartProps {
  absoluteData:     ChartPoint[];
  seriesNames:      string[];
  pctLabel?:        string;
  mode:             "absolute" | "pct"; // owned by parent controls card
  visibleSeries?:   string[];
  highlightConfig?: AnnotationEffect | null;
  preferredMode?:   "absolute" | "yoy" | "fy" | "share" | null; // annotation overrides parent mode
}

function barOpacity(name: string, config: AnnotationEffect | null | undefined): number {
  if (!config) return 1;
  if (config.highlight?.includes(name)) return 1;
  if (config.dim?.includes(name))       return 0.15;
  if ((config.highlight?.length ?? 0) > 0) return 0.15; // auto-fade
  return 1;
}

export default function DistributionChart({
  absoluteData, seriesNames, pctLabel = "% Share", mode, visibleSeries, highlightConfig, preferredMode,
}: DistributionChartProps) {
  // yoy/fy annotations → show % share (relative view); absolute annotation → show ₹ Crore
  // otherwise use the parent-controlled mode
  const effectiveMode: "absolute" | "pct" =
    preferredMode === "yoy" || preferredMode === "fy" || preferredMode === "share" ? "pct"
    : preferredMode === "absolute" ? "absolute"
    : mode;
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  // Which series to actually render (base list from visibleSeries filter)
  const baseNames = useMemo(
    () => (visibleSeries ? seriesNames.filter((n) => visibleSeries.includes(n)) : seriesNames),
    [seriesNames, visibleSeries]
  );

  // When an annotation highlights specific series, focus only on those
  const highlighted = highlightConfig?.highlight ?? [];
  const activeNames = useMemo(
    () => highlighted.length > 0 ? baseNames.filter((n) => highlighted.includes(n)) : baseNames,
    [baseNames, highlighted]
  );

  // When annotation highlights specific series, use effectiveMode (parent-controlled, may be
  // overridden by preferredMode); otherwise same
  const chartMode: "absolute" | "pct" = effectiveMode;

  const chartData = useMemo(() => {
    if (chartMode === "absolute") return absoluteData;
    return absoluteData.map((point) => {
      // Use baseNames (full series list) as denominator so % = share of full section total
      const total = baseNames.reduce((s, k) => s + (Number(point[k]) || 0), 0);
      const pct: ChartPoint = { date: point.date };
      activeNames.forEach((k) => {
        pct[k] = total > 0 ? +((Number(point[k]) || 0) / total * 100).toFixed(1) : 0;
      });
      return pct;
    });
  }, [absoluteData, activeNames, baseNames, chartMode]);

  // Summary table — latest data point
  // latestTotal uses baseNames so "Share" = % of full section, not % of highlighted subset
  const latestRow   = absoluteData[absoluteData.length - 1];
  const latestTotal = baseNames.reduce((s, k) => s + (Number(latestRow?.[k]) || 0), 0);

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
    chartMode === "absolute" ? formatCr(v, 1) : `${v}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] =>
    chartMode === "absolute"
      ? [formatCr(Number(value) || 0), String(name ?? "")]
      : [`${Number(value || 0).toFixed(1)}%`, String(name ?? "")];

  return (
    <div>
      <ChartLegend items={legendItems} onToggle={toggleSeries} />

      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
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
            width={96}
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
          {activeNames.map((name, i) =>
            hidden.has(name) ? null : (
              <Bar
                key={name}
                dataKey={name}
                stackId="a"
                fill={pickColor(name, i)}
                opacity={highlighted.length > 0 ? 1 : barOpacity(name, highlightConfig)}
              />
            )
          )}
        </BarChart>
      </ResponsiveContainer>

      {/* Summary table */}
      {latestRow && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-card)" }}>
                <th className="text-left py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--font-muted)" }}>Segment</th>
                <th className="text-right py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--font-muted)" }}>Outstanding</th>
                <th className="text-right py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--font-muted)" }}>Share</th>
              </tr>
            </thead>
            <tbody>
              {activeNames.map((name, i) => {
                const val   = Number(latestRow[name]) || 0;
                const share = latestTotal > 0 ? (val / latestTotal * 100).toFixed(1) : "—";
                return (
                  <tr key={name} style={{ borderBottom: "1px solid var(--border-card)" }}>
                    <td className="py-2 px-2 flex items-center gap-2">
                      <span
                        className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
                        style={{ background: pickColor(name, i) }}
                      />
                      {name}
                    </td>
                    <td className="py-2 px-2 text-right font-mono">{formatCr(val)}</td>
                    <td className="py-2 px-2 text-right font-mono">{share}%</td>
                  </tr>
                );
              })}
              <tr className="font-semibold" style={{ borderTop: "2px solid var(--border-card)" }}>
                <td className="py-2 px-2">Total</td>
                <td className="py-2 px-2 text-right font-mono">{formatCr(latestTotal)}</td>
                <td className="py-2 px-2 text-right">100%</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
