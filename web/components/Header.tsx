"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth, SignInButton, UserButton } from "@clerk/nextjs";
import { formatCr } from "@/lib/data";

// ── Add future dashboards here ─────────────────────────────────────────────────
const NAV_LINKS = [
  { label: "Credit",        href: "/",             icon: "📊" },
  { label: "Payments",      href: "/payments",      icon: "💳" },
  { label: "Opportunities", href: "/opportunities", icon: "🔒" },
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
  const { isSignedIn } = useAuth();

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
            <span className="font-bold text-sm tracking-wide" style={{ color: "var(--font)" }}>
              India Credit Lens
            </span>
          </div>
        </Link>

        {/* Desktop nav — centred, hidden on mobile */}
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

        {/* Right side: credit metric + auth + dark mode */}
        <div className="hidden sm:flex items-center gap-3 flex-shrink-0">
          {/* Bank credit metric — always reserves space so nav stays centred */}
          <div className="flex flex-col items-end" style={{ minWidth: 110 }}>
            {totalBankCredit ? (
              <>
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
              </>
            ) : null}
          </div>

          {/* Auth — UserButton (signed in) or Sign in link (signed out) */}
          {isSignedIn ? (
            <UserButton />
          ) : (
            <SignInButton mode="modal">
              <button
                className="text-sm font-medium px-3 py-1.5 rounded-full transition-colors"
                style={{
                  color:      "#16A34A",
                  background: "#16A34A10",
                  border:     "1px solid #16A34A40",
                  cursor:     "pointer",
                }}
              >
                Sign in
              </button>
            </SignInButton>
          )}
        </div>

        {/* Dark mode toggle */}
        <button
          onClick={onToggleDark}
          className="w-8 h-8 flex items-center justify-center rounded-full text-base transition-colors flex-shrink-0"
          style={{
            background: "var(--bg-page)",
            border:     "1px solid var(--border-card)",
          }}
          aria-label="Toggle dark mode"
        >
          {darkMode ? "☀️" : "🌙"}
        </button>
      </div>

      {/* ── Mobile nav strip ─────────────────────────────────────────────────── */}
      <nav
        className="sm:hidden flex"
        style={{ borderTop: "1px solid var(--border-card)" }}
      >
        {NAV_LINKS.map(({ label, href, icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className="flex-1 flex items-center justify-center gap-1 py-2.5 text-xs font-medium transition-colors"
              style={{
                color:          isActive ? "#4e8ef7" : "var(--font-muted)",
                background:     isActive ? "#4e8ef710" : "transparent",
                borderBottom:   isActive ? "2px solid #4e8ef7" : "2px solid transparent",
                textDecoration: "none",
              }}
            >
              <span>{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
