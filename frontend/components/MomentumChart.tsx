"use client";
import type { MomentumPoint } from "../lib/types";

// Mirrored momentum chart, BBC-style: home danger above the axis, away below.
export default function MomentumChart({ points, lens }: { points: MomentumPoint[]; lens: string }) {
  if (lens === "story") return null;
  const W = 560;
  const H = 64;
  const mid = H / 2;
  const maxV = Math.max(0.15, ...points.map((p) => Math.max(p.home_danger, p.away_danger)));

  const path = (key: "home_danger" | "away_danger", sign: 1 | -1) => {
    if (points.length === 0) return "";
    const step = W / 90;
    let d = `M 0 ${mid}`;
    for (const p of points) {
      const x = Math.min(p.minute, 90) * step;
      const y = mid + sign * (p[key] / maxV) * (mid - 6);
      d += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    }
    d += ` L ${Math.min(points[points.length - 1].minute, 90) * step} ${mid} Z`;
    return d;
  };

  const xgHome = points.length ? points[points.length - 1].home_cum : 0;
  const xgAway = points.length ? points[points.length - 1].away_cum : 0;

  return (
    <div style={{ position: "relative" }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Match momentum. Home danger above the line, away below. Cumulative xG: home ${xgHome.toFixed(2)}, away ${xgAway.toFixed(2)}.`}
        style={{ width: "100%", display: "block" }}
      >
        <line x1={0} y1={mid} x2={W} y2={mid} stroke="rgba(235,250,240,0.14)" strokeWidth={0.5} />
        <path d={path("home_danger", -1)} fill="rgba(56,189,248,0.32)" stroke="var(--home)" strokeWidth={0.6} />
        <path d={path("away_danger", 1)} fill="rgba(245,158,11,0.30)" stroke="var(--away)" strokeWidth={0.6} strokeDasharray="3 2" />
        {/* now cursor */}
        {points.length > 0 && (
          <line
            x1={Math.min(points[points.length - 1].minute, 90) * (W / 90)}
            y1={4}
            x2={Math.min(points[points.length - 1].minute, 90) * (W / 90)}
            y2={H - 4}
            stroke="var(--gold)"
            strokeWidth={0.8}
            opacity={0.85}
          />
        )}
      </svg>
      <div
        style={{
          position: "absolute",
          top: -2,
          left: 6,
          fontSize: 10,
          letterSpacing: "0.14em",
          color: "var(--muted)",
        }}
        className="display"
      >
        MATCH MOMENTUM · xG {xgHome.toFixed(2)} — {xgAway.toFixed(2)}
      </div>
    </div>
  );
}
