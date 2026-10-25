"use client";
import { useEffect, useReducer, useRef } from "react";
import { streamUrl } from "./api";
import {
  initialState,
  type MatchState,
  type Snapshot,
  type EventFrame,
  type Detection,
  type Insight,
  type Commentary,
  type GoalFrame,
  type MomentumPoint,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Action =
  | { type: "snapshot"; snap: Snapshot }
  | { type: "events"; batch: EventFrame[] }
  | { type: "detection"; d: Detection }
  | { type: "insight"; i: Insight }
  | { type: "commentary"; c: Commentary }
  | { type: "goal"; g: GoalFrame }
  | { type: "momentum"; m: MomentumPoint }
  | { type: "clock"; t: number; minute: number; second: number; speed: number; playing: boolean; failed?: string[] }
  | { type: "full_time"; home: number; away: number }
  | { type: "events_loaded"; map: Record<string, EventFrame> };

function reducer(state: MatchState, a: Action): MatchState {
  switch (a.type) {
    case "snapshot": {
      const s = a.snap;
      const momentum: MomentumPoint[] = s.momentum.minutes.map((m, i) => ({
        minute: m,
        home_cum: s.momentum.home_cum[i] ?? 0,
        away_cum: s.momentum.away_cum[i] ?? 0,
        home_danger: s.momentum.home_danger[i] ?? 0,
        away_danger: s.momentum.away_danger[i] ?? 0,
      }));
      // snapshot re-sync also resyncs the board's event ledger up to the clock;
      // a changed seed means a brand-new match — drop the old ledger entirely
      const seedChanged = state.snapshot !== null && state.snapshot.seed !== s.seed;
      const map: Record<string, EventFrame> = seedChanged ? {} : { ...state.eventById };
      for (const e of s.events ?? []) map[e.id] = toEventFrame(e);
      return {
        ...state,
        eventById: map,
        snapshot: s,
        clock: s.clock,
        minute: s.minute,
        second: s.clock % 60,
        playing: s.playing,
        speed: s.speed,
        score: s.score,
        failed: s.failed,
        detections: s.key_moments,
        insights: s.insights,
        commentary: s.commentary,
        momentum,
        recentEvents: [],
        lastGoal: null,
      };
    }
    case "events_loaded":
      return { ...state, eventById: a.map };
    case "events": {
      const map = { ...state.eventById };
      for (const e of a.batch) map[e.id] = toEventFrame(e);
      const recent = [...state.recentEvents, ...a.batch].slice(-140);
      return { ...state, eventById: map, recentEvents: recent };
    }
    case "detection":
      return { ...state, detections: [...state.detections, a.d] };
    case "insight":
      return { ...state, insights: [...state.insights, a.i] };
    case "commentary":
      return { ...state, commentary: [...state.commentary, a.c] };
    case "goal":
      return {
        ...state,
        score: { home: a.g.home_score, away: a.g.away_score },
        lastGoal: a.g,
        goalFlashUntil: Date.now() + 4000,
      };
    case "momentum":
      return { ...state, momentum: [...state.momentum, a.m] };
    case "clock":
      return {
        ...state,
        clock: a.t,
        minute: a.minute,
        second: a.second,
        speed: a.speed,
        playing: a.playing,
        failed: a.failed ?? state.failed,
      };
    case "full_time":
      return {
        ...state,
        playing: false,
        minute: 90,
        second: 0,
        score: { home: a.home, away: a.away },
      };
    default:
      return state;
  }
}

function parseData(line: string): any {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

// The REST ledger returns nested Pydantic dumps ({position:{x,y}, end_location:{x,y},
// metadata:{xg}}); the SSE stream returns flat frames ({x,y,end_x,end_y,xg}).
// Normalize both to EventFrame so the board always reads flat fields.
export function toEventFrame(e: any): EventFrame {
  return {
    id: e.id,
    type: e.type,
    team: e.team,
    player: e.player,
    minute: e.minute,
    second: e.second,
    x: e.position?.x ?? e.x,
    y: e.position?.y ?? e.y,
    end_x: e.end_location?.x ?? e.end_x ?? null,
    end_y: e.end_location?.y ?? e.end_y ?? null,
    outcome: e.outcome ?? null,
    xg: e.metadata?.xg ?? e.xg ?? null,
  };
}

export function useMatchStream(matchId: string | null, seed: number) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const esRef = useRef<EventSource | null>(null);

  // load the full event ledger once — events are immutable facts
  useEffect(() => {
    if (!matchId) return;
    let cancelled = false;
    (async () => {
      const map: Record<string, EventFrame> = {};
      let offset = 0;
      for (;;) {
        const r = await fetch(`${BASE}/events/${matchId}?limit=500&offset=${offset}`);
        const j = await r.json();
        if (cancelled) return;
        for (const e of j.events) map[e.id] = toEventFrame(e);
        offset += j.events.length;
        if (j.events.length === 0 || offset >= j.total) break;
      }
      dispatch({ type: "events_loaded", map });
    })();
    return () => {
      cancelled = true;
    };
  }, [matchId, seed]);

  useEffect(() => {
    if (!matchId) return;
    const es = new EventSource(streamUrl(matchId));
    esRef.current = es;
    es.addEventListener("snapshot", (e) => {
      const snap = parseData((e as MessageEvent).data);
      if (snap) dispatch({ type: "snapshot", snap });
    });
    es.addEventListener("events", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d?.batch) dispatch({ type: "events", batch: d.batch });
    });
    es.addEventListener("detection", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d) dispatch({ type: "detection", d });
    });
    es.addEventListener("insight", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d) dispatch({ type: "insight", i: d });
    });
    es.addEventListener("commentary", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d) dispatch({ type: "commentary", c: d });
    });
    es.addEventListener("goal", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d) dispatch({ type: "goal", g: d });
    });
    es.addEventListener("momentum", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d) dispatch({ type: "momentum", m: d });
    });
    es.addEventListener("clock", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d) dispatch({ type: "clock", ...d });
    });
    es.addEventListener("full_time", (e) => {
      const d = parseData((e as MessageEvent).data);
      if (d) dispatch({ type: "full_time", home: d.home ?? 0, away: d.away ?? 0 });
    });
    return () => es.close();
  }, [matchId]);

  return state;
}
