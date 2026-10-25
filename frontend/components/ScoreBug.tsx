"use client";

type Props = {
  home: string;
  away: string;
  score: { home: number; away: number };
  minute: number;
  second: number;
  playing: boolean;
  fullTime: boolean;
};

export default function ScoreBug({ home, away, score, minute, second, playing, fullTime }: Props) {
  const mm = String(minute).padStart(2, "0");
  const ss = String(second).padStart(2, "0");
  return (
    <div className="scorebug display">
      <div className="seg" style={{ borderLeft: "3px solid var(--home)" }}>
        <span className="team" style={{ color: "var(--home)" }}>
          {home.toUpperCase()}
        </span>
        <span className="score mono">{score.home}</span>
      </div>
      <div className="seg clock-seg">
        {fullTime ? (
          <span style={{ color: "var(--gold)", fontWeight: 800 }}>FT</span>
        ) : (
          <>
            {playing && <span className="live-dot" />}
            <span className="mono" style={{ color: "#e8f2ec" }}>
              {mm}:{ss}
            </span>
          </>
        )}
      </div>
      <div className="seg" style={{ borderRight: "3px solid var(--away)" }}>
        <span className="score mono">{score.away}</span>
        <span className="team" style={{ color: "var(--away)" }}>
          {away.toUpperCase()}
        </span>
      </div>
    </div>
  );
}
