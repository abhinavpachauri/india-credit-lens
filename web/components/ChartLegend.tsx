"use client";

interface LegendItem {
  label: string;
  color: string;
  active: boolean;
}

interface ChartLegendProps {
  items:      LegendItem[];
  onToggle?:  (label: string) => void;  // undefined = locked (intelligence mode)
}

export default function ChartLegend({ items, onToggle }: ChartLegendProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {items.map((item) =>
        onToggle ? (
          <button
            key={item.label}
            onClick={() => onToggle(item.label)}
            className="flex items-center gap-2 text-sm rounded-full px-3 py-1 transition-all"
            style={item.active ? {
              background: `${item.color}18`,
              border:     `1.5px solid ${item.color}`,
              color:      "var(--font)",
              cursor:     "pointer",
            } : {
              background: "transparent",
              border:     "1.5px solid var(--border-card)",
              color:      "var(--font-muted)",
              opacity:    0.5,
              cursor:     "pointer",
            }}
          >
            <span
              className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ background: item.active ? item.color : "var(--font-muted)" }}
            />
            {item.label}
          </button>
        ) : (
          <div
            key={item.label}
            className="flex items-center gap-2 text-sm px-1"
            style={{
              opacity: item.active ? 1 : 0.2,
              color:   "var(--font-muted)",
            }}
          >
            <span
              className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ background: item.color }}
            />
            {item.label}
          </div>
        )
      )}
    </div>
  );
}
