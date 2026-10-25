const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function generateMatch(matchId = "match_001", seed = 42) {
  const r = await fetch(`${BASE}/matches/generate?match_id=${matchId}&seed=${seed}`, { method: "POST" });
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
