# Microsoft for Startups — application draft

> Copy-paste answers for the Founders Hub application. Up to $150k Azure
> credits + Foundry access + GTM. Apply at startups.microsoft.com.
> Facts below are verified against the repo; claims marked *verify* need
> a number checked before submitting.

## Product (one-liner)

Panna is a verified AI broadcast layer for football: it generates live
commentary, tactical insight and audio description for matches, where
every line a model writes is recounted by deterministic code before it
may air — nothing unverified reaches the fan.

## Problem

Two EU deadlines make this infrastructure mandatory, not nice-to-have:

- **EU AI Act Article 50 (Aug 2026):** AI-generated content must be
  marked machine-readably; AI text shown to the public must be disclosed
  unless it passed human editorial review.
- **European Accessibility Act (in force):** audiovisual streaming must
  provide audio description and accessible interfaces.

Broadcasters and sports-data companies now need (a) generated content
that provably didn't hallucinate, (b) an audit trail of human review,
and (c) audio description for the long tail of matches that will never
afford human describers. None of that exists as a service today.

## Solution

- **Deterministic verification gate** — every line is recounted from the
  raw event ledger before it may air; invented stats, wrong minutes,
  fabricated scores, unattributed numbers, banned wording and causal
  speculation are all caught (10/10 planted attacks, 0% false positives).
- **Human review built in** — rejected lines queue for a producer
  console; approve/kill decisions are the Article 50 "editorial review"
  trail, persisted in a durable audit ledger.
- **Accessibility by construction** — audio description generated
  deterministically from event data (always on, no model), spoken via
  Azure AI Speech, localized into 4 languages via Azure AI Translator.
- **Honest degraded operation** — with no Foundry credentials the
  identical output shapes come from deterministic models, labelled as
  such; with no Translator/Speech configured the API reports it rather
  than faking it.

## Why Azure

- **Microsoft Agent Framework** — the analyst agent is a real MAF
  `agent_framework.Agent` with a six-function tool loop on Azure OpenAI.
- **Foundry GPT-5.4** — narration, insights, recap, every call span-traced.
- **Managed identity end-to-end** — `DefaultAzureCredential` mints Entra
  tokens for OpenAI, Translator and Speech; zero stored secrets.
- **Azure Container Apps** — httpConcurrency scaling, health probes,
  one-command Bicep deploy (`azure/deploy.sh`).
- **Translator + Speech** — multilingual feeds and spoken AD behind
  env-var config, fail-soft.

## Traction / proof

- Live demo: https://panna.sportwarren.com
- Microsoft Premier League "Inside the Game" hackathon submission
- Public repo with a judge-facing 3-minute verification path:
  red-team report (10/10 planted attacks caught), Article 50 readiness
  artifact (`panna-run compliance`), honest `/status` endpoint.
- Test suite: 86 backend tests; frontend builds clean.

## Ask

- Azure credits to run Foundry + Translator + Speech on managed identity.
- Introductions to sports-data/broadcast partners evaluating AI-content
  compliance ahead of the Article 50 deadline.

## Numbers to fill before submitting

- Matches processed / lines verified: *run `panna-run compliance` and
  cite the manifest counts*
- Team size / stage: *fill*
