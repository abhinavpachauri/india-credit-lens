"use client";

import { useEffect, useState } from "react";
import { loadStateBands, loadStatePeriod, type StateMap } from "@/lib/state";
import { loadCutTables, type CutTables } from "@/lib/table";
import { useAppShell } from "@/components/AppShell";
import NbfcReadMode from "@/components/read/NbfcReadMode";
import { FS } from "@/lib/tokens";

/** "2026-07-31" → "Jul 2026" — read off the data, never a hardcoded label. */
function monthLabel(iso: string | undefined): string {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}

export default function NbfcPage() {
  const { setHeaderMetric } = useAppShell();
  const [state, setState] = useState<StateMap>({});
  const [tables, setTables] = useState<CutTables>({});
  const [period, setPeriod] = useState<string>("");

  useEffect(() => {
    loadStateBands("nbfc").then(setState);
    loadCutTables("nbfc").then(setTables);
    loadStatePeriod("nbfc").then((iso) => {
      setPeriod(monthLabel(iso));
      setHeaderMetric(null, monthLabel(iso));
    });
  }, [setHeaderMetric]);

  return (
    <main className="mx-auto max-w-[1440px] px-6 py-6">
      <h1 style={{ fontSize: FS.title, fontWeight: 700, color: "var(--font)" }}>
        NBFC credit deployment
      </h1>
      {/*
        THE SAMPLE CAVEAT IS PAGE-LEVEL, DELIBERATELY. RBI's statement covers NBFCs in the
        Upper and Middle Layers plus HFCs — about 87% of NBFC credit — so "NBFC credit is
        ₹59.9L Cr" is false as stated: that is 87% of it. The qualifier applies to every
        number on this page, so attaching it to one table would understate what it qualifies.
      */}
      <p style={{ fontSize: FS.note, color: "var(--font-muted)", marginTop: 8, maxWidth: 780,
                  lineHeight: 1.55 }}>
        ⚠ A <strong>~87% sample</strong> — NBFCs in the Upper and Middle Layers plus housing
        finance companies, per RBI&apos;s Report on Trend and Progress 2024-25. Every figure
        here describes that sample, not the whole NBFC book.
      </p>
      <div className="mt-5">
        <NbfcReadMode state={state} tables={tables} period={period} />
      </div>
    </main>
  );
}
