from __future__ import annotations

from datetime import date
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_ai.messages import ModelMessage

from agent import ConversationTurn, ProfilePatch, get_advisory_agent, get_intake_agent
from city_data import BUSINESS_TYPES, CITY_DATA
from deterministic import (
    calc_break_even,
    calc_pricing_check,
    calc_working_capital,
    compute_viability_score,
    match_schemes,
)
from weather import get_weather_advisory

app = FastAPI(title="Vyapar Saarthi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------

@app.get("/api/cities")
def get_cities():
    return {
        "districts": [
            {"key": key, "label": d["label"], "blocks": d["blocks"], "note": d["profile_note"]}
            for key, d in CITY_DATA.items()
        ],
        "business_types": BUSINESS_TYPES,
    }


# ---------------------------------------------------------------------------
# Voice intake conversation (LLM: conversation + extraction only)
# ---------------------------------------------------------------------------

class TurnRequest(BaseModel):
    message: str
    history: list[dict] = []  # raw pydantic-ai message dicts round-tripped from the client
    profile_so_far: ProfilePatch = ProfilePatch()


class TurnResponse(BaseModel):
    reply_text: str
    profile: ProfilePatch
    done: bool
    history: list[dict]


@app.post("/api/agent/turn", response_model=TurnResponse)
async def agent_turn(req: TurnRequest):
    try:
        message_history: list[ModelMessage] = (
            ModelMessagesTypeAdapter.validate_python(req.history) if req.history else []
        )
        prompt = (
            f"Known so far: {req.profile_so_far.model_dump_json()}\n"
            f"Speaker just said: {req.message}"
        )
        result = await get_intake_agent().run(prompt, message_history=message_history)
        turn: ConversationTurn = result.output
        new_history = ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")
        return TurnResponse(
            reply_text=turn.reply_text,
            profile=turn.profile,
            done=turn.done,
            history=new_history,
        )
    except Exception as exc:  # pragma: no cover - surfaced to the UI as a toast
        raise HTTPException(status_code=502, detail=f"Agent call failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Deterministic calculators + viability + schemes (no LLM involved at all)
# ---------------------------------------------------------------------------

class CalcRequest(BaseModel):
    fixed_costs: float
    variable_cost_per_unit: float
    price_per_unit: float


@app.post("/api/calc/break-even")
def break_even(req: CalcRequest):
    return calc_break_even(req.fixed_costs, req.variable_cost_per_unit, req.price_per_unit)


class PricingRequest(BaseModel):
    unit_cost: float
    desired_margin_pct: float
    market_price: float


@app.post("/api/calc/pricing")
def pricing(req: PricingRequest):
    return calc_pricing_check(req.unit_cost, req.desired_margin_pct, req.market_price)


class WorkingCapitalRequest(BaseModel):
    monthly_expenses: float
    inventory_days: float
    receivable_days: float


@app.post("/api/calc/working-capital")
def working_capital(req: WorkingCapitalRequest):
    return calc_working_capital(req.monthly_expenses, req.inventory_days, req.receivable_days)


class ViabilityRequest(BaseModel):
    district: str
    business_type: str


@app.post("/api/viability")
def viability(req: ViabilityRequest):
    if req.district not in CITY_DATA:
        raise HTTPException(status_code=400, detail=f"Unknown district '{req.district}'")
    return compute_viability_score(req.district, req.business_type, date.today())


class SchemesRequest(BaseModel):
    monthly_revenue: float
    years_in_operation: float
    business_type: str


@app.post("/api/schemes")
def schemes(req: SchemesRequest):
    return {"schemes": match_schemes(req.monthly_revenue, req.years_in_operation, req.business_type)}


# ---------------------------------------------------------------------------
# Real-time weather advisory (Open-Meteo, free, no key, fully deterministic)
# ---------------------------------------------------------------------------

@app.get("/api/weather-advisory")
def weather_advisory(district: str, business_type: str):
    """
    Fetch a 3-day forecast from Open-Meteo for the given district and apply
    the deterministic stocking-advice rule table in weather.py.

    Returns raw forecast values alongside triggered rules so the UI can
    show the exact numbers the advice is based on (auditable, like everything
    else in this app). Returns {"available": false} gracefully if the network
    call fails - the rest of the report still works.
    """
    if district not in CITY_DATA:
        raise HTTPException(status_code=400, detail=f"Unknown district '{district}'")
    coords = CITY_DATA[district].get("coords")
    if not coords:
        return {"available": False, "reason": f"No coordinates configured for district '{district}'."}
    return get_weather_advisory(
        lat=coords["lat"],
        lon=coords["lon"],
        district_label=CITY_DATA[district]["label"],
        business_type=business_type,
    )


# ---------------------------------------------------------------------------
# Advisory phrasing (LLM: commentary only, on numbers already computed above)
# ---------------------------------------------------------------------------

class AdvisoryRequest(BaseModel):
    profile: dict
    break_even: dict
    pricing: dict
    working_capital: dict
    viability: dict
    matched_schemes: list[dict]


@app.post("/api/advisory")
async def advisory(req: AdvisoryRequest):
    try:
        prompt = (
            "Profile: " + str(req.profile) + "\n"
            "Break-even: " + str(req.break_even) + "\n"
            "Pricing check: " + str(req.pricing) + "\n"
            "Working capital: " + str(req.working_capital) + "\n"
            "Viability score: " + str(req.viability) + "\n"
            "Matched schemes: " + str(req.matched_schemes)
        )
        result = await get_advisory_agent().run(prompt)
        return result.output
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Advisory call failed: {exc}") from exc


@app.get("/api/health")
def health():
    return {"status": "ok"}
