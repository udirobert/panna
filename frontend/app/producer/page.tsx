"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { decide, getProducerBoard, seedBadClaim, type BoardRow } from "../../lib/api";

const STATUS_COLOR: Record<string, string> = {
  aired: "var(--ok)",
  approved: "var(--ok)",
  queued: "var(--muted)",
  held: "var(--warn)",
  killed: "var(--down)",
};

function Row({ r, onDecide }: { r: BoardRow; onDecide: (id: string, d: "approve" | "kill") => void }) {
  const [open, setOpen] = useState(false);
  const color = STATUS_COLOR[r.air_status] ?? "var(--muted)";
  return (
    <div
      className="strip"
      style={{ borderLeft: `3px solid ${color}`, padding: "8px 10px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
        <span style={{ fontSize: 13.5, lineHeight: 1.35 }}>{r.text}</span>
        <span className="display" style={{ color, fontSize: 10, letterSpacing: "0.12em", whiteSpace: "nowrap" }}>
          {r.air_status.toUpperCase()}
        </span>
      </div>
      <div style={{ marginTop: 4, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span className="muted display" style={{ fontSize: 10, letterSpacing: "0.1em" }}>
          {r.kind.toUpperCase()} · {Math.floor(r.at / 60)}' · {r.verdict ?? "—"}
        </span>
        {r.reason && (
          <span style={{ color: "var(--warn)", fontSize: 11 }}>{r.reason}</span>
        )}
        {r.checks.length > 0 && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            style={{
              background: "none",
              border: "1px solid var(--chalk-dim)",
              color: "var(--chalk)",
              borderRadius: 4,
              padding: "0 6px",
              fontSize: 10,
              cursor: "pointer",
            }}
          >
            why?
          </button>
        )}
        {r.air_status === "held" && (
          <>
            <button
              type="button"
              onClick={() => onDecide(r.id, "approve")}
              style={{
                background: "var(--ok)",
                border: "none",
                color: "#04110b",
                borderRadius: 4,
                padding: "2px 10px",
                fontSize: 11,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              APPROVE → AIR
            </button>
            <button
              type="button"
              onClick={() => onDecide(r.id, "kill")}
              style={{
                background: "none",
                border: "1px solid var(--down)",
                color: "var(--down)",
                borderRadius: 4,
                padding: "2px 10px",
                fontSize: 11,
                cursor: "pointer",
              }}
            >
              KILL
            </button>
          </>
        )}
      </div>
      {open && (
        <div
          style={{
            marginTop: 6,
            padding: "6px 8px",
            background: "rgba(0,0,0,0.25)",
            borderRadius: 4,
            fontSize: 11,
            lineHeight: 1.5,
          }}
        >
          {r.checks.map((c, i) => (
            <div key={i} className={c.ok ? "muted" : ""} style={c.ok ? {} : { color: "var(--down)" }}>
              {c.ok ? "✓" : "✕"} {c.detail}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProducerConsole() {
  const params = useSearchParams();
  const matchId = params.get("match") || "match_001";
  const [board, setBoard] = useState<BoardRow[]>([]);
  const [summary, setSummary] = useState<{ checked: number; verified: number; repaired: number; rejected: number } | null>(null);
  const [clock, setClock] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [planted, setPlanted] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const b = await getProducerBoard(matchId);
      setBoard(b.items);
      setSummary(b.verification);
      setClock(b.clock);
      setError(null);
    } catch {
      setError("No active session — open the match on the home page first.");
    }
  }, [matchId]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  const onDecide = useCallback(
    async (id: string, d: "approve" | "kill") => {
      await decide(matchId, id, d);
      refresh();
    },
    [matchId, refresh],
  );

  const plant = useCallback(async () => {
    const out = await seedBadClaim(matchId);
    const held = Object.values(out.verdicts ?? {}).filter(
      (v) => (v as { status?: string }).status === "rejected",
    ).length;
    setPlanted(
      `Planted ${(out.planted ?? []).length} false lines — the gate rejected ${held}. They're waiting in HOLD below.`,
    );
    setTimeout(refresh, 800);
  }, [matchId, refresh]);

  const held = board.filter((r) => r.air_status === "held");
  const rest = board.filter((r) => r.air_status !== "held");

  return (
    <main style={{ maxWidth: 860, margin: "0 auto", padding: "28px 16px" }}>
      <div className="display" style={{ letterSpacing: "0.16em", fontSize: 11, color: "var(--muted)" }}>
        PANNA · PRODUCTION STUDIO
      </div>
      <h1 style={{ fontSize: 26, margin: "6px 0 2px" }}>Producer console — {matchId}</h1>
      <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
        Every line is recounted from the event ledger before it may air. Rejects
        fail closed into HOLD; nothing unverified reaches the screen.
      </p>

      {summary && (
        <div style={{ display: "flex", gap: 18, margin: "12px 0", fontSize: 12 }} className="display">
          <span>CHECKED {summary.checked}</span>
          <span style={{ color: "var(--ok)" }}>VERIFIED {summary.verified}</span>
          <span style={{ color: "var(--warn)" }}>REPAIRED {summary.repaired}</span>
          <span style={{ color: "var(--down)" }}>REJECTED {summary.rejected}</span>
          <span className="muted">clock {Math.floor(clock / 60)}'</span>
        </div>
      )}

      <button
        type="button"
        onClick={plant}
        style={{
          background: "none",
          border: "1px dashed var(--warn)",
          color: "var(--warn)",
          borderRadius: 4,
          padding: "6px 14px",
          fontSize: 12,
          letterSpacing: "0.08em",
          cursor: "pointer",
        }}
      >
        ⚠ SEED A BAD CLAIM (red-team demo)
      </button>
      {planted && <p style={{ fontSize: 12, color: "var(--warn)" }}>{planted}</p>}

      {error && <p style={{ color: "var(--down)", fontSize: 13 }}>{error}</p>}

      {held.length > 0 && (
        <>
          <h2 className="display" style={{ fontSize: 13, letterSpacing: "0.14em", color: "var(--warn)", marginTop: 22 }}>
            HOLD QUEUE — {held.length}
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {held.map((r) => (
              <Row key={r.id} r={r} onDecide={onDecide} />
            ))}
          </div>
        </>
      )}

      <h2 className="display" style={{ fontSize: 13, letterSpacing: "0.14em", color: "var(--muted)", marginTop: 22 }}>
        AIR LOG — {rest.length}
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {rest.map((r) => (
          <Row key={r.id} r={r} onDecide={onDecide} />
        ))}
      </div>
    </main>
  );
}

export default function Page() {
  return (
    <Suspense>
      <ProducerConsole />
    </Suspense>
  );
}
