"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { formatCr } from "@/lib/data";

// ── Add future dashboards here ─────────────────────────────────────────────────
const NAV_LINKS = [
  { label: "Credit",   href: "/",         icon: "📊" },
  { label: "Payments", href: "/payments",  icon: "💳" },
];

interface HeaderProps {
  totalBankCredit: number | null;
  latestDate:      string;
  darkMode:        boolean;
  onToggleDark:    () => void;
}

export default function Header({
  totalBankCredit,
  latestDate,
  darkMode,
  onToggleDark,
}: HeaderProps) {
  const pathname  = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background:   "var(--bg-card)",
        borderBottom: "1px solid var(--border-card)",
        boxShadow:    "0 1px 4px var(--shadow)",
      }}
    >
      {/* ── Main bar ────────────────────────────────────────────────────────── */}
      <div className="px-4 py-3 flex items-center justify-between gap-3">

        {/* Brand */}
        <Link href="/" style={{ textDecoration: "none", flexShrink: 0 }}>
          <div className="flex items-center gap-2">
            <span className="text-xl">🔍</span>
            <span
              className="font-bold text-sm tracking-wide hidden xs:inline"
              style={{ color: "var(--font)" }}
            >
              India Credit Lens
            </span>
          </div>
        </Link>

        {/* Desktop nav — hidden on mobile */}
        <nav className="hidden sm:flex items-center gap-1 flex-1 justify-center">
          {NAV_LINKS.map(({ label, href, icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-full transition-colors"
                style={{
                  color:          isActive ? "#4e8ef7" : "var(--font-muted)",
                  background:     isActive ? "#4e8ef715" : "transparent",
                  textDecoration: "none",
                }}
              >
                <span>{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Desktop: centre metric */}
        {totalBankCredit && (
          <div className="hidden sm:flex flex-col items-end flex-shrink-0">
            <span
              className="text-[10px] font-medium uppercase tracking-wider"
              style={{ color: "var(--font-muted)" }}
            >
              Total Bank Credit
            </span>
            <span className="text-sm font-bold" style={{ color: "var(--font)" }}>
              {formatCr(totalBankCredit, 1)}
            </span>
            <span className="text-[10px]" style={{ color: "var(--font-muted)" }}>
              as of {latestDate}
            </span>
          </div>
        )}

        {/* Right controls */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Dark mode toggle */}
          <button
            onClick={onToggleDark}
            className="w-8 h-8 flex items-center justify-center rounded-full text-base transition-colors"
            style={{
              background: "var(--bg-page)",
              border:     "1px solid var(--border-card)",
            }}
            aria-label="Toggle dark mode"
          >
            {darkMode ? "☀️" : "🌙"}
          </button>

          {/* Hamburger — mobile only */}
          <button
            onClick={() => setOpen((o) => !o)}
            className="sm:hidden w-8 h-8 flex items-center justify-center rounded-full transition-colors"
            style={{
              background: open ? "#4e8ef715" : "var(--bg-page)",
              border:     `1px solid ${open ? "#4e8ef7" : "var(--border-card)"}`,
              color:      open ? "#4e8ef7" : "var(--font)",
              fontSize:   16,
              fontWeight: 600,
            }}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
          >
            {open ? "✕" : "☰"}
          </button>
        </div>
      </div>

      {/* ── Mobile dropdown ──────────────────────────────────────────────────── */}
      {open && (
        <nav
          className="sm:hidden"
          style={{ borderTop: "1px solid var(--border-card)" }}
        >
          {NAV_LINKS.map(({ label, href, icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-5 py-4 text-sm font-medium transition-colors"
                style={{
                  color:          isActive ? "#4e8ef7" : "var(--font)",
                  background:     isActive ? "#4e8ef710" : "transparent",
                  borderBottom:   "1px solid var(--border-card)",
                  textDecoration: "none",
                }}
              >
                <span className="text-base">{icon}</span>
                {label}
                {isActive && (
                  <span
                    className="ml-auto text-xs px-2 py-0.5 rounded-full"
                    style={{ background: "#4e8ef720", color: "#4e8ef7" }}
                  >
                    Current
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
