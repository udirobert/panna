"use client";
import { useMemo } from "react";
import type { Detection, EventFrame, Insight, Lens } from "../lib/types";

// StatsBomb coords: x 0-120 (attack →), y 0-80 (top → bottom). Home attacks right.
const W = 120;
const H = 80;
const HOME = { r: 56, g: 189, b: 248 }; // cyan
const AWAY = { r: 245, g: 158, b: 11 }; // amber

type Props = {
  events: EventFrame[];
  detections: Detection[];
  lens: Lens;
  spotlight: { insight: Insight; events: EventFrame[] } | null;
  goalBurst: { x: number; y: number; team: string; key: number } | null;
  failedAgents: string[];
  score?: { home: number; away: number };
  minute?: number;
};

function teamColor(team: string, alpha: number) {
  const c = team === "Home" ? HOME : AWAY;
  return `rgba(${c.r},${c.g},${c.b},${alpha})`;
}

/** Simplified pitch-control: grid dominance from recent events. */
function useControlField(events: EventFrame[]) {
  return useMemo(() => {
    const GX = 16;
    const GY = 10;
    const grid = new Float32Array(GX * GY);
    const weights = new Float32Array(GX * GY);
    for (const e of events) {
      const gx = Math.min(GX - 1, Math.max(0, Math.floor((e.x / W) * GX)));
      const gy = Math.min(GY - 1, Math.max(0, Math.floor((e.y / H) * GY)));
      const w = e.type === "shot" || e.type === "goal" ? 3 : e.type === "pass" ? 1.4 : 1;
      const i = gy * GX + gx;
      weights[i] += w;
      grid[i] += e.team === "Home" ? w : -w;
    }
    const cells: { x: number; y: number; v: number; strength: number }[] = [];
    for (let i = 0; i < GX * GY; i++) {
      const strength = weights[i];
      if (strength < 0.01) continue;
      cells.push({
        x: ((i % GX) + 0.5) * (W / GX),
        y: (Math.floor(i / GX) + 0.5) * (H / GY),
        v: Math.max(-1, Math.min(1, grid[i] / (strength * 1.6))),
        strength: Math.min(1, strength / 6),
      });
    }
    return cells;
  }, [events]);
}

