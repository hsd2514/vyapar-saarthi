from __future__ import annotations

import asyncio
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_ai.messages import ModelMessage

from agent import (
    ConversationTurn,
    ProfilePatch,
    get_advisory_agent,
    get_feasibility_advisor_agent,
    get_financial_advisor_agent,
    get_intake_agent,
)
from city_data import BUSINESS_TYPES, CITY_DATA
from deterministic import (
    calc_financial_structuring,
    calc_repayment_schedule,
    calc_working_capital_by_phase,
    generate_feasibility_report,
)
from schemes import match_schemes

# ---------------------------------------------------------------------------
# In-memory share store
# Each entry: { "payload": dict, "created_at": float (unix timestamp) }
# Lifetime: 24 hours; cleaned up every 30 minutes by the background task.
# Cleared on server restart — this is intentional for the demo; see README.
# ---------------------------------------------------------------------------

_SHARE_STORE: dict[str, dict[str, Any]] = {}
_SHARE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
_CLEANUP_INTERVAL_SECONDS = 30 * 60  # 30 minutes


async def _cleanup_expired_shares() -> None:
    """Background task: remove share entries older than _SHARE_TTL_SECONDS."""
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        cutoff = time.time() - _SHARE_TTL_SECONDS
        expired = [sid for sid, entry in _SHARE_STORE.items() if entry["created_at"] < cutoff]
        for sid in expired:
            _SHARE_STORE.pop(sid, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_expired_shares())
    yield
    task.cancel()


app = FastAPI(title="Vyapar Saarthi API", lifespan=lifespan)

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
    capitalise_moratorium_interest: bool = False


@app.post("/api/repayment-schedule")
def repayment_schedule(req: RepaymentScheduleRequest):
    return calc_repayment_schedule(
        req.principal,
        req.annual_rate_pct,
        req.tenure_months,
        req.moratorium_months,
        req.capitalise_moratorium_interest,
    )


@app.get("/api/scheme-match")
def scheme_match(project_cost: float, business_type: str | None = None):
    """Ranks real government MSME credit schemes (PMEGP, Mudra tiers,
    Stand-Up India) plus this tool's own margin-money scheme against the
    given project cost, using the explainable weighted rules engine in
    schemes.py - no LLM involved. Each result carries its official portal
    link so the user can go apply/verify directly."""
    if project_cost <= 0:
        raise HTTPException(status_code=400, detail="project_cost must be positive")
    return {"project_cost": project_cost, "matches": match_schemes(project_cost, business_type)}


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



@app.get("/api/feasibility-report/compare")
def feasibility_compare(district: str, block: str):
    """Returns feasibility reports for all 6 business types for the given
    district + block in one shot. Used by the frontend 'Compare All Categories'
    panel so it can show all six side-by-side without 6 separate round trips."""
    if district not in CITY_DATA:
        raise HTTPException(status_code=400, detail=f"Unknown district '{district}'")
    by_type: dict = {}
    for bt_entry in BUSINESS_TYPES:
        bt = bt_entry["value"]
        try:
            by_type[bt] = generate_feasibility_report(district, block, bt)
        except ValueError:
            by_type[bt] = None
    return {"district": district, "block": block, "by_type": by_type}


@app.get("/api/feasibility-report/compare-blocks")
def feasibility_compare_blocks(district: str, business_type: str):
    """Returns feasibility reports for the same business category across
    every block in the given district, in one shot. This is the other half
    of issue #8's "what if" ask - #16's comparison panel covers switching
    business category for a fixed block; this covers switching block for a
    fixed business category."""
    if district not in CITY_DATA:
        raise HTTPException(status_code=400, detail=f"Unknown district '{district}'")
    by_block: dict = {}
    for block_name in CITY_DATA[district]["blocks"]:
        try:
            by_block[block_name] = generate_feasibility_report(district, block_name, business_type)
        except ValueError:
            by_block[block_name] = None
    return {"district": district, "business_type": business_type, "by_block": by_block}


class FeasibilityChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # raw pydantic-ai message dicts round-tripped from the client - this IS the agent's memory
    district: str
    block: str
    business_type: str


class FeasibilityChatResponse(BaseModel):
    reply_text: str
    history: list[dict]


