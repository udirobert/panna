const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function generateMatch(matchId = "match_001", seed = 42) {
  const r = await fetch(`${BASE}/matches/generate?match_id=${matchId}&seed=${seed}`, {
    method: "POST",
  });
  return r.json();
}

/** Ensure a (possibly shared) match is live and return its identity. */
export async function resolveMatch(matchId: string) {
  const r = await fetch(`${BASE}/matches/resolve/${matchId}`);
  return r.json();
}

/** The public share poster for a match. */
export function shareUrl(matchId: string) {
  return `${BASE}/share/${matchId}`;
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

export interface FeedOptions {
  lang?: string;
  audience?: string;
}

export function streamUrl(matchId: string, autoplay = true, feed: FeedOptions = {}) {
  const params = new URLSearchParams();
  if (autoplay) params.set("autoplay", "1");
  if (feed.lang && feed.lang !== "en") params.set("lang", feed.lang);
  if (feed.audience && feed.audience !== "fan") params.set("audience", feed.audience);
  const qs = params.toString();
  return `${BASE}/stream/${matchId}${qs ? `?${qs}` : ""}`;
}

export type PlaybackAction =
  | { action: "play" }
  | { action: "pause" }
  | { action: "seek"; at: number }
  | { action: "speed"; speed: number }
  | { action: "fail"; agent: string }
  | { action: "recover"; agent: string }
  | { action: "seed_bad_claim" };

/** Red-team demo: plant a fabricated line and watch the verifier hold it. */
export async function seedBadClaim(matchId: string) {
  return playback(matchId, { action: "seed_bad_claim" });
}

export type BoardRow = {
  id: string;
  kind: "insight" | "commentary";
  at: number;
  text: string;
  air_status: "aired" | "queued" | "held" | "killed" | "approved";
  verdict: string | null;
  reason: string | null;
  checks: { ok: boolean; kind: string; detail: string }[];
};

export async function getProducerBoard(matchId: string) {
  const r = await fetch(`${BASE}/producer/${matchId}/board`);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{
    match_id: string;
    clock: number;
    verification: { checked: number; verified: number; repaired: number; rejected: number };
    items: BoardRow[];
  }>;
}

export async function decide(matchId: string, itemId: string, decision: "approve" | "kill") {
  const r = await fetch(`${BASE}/producer/${matchId}/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: itemId, decision }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getStatus() {
  const r = await fetch(`${BASE}/status`);
  return r.json();
}

export async function playback(matchId: string, cmd: PlaybackAction) {
  const r = await fetch(`${BASE}/stream/playback/${matchId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cmd),
  });
  return r.json();
}