export default function Pitch({
  events,
  detections,
  lens,
  spotlight,
  goalBurst,
  failedAgents,
  score,
  minute,
}: Props) {
  const control = useControlField(events);
  const showControl = lens === "tactics";
  const showShots = lens !== "story";
  const dimForSpotlight = spotlight !== null;

  const passes = events.filter((e) => e.type === "pass" && e.end_x !== null);
  const shots = events.filter((e) => e.type === "shot" || e.type === "goal");
  const spotIds = new Set((spotlight?.events ?? []).map((e) => e.id));

  // Shape encodes team so the board never relies on color alone (WCAG 1.4.1):
  //   Home — solid lines, filled shot rings
  //   Away — dashed lines, open shot rings
  const dashFor = (team: string) => (team === "Home" ? undefined : "1.5 1.1");

  const homeShots = events.filter((e) => e.team === "Home" && (e.type === "shot" || e.type === "goal")).length;
  const awayShots = events.filter((e) => e.team === "Away" && (e.type === "shot" || e.type === "goal")).length;
  const desc = spotlight
    ? `Evidence spotlight: ${spotlight.insight.claim} — ${spotlight.events.length} cited events highlighted in gold.`
    : `Live pitch at ${minute ?? 0} minutes. ${score ? `Score home ${score.home}, away ${score.away}. ` : ""}` +
      `${events.length} events played; ${homeShots} home shots (solid lines, filled rings) and ${awayShots} away shots (dashed lines, open rings).`;

  return (
    <div style={{ position: "relative", width: "100%" }}>
      {goalBurst && <GoalBurst x={goalBurst.x} y={goalBurst.y} team={goalBurst.team} key={goalBurst.key} />}
      <svg
        viewBox={`-4 -4 ${W + 8} ${H + 8}`}
        role="img"
        aria-labelledby="pitch-title pitch-desc"
        style={{
          width: "100%",
          display: "block",
          filter: dimForSpotlight ? "saturate(0.55) brightness(0.6)" : "none",
          transition: "filter 400ms ease",
        }}
      >
        <title id="pitch-title">
          Panna live pitch{score ? ` — home ${score.home}, away ${score.away}` : ""}
        </title>
        <desc id="pitch-desc">{desc}</desc>
        {/* surface */}
        <defs>
          <linearGradient id="grass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0c1f16" />
            <stop offset="100%" stopColor="#0a1a12" />
          </linearGradient>
          <radialGradient id="floodlight" cx="50%" cy="0%" r="80%">
            <stop offset="0%" stopColor="rgba(220,255,230,0.07)" />
            <stop offset="100%" stopColor="rgba(0,0,0,0)" />
          </radialGradient>
          <filter id="soften">
            <feGaussianBlur stdDeviation="2.2" />
          </filter>
        </defs>
        <rect x={-4} y={-4} width={W + 8} height={H + 8} fill="url(#grass)" rx={2} />
        <rect x={-4} y={-4} width={W + 8} height={H + 8} fill="url(#floodlight)" rx={2} />

        {/* pitch-control dominance glow */}
        {showControl && (
          <g filter="url(#soften)" opacity={0.5}>
            {control.map((c, i) =>
              c.strength > 0.12 ? (
                <circle
                  key={i}
                  cx={c.x}
                  cy={c.y}
                  r={5.5}
                  fill={c.v >= 0 ? teamColor("Home", 0.22 * c.strength * Math.abs(c.v) * 2) : teamColor("Away", 0.22 * c.strength * Math.abs(c.v) * 2)}
                />
              ) : null,
            )}
          </g>
        )}

        {/* markings */}
        <g stroke="var(--chalk-dim)" strokeWidth={0.35} fill="none">
          <rect x={0} y={0} width={W} height={H} />
          <line x1={W / 2} y1={0} x2={W / 2} y2={H} />
          <circle cx={W / 2} cy={H / 2} r={9.15} />
          {/* boxes */}
          <rect x={0} y={H / 2 - 20.16} width={16.5} height={40.32} />
          <rect x={W - 16.5} y={H / 2 - 20.16} width={16.5} height={40.32} />
          <rect x={0} y={H / 2 - 9.16} width={5.5} height={18.32} />
          <rect x={W - 5.5} y={H / 2 - 9.16} width={5.5} height={18.32} />
          {/* penalty arcs */}
          <path d={`M 16.5 ${H / 2 - 7.1} A 9.15 9.15 0 0 1 16.5 ${H / 2 + 7.1}`} />
          <path d={`M ${W - 16.5} ${H / 2 - 7.1} A 9.15 9.15 0 0 0 ${W - 16.5} ${H / 2 + 7.1}`} />
          <circle cx={W / 2} cy={H / 2} r={0.5} fill="var(--chalk-dim)" />
          <circle cx={11} cy={H / 2} r={0.5} fill="var(--chalk-dim)" />
          <circle cx={W - 11} cy={H / 2} r={0.5} fill="var(--chalk-dim)" />
        </g>

        {/* pass vectors (chalk telestration) */}
        {!dimForSpotlight &&
          lens !== "story" &&
          passes.map((e) => (
            <line
              key={e.id}
              x1={e.x}
              y1={e.y}
              x2={e.end_x}
              y2={e.end_y}
              stroke={teamColor(e.team, e.outcome === "success" ? 0.2 : 0.42)}
              strokeWidth={0.3}
              strokeDasharray={dashFor(e.team)}
              className={e.outcome === "success" ? undefined : "chalk-path"}
              style={
                e.outcome === "success"
                  ? undefined
                  : ({ "--chalk-len": 40 } as React.CSSProperties)
              }
            />
          ))}

        {/* shot rings — filled = Home, open = Away (shape, not just color) */}
        {showShots &&
          !dimForSpotlight &&
          shots.map((e) => {
            const r = 0.9 + (e.xg ?? 0.1) * 3.4;
            const goal = e.type === "goal";
            const homeTeam = e.team === "Home";
            return (
              <g key={e.id}>
                {goal && (
                  <circle cx={e.x} cy={e.y} r={r * 2.2} fill="none" stroke="var(--gold)" strokeWidth={0.5} className="pulse-ring" />
                )}
                <circle
                  cx={e.x}
                  cy={e.y}
                  r={r}
                  fill={goal ? "var(--gold)" : homeTeam ? teamColor(e.team, 0.55) : "none"}
                  stroke={goal ? "var(--gold)" : teamColor(e.team, 0.85)}
                  strokeWidth={0.28}
                  strokeDasharray={goal ? undefined : homeTeam ? undefined : "0.8 0.6"}
                />
              </g>
            );
          })}

        {/* scout detections → quorum rings harden into chalk */}
        {!dimForSpotlight &&
          detections.map((d) => {
            const ev = events.find((e) => e.id === d.event_id);
            if (!ev) return null;
            const r = 2 + d.importance * 2.6;
            const col = d.recovered ? "var(--warn)" : "var(--gold)";
            return (
              <g key={d.id}>
                <circle cx={ev.x} cy={ev.y} r={r} fill="none" stroke={col} strokeWidth={0.32} className="quorum-ring" strokeDasharray={d.recovered ? "1.2 0.9" : undefined} />
                <circle cx={ev.x} cy={ev.y} r={r + 1.6} fill="none" stroke={col} strokeWidth={0.16} opacity={0.5} className="quorum-ring" />
              </g>
            );
          })}

        {/* evidence spotlight */}
        {spotlight &&
          spotlight.events.map((e, i) => (
            <g key={e.id}>
              <circle cx={e.x} cy={e.y} r={4.4} fill="var(--gold-soft)" stroke="var(--gold)" strokeWidth={0.4} style={{ filter: "drop-shadow(0 0 3px rgba(245,197,66,0.9))" }} />
              <text x={e.x} y={e.y + 1} textAnchor="middle" fontSize={2.6} fontWeight={800} fill="#141003" style={{ paintOrder: "stroke" }}>
                {i + 1}
              </text>
              {e.end_x !== null && (
                <line x1={e.x} y1={e.y} x2={e.end_x} y2={e.end_y} stroke="var(--gold)" strokeWidth={0.42} strokeDasharray="1.4 1" className="chalk-path gold" style={{ "--chalk-len": 60 } as React.CSSProperties} />
              )}
            </g>
          ))}
        {spotlight && (
          <g>
            {spotlight.events.map((e, i) => (
              <text key={`${e.id}-lbl`} x={Math.min(e.x + 3, W - 8)} y={Math.max(e.y - 2, 3)} fontSize={2.4} fill="var(--gold)" fontFamily="Courier New, monospace" fontWeight={700}>
                {i + 1}·{e.id}
              </text>
            ))}
          </g>
        )}

        {/* analyst dark: chalk mid-draw stays on the board */}
        {failedAgents.includes("analyst") && (
          <g opacity={0.6}>
            <line x1={20} y1={20} x2={34} y2={26} stroke="var(--warn)" strokeWidth={0.4} strokeDasharray="2 1.4" className="chalk-path" style={{ "--chalk-len": 30 } as React.CSSProperties} />
          </g>
        )}
      </svg>

      {/* lens + integrity overlays */}
      <div style={{ position: "absolute", top: 10, right: 12, display: "flex", gap: 8, alignItems: "center" }}>
        {failedAgents.length > 0 && (
          <span className="display" style={{ fontSize: 11, letterSpacing: "0.14em", color: "var(--warn)" }}>
            ⚠ {failedAgents.join(" · ").toUpperCase()} DARK — TRACES PRESERVED
          </span>
        )}
      </div>
    </div>
  );
}

