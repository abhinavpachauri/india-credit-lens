"use client";

interface SectionCardProps {
  title?: string;
  icon?: string;
  accentColor: string;
  bare?: boolean;          // true → skip title header; use when heading is rendered above
  children: React.ReactNode;
}

export default function SectionCard({ title, icon, accentColor, bare, children }: SectionCardProps) {
  return (
    <div
      className="rounded-xl mb-6 overflow-hidden"
      style={{
        // All-longhand borders: mixing `border` shorthand with a `borderLeft` override warns and
        // can bug when the accent changes on rerender (read-mode re-tints this card per selection).
        background: "var(--bg-card)",
        borderStyle: "solid",
        borderTopWidth: 1, borderRightWidth: 1, borderBottomWidth: 1, borderLeftWidth: 4,
        borderTopColor: "var(--border-card)", borderRightColor: "var(--border-card)",
        borderBottomColor: "var(--border-card)", borderLeftColor: accentColor,
        boxShadow: "0 2px 8px var(--shadow)",
      }}
    >
      {/* Card header — omitted when bare=true (heading rendered above) */}
      {!bare && title && (
        <div
          className="px-5 py-3 flex items-center gap-2"
          style={{ background: `${accentColor}15` }}
        >
          {icon && <span className="text-lg">{icon}</span>}
          <h2 className="text-base font-semibold" style={{ color: accentColor }}>
            {title}
          </h2>
        </div>
      )}

      {/* Card body */}
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}
