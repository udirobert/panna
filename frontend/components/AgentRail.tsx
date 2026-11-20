"use client";

type Props = {
  failed: string[];
  onToggleFail: (agent: string, failed: boolean) => void;
  onReset: () => void;
  resetArmed: boolean;
};

const AGENTS = [
  { id: "scout", label: "NUMBERS", role: "the swarm" },
  { id: "analyst", label: "CHALK", role: "the specialists" },
  { id: "commentator", label: "BOOTH", role: "the voice" },
];

export default function AgentRail({ failed, onToggleFail, onReset, resetArmed }: Props) {
  return (
    <div className="agent-rail">
      <div className="display" style={{ fontSize: 10, letterSpacing: "0.22em", color: "var(--muted)" }}>
        THE PITCH IS THE BLACKBOARD
      </div>
      {AGENTS.map((a) => {
        const isFailed = failed.includes(a.id);
        return (
          <button
            key={a.id}
            onClick={() => onToggleFail(a.id, !isFailed)}
            title={isFailed ? "click to recover" : "click to darken (failure demo)"}
            className={`agent-row${isFailed ? " failed" : ""}`}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              textAlign: "left",
              fontFamily: "inherit",
            }}
          >
            <span className="dot" />
            <span className="display" style={{ fontWeight: 700 }}>
              {a.label}
            </span>
            <span className="muted" style={{ letterSpacing: "0.02em" }}>
              {a.role}
              {isFailed ? " — dark" : ""}
            </span>
          </button>
        );
      })}
      <div
        className="agent-row"
        style={{ opacity: 0.9 }}
        title="the Verifier — deterministic recount code, not a model. It can't be darkened."
      >
        <span className="dot" style={{ background: "var(--gold)" }} />
        <span className="display" style={{ fontWeight: 700 }}>
          GATE
        </span>
        <span className="muted" style={{ letterSpacing: "0.02em" }}>
          the recount — code, not a model
        </span>
      </div>
      <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.5, marginTop: 2 }}>
        Specialists write chalk traces to the shared board. Darken one and its work is
        preserved — peers converge on the traces and finish it. The gate can't be
        darkened: every line is recounted from the event ledger before it may air.
      </div>
      <button
        className={`btn${resetArmed ? "" : ""}`}
        onClick={onReset}
        style={{ marginTop: 6, fontSize: 11 }}
      >
        {resetArmed ? "CONFIRM NEW MATCH" : "NEW FIXTURE"}
      </button>
    </div>
  );
}
