"""The only place an LLM is called. Its job is strictly bounded to two
things: (1) holding a natural conversation to collect profile fields into a
structured object, and (2) phrasing advisory commentary on top of numbers
that were already computed deterministically elsewhere (deterministic.py).
The agent never computes a financial figure itself - it only reads numbers
handed to it and talks about them.
"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent

load_dotenv()

AGENT_MODEL = os.environ.get("AGENT_MODEL", "google:gemini-2.5-flash")

BUSINESS_TYPE_VALUES = ("vendor", "dairy", "tailoring", "retail", "handicrafts", "food_stall")
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
    monthly_revenue: float | None = Field(default=None, description="Estimated monthly revenue in rupees.")
    years_in_operation: float | None = Field(default=None, description="How many years the business has run.")
    challenges: list[Literal["pricing", "stock", "credit", "seasonal", "records"]] = Field(
        default_factory=list, description="Challenges the speaker mentioned, mapped to these fixed categories."
    )
    field_confidence: dict[str, Literal["high", "low"]] = Field(
        default_factory=dict,
        description=(
            "Confidence level for each extracted field. Set a field to 'low' when the speaker was vague, "
            "approximate, or hedging (e.g. 'kaafi paisa', 'lagbhag', 'around', 'not sure', 'pata nahi exact'). "
            "Set to 'high' when the speaker gave a specific, unambiguous value. "
            "Only include fields that have been filled in this or a prior turn. "
            "monthly_revenue is especially important to flag low when approximate, because it drives "
            "break-even, working-capital, and loan-scheme calculations downstream."
        ),
    )


class ConversationTurn(BaseModel):
    """One turn of the voice agent's reply."""

    reply_text: str = Field(description="What the agent should say next, spoken aloud via TTS. Warm, plain language, one short question at a time.")
    profile: ProfilePatch = Field(description="The full accumulated profile so far, including this turn's new information merged in.")
    done: bool = Field(description="True once business_type, district, block, monthly_revenue, and years_in_operation are all filled.")


INTAKE_SYSTEM_PROMPT = """You are Saarthi, a warm, plain-spoken voice assistant helping a rural
Indian micro-entrepreneur describe their business out loud, in whatever language or mix of
languages (Hindi/English/regional) they use. You are having a spoken conversation - keep every
reply short (1-2 sentences), ask ONE question at a time, and never use financial jargon.

Your only job is to fill these fields through natural conversation:
- business_type: vendor, dairy, tailoring, retail, handicrafts, or food_stall
- district: latur, sitapur, or indore (only these three are serviced - if they name another place,
  gently say you currently only support these three and ask them to pick the closest one)
- block: the block/tehsil/area within that district
- monthly_revenue: rough monthly earnings in rupees (accept approximate answers like "10-15 hazar")
- years_in_operation: how long they've run the business
- challenges: any of pricing, stock, credit, seasonal swings, or record-keeping they mention unprompted

CONFIDENCE RULES — always populate field_confidence for every filled field:
- Mark "high" when the speaker gave a specific, unambiguous value (e.g. "ek lakh", "Rs 15,000", "3 saal").
- Mark "low" when the speaker was vague, approximate, or hedging. Examples that must be marked low:
    monthly_revenue: "kaafi paisa", "lagbhag 10-15 hazar", "around one lakh", "pata nahi exactly",
                     "thoda kam ya zyada", ranges like "8 se 12 hazar", or any answer with uncertainty.
    years_in_operation: "kaafi saalon se", "kuch saal", "shayad 2-3 saal"
    block: if the speaker named a locality that you had to infer as a block.
- monthly_revenue is especially critical: it feeds every financial calculation (break-even, working
  capital, loan eligibility). Always prefer to ask a clarifying follow-up if the answer was a range
  or contained words like "lagbhag", "around", "pata nahi", "thoda" — and mark it low.

Never invent a number they didn't say. If unsure, ask a clarifying follow-up instead of guessing.
Once all five required fields (business_type, district, block, monthly_revenue,
years_in_operation) are filled, set done=true and give a warm closing line telling them you're
building their credit-readiness report now."""

_intake_agent: Agent | None = None


def get_intake_agent() -> Agent:
    """Lazily construct the agent so the server can boot (and serve the
    fully-deterministic calculator/viability/scheme endpoints) even before
    a valid API key is set - only the voice/advisory endpoints need it."""
    global _intake_agent
    if _intake_agent is None:
        _intake_agent = Agent(AGENT_MODEL, output_type=ConversationTurn, system_prompt=INTAKE_SYSTEM_PROMPT)
    return _intake_agent


class AdvisoryResult(BaseModel):
    headline: str = Field(description="One warm, plain-language sentence summarising the business's credit readiness.")
    talking_points: list[str] = Field(description="3-5 short, concrete, encouraging observations grounded strictly in the numbers provided. Never invent a figure not given to you.")
    caution: str | None = Field(default=None, description="One honest caution if the numbers show a real risk (e.g. break-even not viable, low viability score). Null if nothing concerning.")


ADVISORY_SYSTEM_PROMPT = """You are Saarthi, phrasing plain-language advisory commentary for a
rural micro-entrepreneur's credit-readiness report. You are given ALREADY-COMPUTED numbers
(break-even, pricing check, working capital, viability score breakdown, matched schemes). Your
only job is to explain what these numbers mean in warm, encouraging, plain language.

Hard rules:
- Never state a number that was not given to you in the input.
- Never recompute or contradict a given number.
- Keep talking_points concrete and tied to the actual figures (cite the number).
- If break-even is not viable, or the viability score is below 50, say so honestly in `caution` -
  do not sugar-coat real risk.
"""

_advisory_agent: Agent | None = None


def get_advisory_agent() -> Agent:
    global _advisory_agent
    if _advisory_agent is None:
        _advisory_agent = Agent(AGENT_MODEL, output_type=AdvisoryResult, system_prompt=ADVISORY_SYSTEM_PROMPT)
    return _advisory_agent
