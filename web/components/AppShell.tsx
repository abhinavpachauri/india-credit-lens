"use client";

/**
 * AppShell — single shared shell rendered once for every page via layout.tsx.
 *
 * Owns:
 *   - dark mode state (persisted in localStorage)
 *   - the Header component (rendered once, not duplicated per-page)
 *   - the outermost data-dark / bg-page div
 *
 * Exposes useAppShell() so pages can push page-specific header data
 * (e.g. SIBC's Total Bank Credit metric).
 */

import { useState, useEffect, useCallback, createContext, useContext } from "react";
import Header from "@/components/Header";

// ── Context ────────────────────────────────────────────────────────────────────

interface AppShellContextValue {
  dark: boolean;
  setHeaderMetric: (totalBankCredit: number | null, latestDate: string) => void;
}

const AppShellContext = createContext<AppShellContextValue>({
  dark: false,
  setHeaderMetric: () => {},
});

export function useAppShell() {
  return useContext(AppShellContext);
}

// ── Shell ──────────────────────────────────────────────────────────────────────

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [dark,            setDark]            = useState(false);
  const [totalBankCredit, setTotalBankCredit] = useState<number | null>(null);
  const [latestDate,      setLatestDate]      = useState("Mar 2026");

  // Restore persisted dark mode preference
  useEffect(() => {
    if (localStorage.getItem("icl-dark") === "true") setDark(true);
  }, []);

  const toggleDark = () =>
    setDark((d) => {
      localStorage.setItem("icl-dark", String(!d));
      return !d;
    });

  const setHeaderMetric = useCallback(
    (credit: number | null, date: string) => {
      setTotalBankCredit(credit);
      setLatestDate(date);
    },
    [],
  );

  return (
    <AppShellContext.Provider value={{ dark, setHeaderMetric }}>
      <div data-dark={dark} style={{ background: "var(--bg-page)", minHeight: "100vh" }}>
        <Header
          totalBankCredit={totalBankCredit}
          latestDate={latestDate}
          darkMode={dark}
          onToggleDark={toggleDark}
        />
        {children}
      </div>
    </AppShellContext.Provider>
  );
}
