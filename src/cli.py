"""CLI: generate a match and run the full pipeline."""

from __future__ import annotations

import json

from src.agents.director import DirectorAgent
from src.agents.recap import RecapAgent
from src.events.generator import MatchConfig, SyntheticMatchGenerator


def main() -> None:
    cfg = MatchConfig(match_id="match_001", seed=42)
    events = SyntheticMatchGenerator(cfg).generate()
    print(f"Generated {len(events)} events")

    director = DirectorAgent()
    result = director.run({"events": events})
    print("\n=== HEALTH ===")
    print(json.dumps(result["health"], indent=2))
    print("\n=== INSIGHTS ===")
    for ins in result["insights"]:
        print(f"  [{ins.type}] {ins.claim} (conf={ins.confidence})")
    print("\n=== COMMENTARY (first 5) ===")
    for c in (result["commentary"] or [])[:5]:
        print(f"  {c.minute}' {c.text}")
    print("\n=== RECAP ===")
    print(RecapAgent().run({"insights": result["insights"], "key_moments": result["key_moments"]}))


if __name__ == "__main__":
    main()
