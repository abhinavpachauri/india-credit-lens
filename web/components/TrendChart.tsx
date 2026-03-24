"use client";

import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { formatCr, formatGrowth } from "@/lib/data";
import { pickColor } from "@/lib/theme";
import ChartLegend from "./ChartLegend";
import type { ChartPoint, AnnotationEffect } from "@/lib/types";

interface TrendChartProps {
  absoluteData:    ChartPoint[];
  growthData:      ChartPoint[];
  seriesNames:     string[];
  pctLabel?:       string;
  visibleSeries?:  string[];          // optional subset — used by IndustryFilter
  highlightConfig?: AnnotationEffect | null;  // from active annotation
}

/** Compute per-series visual style based on active annotation. */
function seriesStyle(name: string, config: AnnotationEffect | null | undefined) {
  if (!config) return { opacity: 1, strokeWidth: 2, strokeDasharray: undefined };
  const highlighted = config.highlight?.includes(name) ?? false;
  const dimmed      = config.dim?.includes(name)       ?? false;
  const dashed      = config.dash?.includes(name)      ?? false;
  // Auto-fade anything not explicitly highlighted when a highlight set exists
  const autoFade    = (config.highlight?.length ?? 0) > 0 && !highlighted && !dimmed;
  return {
    opacity:          highlighted ? 1 : (dimmed || autoFade) ? 0.15 : 1,
    strokeWidth:      highlighted ? 3 : 2,
    strokeDasharray:  dashed ? "5 5" : undefined,
  };
}

type ViewMode = "absolute" | "yoy" | "fy";

export default function TrendChart({
  absoluteData, growthData, seriesNames,
  pctLabel = "% of Total", visibleSeries, highlightConfig,
}: TrendChartProps) {
  const [mode, setMode]     = useState<ViewMode>("absolute");
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  // Which series to actually render
  const activeNames = useMemo(
    () => (visibleSeries ? seriesNames.filter((n) => visibleSeries.includes(n)) : seriesNames),
    [seriesNames, visibleSeries]
  );

  // Switch between absolute and growth data based on mode
  const seriesData = useMemo(
    () => (mode === "absolute" ? absoluteData : growthData),
    [mode, absoluteData, growthData]
  );

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
    mode === "absolute" ? formatCr(v, 1) : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] =>
    mode === "absolute"
      ? [formatCr(Number(value) || 0), String(name ?? "")]
      : [formatGrowth(Number(value) || 0), String(name ?? "")];

  return (
    <div>
      {/* Mode toggle */}
      <div className="flex flex-wrap gap-4 mb-3 text-xs">
        <div className="flex items-center gap-2">
          {(["absolute", "yoy", "fy"] as ViewMode[]).map((m) => (
            <label key={m} className="flex items-center gap-1 cursor-pointer" style={{ color: "var(--font)" }}>
              <input
                type="radio"
                name={`mode-${activeNames[0] ?? "chart"}`}
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
              background:   "var(--bg-card)",
              border:       "1px solid var(--border-card)",
              borderRadius: 8,
              fontSize:     12,
              color:        "var(--font)",
            }}
          />
          {activeNames.map((name, i) => {
            if (hidden.has(name)) return null;
            const style = seriesStyle(name, highlightConfig);
            return (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={pickColor(name, i)}
                strokeWidth={style.strokeWidth}
                strokeDasharray={style.strokeDasharray}
                strokeOpacity={style.opacity}
                dot={{ r: 4, strokeWidth: 1, opacity: style.opacity }}
                activeDot={{ r: 6 }}
                connectNulls
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
