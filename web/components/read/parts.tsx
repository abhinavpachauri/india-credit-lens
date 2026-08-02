"use client";

// Shared read-mode primitives (DASHBOARD_SPEC.md §14). The design lives HERE, once — SIBC and
// payments both render these; only the data model (below) + the chart/deep renderers differ per
// pipeline. Colour = section/group (a card's colour is also its chart-line colour).

export type ReadReason = "record" | "reversal" | "surge" | "shift";
export type Direction = "up" | "down" | "flat";

// ── the pipeline-agnostic model an adapter builds ──────────────────────────────
export interface RMCard {
  id: string;
  title: string;
  body?: string;
  implication?: string;
  chain?: string[];
  dimId: string;          // which dimension this card belongs to
  isRead: boolean;        // a "mover" — gets the ▲ marker in the rail
}
export interface RMSubject { name: string; cards: RMCard[] }
export interface RMDimension {
  id: string;
  title: string;
  icon: string;
  color: string;
  cardCount: number;
  moved: number;
  subjects: RMSubject[];
  compositionTitles: string[];   // structural cards → the composition caption
}
export interface RMRead {
  id: string;             // card id
  title: string;
  dimId: string;
  dimTitle: string;
  color: string;
  reason: ReadReason | null;
  direction: Direction | null;
  mode: string;           // display label of the card's chart view (e.g. "YoY")
}
export interface RMModel { reads: RMRead[]; dimensions: RMDimension[] }

// ── styling ────────────────────────────────────────────────────────────────────
// Card visuals live in CSS so :hover applies (inline border/box-shadow win specificity and kill it).
// Dynamic bits come in as the --sec (section colour) / --sel (selected tint) custom props.
export const STYLE = `
@keyframes rmfade{from{opacity:0}to{opacity:1}}
.rm-card{border:1px solid var(--border-card);box-shadow:inset 3px 0 0 var(--sec);background:var(--bg-card);transition:box-shadow .12s ease,border-color .12s ease,transform .12s ease}
.rm-card:hover{border-color:var(--sec);box-shadow:inset 3px 0 0 var(--sec),0 4px 14px var(--shadow)}
.rm-card.sel{border-color:var(--sec);background:var(--sel)}
.rm-tile:hover{transform:translateY(-2px)}
.rm-flat{border:1px solid var(--border-card);background:transparent;transition:box-shadow .12s ease,border-color .12s ease}
.rm-flat:hover{border-color:var(--sec);box-shadow:0 2px 8px var(--shadow)}
.rm-flat.sel{border-color:var(--sec);background:var(--sel)}
.rm-chip{border:1px solid var(--sec);background:var(--bg-card);color:var(--font);transition:background .12s ease,color .12s ease}
.rm-chip:hover{background:var(--sel)}
.rm-chip.on{background:var(--sec);color:#fff}
.rm-chip.on:hover{background:var(--sec)}
.rm-strip{scrollbar-width:none}
.rm-strip::-webkit-scrollbar{display:none}
.rm-link{transition:color .12s ease}
.rm-link:hover{color:var(--font)}
`;

export const PANEL: React.CSSProperties = {
  background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: 12, padding: 18,
};
export const EYEBROW: React.CSSProperties = {
  fontSize: 13, fontWeight: 600, letterSpacing: "0.06em", color: "var(--font-muted)", textTransform: "uppercase",
};
export const READS_COLOR = "#4e8ef7";

export const REASON: Record<ReadReason, string> = { record: "record", reversal: "reversal", surge: "surge", shift: "shift" };
export const glyph = (d: Direction | null) => (d === "up" ? "▲" : d === "down" ? "▼" : "•");

export function tint(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}
export function vars(col: string, sel?: string): React.CSSProperties {
  return { ["--sec" as string]: col, ["--sel" as string]: sel ?? "transparent" } as React.CSSProperties;
}
export function chipStyle(active: boolean): React.CSSProperties {
  return {
    background: active ? "#4e8ef7" : "var(--bg-page)",
    color: active ? "#fff" : "var(--font-muted)",
    border: `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`,
  };
}

