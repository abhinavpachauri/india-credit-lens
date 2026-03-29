import { ImageResponse } from "next/og";

export const size        = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background:     "#0f172a",
          width:          "100%",
          height:         "100%",
          display:        "flex",
          flexDirection:  "column",
          justifyContent: "space-between",
          padding:        "72px 80px",
          fontFamily:     "sans-serif",
        }}
      >
        {/* Top: wordmark */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <span style={{ fontSize: 36 }}>🔍</span>
          <span style={{ color: "#94a3b8", fontSize: 22, fontWeight: 500, letterSpacing: "0.02em" }}>
            indiacreditlens.com
          </span>
        </div>

        {/* Middle: headline + tagline */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div
            style={{
              color:      "#f1f5f9",
              fontSize:   76,
              fontWeight: 800,
              lineHeight: 1.05,
              letterSpacing: "-0.02em",
            }}
          >
            India Credit Lens
          </div>
          <div style={{ color: "#94a3b8", fontSize: 30, lineHeight: 1.4 }}>
            Strategic intelligence from India&apos;s public lending data
          </div>
        </div>

        {/* Bottom: stat pills */}
        <div style={{ display: "flex", gap: "16px" }}>
          {[
            { label: "TOTAL BANK CREDIT",  value: "₹204.8L Cr" },
            { label: "DATA AS OF",         value: "Jan 2026"    },
            { label: "SOURCE",             value: "RBI SIBC"    },
          ].map((s) => (
            <div
              key={s.label}
              style={{
                display:         "flex",
                flexDirection:   "column",
                gap:             "6px",
                background:      "#1e293b",
                borderRadius:    "12px",
                padding:         "16px 24px",
                border:          "1px solid #334155",
              }}
            >
              <span style={{ color: "#475569", fontSize: 13, fontWeight: 600, letterSpacing: "0.08em" }}>
                {s.label}
              </span>
              <span style={{ color: "#4e8ef7", fontSize: 26, fontWeight: 700 }}>
                {s.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size }
  );
}
