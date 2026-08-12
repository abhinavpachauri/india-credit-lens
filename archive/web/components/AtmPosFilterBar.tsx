"use client";

import { useState } from "react";
import type { FilterState } from "@/lib/atm_pos_data";

interface AtmPosFilterBarProps {
  filter:    FilterState;
  onChange:  (f: FilterState) => void;
  allBanks:  string[];
}

const ACTIVE_PILL_STYLE: React.CSSProperties = {
  background:   "#4e8ef7",
  color:        "#fff",
  border:       "1px solid #4e8ef7",
};

const INACTIVE_PILL_STYLE: React.CSSProperties = {
  background:   "var(--bg-card)",
  color:        "var(--font-muted)",
  border:       "1px solid var(--border-card)",
};

export default function AtmPosFilterBar({ filter, onChange, allBanks }: AtmPosFilterBarProps) {
  const [bankSearch, setBankSearch] = useState("");

  const setMode = (mode: FilterState["mode"]) =>
    onChange({ ...filter, mode });

  const toggleBank = (bank: string) => {
    const next = filter.selectedBanks.includes(bank)
      ? filter.selectedBanks.filter((b) => b !== bank)
      : [...filter.selectedBanks, bank];
    onChange({ ...filter, selectedBanks: next });
  };

  const setTopN = (n: number) => onChange({ ...filter, topN: n });

  const filteredBanks = bankSearch
    ? allBanks.filter((b) => b.toLowerCase().includes(bankSearch.toLowerCase()))
    : allBanks;

  const MODES: { id: FilterState["mode"]; label: string }[] = [
    { id: "by_type",    label: "By Type"     },
    { id: "individual", label: "Individual"  },
    { id: "top_n",      label: "Top N"       },
  ];

  return (
    <div
      className="px-6 py-3 flex flex-wrap items-start gap-4"
      style={{
        background:   "var(--bg-card)",
        borderBottom: "1px solid var(--border-card)",
      }}
    >
      {/* Mode buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        {MODES.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setMode(id)}
            className="text-sm font-medium px-3 py-1 rounded-full transition-colors"
            style={filter.mode === id ? ACTIVE_PILL_STYLE : INACTIVE_PILL_STYLE}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Individual bank selector */}
      {filter.mode === "individual" && (
        <div className="flex flex-col gap-1" style={{ minWidth: 240 }}>
          <input
            type="text"
            placeholder="Search banks…"
            value={bankSearch}
            onChange={(e) => setBankSearch(e.target.value)}
            className="text-sm px-3 py-1 rounded"
            style={{
              background:   "var(--bg-page)",
              border:       "1px solid var(--border-card)",
              color:        "var(--font)",
              outline:      "none",
            }}
          />
          <div
            className="overflow-y-auto rounded"
            style={{
              maxHeight:  200,
              border:     "1px solid var(--border-card)",
              background: "var(--bg-page)",
            }}
          >
            {filteredBanks.map((bank) => (
              <label
                key={bank}
                className="flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer hover:bg-opacity-50"
                style={{ color: "var(--font)" }}
              >
                <input
                  type="checkbox"
                  checked={filter.selectedBanks.includes(bank)}
                  onChange={() => toggleBank(bank)}
                  className="accent-blue-500"
                />
                <span className="truncate">{bank}</span>
              </label>
            ))}
          </div>
          {filter.selectedBanks.length > 0 && (
            <span className="text-xs" style={{ color: "var(--font-muted)" }}>
              {filter.selectedBanks.length} selected
            </span>
          )}
        </div>
      )}

      {/* Top N selector */}
      {filter.mode === "top_n" && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium" style={{ color: "var(--font-muted)" }}>
            Show top:
          </span>
          {[5, 10, 20].map((n) => (
            <button
              key={n}
              onClick={() => setTopN(n)}
              className="text-sm font-medium px-3 py-1 rounded-full transition-colors"
              style={filter.topN === n ? ACTIVE_PILL_STYLE : INACTIVE_PILL_STYLE}
            >
              {n}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
