# Post-hackathon strategy — where the opportunity actually is

> Researched 2026-11-20 (Tavily, sources linked inline). Companion to
> `docs/strategy.md` (which stays authoritative for the build) — this is
> where the thing could go *after* judging.

## The headline: regulation created the market

Two EU deadlines turn Panna's trust architecture from a demo feature into
**compliance infrastructure buyers legally need**:

- **EU AI Act Article 50 — enforceable 2 Aug 2026.** AI systems must mark
  generated content machine-readably; deployers must disclose AI-generated
  public-interest text *unless it has undergone human editorial review*.
  Fines up to €15M or 3% of worldwide turnover. Panna's Verifier +
  provenance chips + **producer console is literally the "human editorial
  review" exemption**, and the audit ledger (`src/audit.py`) is the
  disclosure record. Sources: [wasitaigenerated.com](https://www.wasitaigenerated.com/research/eu-ai-act-article-50-content-detection),
  [Paul Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-).

- **European Accessibility Act — in force since 2025.** Audiovisual
  streaming must provide audio description, ~98.5% accurate captions,
  accessible UIs. Live AD services ≈ $200M segment growing with
  enforcement. The deterministic AD feed (`src/events/audio.py`) + Speech
  client (`src/foundry/speech.py`) is compliance-shaped — and sports is
  chronically under-described: the long tail of matches will *never* get
  human describers, exactly where deterministic generation wins.
  Sources: [AVIXA](https://www.avixa.org/explore/articles/european-accessibility-act),
  [3PlayMedia](https://www.3playmedia.com/blog/european-accessibility-act-eaa).

## Opportunity table

| Opportunity | Evidence | Status in repo |
|---|---|---|
| **Sell the gate, not the broadcast.** Verifier + provenance + producer review + audit as an embeddable "AI content trust" API for sports-content generators | 92% of Fortune 500 require systematic factuality verification for LLM deployment; detection is "mandatory infrastructure" ([Galileo](https://galileo.ai/blog/best-hallucination-detection-tools-llm), [Dataiku](https://www.dataiku.com/blog/ai-hallucination-detection)) | All components exist; needs packaging + a real-data pilot |
| **Accessibility-as-a-service for the long tail** — deterministic AD + TTS for matches no one will ever describe | Broadcast precedents exist: IBM AI spoken commentary at Wimbledon, Bundesliga AI Live Ticker, MLB Scout Insights ([Murata](https://article.murata.com/en-us/article/generative-ai-technology-revamps-sports), [Blits](https://www.blits.ai/ai-use-cases/live-sports-commentary-generation)) | AD feed live; `/audio/speak` wired, needs `SPEECH_*` config |
| **Real data, real product** — the synthetic engine was the demo; swap licensed feeds into the Event Hubs seam | Sportmonks from €29/mo, API-Football $19/mo ([Sportmonks pricing](https://www.sportmonks.com/football-api/plans-pricing)) | Event Hubs ingestion staged; generator is seedable |
| **Microsoft for Startups Founders Hub** — up to $150k Azure credits + Foundry access + GTM | Already Azure-native + keyless Entra; cheapest possible onboarding ([Microsoft Learn](https://learn.microsoft.com/en-us/startups/standard-benefits/getting-started-mic)) | `azure/deploy.sh` + bicep ready |
| **Multilingual sports AI is a funded category** — Camb.ai raised on real-time translation | [SportsPro 2025 investment landscape](https://www.sportspro.com/insights/analysis/sports-tech-trends-investment-2025) | `?lang=` live behind `TRANSLATOR_*` config |

## The pitch, crystallized

*EU law now requires AI sports content to be disclosed and matches to be
audio-described. Panna is the verification + accessibility layer that makes
both compliant — verifiably.*

## Ranked next steps

1. **Article 50 readiness demo** — run the live pipeline against a licensed
   feed (Sportmonks €29/mo), produce the audit ledger + provenance output
   as a one-page "compliance readiness" artifact. *Adapter shipped*
   (`src/ingest/sportmonks.py`, `panna-run ingest`) — a real-payload pilot
   now needs only a `SPORTMONKS_API_TOKEN`.
2. **Founders Hub application** — funds Foundry + Translator + Speech on
   managed identity; the deploy path is already keyless.
3. **Package the gate** — extract `verifier.py` + `audit.py` +
   `feed.py`'s post-transform integrity checks into a licensable trust
   layer independent of the broadcast app.
4. **Speech live** — provision a Speech resource, export `SPEECH_REGION` +
   `SPEECH_AUTH=entra`, and `/audio/speak` goes real with no code change.
