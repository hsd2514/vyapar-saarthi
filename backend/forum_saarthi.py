"""Saarthi's take - the first reply on every Chaupal question.

The one hard lesson from the field literature on rural voice forums is
that a question left unanswered kills the forum: in the Avaaj Otalo pilot,
traffic collapsed the month staff stopped replying, and peers did not step
in (they feared being blamed for a wrong answer). So every question gets a
first response within seconds, from the same deterministic engine the rest
of the app runs on. It is labelled as the engine's, carries a provenance tag
on every figure, and explicitly invites a verified human to add to it.

Two layers, same boundary as the rest of the project:
  1. build_facts()   - deterministic. Picks the facts relevant to the post's
                       topic from deterministic.py / forum_store crowd data.
                       This alone is a complete, publishable reply.
  2. phrase()        - optional LLM pass that rewrites the facts in the
                       poster's language. It may not add a number. If no
                       model is configured or the call fails, the template
                       text from layer 1 is used as-is.
"""

from __future__ import annotations

import asyncio
import os
import re

from city_data import CITY_DATA
from deterministic import (
    MICRO_FINANCE_SCHEME,
    TERM_LOAN_SCHEME,
    calc_financial_structuring,
    calc_repayment_schedule,
    get_competitor_mapping,
    get_market_reach,
    get_opportunity_analysis,
    get_product_market_value,
    get_threats,
)
import forum_store

NO_FEE_NOTICE = (
    "No government loan scheme (NBCFDC, NSFDC, MUDRA, PMEGP) charges any processing fee, file charge or "
    "advance to sanction a loan, and none of them use agents. Anyone asking for money before sanction is a scam. "
    "Report them here and to your nearest bank branch."
)

_AMOUNT_RE = re.compile(r"(?:rs\.?|₹|inr)?\s*(\d[\d,]{2,})\s*(lakh|lac|lakhs|k|thousand|hazar)?", re.I)


def _first_amount(text: str) -> float | None:
    """A rupee figure mentioned in the post, if any. Used only to make the
    engine's example concrete; the reply always states the assumption."""
    for m in _AMOUNT_RE.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        unit = (m.group(2) or "").lower()
        if unit in ("lakh", "lac", "lakhs"):
            val *= 100000
        elif unit in ("k", "thousand", "hazar"):
            val *= 1000
        if val >= 1000:
            return val
    return None


def _resolve_block(district: str, block: str) -> str | None:
    d = CITY_DATA.get(district)
    if not d:
        return None
    for key in d["blocks"]:
        if key.casefold() == (block or "").strip().casefold():
            return key
    return next(iter(d["blocks"]))


def _fmt(n: float) -> str:
    return f"Rs {n:,.0f}"


