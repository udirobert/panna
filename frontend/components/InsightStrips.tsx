"use client";
import type { Insight, Lens } from "../lib/types";

type Props = {
  insights: Insight[];
  lens: Lens;
  activeId: string | null;
  onSelect: (insight: Insight | null) => void;
};

const LENS_FILTER: Record<Lens, (i: Insight) => boolean> = {
  all: () => true,
  tactics: (i) => /formation|press|ppda|influence/.test(i.type),
  attack: (i) => /xg|momentum|shot/.test(i.type),
  story: (i) => /goal|moment/.test(i.type),
};

function ConfDial({ value }: { value: number }) {
  const r = 10;
  const c = 2 * Math.PI * r;
  return (
    <span className="conf-dial">
      <svg className="arc" viewBox="0 0 26 26">
        <circle cx={13} cy={13} r={r} fill="none" stroke="rgba(235,250,240,0.12)" strokeWidth={2.4} />
        <circle
          cx={13}
          cy={13}
          r={r}
          fill="none"
          stroke="var(--gold)"
          strokeWidth={2.4}
          strokeDasharray={`${c * value} ${c}`}
          strokeLinecap="round"
          transform="rotate(-90 13 13)"
        />
        <text x={13} y={16} textAnchor="middle" fontSize={8} fill="#e8f2ec" fontWeight={700}>
          {Math.round(value * 100)}
        </text>
      </svg>
      confidence
    </span>
  );
}

export default function InsightStrips({ insights, lens, activeId, onSelect }: Props) {
  const visible = insights.filter(LENS_FILTER[lens]).slice(-12).reverse();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {visible.length === 0 && <div className="muted">Chalk is reading the match…</div>}
      {visible.map((i) => (
        <div
          key={i.id}
          className={`strip${i.id === activeId ? " active" : ""}${i.recovered ? " recovered" : ""}`}
          onClick={() => onSelect(i.id === activeId ? null : i)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && onSelect(i.id === activeId ? null : i)}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
            <span style={{ fontWeight: 650, fontSize: 13.5, lineHeight: 1.35 }}>{i.claim}</span>
            <ConfDial value={i.confidence} />
          </div>
          <div style={{ marginTop: 4 }}>
            <span className="muted display" style={{ letterSpacing: "0.12em", marginRight: 8 }}>
              {i.type.replace(/_/g, " ").toUpperCase()}
            </span>
            {i.evidence.map((eid, idx) => (
              <span key={eid} className={`evidence-chip${i.id === activeId ? " lit" : ""}`}>
                {i.id === activeId ? `${idx + 1}·` : ""}
                {eid}
              </span>
            ))}
            {i.recovered && (
              <span className="muted" style={{ color: "var(--warn)", marginLeft: 6 }}>
                ↺ recovered by peers
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
