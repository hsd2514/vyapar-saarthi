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
