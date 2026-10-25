"use client";
import type { Insight } from "../lib/types";

type Props = {
  recap: string;
  score: { home: number; away: number };
  home: string;
  away: string;
  insights: Insight[];
  onNewFixture: () => void;
  resetArmed: boolean;
};

/** Full-time panel: the board's case, printed. The shareable artifact. */
export default function Verdict({ recap, score, home, away, insights, onNewFixture, resetArmed }: Props) {
  const winner = score.home === score.away ? "a draw" : score.home > score.away ? home : away;
  const headline =
    score.home === score.away
      ? `FULL-TIME — ${score.home}–${score.away}: DEADLOCK`
      : `FULL-TIME — ${winner.toUpperCase()} WINS ${score.home > score.away ? `${score.home}–${score.away}` : `${score.away}–${score.home}`}`;
  const exhibits = [...insights].sort((a, b) => b.confidence - a.confidence).slice(0, 4);

  return (
    <div
      style={{
        position: "relative",
        border: "1px solid rgba(245,197,66,0.45)",
        borderRadius: 8,
        padding: "18px 22px",
        background: "linear-gradient(180deg, rgba(245,197,66,0.05), transparent 55%)",
      }}
    >
      <div className="display" style={{ fontSize: 10, letterSpacing: "0.26em", color: "var(--gold)" }}>
        THE VERDICT — CASE FILED
      </div>
      <div className="display" style={{ fontSize: 22, fontWeight: 900, marginTop: 6, letterSpacing: "0.06em" }}>
        {headline}
      </div>
      <pre
        style={{
          whiteSpace: "pre-wrap",
          fontFamily: "inherit",
          fontSize: 13,
          lineHeight: 1.6,
          margin: "10px 0 0",
          color: "#d9e8df",
        }}
      >
        {recap}
      </pre>

      <div className="display" style={{ fontSize: 10, letterSpacing: "0.2em", color: "var(--muted)", margin: "14px 0 6px" }}>
        EXHIBITS ON FILE
      </div>
      {exhibits.map((i, n) => (
        <div key={i.id} style={{ fontSize: 12.5, padding: "3px 0", display: "flex", gap: 8 }}>
          <span style={{ color: "var(--gold)", fontWeight: 800, width: 22 }}>E{n + 1}</span>
          <span>
            {i.claim}{" "}
            <span className="muted">
              ({Math.round(i.confidence * 100)}% conf · {i.evidence.length} evidence)
            </span>
          </span>
        </div>
      ))}

      <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 14 }}>
        <button
          className={`btn ${resetArmed ? "btn-primary" : ""}`}
          onClick={onNewFixture}
          style={{ fontSize: 13, padding: "10px 20px" }}
        >
          {resetArmed ? "⟳ CONFIRM — GENERATE NEW MATCH" : "⟳ CROSS-EXAMINE YOURS"}
        </button>
        <span className="muted">Every match is generated on demand. The case file is shareable.</span>
      </div>
    </div>
  );
}
