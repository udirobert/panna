"use client";

import { formationMarkers } from "../lib/formation";

/**
 * Minimal chalk-style formation diagram: a small pitch strip with the team's
 * 11 markers placed per the formation string (4-3-3, 4-4-2, 3-5-2, 4-2-3-1).
 * The team attacks toward `attack` ("right" or "left").
 */

type Props = {
  formation: string;
  attack: "right" | "left";
  label?: string;
  color?: string;
};

export default function FormationDiagram({
  formation,
  attack,
  label,
  color = "#38bdf8",
}: Props) {
  const markers = formationMarkers(formation);
  const W = 220;
  const H = 118;
  const pad = 8;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width={W}
        height={H}
        style={{ display: "block" }}
        aria-label={`${formation} formation`}
      >
        {/* pitch strip */}
        <rect x="2" y="2" width={W - 4} height={H - 4} rx="6" fill="rgba(235,250,240,0.03)" />
        <rect x="2" y="2" width={W - 4} height={H - 4} rx="6" fill="none" stroke="rgba(235,250,240,0.18)" strokeWidth="1" />
        <line x1={W / 2} y1="4" x2={W / 2} y2={H - 4} stroke="rgba(235,250,240,0.14)" strokeWidth="1" />
        <circle cx={W / 2} cy={H / 2} r="12" fill="none" stroke="rgba(235,250,240,0.14)" strokeWidth="1" />
        {/* goals */}
        <rect x="2" y={H / 2 - 16} width="5" height="32" fill="none" stroke="rgba(235,250,240,0.3)" strokeWidth="1" />
        <rect x={W - 7} y={H / 2 - 16} width="5" height="32" fill="none" stroke="rgba(235,250,240,0.3)" strokeWidth="1" />
        {markers.map((m, i) => {
          const mx = (attack === "right" ? m.x : 1 - m.x) * (W - pad * 2) + pad;
          const my = m.y * (H - pad * 2) + pad;
          return (
            <g key={i}>
              <circle cx={mx} cy={my} r={i === 0 ? 5 : 4} fill={i === 0 ? color : "none"} stroke={color} strokeWidth="1.5" />
            </g>
          );
        })}
      </svg>
      <div className="display" style={{ fontSize: 10, letterSpacing: "0.16em", color: color }}>
        {label ? `${label} · ` : ""}{formation}
      </div>
    </div>
  );
}
