import { describe, expect, it } from "vitest";
import { toEventFrame } from "../useMatchStream";

/**
 * The board reads only flat EventFrame fields. Both wire shapes must normalize
 * to the same frame: the REST ledger (nested Pydantic) and the SSE stream (flat).
 */
describe("toEventFrame", () => {
  it("normalizes a nested REST event", () => {
    const rest = {
      id: "evt_0001",
      type: "pass",
      team: "Home",
      player: "P3",
      minute: 12,
      second: 30,
      position: { x: 55.5, y: 22.1 },
      end_location: { x: 71.2, y: 30.0 },
      outcome: "success",
      metadata: { pass_type: "short", distance: 16.7 },
    };
    const f = toEventFrame(rest);
    expect(f.id).toBe("evt_0001");
    expect(f.x).toBe(55.5);
    expect(f.y).toBe(22.1);
    expect(f.end_x).toBe(71.2);
    expect(f.end_y).toBe(30.0);
    expect(f.outcome).toBe("success");
    expect(f.xg).toBeNull();
  });

  it("normalizes a flat SSE frame", () => {
    const sse = {
      id: "evt_0900",
      type: "shot",
      team: "Away",
      player: "P9",
      minute: 88,
      second: 5,
      x: 104.3,
      y: 38.8,
      outcome: "on_target",
      xg: 0.31,
    };
    const f = toEventFrame(sse);
    expect(f.x).toBe(104.3);
    expect(f.y).toBe(38.8);
    expect(f.end_x).toBeNull();
    expect(f.end_y).toBeNull();
    expect(f.xg).toBe(0.31);
  });

  it("prefers nested position over flat x when both present", () => {
    const hybrid = {
      id: "evt_0002",
      type: "tackle",
      team: "Home",
      player: "P6",
      minute: 40,
      second: 0,
      x: 0, // stale flat default
      position: { x: 61.0, y: 12.0 },
      outcome: "success",
      metadata: {},
    };
    const f = toEventFrame(hybrid);
    expect(f.x).toBe(61.0);
    expect(f.y).toBe(12.0);
  });
});
