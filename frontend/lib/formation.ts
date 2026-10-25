/**
 * Pure formation geometry for the chalk formation diagram.
 * A formation string like "4-3-3" means (defence, midfield, forwards);
 * we place a GK plus one marker per field player in line depths.
 */

export type Marker = { x: number; y: number };

// Line depths from own goal (0 = back) to opponent goal (1 = forward).
const LINE_X: Record<number, number> = {
  0: 0.16,
  1: 0.38,
  2: 0.62,
  3: 0.84,
};

export function formationMarkers(formation: string): Marker[] {
  const parts = formation
    .split("-")
    .map((n) => parseInt(n, 10))
    .filter((n) => !Number.isNaN(n));
  const lines: number[][] = [];
  // all numbers except the last describe lines; the last is the forwards
  for (let i = 0; i < parts.length - 1; i++) lines.push(new Array(parts[i]).fill(i));
  lines.push(new Array(parts[parts.length - 1]).fill(parts.length - 1));

  const markers: Marker[] = [{ x: 0.04, y: 0.5 }]; // GK
  lines.forEach((line, li) => {
    const n = line.length;
    const x = LINE_X[Math.min(li, 3)] ?? 0.84;
    line.forEach((_, i) => {
      // spread across the pitch, keeping a margin
      const y = n === 1 ? 0.5 : 0.14 + (0.72 * i) / (n - 1);
      markers.push({ x, y });
    });
  });
  return markers; // 1 GK + defenders + midfielders + forwards = 11
}
