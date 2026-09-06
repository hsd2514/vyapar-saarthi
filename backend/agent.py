"""The only place an LLM is called. Its job is strictly bounded to two
things: (1) holding a natural conversation to collect the three inputs this
tool needs - location, available margin capital, business category - into a
structured object, and (2) narrating the feasibility report / advisory
commentary on top of numbers that were already computed deterministically
elsewhere (deterministic.py). The agent never computes a financial figure
itself - it only reads numbers handed to it and talks about them.
"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent

load_dotenv()

AGENT_MODEL = os.environ.get("AGENT_MODEL", "google:gemini-2.0-flash")

BUSINESS_TYPE_VALUES = ("vendor", "dairy", "textiles", "retail", "handicrafts", "food_stall")
DISTRICT_VALUES = ("latur", "sitapur", "indore")


class ProfilePatch(BaseModel):
    """Fields the agent has confidently extracted so far. Every field is
    optional - only fill in what the speaker has actually said."""

    business_type: Literal[BUSINESS_TYPE_VALUES] | None = Field(
        default=None, description="One of the fixed business categories, inferred from what the speaker described."
    )
    district: Literal[DISTRICT_VALUES] | None = Field(
        default=None, description="Must be one of the three serviced districts: latur, sitapur, indore."
    )
    block: str | None = Field(default=None, description="Block/tehsil name within the district, if mentioned.")
    village: str | None = Field(default=None, description="Village name within the block, if mentioned (optional).")
    available_margin_capital: float | None = Field(
        default=None, description="The rupee amount the speaker says they already have saved/available to contribute as their 10% margin money."
    )


class ConversationTurn(BaseModel):
    """One turn of the voice agent's reply."""

    reply_text: str = Field(description="What the agent should say next, spoken aloud via TTS. Warm, plain language, one short question at a time.")
    profile: ProfilePatch = Field(description="The full accumulated profile so far, including this turn's new information merged in.")
    done: bool = Field(description="True once business_type, district, block, and available_margin_capital are all filled.")


INTAKE_SYSTEM_PROMPT = """You are Saarthi, a warm, plain-spoken voice assistant helping a rural
Indian micro-entrepreneur set up their business feasibility and loan-eligibility check, in
whatever language or mix of languages (Hindi/English/regional) they use. You are having a
spoken conversation - keep every reply short (1-2 sentences), ask ONE question at a time, and
never use financial jargon.

Your only job is to fill these fields through natural conversation:
- district: latur, sitapur, or indore (only these three are serviced - if they name another
  place, gently say you currently only support these three and ask them to pick the closest one)
- block: the block/tehsil/area within that district
- village: the village name, if they mention one (optional, don't push hard for this)
- business_type: vendor, dairy, textiles, retail, handicrafts, or food_stall
- available_margin_capital: how much money in rupees they already have saved that they could put
  in as their own contribution toward a new enterprise (accept approximate answers like "around
  one lakh" or "1 lakh"). Explain simply if asked: this is the cash they'd bring themselves, with
  a loan covering the rest.

Never invent a number they didn't say. If unsure, ask a clarifying follow-up instead of guessing.
Once all four required fields (district, block, business_type, available_margin_capital) are
filled, set done=true and give a warm closing line telling them you're building their feasibility
report and loan eligibility now."""

_intake_agent: Agent | None = None


def get_intake_agent() -> Agent:
    """Lazily construct the agent so the server can boot (and serve the
    fully-deterministic financial-structuring/feasibility endpoints) even
    before a valid API key is set - only the voice/advisory endpoints need it."""
    global _intake_agent
    if _intake_agent is None:
        _intake_agent = Agent(AGENT_MODEL, output_type=ConversationTurn, system_prompt=INTAKE_SYSTEM_PROMPT)
    return _intake_agent


class AdvisoryResult(BaseModel):
    headline: str = Field(description="One warm, plain-language sentence summarising the business's feasibility and loan readiness.")
    talking_points: list[str] = Field(description="3-5 short, concrete, encouraging observations grounded strictly in the numbers provided. Never invent a figure not given to you.")
    caution: str | None = Field(default=None, description="One honest caution if the numbers show a real risk (e.g. an underserved-vs-crowded market, tight working capital during moratorium). Null if nothing concerning.")


ADVISORY_SYSTEM_PROMPT = """You are Saarthi, phrasing plain-language advisory commentary for a
rural micro-entrepreneur's feasibility report and financial structuring plan. You are given
ALREADY-COMPUTED numbers (project cost, loan amount, scheme tier, EMI and moratorium schedule,
working capital by phase, and the feasibility report's market reach / competitor / pricing
figures). Your only job is to explain what these numbers mean in warm, encouraging, plain
language.

Hard rules:
- Never state a number that was not given to you in the input.
- Never recompute or contradict a given number.
- Keep talking_points concrete and tied to the actual figures (cite the number).
- If the market reads crowded, or working capital during the moratorium looks tight relative to
  the margin capital, say so honestly in `caution` - do not sugar-coat real risk.
"""

_advisory_agent: Agent | None = None


def get_advisory_agent() -> Agent:
    global _advisory_agent
    if _advisory_agent is None:
        _advisory_agent = Agent(AGENT_MODEL, output_type=AdvisoryResult, system_prompt=ADVISORY_SYSTEM_PROMPT)
    return _advisory_agent


class FeasibilityNarrative(BaseModel):
    opportunity_narrative: str = Field(description="1-2 sentences narrating the opportunity analysis, grounded strictly in the given numbers.")
    swot_narrative: dict[str, str] = Field(description="One short narrated sentence each for 'strengths', 'weaknesses', 'opportunities', 'threats', grounded in the given lists.")
    pricing_narrative: str = Field(description="1-2 sentences narrating the suggested pricing strategy, grounded strictly in the given numbers.")


FEASIBILITY_SYSTEM_PROMPT = """You are Saarthi, narrating a hyper-local business feasibility
report. You are given ALREADY-COMPUTED deterministic facts (market reach numbers, competitor
density, SWOT bullet lists, threat categories, pricing range). Turn these into warm, plain,
locally-grounded prose for a first-time entrepreneur. Never invent a fact, name, or number that
isn't in the input - you are a narrator of given data, not a source of new data."""

_feasibility_agent: Agent | None = None


def get_feasibility_agent() -> Agent:
    global _feasibility_agent
    if _feasibility_agent is None:
        _feasibility_agent = Agent(AGENT_MODEL, output_type=FeasibilityNarrative, system_prompt=FEASIBILITY_SYSTEM_PROMPT)
    return _feasibility_agent
