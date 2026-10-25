"use client";
import { useState } from "react";
import { generateMatch, getInsights, getCommentary, getRecap } from "../lib/api";

type Insight = { id: string; type: string; claim: string; value: any; confidence: number; evidence: string[] };
type KM = { id: string; event_id: string; minute: number; type: string; importance: number; description: string; evidence: string[] };
type CE = { minute: number; second: number; text: string; tone: string; insight_ids: string[] };

export default function Home() {
  const [matchId, setMatchId] = useState("match_001");
  const [loading, setLoading] = useState(false);
  const [eventsCount, setEventsCount] = useState(0);
  const [keyMoments, setKeyMoments] = useState<KM[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [commentary, setCommentary] = useState<CE[]>([]);
  const [recap, setRecap] = useState("");
  const [health, setHealth] = useState<any>(null);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [lens, setLens] = useState<"all" | "tactics" | "attack">("all");

  async function run() {
    setLoading(true);
    try {
      const g = await generateMatch(matchId, 42);
      setEventsCount(g.event_count);
      const ins = await getInsights(matchId);
      setKeyMoments(ins.key_moments);
      setInsights(ins.insights);
      const com = await getCommentary(matchId);
      setCommentary(com.commentary || []);
      setHealth(com.health);
      const rec = await getRecap(matchId);
      setRecap(rec.recap);
    } finally {
      setLoading(false);
    }
  }

  const filteredInsights = insights.filter((i) => {
    if (lens === "tactics") return i.type.includes("formation") || i.type.includes("pressing");
    if (lens === "attack") return i.type.includes("xg") || i.type.includes("momentum") || i.type.includes("player_influence");
    return true;
  });

  return (
    <div className="container">
      <h1>Panna — Match Intelligence</h1>
      <p className="muted">Synthetic football → explainable insights, live commentary, recap, personalized lens.</p>

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <input value={matchId} onChange={(e) => setMatchId(e.target.value)} style={{ padding: 8, borderRadius: 8, border: "1px solid #30363d", background: "#161b22", color: "#e6edf3" }} />
        <button className="btn" onClick={run} disabled={loading}>{loading ? "Running…" : "Generate & Analyze"}</button>
        {eventsCount > 0 && <span className="muted">{eventsCount} events processed</span>}
        <span className="muted">Lens:</span>
        {(["all", "tactics", "attack"] as const).map((l) => (
          <button key={l} onClick={() => setLens(l)} style={{ background: lens === l ? "#1f6feb" : "#161b22", color: "#e6edf3", border: "1px solid #30363d", borderRadius: 8, padding: "6px 12px", cursor: "pointer" }}>{l}</button>
        ))}
      </div>

      {health && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h2>Agent Health</h2>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {Object.values(health).map((h: any) => (
              <span key={h.agent} style={{ padding: "4px 10px", borderRadius: 8, background: h.status === "healthy" ? "#23863633" : "#f8514933", border: `1px solid ${h.status === "healthy" ? "#238636" : "#f85149"}` }}>
                {h.agent}: {h.status}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid">
        <div className="card">
          <h2>Insights ({filteredInsights.length})</h2>
          {filteredInsights.map((i) => (
            <div key={i.id} className="entry">
              <div style={{ fontWeight: 600 }}>{i.claim}</div>
              <div className="muted">type={i.type} · conf={i.confidence} · value={i.value}</div>
              <div style={{ marginTop: 4 }}>
                {i.evidence.map((e) => (
                  <span key={e} className="chip" onClick={() => setHighlighted(e)} title="source event">{e}</span>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <h2>Live Commentary</h2>
          <div style={{ maxHeight: 420, overflow: "auto" }}>
            {commentary.slice(0, 40).map((c, idx) => (
              <div key={idx} className="entry">
                <span className="muted">{c.minute}&apos; </span>
                <span>{c.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Key Moments</h2>
          <div style={{ maxHeight: 420, overflow: "auto" }}>
            {keyMoments.map((km) => (
              <div key={km.id} className="entry">
                <span className="muted">{km.minute}&apos; </span>
                <span style={{ fontWeight: 600 }}>{km.type}</span> — {km.description}
                <span className="muted"> (imp {km.importance})</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Post-Match Recap</h2>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: 0 }}>{recap}</pre>
        </div>
      </div>

      {highlighted && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2>Highlighted Source Event</h2>
          <p className="muted">Event id: {highlighted} — see /events/{matchId} for full payload.</p>
          <button className="btn" onClick={() => setHighlighted(null)}>Clear</button>
        </div>
      )}
    </div>
  );
}