def build_facts(*, topic: str, trade: str, district: str, block: str, text: str) -> dict:
    """Returns {"paragraphs": [str], "provenance": [dict], "facts": dict}.
    Every paragraph is plain language a low-literacy reader can follow; every
    number in it has a matching provenance entry."""
    paragraphs: list[str] = []
    prov: list[dict] = []
    facts: dict = {}
    resolved_block = _resolve_block(district, block)
    engine_ok = resolved_block is not None and trade in {"vendor", "dairy", "textiles", "retail", "handicrafts", "food_stall"}
    amount = _first_amount(text)

    if topic == "scam":
        paragraphs.append(NO_FEE_NOTICE)
        prov.append({"fact": "no_fee_rule", "source": "PIB Fact Check / scheme guidelines", "provenance": "RULE"})

    elif topic in ("loan_scheme", "bank_process"):
        paragraphs.append(
            f"Two scheme tiers apply. Up to {_fmt(MICRO_FINANCE_SCHEME['project_cost_max'])} project cost: "
            f"{MICRO_FINANCE_SCHEME['name']} at {MICRO_FINANCE_SCHEME['annual_rate_pct']}% for {MICRO_FINANCE_SCHEME['tenure_months'] // 12} years "
            f"with a {MICRO_FINANCE_SCHEME['moratorium_months']}-month holiday. Above that, up to {_fmt(TERM_LOAN_SCHEME['project_cost_max'])}: "
            f"{TERM_LOAN_SCHEME['name']} at {TERM_LOAN_SCHEME['annual_rate_pct']}% for {TERM_LOAN_SCHEME['tenure_months'] // 12} years "
            f"with a {TERM_LOAN_SCHEME['moratorium_months']}-month holiday. You bring 10% of the project cost; the scheme lends 90%."
        )
        prov.append({"fact": "scheme_tiers", "source": "deterministic.py scheme tables (PS specification)", "provenance": "RULE"})
        if amount:
            fs = calc_financial_structuring(amount)
            facts["structuring"] = fs
            if fs["scheme"]:
                paragraphs.append(
                    f"If the {_fmt(amount)} you mention is your own 10% margin, that supports a project of {_fmt(fs['project_cost'])} "
                    f"and a loan of up to {_fmt(fs['max_loan_amount'])} under the {fs['scheme']['name']}. If it is the loan you want instead, "
                    f"you would need about {_fmt(amount / 9)} of your own money."
                )
                prov.append({"fact": "structuring_example", "source": "calc_financial_structuring", "provenance": "RULE", "assumption": "amount treated as margin capital"})
        if topic == "bank_process":
            waits = forum_store.wait_summary(district=district)
            if waits:
                w = waits[0]
                bits = []
                if w["median_months_to_sanction"] is not None:
                    bits.append(f"application to sanction about {w['median_months_to_sanction']:.0f} months")
                if w["median_months_sanction_to_money"] is not None:
                    bits.append(f"sanction to money in hand about {w['median_months_sanction_to_money']:.0f} months")
                if bits:
                    paragraphs.append(f"Members here report, for {w['agency']} in {district.title()} ({w['n']} reports): " + "; ".join(bits) + ". Plan for that wait; do not borrow your margin from a moneylender to bridge it.")
                    prov.append({"fact": "wait_times", "source": "forum wait_reports", "provenance": "USER_REPORTED", "n": w["n"]})
            paragraphs.append(NO_FEE_NOTICE)
            prov.append({"fact": "no_fee_rule", "source": "PIB Fact Check / scheme guidelines", "provenance": "RULE"})

    elif topic == "repayment":
        paragraphs.append(
            "Missing one instalment is not the end, but it must not become a pattern - repayment records follow you to the next loan. "
            "Speak to the branch or SCA officer before the due date, not after; a rescheduling request made early is usually heard."
        )
        prov.append({"fact": "repayment_guidance", "source": "scheme practice", "provenance": "RULE"})
        if amount:
            sched = calc_repayment_schedule(amount, TERM_LOAN_SCHEME["annual_rate_pct"], TERM_LOAN_SCHEME["tenure_months"], TERM_LOAN_SCHEME["moratorium_months"])
            facts["schedule"] = {"monthly_emi": sched["monthly_emi"]}
            paragraphs.append(
                f"For reference, a {_fmt(amount)} loan on the Term Loan Scheme works out to roughly {_fmt(sched['monthly_emi'])} a month "
                f"after the holiday. Setting aside about a third of that every month during the holiday builds a cushion for the leanest quarter."
            )
            prov.append({"fact": "emi_example", "source": "calc_repayment_schedule", "provenance": "RULE", "assumption": "Term Loan Scheme terms"})

    elif topic == "prices":
        if engine_ok:
            pmv = get_product_market_value(district, resolved_block, trade)
            if pmv:
                facts["product_market_value"] = pmv
                paragraphs.append(
                    f"In {district.title()}, the local price for {pmv['unit']} runs {_fmt(pmv['range_low'])} to {_fmt(pmv['range_high'])}, "
                    f"about {_fmt(pmv['current'])} today. A new seller pricing near {_fmt(pmv['suggested_entry_price'])} builds footfall without joining the price war at the bottom."
                )
                prov.append({"fact": "product_market_value", "source": "city_data.py commodities", "provenance": "DEMO"})
        crowd = forum_store.price_summary(trade=trade, district=district)
        if crowd:
            lines = [f"{g['item']}: median {_fmt(g['median'])} per {g['unit']} ({g['n']} reports, latest {g['latest_month']})" for g in crowd[:4]]
            paragraphs.append(f"What members in {district.title()} say they actually paid - " + "; ".join(lines) + ".")
            prov.append({"fact": "crowd_prices", "source": "forum price_reports", "provenance": "USER_REPORTED"})
        if not paragraphs:
            paragraphs.append("No price data for this trade in this district yet. If you have bought recently, add a price report - the next person will thank you.")

    elif topic in ("selling", "suppliers", "operations", "training"):
        if engine_ok:
            reach = get_market_reach(district, resolved_block, trade)
            comp = get_competitor_mapping(district, resolved_block, trade)
            opp = get_opportunity_analysis(district, resolved_block, trade)
            thr = get_threats(district, resolved_block, trade)
            facts.update({"market_reach": reach, "competitor_mapping": comp, "opportunity": opp})
            if topic == "selling":
                paragraphs.append(
                    f"Around {resolved_block}, about {reach['addressable_consumers']:,} people are plausible regular customers for this trade, "
                    f"with {comp['competitor_count']} similar businesses already there. " + opp["detail"]
                )
                if reach["distribution_channels"]:
                    paragraphs.append("Usual selling channels for this trade: " + ", ".join(reach["distribution_channels"]) + ".")
                prov.append({"fact": "market_reach", "source": "city_data.py block data", "provenance": "DEMO"})
            else:
                if thr["items"]:
                    paragraphs.append("Risks others in this trade name most often: " + "; ".join(thr["items"][:3]) + f". Peak demand season here: {thr['seasonal_peak']}.")
                    prov.append({"fact": "threats", "source": "city_data.py threat templates", "provenance": "DEMO"})
        if topic == "training":
            paragraphs.append(
                "Every district has a free RSETI (Rural Self Employment Training Institute) running 10-30 day courses, and banks look kindly on applicants who finished one. "
                "Ask at your nearest lead bank branch or the SCA office for the current batch."
            )
            prov.append({"fact": "rseti", "source": "MoRD RSETI programme", "provenance": "RULE"})
        if not paragraphs:
            paragraphs.append("The engine has no block-level data for this trade yet, so this one is for the members and experts here.")

    if not paragraphs:
        paragraphs.append("This one needs a person. A verified expert has been asked to look at it.")

    paragraphs.append("This is the engine's first response, not a human's. A verified expert or a member who has done this can add to it below.")
    return {"paragraphs": paragraphs, "provenance": prov, "facts": facts}


