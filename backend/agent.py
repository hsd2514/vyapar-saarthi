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

# Sarvam AI's chat completions API (https://docs.sarvam.ai) is OpenAI-compatible -
# it accepts `Authorization: Bearer <key>` and the standard chat/completions
# request shape - but Pydantic AI has no built-in `sarvam:` provider string
# like it does for google:/groq:/openai:/anthropic:. So a `sarvam:<model>`
# value in AGENT_MODEL is resolved here into an explicit OpenAI-compatible
# model pointed at Sarvam's base URL, instead of being passed straight
# through to Agent() as a string.
SARVAM_BASE_URL = os.environ.get("SARVAM_BASE_URL", "https://api.sarvam.ai/v1")


def resolve_model():
    """Turn AGENT_MODEL into whatever Agent() expects: the raw string for
    providers Pydantic AI knows natively, or an explicit OpenAIChatModel
    pointed at Sarvam's OpenAI-compatible endpoint for `sarvam:<model>`."""
    if not AGENT_MODEL.startswith("sarvam:"):
        return AGENT_MODEL

    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    model_name = AGENT_MODEL.removeprefix("sarvam:")
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("AGENT_MODEL is set to a sarvam: model but SARVAM_API_KEY is not set.")
    return OpenAIChatModel(model_name, provider=OpenAIProvider(base_url=SARVAM_BASE_URL, api_key=api_key))


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

The transcript you receive may be in Devanagari script (Hindi/Marathi), Roman-transliterated
Hindi/Marathi ("main Sitapur mein sabzi bechta hoon"), English, or freely code-mixed between
them - the same as how people actually talk in a village or small town. Extract fields from
whatever script or mix you're given without asking the speaker to repeat themselves in English;
only ask a clarifying follow-up if the field itself is genuinely ambiguous, never because of the
language it was said in. Reply in the same language (or mix) the speaker just used, so the
conversation feels natural rather than switching languages on them mid-way.

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
        _intake_agent = Agent(resolve_model(), output_type=ConversationTurn, system_prompt=INTAKE_SYSTEM_PROMPT)
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
        _advisory_agent = Agent(resolve_model(), output_type=AdvisoryResult, system_prompt=ADVISORY_SYSTEM_PROMPT)
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
        _feasibility_agent = Agent(resolve_model(), output_type=FeasibilityNarrative, system_prompt=FEASIBILITY_SYSTEM_PROMPT)
    return _feasibility_agent


# ---------------------------------------------------------------------------
# Feasibility Advisor - a real tool-using agent with conversation memory.
#
# Unlike the narration agent above (one input -> one narrated output), this
# agent can hold a back-and-forth conversation and, critically, can CALL the
# same deterministic functions the Feasibility Report screen displays -
# for the entrepreneur's actual (district, block, business_type), or for any
# other valid combination it needs to answer a "what if I picked a different
# block" or "which of these businesses suits me best here" question. It
# never invents a number: every figure it states must come from a tool call
# response, not from its own reasoning.
# ---------------------------------------------------------------------------

FEASIBILITY_ADVISOR_SYSTEM_PROMPT = """You are Saarthi, an expert hyper-local business
feasibility advisor for a rural or semi-urban Indian entrepreneur. You are having an ongoing,
remembered conversation - you can refer back to anything discussed earlier in this session.

You have tools to fetch REAL, already-computed deterministic data for any (district, block,
business_type) combination the three serviced districts support: latur, sitapur, indore.
Serviced blocks: Latur has Latur, Ausa, Nilanga, Renapur, Chakur. Sitapur has Biswan,
Mahmoodabad, Sidhauli, Laharpur, Machhrehta. Indore has Sanwer, Depalpur, Mhow, Hatod, Rau.
Business categories: vendor, dairy, textiles, retail, handicrafts, food_stall.

Hard rules:
- ALWAYS call the relevant tool(s) before stating any number, name, or fact about market reach,
  competitors, pricing, SWOT, threats, or the loan/scheme math. Never state a figure from memory
  or estimation - call the tool, even if you already called it earlier this conversation and
  think you remember the answer, unless the user is asking about the exact same combination you
  just fetched.
- If the user asks a "what if" question (a different block, a different business category, or a
  different margin capital), call the tools again with those new parameters and compare the
  result to what you already know about their actual profile - be explicit that this is a
  hypothetical comparison, not their real filing.
- If the user asks something outside what the tools can answer, say so plainly rather than
  guessing.
- Keep answers concise and grounded - cite the actual number or fact from the tool result."""

_feasibility_advisor_agent: Agent | None = None


def get_feasibility_advisor_agent() -> Agent:
    global _feasibility_advisor_agent
    if _feasibility_advisor_agent is not None:
        return _feasibility_advisor_agent

    # Imported here (not at module load) so this file has no hard dependency
    # on deterministic.py until the advisor is actually used.
    from deterministic import (
        calc_financial_structuring,
        get_competitor_mapping,
        get_market_reach,
        get_opportunity_analysis,
        get_product_market_value,
        get_swot,
        get_threats,
    )

    advisor = Agent(resolve_model(), system_prompt=FEASIBILITY_ADVISOR_SYSTEM_PROMPT)

    def _safe(fn, *args):
        try:
            return fn(*args)
        except ValueError as exc:
            return {"error": str(exc)}

    @advisor.tool_plain
    def market_reach(district: str, block: str, business_type: str) -> dict:
        """Real market reach numbers (addressable consumers within 5-10km, distribution channels) for this district/block/business category."""
        return _safe(get_market_reach, district, block, business_type)

    @advisor.tool_plain
    def competitor_mapping(district: str, block: str, business_type: str) -> dict:
        """Real competitor density and consumers-per-competitor for this district/block/business category."""
        return _safe(get_competitor_mapping, district, block, business_type)

    @advisor.tool_plain
    def opportunity_analysis(district: str, block: str, business_type: str) -> dict:
        """Whether this district/block/business category reads as under-served or competitive, with the reasoning."""
        return _safe(get_opportunity_analysis, district, block, business_type)

    @advisor.tool_plain
    def swot_analysis(district: str, block: str, business_type: str) -> dict:
        """Strengths/weaknesses/opportunities/threats lists for this district/block/business category."""
        return _safe(get_swot, district, block, business_type)

    @advisor.tool_plain
    def threats(district: str, block: str, business_type: str) -> dict:
        """Named threat categories and the nearest seasonal demand peak for this district/block/business category."""
        return _safe(get_threats, district, block, business_type)

    @advisor.tool_plain
    def product_market_value(district: str, block: str, business_type: str) -> dict | None:
        """Local price range, current price, and suggested entry price for this district/block/business category."""
        return _safe(get_product_market_value, district, block, business_type)

    @advisor.tool_plain
    def financial_structuring(available_margin_capital: float) -> dict:
        """Project cost, max loan amount, and which scheme tier (Micro Finance or Term Loan) this margin capital qualifies for."""
        return _safe(calc_financial_structuring, available_margin_capital)

    _feasibility_advisor_agent = advisor
    return _feasibility_advisor_agent
