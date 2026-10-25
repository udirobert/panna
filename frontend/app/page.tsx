"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AgentRail from "../components/AgentRail";
import InsightStrips from "../components/InsightStrips";
import MomentumChart from "../components/MomentumChart";
import Pitch from "../components/Pitch";
import ScoreBug from "../components/ScoreBug";
import Swarm from "../components/Swarm";
import Ticker from "../components/Ticker";
import Verdict from "../components/Verdict";
import { generateMatch, playback } from "../lib/api";
import { LENSES, type Lens, type Insight } from "../lib/types";
import { useMatchStream } from "../lib/useMatchStream";

const SPEEDS = [15, 30, 60, 120, 300];
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [matchId, setMatchId] = useState("match_001");
  const [seed, setSeed] = useState(42);
  const [active, setActive] = useState(false); // stream connected
  const [lens, setLens] = useState<Lens>("all");
  const [spotlightId, setSpotlightId] = useState<string | null>(null);
  const [resetArmed, setResetArmed] = useState(false);
  const [goalKey, setGoalKey] = useState(0);
  const [recap, setRecap] = useState<string | null>(null);
  const lastGoalRef = useRef<string | null>(null);

  const s = useMatchStream(active ? matchId : null, seed);

  const start = useCallback(async (id: string, newSeed: number) => {
    setResetArmed(false);
    const g = await generateMatch(id, newSeed);
    if (g.event_count > 0) {
      setSeed(newSeed);
      setActive(true);
    }
  }, []);

  const arm = useCallback(async () => {
    if (!resetArmed) {
      setResetArmed(true);
      return;
    }
    const newSeed = Math.floor(Math.random() * 1000); // seed regenerated on air
    const newId = `match_${newSeed}`;
    setMatchId(newId);
    setSpotlightId(null);
    setLens("all");
    setRecap(null);
    lastGoalRef.current = null;
    await start(newId, newSeed);
  }, [resetArmed, start]);

  // goal burst trigger
  useEffect(() => {
    const g = s.lastGoal;
    if (g && lastGoalRef.current !== `${g.minute}-${g.player}`) {
      lastGoalRef.current = `${g.minute}-${g.player}`;
      setGoalKey((k) => k + 1);
    }
  }, [s.lastGoal]);

  // full time → pull the case (recap) once
  const fullTime = active && s.minute >= 90 && !s.playing;
  useEffect(() => {
    if (!fullTime || recap) return;
    let cancelled = false;
    (async () => {
      const r = await fetch(`${BASE}/recap/${matchId}`);
      const j = await r.json();
      if (!cancelled) setRecap(j.recap ?? "");
    })();
    return () => {
      cancelled = true;
    };
  }, [fullTime, recap, matchId]);

  const spotlight: { insight: Insight; events: any[] } | null = useMemo(() => {
    if (!spotlightId) return null;
    const insight = s.insights.find((i) => i.id === spotlightId);
    if (!insight) return null;
    const events = insight.evidence.map((id) => s.eventById[id]).filter(Boolean);
    if (events.length === 0) return null;
    return { insight, events };
  }, [spotlightId, s.insights, s.eventById]);

  // Board = clock-filtered event ledger (deterministic, survives any seek).
  // SSE events are redundant for rendering; the ledger is ground truth.
  const visibleEvents = useMemo(() => {
    const all = Object.values(s.eventById);
    if (all.length === 0) return [];
    return all.filter((e) => e.minute * 60 + e.second <= s.clock);
  }, [s.eventById, s.clock]);

  const failToggle = useCallback(
    (agent: string, failed: boolean) => {
      if (active) void playback(matchId, { action: failed ? "fail" : "recover", agent });
    },
    [active, matchId],
  );

  const playToggle = () => {
    if (!active) return void start(matchId, seed);
    void playback(matchId, { action: s.playing ? "pause" : "play" });
  };

  const goalBurst = s.lastGoal
    ? { x: s.lastGoal.x, y: s.lastGoal.y, team: s.lastGoal.team, key: goalKey }
    : null;

  return (
    <div className="container">
      {/* top chrome: wordmark + score bug + controls */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
          marginBottom: 14,
        }}
      >
        <div>
          <div className="display" style={{ fontSize: 26, fontWeight: 900, letterSpacing: "0.18em" }}>
            PANNA
          </div>
          <div className="muted" style={{ letterSpacing: "0.08em" }}>
            MATCH INTELLIGENCE THAT EXPLAINS ITSELF · SEED {seed}
          </div>
        </div>

        {active && s.snapshot && (
          <ScoreBug
            home={s.snapshot.home_team}
            away={s.snapshot.away_team}
            score={s.score}
            minute={s.minute}
            second={s.second}
            playing={s.playing}
            fullTime={s.minute >= 90 && !s.playing}
          />
        )}

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button className={`btn ${!active || s.playing ? "btn-primary" : ""}`} onClick={playToggle}>
            {!active ? "▶ GENERATE & KICK OFF" : s.playing ? "❚❚ FREEZE" : "▶ PLAY"}
          </button>
          {active && (
            <button
              className="btn"
              onClick={() => void playback(matchId, { action: "seek", at: (s.minute + 1) * 60 })}
              title="jump +1 minute"
            >
              ⏭
            </button>
          )}
          {active && (
            <button
              className="btn"
              onClick={() => void playback(matchId, { action: "seek", at: Math.max(0, s.clock - 60) })}
              title="rewind 1 match-minute (chalk un-draws)"
            >
              ⏪
            </button>
          )}
          {active && (
            <select
              value={s.speed}
              onChange={(e) => void playback(matchId, { action: "speed", speed: Number(e.target.value) })}
              style={{
                background: "rgba(8,16,12,0.9)",
                color: "#e8f2ec",
                border: "1px solid rgba(235,250,240,0.25)",
                borderRadius: 6,
                padding: "7px 8px",
                fontSize: 13,
              }}
            >
              {SPEEDS.map((sp) => (
                <option key={sp} value={sp}>
                  {sp}×
                </option>
              ))}
            </select>
          )}
          <button className="btn" onClick={arm}>
            {resetArmed ? "⟳ CONFIRM" : "⟳ NEW FIXTURE"}
          </button>
        </div>
      </div>

      {!active ? (
        <div
          style={{
            border: "1px dashed rgba(235,250,240,0.25)",
            borderRadius: 8,
            padding: "90px 24px",
            textAlign: "center",
          }}
        >
          <div className="display" style={{ fontSize: 20, letterSpacing: "0.16em", color: "var(--gold)" }}>
            EVERY MATCH LEAVES A VERDICT.
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            Cross-examine yours — every match is generated on demand, seed {seed}.
          </div>
          <div style={{ marginTop: 22 }}>
            <button className="btn btn-primary" style={{ fontSize: 15, padding: "12px 26px" }} onClick={playToggle}>
              ▶ GENERATE & KICK OFF
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 14 }}>
          {/* left: the board */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
            <div
              style={{
                position: "relative",
                border: "1px solid rgba(235,250,240,0.12)",
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              <Pitch
                events={visibleEvents}
                detections={s.detections}
                lens={lens}
                spotlight={spotlight}
                goalBurst={goalBurst}
                failedAgents={s.failed}
              />
              <Swarm
                events={visibleEvents}
                detections={s.detections}
                clock={s.clock}
                failedAgents={s.failed}
                lens={lens}
                spotlightActive={spotlight !== null}
              />
              {s.lastGoal && Date.now() < s.goalFlashUntil && (
                <div className="goal-flash-overlay" key={goalKey} />
              )}
              {/* lens switcher as camera angles */}
              <div style={{ position: "absolute", top: 10, left: 12, display: "flex", gap: 6 }}>
                {LENSES.map((l) => (
                  <button
                    key={l.id}
                    onClick={() => setLens(l.id)}
                    className="display"
                    style={{
                      fontSize: 10,
                      letterSpacing: "0.16em",
                      padding: "4px 10px",
                      borderRadius: 3,
                      cursor: "pointer",
                      border: "1px solid rgba(235,250,240,0.25)",
                      background: lens === l.id ? "var(--gold)" : "rgba(8,16,12,0.85)",
                      color: lens === l.id ? "#141003" : "#d9e8df",
                      fontWeight: 700,
                    }}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
              {/* key-moment readout strip */}
              <div
                style={{
                  position: "absolute",
                  bottom: 10,
                  left: 12,
                  right: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  pointerEvents: "none",
                }}
              >
                <span className="muted display" style={{ letterSpacing: "0.14em" }}>
                  {visibleEvents.length} SIGNALS TRACED
                </span>
                {s.detections.length > 0 && (
                  <span className="display" style={{ fontSize: 11, letterSpacing: "0.12em", color: "var(--gold)" }}>
                    LAST DETECTION · {s.detections[s.detections.length - 1].description}
                  </span>
                )}
              </div>
            </div>

            <MomentumChart points={s.momentum} lens={lens} />

            <div style={{ position: "relative" }}>
              <div
                className="display"
                style={{
                  fontSize: 10,
                  letterSpacing: "0.22em",
                  color: "var(--muted)",
                  marginBottom: 6,
                }}
              >
                CHALK&apos;S BOARD — CLICK A FINDING TO SPOTLIGHT ITS EVIDENCE
              </div>
              <InsightStrips
                insights={s.insights}
                lens={lens}
                activeId={spotlightId}
                onSelect={(ins) => setSpotlightId(ins ? ins.id : null)}
              />
            </div>

            <Ticker items={s.commentary} />
          </div>

          {/* right rail: agent integrity */}
          <div
            style={{
              border: "1px solid rgba(235,250,240,0.12)",
              borderRadius: 8,
              padding: 14,
              alignSelf: "start",
            }}
          >
            <AgentRail failed={s.failed} onToggleFail={failToggle} onReset={arm} resetArmed={resetArmed} />
          </div>
        </div>
      )}

      {/* full time: the case, filed */}
      {fullTime && recap && s.snapshot && (
        <div style={{ marginTop: 14 }}>
          <Verdict
            recap={recap}
            score={s.score}
            home={s.snapshot.home_team}
            away={s.snapshot.away_team}
            insights={s.insights}
            onNewFixture={arm}
            resetArmed={resetArmed}
          />
        </div>
      )}

      <div className="muted" style={{ marginTop: 18, display: "flex", justifyContent: "space-between" }}>
        <span>
          Synthetic, football-realistic data only · generated on demand (seed {seed}) · no real
          Premier League data redistributed.
        </span>
        <span className="display" style={{ letterSpacing: "0.14em" }}>
          MICROSOFT FOUNDRY · MAF · AZURE
        </span>
      </div>
    </div>
  );
}