@app.post("/api/feasibility-agent/chat", response_model=FeasibilityChatResponse)
async def feasibility_agent_chat(req: FeasibilityChatRequest):
    """A real tool-using, memory-carrying conversation with the feasibility
    advisor. The agent calls into deterministic.py's section functions
    itself (see agent.py's get_feasibility_advisor_agent) rather than being
    handed a pre-baked report - so it can answer follow-up and 'what if'
    questions by actually calling those functions again with new
    parameters, never by guessing."""
    try:
        message_history: list[ModelMessage] = (
            ModelMessagesTypeAdapter.validate_python(req.history) if req.history else []
        )
        prompt = (
            f"Entrepreneur's actual profile: district={req.district}, block={req.block}, business_type={req.business_type}\n"
            f"Entrepreneur says: {req.message}"
        )
        result = await get_feasibility_advisor_agent().run(prompt, message_history=message_history)
        new_history = ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")
        return FeasibilityChatResponse(reply_text=result.output, history=new_history)
    except Exception as exc:  # pragma: no cover - surfaced to the UI as a toast
        raise HTTPException(status_code=502, detail=f"Feasibility advisor call failed: {exc}") from exc


class FinancialChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # raw pydantic-ai message dicts round-tripped from the client - this IS the agent's memory


class FinancialChatResponse(BaseModel):
    reply_text: str
    history: list[dict]


@app.post("/api/financial-advisor/chat", response_model=FinancialChatResponse)
async def financial_advisor_chat(req: FinancialChatRequest):
    """A tool-using, memory-carrying conversation scoped to Module 2 (financial
    structuring, repayment schedule, working capital, scheme matching). The
    agent calls into deterministic.py and schemes.py itself rather than being
    handed pre-baked numbers, so it can answer 'what if' and 'why this scheme'
    questions by actually recomputing, never by guessing."""
    try:
        message_history: list[ModelMessage] = (
            ModelMessagesTypeAdapter.validate_python(req.history) if req.history else []
        )
        result = await get_financial_advisor_agent().run(req.message, message_history=message_history)
        new_history = ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")
        return FinancialChatResponse(reply_text=result.output, history=new_history)
    except Exception as exc:  # pragma: no cover - surfaced to the UI as a toast
        raise HTTPException(status_code=502, detail=f"Financial advisor call failed: {exc}") from exc


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


from city_data import get_block

@app.get("/api/contacts")
def get_contacts(district: str, block: str):
    b = get_block(district, block)
    if not b:
        raise HTTPException(status_code=400, detail="Unknown district or block")
    return {"contacts": b.get("contacts", [])}


# ---------------------------------------------------------------------------
# Shareable read-only summary link
#
# Storage: in-memory Python dict. Cleared on server restart (intentional for
# demo). Entries expire after 24 hours; a background task prunes them every
# 30 minutes.
#
# Known limitations (out of scope for this demo):
#  - No authentication: anyone with the URL can read the plan.
#  - No real persistence: restarting the server invalidates all links.
#  - No PII hardening: the payload contains financial details the user typed.
# ---------------------------------------------------------------------------

class SharePayload(BaseModel):
    """The compiled summary snapshot sent by the frontend when creating a link."""
    profile: dict
    operations: dict
    structuring: dict | None = None
    schedule: dict | None = None
    working_capital: dict | None = None
    feasibility: dict | None = None
    advisory: dict | None = None
    contacts: list = []


class ShareCreateResponse(BaseModel):
    share_id: str
    share_url: str
    expires_at: float  # Unix timestamp


@app.post("/api/summary/share", response_model=ShareCreateResponse)
def create_share(payload: SharePayload, frontend_origin: str = "http://localhost:5173"):
    """
    Store the compiled summary payload and return a shareable link.

    The link is valid for 24 hours from creation. Data is stored in memory
    and will be lost if the server restarts (acceptable for a demo).
    """
    share_id = secrets.token_urlsafe(8)
    created_at = time.time()
    expires_at = created_at + _SHARE_TTL_SECONDS
    _SHARE_STORE[share_id] = {
        "payload": payload.model_dump(),
        "created_at": created_at,
        "expires_at": expires_at,
    }
    # The shareable URL uses the HashRouter fragment format (#/view/<id>)
    share_url = f"{frontend_origin}/#/view/{share_id}"
    return ShareCreateResponse(share_id=share_id, share_url=share_url, expires_at=expires_at)


@app.get("/api/summary/share/{share_id}")
def get_share(share_id: str):
    """
    Retrieve a previously stored summary snapshot by its share ID.
    Returns 404 if the ID is unknown or has expired and been cleaned up.
    """
    entry = _SHARE_STORE.get(share_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Share link not found or has expired.")
    # Lazy expiry check (safety net in case cleanup hasn't run yet)
    if time.time() > entry["expires_at"]:
        _SHARE_STORE.pop(share_id, None)
        raise HTTPException(status_code=404, detail="Share link has expired.")
    return {
        **entry["payload"],
        "expires_at": entry["expires_at"],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
