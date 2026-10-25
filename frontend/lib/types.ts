export type EventFrame = {
  id: string;
  type: string;
  team: "Home" | "Away";
  player: string;
  minute: number;
  second: number;
  x: number;
  y: number;
  end_x: number | null;
  end_y: number | null;
  outcome: string | null;
  xg: number | null;
};

export type Detection = {
  id: string;
  event_id: string;
  minute: number;
  type: string;
  importance: number;
  description: string;
  evidence: string[];
  recovered?: boolean;
};

export type Insight = {
  id: string;
  type: string;
  claim: string;
  value: number | string;
  confidence: number;
  evidence: string[];
  agent: string;
  timestamp: string;
  reveal_minute: number;
  recovered?: boolean;
};

export type Commentary = {
  minute: number;
  second: number;
  text: string;
  tone: string;
  insight_ids: string[];
  recovered?: boolean;
};

export type GoalFrame = {
  minute: number;
  team: "Home" | "Away";
  player: string;
  home_score: number;
  away_score: number;
  xg: number | null;
  x: number;
  y: number;
};

export type MomentumPoint = {
  minute: number;
  home_cum: number;
  away_cum: number;
  home_danger: number;
  away_danger: number;
};

export type HealthEntry = { agent: string; status: string; error: string | null };

export type Snapshot = {
  match_id: string;
  seed: number;
  home_team: string;
  away_team: string;
  clock: number;
  minute: number;
  speed: number;
  playing: boolean;
  score: { home: number; away: number };
  failed: string[];
  health: Record<string, HealthEntry>;
  events: EventFrame[];
  key_moments: Detection[];
  insights: Insight[];
  commentary: Commentary[];
  momentum: {
    minutes: number[];
    home_cum: number[];
    away_cum: number[];
    home_danger: number[];
    away_danger: number[];
  };
};

export type MatchState = {
  snapshot: Snapshot | null;
  clock: number;
  minute: number;
  second: number;
  playing: boolean;
  speed: number;
  score: { home: number; away: number };
  failed: string[];
  eventById: Record<string, EventFrame>;
  recentEvents: EventFrame[];
  detections: Detection[];
  insights: Insight[];
  commentary: Commentary[];
  momentum: MomentumPoint[];
  lastGoal: GoalFrame | null;
  goalFlashUntil: number;
};

export const initialState: MatchState = {
  snapshot: null,
  clock: 0,
  minute: 0,
  second: 0,
  playing: false,
  speed: 60,
  score: { home: 0, away: 0 },
  failed: [],
  eventById: {},
  recentEvents: [],
  detections: [],
  insights: [],
  commentary: [],
  momentum: [],
  lastGoal: null,
  goalFlashUntil: 0,
};

export type Lens = "all" | "tactics" | "attack" | "story";

export const LENSES: { id: Lens; label: string }[] = [
  { id: "all", label: "FULL MATCH" },
  { id: "tactics", label: "TACTICAL" },
  { id: "attack", label: "ATTACK" },
  { id: "story", label: "STORY" },
];
