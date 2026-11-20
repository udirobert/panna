"use client";
import { useState } from "react";
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

function VerdictChip({ insight }: { insight: Insight }) {
  const [open, setOpen] = useState(false);
  const v = insight.verification;
  if (!v) return null;
  const color =
    v.status === "verified" ? "var(--ok)" : v.status === "repaired" ? "var(--warn)" : "var(--down)";
  return (
    <span style={{ marginLeft: 6 }}>
      <button
        type="button"
        className="why-btn"
        style={{
          background: "none",
          border: `1px solid ${color}`,
          color,
          borderRadius: 4,
          padding: "0 6px",
          fontSize: 10,
          letterSpacing: "0.08em",
          cursor: "pointer",
        }}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
      >
        {v.status === "verified" ? "✓ verified" : v.status === "repaired" ? "✎ repaired" : "✕ rejected"} · why?
      </button>
      {open && (
        <div
          className="why-panel"
          style={{
            display: "block",
            marginTop: 4,
            padding: "6px 8px",
            background: "rgba(0,0,0,0.25)",
            borderRadius: 4,
            fontSize: 11,
            lineHeight: 1.5,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {v.repair_of && (
            <div className="muted" style={{ marginBottom: 4 }}>
              aired as: <s style={{ opacity: 0.7 }}>{v.repair_of}</s>
            </div>
          )}
          {v.reason && <div style={{ color, marginBottom: 4 }}>{v.reason}</div>}
          {v.checks.map((c, i) => (
            <div key={i} className={c.ok ? "muted" : ""} style={c.ok ? {} : { color: "var(--down)" }}>
              {c.ok ? "✓" : "✕"} {c.detail}
            </div>
          ))}
        </div>
      )}
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
            <VerdictChip insight={i} />
            {i.recovered && (
              <span className="muted" style={{ color: "var(--warn)", marginLeft: 6 }}>
                ↺ recovered by peers
              </span>
            )}
            {i.approved && (
              <span className="muted" style={{ color: "var(--ok)", marginLeft: 6 }}>
                ✓ producer approved
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
