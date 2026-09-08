"""The only place an LLM is called. Its job is strictly bounded to two
things: (1) holding a natural conversation to collect the three inputs this
tool needs - location, available margin capital, business category - into a
structured object, and (2) narrating the feasibility report / advisory
commentary on top of numbers that were already computed deterministically
elsewhere (deterministic.py). The agent never computes a financial figure
itself - it only reads numbers handed to it and talks about them.
"""

from __future__ import annotations

import json
import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from city_data import CITY_DATA

load_dotenv()

AGENT_MODEL = os.environ.get("AGENT_MODEL", "google:gemini-2.0-flash")

# Sarvam AI's chat completions API (https://docs.sarvam.ai) is OpenAI-compatible -
# it accepts `Authorization: Bearer <key>` and the standard chat/completions
# request shape - but Pydantic AI has no built-in `sarvam:` provider string
# like it does for google:/groq:/openai:/anthropic:. So a `sarvam:<model>`
# value in AGENT_MODEL is resolved here into an explicit OpenAI-compatible
# model pointed at Sarvam's base URL, instead of being passed straight
# through to Agent() as a string.
# `os.environ.get(name, default)` only falls back to `default` when the var
# is completely unset - a `.env` line like `SARVAM_BASE_URL=` (present but
# blank, which .env.example encourages people to leave as a placeholder)
# sets it to "", which is NOT unset, so the default never kicks in and every
# request goes out with an empty base URL. `or default` treats blank the
# same as unset, which is what every "only needed if X changes their URL"
# variable in .env.example actually means.
SARVAM_BASE_URL = os.environ.get("SARVAM_BASE_URL") or "https://api.sarvam.ai/v1"