// ── presentational components ──────────────────────────────────────────────────

export function ReadCard({ read, selected, onClick }: { read: RMRead; selected: boolean; onClick: () => void }) {
  const col = read.color;
  return (
    <button onClick={onClick} className={`rm-card w-full h-full text-left rounded-xl${selected ? " sel" : ""}`}
            style={{ ...vars(col, tint(col, 0.08)), padding: "12px 15px 12px 17px" }}>
      <div style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.35, color: "var(--font)" }}>{read.title}</div>
      <div className="flex items-center gap-1.5 mt-1.5" style={{ fontSize: 13, color: "var(--font-muted)" }}>
        <span style={{ color: col }}>{glyph(read.direction)}</span>
        {read.reason && <span>{REASON[read.reason]}</span>}
        <span>·</span><span>{read.mode}</span>
        <span className="ml-auto" style={{ color: col, fontWeight: 600 }}>{read.dimTitle}</span>
      </div>
    </button>
  );
}

export function DimensionCard({ dim, onClick }: { dim: RMDimension; onClick: () => void }) {
  const col = dim.color;
  return (
    <button onClick={onClick} className="rm-card rm-tile text-left rounded-xl"
            style={{ ...vars(col), padding: "16px 18px" }}>
      <div style={{ fontSize: 24, lineHeight: 1 }}>{dim.icon}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: "var(--font)", marginTop: 10, lineHeight: 1.25 }}>{dim.title}</div>
      <div className="flex items-center gap-2 mt-2">
        <span style={{ fontSize: 13, color: "var(--font-muted)" }}>{dim.cardCount} insights</span>
        {dim.moved > 0 && <span style={{ fontSize: 13, fontWeight: 600, color: col }}>▲ {dim.moved} moved</span>}
      </div>
    </button>
  );
}

export interface ChipItem { id: string; title: string; icon: string; color: string; moved: number }

export function ChipStrip({ chips, active, stripRef, onPick }: {
  chips: ChipItem[]; active: string; stripRef: React.RefObject<HTMLDivElement | null>; onPick: (id: string) => void;
}) {
  const scroll = (dir: number) => stripRef.current?.scrollBy({ left: dir * 260, behavior: "smooth" });
  return (
    <div className="flex items-center gap-1">
      <button onClick={() => scroll(-1)} className="rm-link px-1 shrink-0"
              style={{ fontSize: 20, color: "var(--font-muted)" }} aria-label="scroll left">‹</button>
      <div ref={stripRef} className="rm-strip flex gap-2 overflow-x-auto py-1">
        {chips.map((c) => (
          <button key={c.id} data-on={c.id === active} onClick={() => onPick(c.id)}
                  className={`rm-chip whitespace-nowrap rounded-full shrink-0${c.id === active ? " on" : ""}`}
                  style={{ ...vars(c.color, tint(c.color, 0.14)), fontSize: 13.5, fontWeight: 600, padding: "6px 14px" }}>
            {c.icon} {c.title}{c.moved > 0 ? ` · ▲ ${c.moved}` : ""}
          </button>
        ))}
      </div>
      <button onClick={() => scroll(1)} className="rm-link px-1 shrink-0"
              style={{ fontSize: 20, color: "var(--font-muted)" }} aria-label="scroll right">›</button>
    </div>
  );
}

export type Depth = "brief" | "full" | "deep";

export function DepthLadder({ depth, setDepth, deepAvailable }: { depth: Depth; setDepth: (d: Depth) => void; deepAvailable: boolean }) {
  const levels: Depth[] = deepAvailable ? ["brief", "full", "deep"] : ["brief", "full"];
  return (
    <div className="flex gap-1">
      {levels.map((d) => (
        <button key={d} onClick={() => setDepth(d)} className="rounded-full transition-colors"
                style={{ fontSize: 12.5, padding: "5px 11px", ...chipStyle(depth === d) }}>
          {d === "brief" ? "Brief" : d === "full" ? "Full" : "Deep ⌁"}
        </button>
      ))}
    </div>
  );
}