/** Canvas confetti burst for goals. */
function GoalBurst({ x, y, team }: { x: number; y: number; team: string; key: number }) {
  const particles = useMemo(
    () =>
      Array.from({ length: 36 }, (_, i) => {
        const a = (i / 36) * Math.PI * 2 + Math.random() * 0.3;
        const v = 60 + Math.random() * 160;
        return {
          dx: Math.cos(a) * v,
          dy: Math.sin(a) * v * 0.7 - 60,
          size: 3 + Math.random() * 4,
          hue: Math.random() < 0.5 ? team : "gold",
          dur: 0.9 + Math.random() * 0.7,
        };
      }),
    [team],
  );
  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
      {particles.map((p, i) => (
        <span
          key={i}
          style={
            {
              position: "absolute",
              left: `${(x / W) * 100}%`,
              top: `${(y / H) * 100}%`,
              width: p.size,
              height: p.size,
              borderRadius: p.hue === "gold" ? "50%" : 1,
              background: p.hue === "gold" ? "var(--gold)" : teamColor(team, 1),
              opacity: 0,
              "--bx": `${p.dx}px`,
              "--by": `${p.dy}px`,
              animation: `burst ${p.dur}s ease-out forwards`,
            } as React.CSSProperties
          }
        />
      ))}
      <style>{`@keyframes burst {
        0% { opacity: 1; transform: translate(0,0) scale(1); }
        100% { opacity: 0; transform: translate(var(--bx,0), var(--by,0)) scale(0.4); }
      }`}</style>
    </div>
  );
}
