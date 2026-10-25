"use client";
import FormationDiagram from "./FormationDiagram";
import type { Insight, RecapStructured } from "../lib/types";

type Props = {
  recap: string;
  source: string; // foundry | template
  score: { home: number; away: number };
  home: string;
  away: string;
  insights: Insight[];
  data: RecapStructured | null;
  onNewFixture: () => void;
  resetArmed: boolean;
  onShare: () => void;
};

function XgBar({ label, value, other, color }: { label: string; value: number; other: number; color: string }) {
  const total = Math.max(0.2, value + other);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span className="display" style={{ fontSize: 10, letterSpacing: "0.12em", width: 86, color: "#d9e8df" }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 8, background: "rgba(235,250,240,0.08)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${(value / total) * 100}%`, background: color, height: "100%", borderRadius: 4 }} />
      </div>
      <span className="display" style={{ fontSize: 11, width: 30, textAlign: "right", color: "#e8f2ec" }}>
        {value.toFixed(2)}
      </span>
    </div>
  );
}

/** Full-time panel: the board's case, printed editorially. The shareable artifact. */
export default function Verdict({
  recap,
  source,
  score,
  home,
  away,
  insights,
  data,
  onNewFixture,
  resetArmed,
  onShare,
}: Props) {
  const winner = score.home === score.away ? "a draw" : score.home > score.away ? home : away;
  const headline =
    score.home === score.away
      ? `FULL-TIME — ${score.home}–${score.away}: DEADLOCK`
      : `FULL-TIME — ${winner.toUpperCase()} WINS ${score.home > score.away ? `${score.home}–${score.away}` : `${score.away}–${score.home}`}`;
  const exhibits = [...insights].sort((a, b) => b.confidence - a.confidence).slice(0, 4);
  const modelNarrative = source === "foundry";
  const xg = data?.xg;
  const formations = data?.formations;
  const goals = data?.goals ?? [];

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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div className="display" style={{ fontSize: 10, letterSpacing: "0.26em", color: "var(--gold)" }}>
          THE VERDICT — CASE FILED
        </div>
        <span
          className="display"
          style={{ fontSize: 10, letterSpacing: "0.14em", color: modelNarrative ? "var(--gold)" : "var(--muted)" }}
        >
          {modelNarrative ? "✦ NARRATED BY GPT-5.4 (FOUNDRY)" : "TEMPLATE NARRATION · FOUNDRY OFFLINE"}
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)",
          gap: 24,
          marginTop: 12,
        }}
      >
        {/* left: headline, story, exhibits */}
        <div style={{ minWidth: 0 }}>
          <div className="display" style={{ fontSize: 22, fontWeight: 900, letterSpacing: "0.06em" }}>
            {headline}
          </div>
          <div
            style={{
              whiteSpace: "pre-wrap",
              fontFamily: "inherit",
              fontSize: 13.5,
              lineHeight: 1.65,
              marginTop: 10,
              color: "#d9e8df",
            }}
          >
            {recap}
          </div>

          <div className="display" style={{ fontSize: 10, letterSpacing: "0.2em", color: "var(--muted)", margin: "16px 0 6px" }}>
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
        </div>

        {/* right: the numbers, chalked */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 18,
              padding: "10px 0",
              border: "1px solid rgba(235,250,240,0.14)",
              borderRadius: 6,
            }}
          >
            <span className="display" style={{ fontSize: 13, letterSpacing: "0.08em", color: "#38bdf8", textAlign: "right", flex: 1 }}>
              {home.toUpperCase()}
            </span>
            <span className="display" style={{ fontSize: 30, fontWeight: 900, fontVariantNumeric: "tabular-nums" }}>
              {score.home} – {score.away}
            </span>
            <span className="display" style={{ fontSize: 13, letterSpacing: "0.08em", color: "#f59e0b", flex: 1 }}>
              {away.toUpperCase()}
            </span>
          </div>

          {xg && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div className="display" style={{ fontSize: 9, letterSpacing: "0.22em", color: "var(--muted)" }}>
                EXPECTED GOALS
              </div>
              <XgBar label={home} value={xg.home} other={xg.away} color="#38bdf8" />
              <XgBar label={away} value={xg.away} other={xg.home} color="#f59e0b" />
            </div>
          )}

          {goals.length > 0 && (
            <div>
              <div className="display" style={{ fontSize: 9, letterSpacing: "0.22em", color: "var(--muted)", marginBottom: 4 }}>
                GOALS
              </div>
              {goals.map((g, i) => (
                <div key={i} style={{ fontSize: 12, padding: "2px 0", display: "flex", gap: 8 }}>
                  <span className="display" style={{ color: "var(--gold)", fontWeight: 800, width: 26 }}>
                    {g.minute}&prime;
                  </span>
                  <span>{g.description}</span>
                </div>
              ))}
            </div>
          )}

          {formations && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-around",
                padding: "10px 6px",
                border: "1px solid rgba(235,250,240,0.14)",
                borderRadius: 6,
              }}
            >
              <FormationDiagram formation={formations.final.home} attack="right" label="HOME" color="#38bdf8" />
              <FormationDiagram formation={formations.final.away} attack="left" label="AWAY" color="#f59e0b" />
            </div>
          )}
          {formations && formations.kickoff && (
            <div className="muted display" style={{ fontSize: 9, letterSpacing: "0.12em", textAlign: "center" }}>
              KICK-OFF {formations.kickoff.home} v {formations.kickoff.away}
              {formations.kickoff.home !== formations.final.home || formations.kickoff.away !== formations.final.away
                ? " — FORMATIONS SHIFTED ON THE CHALK"
                : ""}
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <button
          className={`btn ${resetArmed ? "btn-primary" : ""}`}
          onClick={onNewFixture}
          style={{ fontSize: 13, padding: "10px 20px" }}
        >
          {resetArmed ? "⟳ CONFIRM — GENERATE NEW MATCH" : "⟳ CROSS-EXAMINE YOURS"}
        </button>
        <button className="btn" onClick={onShare} style={{ fontSize: 13, padding: "10px 20px" }}>
          ⇪ SHARE THIS CASE
        </button>
        <span className="muted">Every match is generated on demand. The link is the match.</span>
      </div>
    </div>
  );
}
