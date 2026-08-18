"use client";

// ── DeepReading ───────────────────────────────────────────────────────────────
// The Deep rung of the depth ladder: the causal layer for whichever dimension the reader is
// already looking at. Same data that used to fill the /opportunities page; the difference is
// that it is now a deeper reading OF an insight rather than a separate catalogue beside it.
//
// The register is analyst, not advisor. The model classifies these nodes as opportunity or risk,
// and that vocabulary stays in the model — the reader sees a finding, its mechanism, and the
// measurements behind it. We report what the data shows and why. We do not suggest moves.

import { useState } from "react";
import BasisBlock from "@/components/dls/BasisBlock";
import { crossSystemFor, opportunitiesFor, type CrossFinding, type OppFeedItem } from "@/lib/opportunities";
import { FS } from "@/lib/tokens";

const STATUS_COLOR: Record<string, string> = {
  active: "#16A34A",
  watch: "#D97706",
};

/** Descriptive, not directive: it says whether the driver is currently firing. */
function StatusChip({ status }: { status: string }) {
  const color = STATUS_COLOR[status] ?? "var(--font-muted)";
  return (
    <span style={{ fontSize: FS.meta, fontWeight: 600, color, whiteSpace: "nowrap" }}>
      · {status}
    </span>
  );
}

function Mechanism({ chain }: { chain: string[] }) {
  const [open, setOpen] = useState(false);
  if (!chain?.length) return null;
  const shown = open ? chain : chain.slice(0, 2);
  return (
    <div style={{ marginTop: 10 }}>
      <div
        style={{
          fontSize: FS.meta, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em",
          color: "var(--font-muted)", marginBottom: 5,
        }}
      >
        The mechanism
      </div>
      <ol style={{ paddingLeft: 0, listStyle: "none", margin: 0, display: "flex", flexDirection: "column", gap: 5 }}>
        {shown.map((step, i) => (
          <li key={i} className="flex gap-2" style={{ lineHeight: 1.55 }}>
            <span className="flex-shrink-0 font-bold" style={{ color: "var(--font-muted)", minWidth: 16, fontSize: FS.label }}>
              {i + 1}
            </span>
            <span style={{ fontSize: FS.note, color: "var(--font)" }}>{step}</span>
          </li>
        ))}
      </ol>
      {chain.length > 2 && (
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-xs mt-1.5"
          style={{ color: "var(--font-muted)", background: "none", border: "none", padding: 0, cursor: "pointer" }}
        >
          {open ? "show less" : `+${chain.length - 2} more`}
        </button>
      )}
    </div>
  );
}

function Finding({ item, color, anchor }: { item: OppFeedItem; color: string; anchor?: string }) {
  return (
    <div
      style={{
        borderLeft: `3px solid ${color}`,
        paddingLeft: 14,
        marginTop: 16,
      }}
    >
      <div className="flex items-baseline gap-2 flex-wrap">
        <span style={{ fontSize: FS.lead, fontWeight: 700, color: "var(--font)" }}>{item.title}</span>
        <StatusChip status={item.status} />
      </div>
      {item.body && (
        <p style={{ fontSize: FS.body, lineHeight: 1.6, color: "var(--font)", marginTop: 6 }}>{item.body}</p>
      )}
      {anchor && (
        <p style={{ fontSize: FS.note, color: "var(--font-muted)", marginTop: 6 }}>
          On this dimension: {anchor}
        </p>
      )}
      <Mechanism chain={item.chain} />
      {item.basis && <BasisBlock basis={item.basis} />}
    </div>
  );
}

export interface DeepReadingProps {
  pipeline: string;
  sectionId: string;
  sectionTitle: string;
  color: string;
  /** What the other dataset is called, for the cross-system heading. */
  otherLabel: string;
}

export default function DeepReading({ pipeline, sectionId, sectionTitle, color, otherLabel }: DeepReadingProps) {
  const own: OppFeedItem[] = opportunitiesFor(pipeline, sectionId);
  const cross: CrossFinding[] = crossSystemFor(pipeline, sectionTitle);
  const total = own.length + cross.length;
  if (!total) return null;

  return (
    <div style={{ marginTop: 22, paddingTop: 16, borderTop: "2px solid var(--border-card)" }}>
      <div className="flex items-baseline justify-between">
        <div
          style={{
            fontSize: FS.label, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em",
            color: "var(--font-muted)",
          }}
        >
          Deeper reading
        </div>
        <div style={{ fontSize: FS.meta, color: "var(--font-muted)" }}>
          {total} finding{total === 1 ? "" : "s"}
        </div>
      </div>

      {own.map((item) => (
        <Finding key={item.id} item={item} color={color} />
      ))}

      {cross.length > 0 && (
        <>
          <div
            style={{
              fontSize: FS.meta, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em",
              color: "var(--font-muted)", marginTop: 22, paddingTop: 12,
              borderTop: "1px solid var(--border-card)",
            }}
          >
            Read together with {otherLabel}
          </div>
          {cross.map(({ item, anchor }) => (
            <Finding
              key={item.id}
              item={item}
              color={color}
              anchor={anchor ? `${anchor.label.replace(/\s*\((Credit|Payments)\)\s*$/, "")}${anchor.value ? `, ${anchor.value}` : ""}` : undefined}
            />
          ))}
        </>
      )}
    </div>
  );
}
