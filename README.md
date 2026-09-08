# Vyapar Saarthi

Voice-first credit-readiness assistant for rural micro-entrepreneurs.

- **Voice conversation** (browser mic + speech synthesis) collects the business
  profile via a Pydantic AI agent - the LLM only extracts structured fields
  and phrases advisory commentary, it never computes a financial number.
- **Deterministic backend** (FastAPI, `backend/deterministic.py`) does every
  calculation: break-even, pricing check, working capital, the viability
  score breakdown, and scheme eligibility - all plain arithmetic and lookup
  tables against real district data for **Latur (MH)**, **Sitapur (UP)**, and
  **Indore (MP)**.

## Run it

**1. Backend** (FastAPI + Pydantic AI, managed with `uv`):

```bash
cd backend
cp .env.example .env   # then fill in AGENT_MODEL + the matching API key
uv run fastapi dev main.py --port 8000
```

`AGENT_MODEL` accepts any Pydantic AI model string - `google:gemini-2.0-flash`,
`groq:llama-3.3-70b-versatile`, `openai:gpt-4o-mini`, `anthropic:claude-haiku-4-5`,
`sarvam:sarvam-105b` (Sarvam AI's OpenAI-compatible endpoint, resolved in
`backend/agent.py`), etc. Set the matching `*_API_KEY` in `.env`.

**2. Frontend** (Vite + React):

```bash
npm install
npm run dev
```

Open the printed localhost URL. Voice intake needs a Chromium-based browser
(Web Speech API); a typed fallback is always available if the mic isn't
supported.

## Tests

`backend/deterministic.py` holds every financial calculation and rule in
the app, so it carries the most test coverage in the repo:

```bash
cd backend
uv run pytest
```

## Hyper-Local Business Viability Engine

Step 2 ("Will it work here?") also runs a six-dimension viability score on
top of the existing feasibility report, via `POST /api/viability/analyze`
(`backend/viability_engine.py` orchestrating `market_demand_engine.py`,
`competition_engine.py`, `location_engine.py`, `resource_engine.py`,
`risk_engine.py`, `financial_fit_engine.py`, `recommendation_engine.py`).
It is entirely deterministic - the LLM (`agent.py`'s
`get_viability_explainer_agent`) only narrates the already-computed result;
it cannot change a score, an EMI, or a scheme figure.

### Score formula

```
ViabilityScore =
    0.25 * MarketDemandScore
  + 0.20 * FinancialFitScore
  + 0.15 * CompetitionScore
  + 0.15 * LocationInfrastructureScore
  + 0.10 * ResourceAvailabilityScore
  + 0.15 * RiskSeasonalityScore
```

All weights, sub-weights, hard-constraint thresholds, and risk severity
bands live in one place - `backend/viability_config.py` - and are asserted
to sum to 1.0 at import time. They are **domain-informed baseline
weights**, not trained ML hyperparameters (see "Machine learning boundary"
below). Every response is tagged with `engine_version` and the exact
`weights_used` snapshot, so a future weight change never silently changes
how an already-returned result should be read.

```
Location + business input -> data providers (city_data.py, DEMO-labelled)
  -> six dimension engines -> confidence engine -> recommendation engine
  (hard safety gates) -> explainability breakdown -> optional AI narration
```

### The six dimensions

| Dimension | Weight | What it reads |
|---|---|---|
| Market Demand | 25% | Addressable consumers, target-customer fit (from `deterministic.get_market_reach`) |
| Financial Fit | 20% | Disposable income, business surplus, DSCR, post-loan surplus - deterministic arithmetic on the user's own optional inputs |
| Competition | 15% | Competitor density vs. this category's expected benchmark (reuses `deterministic.get_opportunity_analysis`) |
| Location & Infrastructure | 15% | Illustrative per-block infrastructure scores (`city_data.BLOCK_INFRASTRUCTURE`) |
| Resource Availability | 10% | The business category's resource checklist (`business_category_config.py`) - no availability data exists yet, so this is a checklist, not a fabricated score |
| Risk & Seasonality | 15% | Market-competition risk, price volatility, debt burden, plus qualitative seasonal/threat items from `city_data.THREAT_TEMPLATES` |

### Confidence and provenance - never fabricated

Every data point returned by `backend/data_providers.py` carries a
provenance tag: `VERIFIED_EXTERNAL`, `USER_PROVIDED`, `ESTIMATED`,
`ASSUMPTION`, `DEMO`, or `UNAVAILABLE`. **Today every non-user-provided
figure is `DEMO`** - `city_data.py` is illustrative static data for 3
districts (Latur, Sitapur, Indore) and 6 business categories, not a live
feed, and the engine never claims otherwise. `DATA_GOV_API_KEY` /
`AGMARKNET_API_KEY` are reserved, unused environment variables for a future
real provider (`data_providers.is_real_data_gov_available()` /
`is_real_agmarknet_available()`); while they're unset, every provider call
returns `status: "UNAVAILABLE"` for anything it can't source rather than
fabricating a value. A dimension with missing data gets a documented
neutral fallback score (50) and low confidence - never an invented "good"
or "bad" number - and is listed in `missing_information`.

### Hard safety gates

A weighted average can hide a dangerous number, so `recommendation_engine.py`
checks hard constraints first and can only ever **downgrade** a score-based
verdict, never upgrade one: `INSUFFICIENT_REPAYMENT_CAPACITY` (DSCR below
1.2), `HIGH_DEBT_BURDEN`, `INSUFFICIENT_EVIDENCE` (overall confidence below
40%), `CRITICAL_RESOURCE_GAP`, `OPERATIONALLY_UNVIABLE`. Recommendation
states: `PROCEED`, `PROCEED_WITH_CAUTION`, `VALIDATE_FIRST`, `REDUCE_SCALE`,
`HIGH_RISK`, `INSUFFICIENT_EVIDENCE`.

### Machine learning boundary

This is an **explainable weighted decision model + rule-based safety
engine + data confidence engine** - not a trained ML model. No historical
outcome data (business survival, repayment performance, defaults) exists
yet to train one. A future phase could calibrate the weights against real
outcomes (logistic regression / gradient boosting once that data exists),
but that would replace `viability_config.py`'s baseline weights only after
real validation - not before.

### Known limitations / Phase 3

- **No persistence, no auth** - the analyze endpoint is stateless, matching
  every other endpoint in this app today. Auditability comes from the
  self-contained `engine_version`/`weights_used` snapshot in each response,
  not a database record.
- **No live external data** - no API credentials are configured; every
  demand/competition/pricing/infrastructure figure is `city_data.py`'s
  illustrative data, always labelled `DEMO`.
- **6 business categories, 3 districts** - the same ones the rest of the app
  already services. Adding Poultry/Small Manufacturing/new districts without
  real backing data would just add categories that always read
  `UNAVAILABLE`.
- **No live GIS map** - the app has no mapping library and no per-competitor
  coordinates (only an aggregate count), so the "hyper-local map" is a
  labelled schematic (concentric rings + the real observed count), not an
  interactive map.
- **`speech_provider.py` is preparation only** - the voice intake still uses
  the browser's own Web Speech API; a backend Sarvam speech pipeline is not
  wired into any live endpoint this phase.
- **`CRITICAL_RESOURCE_GAP` and most individual risk sub-scores rarely/never
  fire** in this phase, because no real per-block resource/risk data source
  exists yet to confirm one - architecturally ready, honestly inert until
  real data exists.
