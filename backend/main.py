from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_ai.messages import ModelMessage

from agent import ConversationTurn, ProfilePatch, get_advisory_agent, get_feasibility_agent, get_intake_agent
from city_data import BUSINESS_TYPES, CITY_DATA
from deterministic import (
    calc_financial_structuring,
    calc_repayment_schedule,
    calc_working_capital_by_phase,
    generate_feasibility_report,
)

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
            {"key": key, "label": d["label"], "blocks": list(d["blocks"].keys()), "note": d["profile_note"]}
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
# Module 2: Smart Financial Calculator & Scheme Router (no LLM at all)
# ---------------------------------------------------------------------------

class FinancialStructuringRequest(BaseModel):
    available_margin_capital: float


@app.post("/api/financial-structuring")
def financial_structuring(req: FinancialStructuringRequest):
    return calc_financial_structuring(req.available_margin_capital)


class RepaymentScheduleRequest(BaseModel):
    principal: float
    annual_rate_pct: float
    tenure_months: int
    moratorium_months: int


@app.post("/api/repayment-schedule")
def repayment_schedule(req: RepaymentScheduleRequest):
    return calc_repayment_schedule(req.principal, req.annual_rate_pct, req.tenure_months, req.moratorium_months)


class WorkingCapitalPhaseRequest(BaseModel):
    monthly_operational_cost: float
    inventory_days: float
    receivable_days: float
    monthly_emi: float


@app.post("/api/working-capital")
def working_capital(req: WorkingCapitalPhaseRequest):
    return calc_working_capital_by_phase(req.monthly_operational_cost, req.inventory_days, req.receivable_days, req.monthly_emi)


# ---------------------------------------------------------------------------
# Module 1: Hyper-Local Business Feasibility Report (deterministic facts;
# optional LLM narration layered on top, never replacing the numbers)
# ---------------------------------------------------------------------------

class FeasibilityRequest(BaseModel):
    district: str
    block: str
    business_type: str


@app.post("/api/feasibility-report")
def feasibility_report(req: FeasibilityRequest):
    if req.district not in CITY_DATA:
        raise HTTPException(status_code=400, detail=f"Unknown district '{req.district}'")
    try:
        return generate_feasibility_report(req.district, req.block, req.business_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/feasibility-narrative")
async def feasibility_narrative(req: FeasibilityRequest):
    report = generate_feasibility_report(req.district, req.block, req.business_type)
    try:
        prompt = (
            f"Opportunity analysis facts: {report['opportunity_analysis']}\n"
            f"SWOT facts: {report['swot']}\n"
            f"Pricing facts: {report['product_market_value']}"
        )
        result = await get_feasibility_agent().run(prompt)
        return result.output
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Feasibility narration failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Advisory phrasing (LLM: commentary only, on numbers already computed above)
# ---------------------------------------------------------------------------

class AdvisoryRequest(BaseModel):
    profile: dict
    financial_structuring: dict
    repayment_schedule: dict
    working_capital: dict
    feasibility: dict


@app.post("/api/advisory")
async def advisory(req: AdvisoryRequest):
    try:
        prompt = (
            "Profile: " + str(req.profile) + "\n"
            "Financial structuring: " + str(req.financial_structuring) + "\n"
            "Repayment schedule: " + str(req.repayment_schedule) + "\n"
            "Working capital: " + str(req.working_capital) + "\n"
            "Feasibility report: " + str(req.feasibility)
        )
        result = await get_advisory_agent().run(prompt)
        return result.output
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Advisory call failed: {exc}") from exc


@app.get("/api/health")
def health():
    return {"status": "ok"}