PHRASE_SYSTEM_PROMPT = """You are Saarthi, writing the first reply on a rural entrepreneur's forum post.
You are given FACTS already computed by a deterministic engine. Rewrite them as one warm, plain reply
in the language and script the poster used (Hindi, Marathi, English, or their mix). Rules:
- Every number, price, rate, tenure, month count, and scheme name must come from the FACTS verbatim.
  Do not add, round, or estimate any figure that is not in the FACTS.
- Keep it short: 4-7 sentences. No bullet points, no headings.
- Keep the final sentence that says this is the engine's first response and invites a verified expert.
- Never suggest contacting an agent or paying any fee."""

_phrase_agent = None


def _get_phrase_agent():
    global _phrase_agent
    if _phrase_agent is None:
        from pydantic_ai import Agent
        from agent import resolve_model
        _phrase_agent = Agent(resolve_model(), system_prompt=PHRASE_SYSTEM_PROMPT)
    return _phrase_agent


def _model_configured() -> bool:
    return any(os.environ.get(k) for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SARVAM_API_KEY", "FASTROUTER_API_KEY", "OPENCODE_API_KEY"))


async def phrase(facts: dict, post_text: str, timeout_s: float = 20.0) -> str:
    """LLM rewrite of the template text, or the template text itself when no
    model is configured or the call fails/times out. Either way the caller
    gets a publishable string."""
    template = "\n\n".join(facts["paragraphs"])
    if not _model_configured():
        return template
    try:
        prompt = f"POST:\n{post_text}\n\nFACTS (verbatim, do not alter):\n{template}"
        result = await asyncio.wait_for(_get_phrase_agent().run(prompt), timeout=timeout_s)
        out = (result.output or "").strip()
        return out if out else template
    except Exception:
        return template
