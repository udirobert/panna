const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function generateMatch(matchId = "match_001", seed = 42) {
  const r = await fetch(`${BASE}/matches/generate?match_id=${matchId}&seed=${seed}`, {
    method: "POST",
  });
  return r.json();
}

export async function getInsights(matchId: string) {
  const r = await fetch(`${BASE}/insights/${matchId}`);
  return r.json();
}

export async function getCommentary(matchId: string) {
  const r = await fetch(`${BASE}/commentary/${matchId}`);
  return r.json();
}

export async function getRecap(matchId: string) {
  const r = await fetch(`${BASE}/recap/${matchId}`);
  return r.json();
}

export function streamUrl(matchId: string, autoplay = true) {
  return `${BASE}/stream/${matchId}${autoplay ? "?autoplay=1" : ""}`;
}

export type PlaybackAction =
  | { action: "play" }
  | { action: "pause" }
  | { action: "seek"; at: number }
  | { action: "speed"; speed: number }
  | { action: "fail"; agent: string }
  | { action: "recover"; agent: string };

export async function playback(matchId: string, cmd: PlaybackAction) {
  const r = await fetch(`${BASE}/stream/playback/${matchId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cmd),
  });
  return r.json();
}
