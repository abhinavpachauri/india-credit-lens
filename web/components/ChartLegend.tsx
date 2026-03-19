"use client";

interface LegendItem {
  label: string;
  color: string;
  active: boolean;
}

interface ChartLegendProps {
  items: LegendItem[];
  onToggle: (label: string) => void;
}

export default function ChartLegend({ items, onToggle }: ChartLegendProps) {
  return (
    <div className="flex flex-wrap gap-3 mb-3">
      {items.map((item) => (
        <button
          key={item.label}
          onClick={() => onToggle(item.label)}
          className="flex items-center gap-1.5 text-xs rounded px-2 py-1 transition-opacity"
          style={{
            opacity: item.active ? 1 : 0.35,
            background: "var(--bg-card)",
            border: "1px solid var(--border-card)",
            color: "var(--font)",
          }}
        >
          <span
            className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
            style={{ background: item.color }}
          />
          {item.label}
        </button>
      ))}
    </div>
  );
}