# OpenCode Zen (https://opencode.ai/docs/zen) is a curated model gateway with
# a temporary free tier (e.g. "muse-spark-1.3-contributor-free"). It speaks
# OpenAI's newer Responses API (not the classic chat/completions shape Sarvam
# uses above) at /zen/v1/responses, so it needs Pydantic AI's
# OpenAIResponsesModel rather than OpenAIChatModel - same "no native provider
# string" situation as Sarvam, different OpenAI-compatible wire format.
OPENCODE_BASE_URL = os.environ.get("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1"

# FastRouter (https://fastrouter.ai) is a multi-provider model router with a
# standard OpenAI-compatible chat/completions endpoint - same wire format as
# Sarvam above, just a different base URL and its own model-namespacing
# convention (e.g. "z-ai/glm-5.3-flash", "anthropic/claude-opus-4.7").
FASTROUTER_BASE_URL = os.environ.get("FASTROUTER_BASE_URL") or "https://api.fastrouter.ai/api/v1"


def resolve_model():
    """Turn AGENT_MODEL into whatever Agent() expects: the raw string for
    providers Pydantic AI knows natively, or an explicit OpenAI-compatible
    model pointed at a gateway's own base URL for providers Pydantic AI has
    no native prefix for (sarvam:, opencode:, fastrouter:)."""
    from pydantic_ai.providers.openai import OpenAIProvider

    if AGENT_MODEL.startswith("sarvam:"):
        from pydantic_ai.models.openai import OpenAIChatModel

        model_name = AGENT_MODEL.removeprefix("sarvam:")
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key:
            raise RuntimeError("AGENT_MODEL is set to a sarvam: model but SARVAM_API_KEY is not set.")
        return OpenAIChatModel(model_name, provider=OpenAIProvider(base_url=SARVAM_BASE_URL, api_key=api_key))

    if AGENT_MODEL.startswith("opencode:"):
        from pydantic_ai.models.openai import OpenAIResponsesModel

        model_name = AGENT_MODEL.removeprefix("opencode:")
        api_key = os.environ.get("OPENCODE_API_KEY")
        if not api_key:
            raise RuntimeError("AGENT_MODEL is set to an opencode: model but OPENCODE_API_KEY is not set.")
        return OpenAIResponsesModel(model_name, provider=OpenAIProvider(base_url=OPENCODE_BASE_URL, api_key=api_key))

    if AGENT_MODEL.startswith("fastrouter:"):
        model_name = AGENT_MODEL.removeprefix("fastrouter:")
        api_key = os.environ.get("FASTROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("AGENT_MODEL is set to a fastrouter: model but FASTROUTER_API_KEY is not set.")
        provider = OpenAIProvider(base_url=FASTROUTER_BASE_URL, api_key=api_key)

        # FastRouter internally serves OpenAI's GPT-5 family through its own
        # Responses API (confirmed via docs.fastrouter.ai and by hitting
        # /api/v1/responses directly), even when called at the classic
        # /chat/completions path - the reply comes back Responses-shaped
        # (object: "response") and fails validation against Pydantic AI's
        # OpenAIChatModel, which expects object: "chat.completion". Every
        # other model tested (glm-5.3-flash, deepseek-v4-flash) speaks
        # genuine chat/completions and works fine there. So GPT-5 models get
        # OpenAIResponsesModel (the correct client for what FastRouter
        # actually returns for them); everything else stays on OpenAIChatModel.
        is_gpt5_family = model_name.split("/")[-1].startswith("gpt-5")

        # Reasoning-capable models routed through FastRouter (tested:
        # glm-5.3-flash, deepseek-v4-flash, gpt-5-nano, gpt-5.4-nano) were
        # measured at 7-48 seconds per turn with default reasoning effort -
        # fatal for the Twilio phone webhook's ~15s hard timeout
        # (twilio_ivr.py). "minimal" is rejected by the gpt-5.4-nano model
        # itself (its own error lists valid values as none/low/medium/high/
        # xhigh) - "none" is accepted by every GPT-5 variant tested.
        #
        # Caveat worth knowing: bare single-message API calls with "none"
        # measured 2.7-4.6s, but the REAL intake agent (long system prompt +
        # tool-call schema + this ProfilePatch validator) measured 11-14s per
        # turn across repeated runs - still under Twilio's ~15s ceiling, but
        # with less margin than the bare-call numbers implied. Treat this as
        # "usually fine, occasionally tight" rather than comfortably safe.
        if is_gpt5_family:
            from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings

            settings = OpenAIResponsesModelSettings(openai_reasoning_effort="none")
            return OpenAIResponsesModel(model_name, provider=provider, settings=settings)

        from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings

        settings = OpenAIChatModelSettings(openai_reasoning_effort="none")
        return OpenAIChatModel(model_name, provider=provider, settings=settings)

    return AGENT_MODEL


BUSINESS_TYPE_VALUES = ("vendor", "dairy", "textiles", "retail", "handicrafts", "food_stall")
DISTRICT_VALUES = ("latur", "sitapur", "indore")

# Every serviced block name, across all three districts (block names don't
# collide across districts, so one flat set is fine). Extracted from
# city_data.py so it can never drift out of sync with what the rest of the
# app (feasibility report, contacts, etc.) actually services. block is
# constrained to exactly these strings - free-text extraction here was the
# bug: the frontend's block <select> is a controlled dropdown matched by
# exact string, so a slightly different casing or spelling that isn't one of
# these options would fill the profile with a value the dropdown can't
# display, making it look like the field silently failed to autofill.
BLOCK_VALUES = tuple(block for district in CITY_DATA.values() for block in district["blocks"])
BLOCKS_BY_DISTRICT_TEXT = " ".join(
    f"{district['district']} has {', '.join(district['blocks'].keys())}." for district in CITY_DATA.values()
)


class ProfilePatch(BaseModel):
    """Fields the agent has confidently extracted so far. Every field is
    optional - only fill in what the speaker has actually said."""

    business_type: Literal[BUSINESS_TYPE_VALUES] | None = Field(
        default=None, description="One of the fixed business categories, inferred from what the speaker described."
    )
    district: Literal[DISTRICT_VALUES] | None = Field(
        default=None, description="Must be one of the three serviced districts: latur, sitapur, indore."
    )
    block: Literal[BLOCK_VALUES] | None = Field(
        default=None, description="Exact block/tehsil name, spelled exactly as listed for that district in the system prompt - never a free-text guess."
    )
    village: str | None = Field(default=None, description="Village name within the block, if mentioned (optional).")
    available_margin_capital: float | None = Field(
        default=None, description="The rupee amount the speaker says they already have saved/available to contribute as their 10% margin money."
    )


class ConversationTurn(BaseModel):
    """One turn of the voice agent's reply."""

    reply_text: str = Field(description="What the agent should say next, spoken aloud via TTS. Warm, plain language, one short question at a time.")
    profile: ProfilePatch = Field(description="The full accumulated profile so far, including this turn's new information merged in.")
    done: bool = Field(description="True once business_type, district, block, and available_margin_capital are all filled.")

    @field_validator("profile", mode="before")
    @classmethod
    def _accept_stringified_profile(cls, v):
        """Some models (observed with glm-5.3-flash via FastRouter) emit a
        nested object field as a JSON *string* instead of a real nested
        object in their tool-call arguments - technically invalid against
        the schema, but recoverable. Without this, that one quirk burns
        every retry and the whole turn fails even though the model actually
        extracted the right fields. Only string values are touched; a
        properly-nested dict/ProfilePatch passes through unchanged."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v


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
language it was said in.

Each turn tells you "Reply in: <language>" - this is the language the speaker explicitly chose
in the app, and it is the ONLY thing that decides what language your reply_text is written in.
Always write your reply in exactly that language (script and all - e.g. "Reply in: Hindi" means
Devanagari Hindi, not transliterated or English), no matter what script or language mix the
speaker's own transcript used. Never switch to match the transcript's language instead.

Your only job is to fill these fields through natural conversation:
- district: latur, sitapur, or indore (only these three are serviced - if they name another
  place, gently say you currently only support these three and ask them to pick the closest one)
- block: the block/tehsil within that district - each district only services these exact
  blocks: {blocks_by_district}. Map whatever the speaker says (any spelling, script, or
  mispronunciation, e.g. "ausa", "औसा", "Ausa taluka") to the exact block name as spelled above -
  never write it back in a different spelling or casing. If what they name isn't one of their
  district's listed blocks, say so plainly and ask them to pick one of the serviced blocks instead
  of guessing or inventing a close match.
- village: the village name, if they mention one (optional, don't push hard for this)
- business_type: vendor, dairy, textiles, retail, handicrafts, or food_stall
- available_margin_capital: how much money in rupees they already have saved that they could put
  in as their own contribution toward a new enterprise (accept approximate answers like "around
  one lakh" or "1 lakh"). Explain simply if asked: this is the cash they'd bring themselves, with
  a loan covering the rest.

Never invent a number they didn't say. If unsure, ask a clarifying follow-up instead of guessing.
Once all four required fields (district, block, business_type, available_margin_capital) are
filled, set done=true and give a warm closing line telling them you're building their feasibility
report and loan eligibility now.""".format(blocks_by_district=BLOCKS_BY_DISTRICT_TEXT)

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


# ---------------------------------------------------------------------------
# Viability explainer - narrates the Hyper-Local Viability Engine's
# deterministic output (viability_engine.py). Same "narrate given numbers,
# never invent or recompute one" contract as the advisory agent above, with
# the explicit guardrails the engine's product framing requires: no
# guaranteed outcomes, and provenance (verified/demo/user-provided) must be
# represented honestly rather than implied to be more certain than it is.
# ---------------------------------------------------------------------------

class ViabilityExplanation(BaseModel):
    plain_language_summary: str = Field(
        description="2-4 sentences explaining the overall score and recommendation in plain language for a first-time entrepreneur."
    )
    risk_explanation: str = Field(description="1-2 sentences on the most important risk(s) driving the score down, if any.")
    next_steps: list[str] = Field(description="2-4 concrete, specific things the entrepreneur should validate or do next, grounded in the given data.")
    clarification_questions: list[str] = Field(
        default_factory=list, description="Questions to ask the entrepreneur that would improve confidence if answered (e.g. missing financial fields)."
    )


VIABILITY_EXPLAINER_SYSTEM_PROMPT = """You are explaining a deterministic business
decision-support analysis to a rural or semi-urban Indian entrepreneur, in warm,
plain language with no financial jargon.

Hard rules:
- Do not invent facts. Use only the structured data you are given.
- Never change, recompute, or contradict any score, number, EMI, DSCR, or scheme
  figure in the input - you only explain what is already there.
- Clearly distinguish verified, estimated, demo, and user-provided information when
  it matters to the explanation (e.g. if confidence is low because the underlying
  data is illustrative/demo rather than live, say so plainly rather than implying
  it is verified).
- Do not provide guaranteed financial outcomes, guaranteed loan approval, or
  guaranteed market success - use language like "potential opportunity",
  "indicative financing", and "decision support", never "guaranteed" or "approved".
- If hard_constraints are present in the input, your summary must reflect them
  honestly even if the overall score alone looks high."""

_viability_explainer_agent: Agent | None = None


def get_viability_explainer_agent() -> Agent:
    global _viability_explainer_agent
    if _viability_explainer_agent is None:
        _viability_explainer_agent = Agent(resolve_model(), output_type=ViabilityExplanation, system_prompt=VIABILITY_EXPLAINER_SYSTEM_PROMPT)
    return _viability_explainer_agent


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

The entrepreneur may type in Devanagari script (Hindi/Marathi), Roman-transliterated Hindi/
Marathi ("yeh area underserved hai kya?"), English, or freely code-mixed between them - answer
in whatever script or mix they just used, without asking them to switch to English. Numbers and
place names stay as-is regardless of language.

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


# ---------------------------------------------------------------------------
# Financial advisor - the same tool-calling, memory-carrying pattern as the
# feasibility advisor above, but scoped to Module 2 (financial structuring,
# EMI/moratorium schedule, working capital, and the scheme-matching engine).
# The PS asks for an NLP-powered advisory assistant across both modules;
# until this agent existed, Module 2 was a pure calculator screen with no
# conversational layer at all.
# ---------------------------------------------------------------------------

FINANCIAL_ADVISOR_SYSTEM_PROMPT = """You are Saarthi, explaining a rural entrepreneur's loan
structuring, repayment plan, and government scheme matches in an ongoing, remembered
conversation. Keep answers short, plain-language, and grounded strictly in tool output.

The entrepreneur may type in Devanagari script (Hindi/Marathi), Roman-transliterated Hindi/
Marathi ("yeh scheme kyu mila?"), English, or freely code-mixed between them - answer in
whatever script or mix they just used, without asking them to switch to English. Rupee figures,
scheme names, and numbers stay as-is regardless of language.

Hard rules:
- ALWAYS call a tool before stating any rupee figure, interest rate, tenure, moratorium, or
  scheme name. Never state a number from memory - call the tool again for a new margin capital
  or project cost even if you answered a similar question earlier.
- If asked "what if I had X instead", call the tools with that new number and be explicit this
  is a hypothetical, not their actual filing.
- If asked "why did I get scheme X and not Y", call scheme_match and walk through the actual
  score_breakdown fields you got back - never invent a reason not present in that output.
- If something is outside what the tools can answer, say so rather than guessing."""

_financial_advisor_agent: Agent | None = None


def get_financial_advisor_agent() -> Agent:
    global _financial_advisor_agent
    if _financial_advisor_agent is not None:
        return _financial_advisor_agent

    from deterministic import calc_financial_structuring, calc_repayment_schedule, calc_working_capital_by_phase
    from schemes import match_schemes

    advisor = Agent(resolve_model(), system_prompt=FINANCIAL_ADVISOR_SYSTEM_PROMPT)

    def _safe(fn, *args):
        try:
            return fn(*args)
        except ValueError as exc:
            return {"error": str(exc)}

    @advisor.tool_plain
    def financial_structuring(available_margin_capital: float) -> dict:
        """Project cost, max loan amount, and which scheme tier (Micro Finance or Term Loan) this margin capital qualifies for."""
        return _safe(calc_financial_structuring, available_margin_capital)

    @advisor.tool_plain
    def repayment_schedule(
        principal: float,
        annual_rate_pct: float,
        tenure_months: int,
        moratorium_months: int,
        capitalise_moratorium_interest: bool = False,
    ) -> dict:
        """The quarterly EMI/moratorium repayment schedule for a given loan principal, rate, tenure, and moratorium."""
        return _safe(calc_repayment_schedule, principal, annual_rate_pct, tenure_months, moratorium_months, capitalise_moratorium_interest)

    @advisor.tool_plain
    def working_capital(monthly_operational_cost: float, inventory_days: float, receivable_days: float, monthly_emi: float) -> dict:
        """Working capital needed during and after the moratorium, given monthly operating cost, inventory/receivable days, and the EMI."""
        return _safe(calc_working_capital_by_phase, monthly_operational_cost, inventory_days, receivable_days, monthly_emi)

    @advisor.tool_plain
    def scheme_match(project_cost: float, business_type: str | None = None) -> list[dict]:
        """Ranks real government schemes (PMEGP, Mudra tiers, Stand-Up India, PM SVANidhi, PM Vishwakarma, PMFME, dairy scheme) plus this tool's own margin-money scheme against a project cost, with the exact weighted score breakdown for each."""
        return _safe(match_schemes, project_cost, business_type)

    _financial_advisor_agent = advisor
    return _financial_advisor_agent
