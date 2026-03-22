"use client";

import type { SectionInsight } from "@/lib/insights";
import { InsightStrip } from "./InsightStrip";

interface SectionCardProps {
  title: string;
  icon: string;
  accentColor: string;
  children: React.ReactNode;
  insights?: SectionInsight;
}

export default function SectionCard({ title, icon, accentColor, children, insights }: SectionCardProps) {
  return (
    <div
      className="rounded-xl mb-6 overflow-hidden"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-card)",
        boxShadow: "0 2px 8px var(--shadow)",
        borderLeft: `4px solid ${accentColor}`,
      }}
    >
      {/* Card header */}
      <div
        className="px-5 py-3 flex items-center gap-2"
        style={{ background: `${accentColor}15` }}
      >
        <span className="text-lg">{icon}</span>
        <h2 className="text-base font-semibold" style={{ color: accentColor }}>
          {title}
        </h2>
      </div>

      {/* Card body */}
      <div className="px-5 py-4">{children}</div>

      {/* Insight / Gap / Opportunity strip */}
      {insights && <InsightStrip data={insights} />}
    </div>
  );
}
