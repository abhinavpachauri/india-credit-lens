"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { formatCr } from "@/lib/data";

interface HeaderProps {
  totalBankCredit: number | null;
  latestDate: string;
  darkMode: boolean;
  onToggleDark: () => void;
}

export default function Header({ totalBankCredit, latestDate, darkMode, onToggleDark }: HeaderProps) {
  const pathname = usePathname();

  const navLinks = [
    { label: "Credit Dashboard", href: "/" },
    { label: "Payments",         href: "/payments" },
  ];

  return (
    <header
      className="sticky top-0 z-50 px-6 py-3 flex items-center justify-between"
      style={{
        background: "var(--bg-card)",
        borderBottom: "1px solid var(--border-card)",
        boxShadow: "0 1px 4px var(--shadow)",
      }}
    >
      {/* Brand */}
      <div className="flex items-center gap-3">
        <span className="text-xl">🔍</span>
        <div>
          <span className="font-bold text-sm tracking-wide" style={{ color: "var(--font)" }}>
            India Credit Lens
          </span>
          <span
            className="ml-2 text-xs px-2 py-0.5 rounded-full font-medium"
            style={{ background: "#4e8ef720", color: "#4e8ef7" }}
          >
            RBI Bank Credit
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="hidden sm:flex items-center gap-1">
        {navLinks.map(({ label, href }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className="text-sm font-medium px-3 py-1 transition-colors"
              style={{
                color:        isActive ? "#4e8ef7" : "var(--font-muted)",
                borderBottom: isActive ? "2px solid #4e8ef7" : "2px solid transparent",
                textDecoration: "none",
              }}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Centre metric */}
      {totalBankCredit && (
        <div className="hidden sm:flex flex-col items-center">
          <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--font-muted)" }}>
            Total Bank Credit
          </span>
          <span className="text-base font-bold" style={{ color: "var(--font)" }}>
            {formatCr(totalBankCredit, 1)}
          </span>
          <span className="text-[10px]" style={{ color: "var(--font-muted)" }}>
            as of {latestDate}
          </span>
        </div>
      )}

      {/* Dark mode toggle */}
      <button
        onClick={onToggleDark}
        className="w-8 h-8 flex items-center justify-center rounded-full text-base transition-colors"
        style={{
          background: "var(--bg-page)",
          border: "1px solid var(--border-card)",
        }}
        aria-label="Toggle dark mode"
      >
        {darkMode ? "☀️" : "🌙"}
      </button>
    </header>
  );
}
