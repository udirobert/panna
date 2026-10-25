import { describe, expect, it } from "vitest";
import { formationMarkers } from "../formation";

/** The formation diagram must always place exactly 11 markers (GK + 10). */
describe("formationMarkers", () => {
  it("places 11 markers for 4-3-3", () => {
    expect(formationMarkers("4-3-3")).toHaveLength(11);
  });

  it("places 11 markers for 4-4-2", () => {
    expect(formationMarkers("4-4-2")).toHaveLength(11);
  });

  it("places 11 markers for 3-5-2", () => {
    expect(formationMarkers("3-5-2")).toHaveLength(11);
  });

  it("places 11 markers for 4-2-3-1", () => {
    expect(formationMarkers("4-2-3-1")).toHaveLength(11);
  });

  it("pins the goalkeeper in the back", () => {
    const m = formationMarkers("4-3-3");
    expect(m[0].x).toBeLessThan(0.1);
    expect(m[0].y).toBeCloseTo(0.5);
  });

  it("spreads a 4-man back line across the pitch", () => {
    const m = formationMarkers("4-3-3");
    const backLine = m.slice(1, 5);
    const ys = backLine.map((p) => p.y).sort((a, b) => a - b);
    expect(ys[0]).toBeLessThan(0.2);
    expect(ys[3]).toBeGreaterThan(0.8);
    // all at the same depth
    expect(new Set(backLine.map((p) => p.x)).size).toBe(1);
  });

  it("keeps all markers inside the pitch", () => {
    for (const f of ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1"]) {
      for (const p of formationMarkers(f)) {
        expect(p.x).toBeGreaterThanOrEqual(0);
        expect(p.x).toBeLessThanOrEqual(1);
        expect(p.y).toBeGreaterThanOrEqual(0);
        expect(p.y).toBeLessThanOrEqual(1);
      }
    }
  });
});
