# Changelog - Hyper-Local Business Viability Engine (Phase 1)

## What existed before this change

- A Vite + React SPA (5-step wizard: Intake -> Feasibility -> Financial Plan
  -> Repayment Plan -> Summary), state in browser `localStorage`, no auth, no
  database.
- A FastAPI backend with zero live data fetching: `backend/city_data.py` is
  explicitly documented illustrative/static data for 3 districts (Latur,
  Sitapur, Indore), 15 blocks, 6 business categories.
- `backend/deterministic.py` already computed market reach, competitor
  mapping, opportunity analysis, SWOT, pricing (the "Feasibility Report"),
  plus margin-money financial structuring, EMI/repayment schedules, and
  working capital by phase.
- `backend/schemes.py` already ranked real government MSME schemes with an
  explainable weighted match score.
- `backend/agent.py` used Pydantic AI for voice intake, feasibility
  narration, and a tool-using feasibility advisor chat.

## What was added

**Backend (new files, `backend/`):**
`viability_config.py`, `normalization.py`, `geospatial.py`,
`business_category_config.py`, `data_providers.py`, `confidence_engine.py`,
`market_demand_engine.py`, `competition_engine.py`, `location_engine.py`,
`resource_engine.py`, `risk_engine.py`, `financial_fit_engine.py`,
`recommendation_engine.py`, `viability_engine.py` (orchestrator),
`speech_provider.py` (Sarvam adapter prep, not wired live),
`test_viability_engine.py` (33 tests covering weight-sum, score-range,
missing/partial/invalid data, DSCR + zero-division, hard constraints,
recommendation logic, opportunity gap, confidence calc, extreme/negative
inputs, unknown category).

**Backend (modified):**
- `city_data.py` - added illustrative `BLOCK_INFRASTRUCTURE` per block
  (documented DEMO data, same style as the file's existing content).
- `main.py` - new `POST /api/viability/analyze` endpoint.
- `agent.py` - new `get_viability_explainer_agent()` (narrates the
  deterministic result; never changes a number).
- `.env.example` - added unused, documented `DATA_GOV_API_KEY` /
  `AGMARKNET_API_KEY` placeholders for a future real data provider.

**Frontend:**
- `src/components/ViabilityDashboard.jsx` (new) - overall score,
  confidence, recommendation, six dimension tiles, explainability
  breakdown, opportunity gaps, named risks, an optional financial-details
  mini-form, financial-fit summary, hard-constraint warnings, a
  provenance/data-quality section, a labelled radius schematic (no new
  mapping dependency), missing-information list, and the required
  financial-safety disclaimer.
- `src/pages/FeasibilityReport.jsx` - renders `<ViabilityDashboard>` as a
  new section, reusing the page's existing district/block/business_type.
- `src/lib/api.js` - added `viabilityAnalyze()`.
- `src/context/AppContext.jsx` - extended the existing `operations` slice
  with 4 new optional fields (`monthlyHouseholdIncome`,
  `monthlyHouseholdExpenses`, `existingLoanEmi`, `expectedBusinessRevenue`);
  reused the existing `monthlyOperationalCost` field as `operating_expenses`
  rather than duplicating it.

**Docs:** README's new "Hyper-Local Business Viability Engine" section
(architecture, score formula, six dimensions, confidence/provenance model,
hard safety gates, ML boundary, known limitations).

## What was modified (behavior changes to existing code)

- None of the existing endpoints, pages, or calculations changed behavior.
  This phase is additive: one new endpoint, one new frontend section, one
  new data field (`BLOCK_INFRASTRUCTURE`) appended to `city_data.py`.

## Known deviations from the original request (and why)

- **No database/auth/RLS/Supabase** - none exist anywhere in this project;
  the analyze endpoint is stateless like every other endpoint today.
  Auditability is satisfied by embedding `engine_version` + the weight
  snapshot in every response instead.
- **6 business categories, not 8** - Poultry/Small Manufacturing have no
  backing data anywhere in the app; adding them now would create categories
  that always read `UNAVAILABLE`.
- **No live external API integration** - no credentials exist for
  data.gov.in/Agmarknet; only the `DemoProvider` path runs, every value
  tagged `DEMO`.
- **No interactive GIS map** - no mapping library exists in the project;
  added a labelled schematic instead of a new dependency.
- **Demo flow uses Latur/Ausa/Dairy/₹50,000**, not the request's own
  "Rajeana, Moga" example - that location isn't in any serviced district.
- **No rebrand to "Udyam Setu"** this phase - kept out of scope per explicit
  agreement, to keep this change focused on the engine.

## Remaining for Phase 3 (explicitly out of scope this phase)

- Real external data providers (data.gov.in, Agmarknet) once credentials
  exist - the adapter interface (`data_providers.py`) is ready for them.
- Server-side persistence/auth (analysis history, multi-user accounts) if
  the product later needs it.
- A live Sarvam speech-to-text/text-to-speech pipeline
  (`speech_provider.py` is interface-only).
- ML calibration of the viability weights against real historical outcomes
  (survival, repayment, default) once such data exists.
- Additional business categories/districts once real backing data exists
  for them.
