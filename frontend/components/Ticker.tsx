"use client";
import { useEffect, useRef } from "react";
import type { Commentary } from "../lib/types";

export default function Ticker({ items }: { items: Commentary[] }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const recent = items.slice(-14);

  useEffect(() => {
    if (ref.current) ref.current.scrollLeft = ref.current.scrollWidth;
  }, [recent.length]);

  return (
    <div className="ticker" ref={ref} style={{ overflowX: "auto" }}>
      {recent.length === 0 && (
        <span className="ticker-item" style={{ color: "var(--muted)" }}>
          AWAITING KICKOFF — THE BOOTH IS QUIET
        </span>
      )}
      {recent.map((c, i) => (
        <span key={i} className={`ticker-item tone-${c.tone}${c.recovered ? " recovered" : ""}`}>
          <span className="stamp">{String(c.minute).padStart(2, "0")}&apos;</span>
          {c.text}
        </span>
      ))}
    </div>
  );
}
