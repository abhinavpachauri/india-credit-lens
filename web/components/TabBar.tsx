"use client";

export type TabId = "trend" | "distribution";

interface TabBarProps {
  active: TabId;
  onChange: (tab: TabId) => void;
}

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "trend",        label: "Trend",        icon: "📈" },
  { id: "distribution", label: "Distribution",  icon: "📊" },
];

export default function TabBar({ active, onChange }: TabBarProps) {
  return (
    <div
      className="flex gap-1 px-6 pt-4 pb-0"
      style={{ borderBottom: "1px solid var(--border-card)" }}
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className="px-5 py-2 text-sm font-medium rounded-t-lg transition-colors"
          style={{
            background:   active === tab.id ? "var(--bg-card)"  : "transparent",
            color:        active === tab.id ? "#4e8ef7"          : "var(--font-muted)",
            borderBottom: active === tab.id ? "2px solid #4e8ef7" : "2px solid transparent",
          }}
        >
          {tab.icon}  {tab.label}
        </button>
      ))}
    </div>
  );
}
