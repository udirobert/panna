"use client";
import { useEffect, useRef } from "react";
import type { Detection, EventFrame, Lens } from "../lib/types";

// Boids "Numbers" swarm: lightweight detectors drifting over the pitch,
// attracted to recent signal, converging into quorum rings on detections.
const N = 64;
const W = 120;
const H = 80;

type Boid = { x: number; y: number; vx: number; vy: number; hue: "home" | "away" };
type Target = { x: number; y: number; w: number };

const HOME = [56, 189, 248];
const AWAY = [245, 158, 11];

function makeBoids(): Boid[] {
  return Array.from({ length: N }, (_, i) => ({
    x: Math.random() * W,
    y: Math.random() * H,
    vx: (Math.random() - 0.5) * 8,
    vy: (Math.random() - 0.5) * 8,
    hue: i % 2 === 0 ? "home" : "away",
  }));
}

type Props = {
  events: EventFrame[];
  detections: Detection[];
  clock: number;
  failedAgents: string[];
  lens: Lens;
  spotlightActive: boolean;
};

export default function Swarm({
  events,
  detections,
  clock,
  failedAgents,
  lens,
  spotlightActive,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef({ boids: makeBoids(), events, detections, clock, failedAgents, lens, spotlightActive });
  stateRef.current = { boids: stateRef.current.boids, events, detections, clock, failedAgents, lens, spotlightActive };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let last = performance.now();

    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width * window.devicePixelRatio;
        canvas.height = rect.height * window.devicePixelRatio;
      }
    };
    resize();
    window.addEventListener("resize", resize);

    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const { boids, events: evs, detections: dets, clock: clk, failedAgents: failed, lens: ln, spotlightActive: spot } =
        stateRef.current;

      // attraction targets: recent events weighted by recency + active detections
      const targets: Target[] = [];
      const recentWindow = 240; // last 4 match-minutes
      for (const e of evs) {
        const t = e.minute * 60 + e.second;
        const age = clk - t;
        if (age < 0 || age > recentWindow) continue;
        const recency = 1 - age / recentWindow;
        const w =
          (e.type === "goal" ? 5 : e.type === "shot" ? 3 : e.type === "pass" ? 0.8 : 1.4) * recency;
        targets.push({ x: e.x, y: e.y, w });
      }
      for (const d of dets.slice(-3)) {
        const ev = evs.find((e) => e.id === d.event_id);
        if (ev) targets.push({ x: ev.x, y: ev.y, w: 4 * d.importance });
      }

      const scoutDown = failed.includes("scout");
      const dimmed = spot || ln === "story";
      const alphaMul = dimmed ? 0.16 : scoutDown ? 0.25 : 1;

      // boid rules
      for (const b of boids) {
        let sx = 0, sy = 0, ax = 0, ay = 0, cx = 0, cy = 0, n = 0;
        for (const o of boids) {
          if (o === b) continue;
          const dx = o.x - b.x;
          const dy = o.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 > 64) continue;
          const d = Math.sqrt(d2) || 0.001;
          if (d < 3) {
            sx -= (dx / d) * (3 - d);
            sy -= (dy / d) * (3 - d);
          }
          ax += o.vx;
          ay += o.vy;
          cx += o.x;
          cy += o.y;
          n++;
        }
        let fx = sx * 2.2;
        let fy = sy * 2.2;
        if (n > 0) {
          fx += (ax / n - b.vx) * 0.12 + (cx / n - b.x) * 0.05;
          fy += (ay / n - b.vy) * 0.12 + (cy / n - b.y) * 0.05;
        }
        // wander
        fx += (Math.random() - 0.5) * 4;
        fy += (Math.random() - 0.5) * 4;
        // signal attraction
        if (!scoutDown && targets.length) {
          let best: Target | null = null;
          let bestScore = -1;
          for (const t of targets) {
            const dx = t.x - b.x;
            const dy = t.y - b.y;
            const d = Math.sqrt(dx * dx + dy * dy) || 1;
            const score = t.w / (d * 0.15 + 1);
            if (score > bestScore) {
              bestScore = score;
              best = t;
            }
          }
          if (best) {
            const dx = best.x - b.x;
            const dy = best.y - b.y;
            const d = Math.sqrt(dx * dx + dy * dy) || 1;
            const pull = Math.min(2.4, bestScore * 0.9);
            fx += (dx / d) * pull * 3;
            fy += (dy / d) * pull * 3;
          }
        }
        b.vx += fx * dt * 3;
        b.vy += fy * dt * 3;
        const sp = Math.sqrt(b.vx * b.vx + b.vy * b.vy) || 1;
        const maxSp = scoutDown ? 4 : 11;
        if (sp > maxSp) {
          b.vx = (b.vx / sp) * maxSp;
          b.vy = (b.vy / sp) * maxSp;
        }
        b.x += b.vx * dt;
        b.y += b.vy * dt;
        // soft bounds
        if (b.x < 0) b.vx += 2;
        if (b.x > W) b.vx -= 2;
        if (b.y < 0) b.vy += 2;
        if (b.y > H) b.vy -= 2;
      }

      // draw
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      const px = w / W;
      const py = h / H;
      for (const b of boids) {
        const rgb = b.hue === "home" ? HOME : AWAY;
        const spd = Math.sqrt(b.vx * b.vx + b.vy * b.vy);
        const a = (0.25 + Math.min(0.6, spd / 18)) * alphaMul;
        ctx.beginPath();
        ctx.fillStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`;
        ctx.arc(b.x * px, b.y * py, 1.6 * window.devicePixelRatio, 0, Math.PI * 2);
        ctx.fill();
        // motion trail
        ctx.beginPath();
        ctx.strokeStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a * 0.35})`;
        ctx.lineWidth = 0.7 * window.devicePixelRatio;
        ctx.moveTo(b.x * px, b.y * py);
        ctx.lineTo((b.x - b.vx * 0.6) * px, (b.y - b.vy * 0.6) * py);
        ctx.stroke();
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    />
  );
}
