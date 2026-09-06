"""Pure, deterministic financial logic. No LLM call happens in this file -
every function here is plain arithmetic or a lookup-table rule, and every
output is traceable back to its formula. The LLM layer (agent.py) only
narrates what these functions already computed; it never invents a figure.
"""

from __future__ import annotations

from city_data import (
    CITY_DATA,
    COMPETITION_DENSITY_MAX,
    DISTRIBUTION_CHANNELS,
    EXPECTED_CONSUMERS_PER_COMPETITOR,
    RELEVANT_CONSUMER_SHARE,
    THREAT_TEMPLATES,
    get_block,
)

# ---------------------------------------------------------------------------
# Scheme tiers - exactly the two tiers this PS specifies.
# ---------------------------------------------------------------------------

MICRO_FINANCE_SCHEME = {
    "id": "micro_finance",
    "name": "Micro Finance Scheme",
    "project_cost_max": 140000,
    "loan_pct": 0.90,
    "loan_cap": 125000,
    "annual_rate_pct": 6.5,
    "tenure_months": 36,
    "moratorium_months": 3,
}

TERM_LOAN_SCHEME = {
    "id": "term_loan",
    "name": "Term Loan Scheme",
    "project_cost_max": 5000000,
    "loan_pct": 0.90,
    "loan_cap": 4500000,
    "annual_rate_pct": 8.0,
    "tenure_months": 84,
    "moratorium_months": 6,
}


def calc_financial_structuring(available_margin_capital: float) -> dict:
    """Margin capital (10% contribution) -> project cost -> max loan (90%) ->
    scheme tier, following the PS's own worked example exactly:
    margin ₹1,00,000 -> project cost ₹10,00,000 -> loan ₹9,00,000."""
    margin = float(available_margin_capital)
    project_cost = margin / 0.10

    if project_cost <= MICRO_FINANCE_SCHEME["project_cost_max"]:
        scheme = MICRO_FINANCE_SCHEME
        rule_text = (
            "Your business costs under 1.4 lakh rupees to start, so it comes under the "
            "Micro Finance Scheme, which is meant for small businesses like yours."
        )
    elif project_cost <= TERM_LOAN_SCHEME["project_cost_max"]:
        scheme = TERM_LOAN_SCHEME
        rule_text = (
            "Your business costs more than 1.4 lakh rupees to start, so it comes under the "
            "Term Loan Scheme, which is for bigger businesses and gives you more time to repay."
        )
    else:
        scheme = None
        rule_text = (
            "Your business would cost over 50 lakh rupees to start. That is more than these "
            "two schemes can lend."
        )

    if scheme is None:
        return {
            "margin_capital": margin,
            "project_cost": project_cost,
            "max_loan_amount": None,
            "scheme": None,
            "rule_text": rule_text,
        }

    uncapped_loan = project_cost * scheme["loan_pct"]
    max_loan_amount = min(uncapped_loan, scheme["loan_cap"])

    return {
        "margin_capital": margin,
        "project_cost": project_cost,
        "max_loan_amount": max_loan_amount,
        "loan_capped": uncapped_loan > scheme["loan_cap"],
        "scheme": {
            "id": scheme["id"],
            "name": scheme["name"],
            "annual_rate_pct": scheme["annual_rate_pct"],
            "tenure_months": scheme["tenure_months"],
            "moratorium_months": scheme["moratorium_months"],
            "loan_cap": scheme["loan_cap"],
        },
        "rule_text": rule_text,
    }


# ---------------------------------------------------------------------------
# EMI + moratorium quarterly repayment schedule.
# ---------------------------------------------------------------------------

def calc_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """Standard reducing-balance EMI formula."""
    r = (annual_rate_pct / 100) / 12
    n = tenure_months
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def calc_repayment_schedule(principal: float, annual_rate_pct: float, tenure_months: int, moratorium_months: int) -> dict:
    """No repayment is due during the moratorium (interest is not
    capitalised during this window - a stated simplifying assumption, since
    the PS does not specify capitalisation treatment). EMI is then computed
    via the standard formula over the remaining (tenure - moratorium)
    months, and grouped into quarters for display, as the PS asks for a
    quarterly repayment schedule."""
    repayment_months = tenure_months - moratorium_months
    monthly_emi = calc_emi(principal, annual_rate_pct, repayment_months)
    total_repayment = monthly_emi * repayment_months
    total_interest = total_repayment - principal

    quarters = []
    month = 0
    quarter_index = 1
    while month < tenure_months:
        months_in_quarter = min(3, tenure_months - month)
        moratorium_months_in_quarter = max(0, min(moratorium_months, month + months_in_quarter) - month)
        repayment_months_in_quarter = months_in_quarter - moratorium_months_in_quarter
        quarter_amount = monthly_emi * repayment_months_in_quarter
        quarters.append(
            {
                "quarter": quarter_index,
                "months_covered": months_in_quarter,
                "moratorium_months": moratorium_months_in_quarter,
                "repayment_months": repayment_months_in_quarter,
                "amount_due": quarter_amount,
                "is_moratorium_only": repayment_months_in_quarter == 0,
            }
        )
        month += months_in_quarter
        quarter_index += 1

    return {
        "principal": principal,
        "annual_rate_pct": annual_rate_pct,
        "tenure_months": tenure_months,
        "moratorium_months": moratorium_months,
        "repayment_months": repayment_months,
        "monthly_emi": monthly_emi,
        "total_repayment": total_repayment,
        "total_interest": total_interest,
        "quarters": quarters,
        "assumption": "How we worked this out: you pay nothing during the free period at the start, and no interest is added during it either. The monthly amount is then spread evenly over the months that are left.",
    }


def calc_working_capital_by_phase(monthly_operational_cost: float, inventory_days: float, receivable_days: float, monthly_emi: float) -> dict:
    """Cash needed per month during the moratorium (operating costs only,
    no loan repayment yet) versus after the moratorium ends (operating
    costs plus the EMI installment) - the PS asks the calculator to factor
    moratorium periods into the working capital picture, not just the loan
    math alone."""
    daily_cost = monthly_operational_cost / 30
    cash_cycle_days = inventory_days + receivable_days
    cycle_buffer = daily_cost * cash_cycle_days

    return {
        "monthly_operational_cost": monthly_operational_cost,
        "cash_cycle_days": cash_cycle_days,
        "one_time_cycle_buffer": cycle_buffer,
        "monthly_cash_needed_during_moratorium": monthly_operational_cost,
        "monthly_cash_needed_after_moratorium": monthly_operational_cost + monthly_emi,
    }


# ---------------------------------------------------------------------------
# Module 1: Hyper-Local Business Feasibility Report (6 named sections).
#
# Each section is its own standalone function, callable independently - this
# is deliberate: the feasibility agent (agent.py) wires each of these up as
# a tool it can call with whatever (district, block, business_type) it
# needs, including combinations the entrepreneur didn't originally pick, so
# it can answer "what if" and "which business suits me best here" questions
# by actually calling these functions again rather than guessing an answer.
# ---------------------------------------------------------------------------

def _resolve(district_key: str, block_name: str, business_type: str):
    district = CITY_DATA.get(district_key)
    if not district:
        raise ValueError(f"Unknown district '{district_key}'. Valid districts: {list(CITY_DATA.keys())}")
    block = get_block(district_key, block_name)
    if not block:
        raise ValueError(f"Unknown block '{block_name}' in district '{district_key}'. Valid blocks: {list(district['blocks'].keys())}")
    return district, block


def get_market_reach(district_key: str, block_name: str, business_type: str) -> dict:
    district, block = _resolve(district_key, block_name, business_type)
    population = block["population"]
    consumer_share = RELEVANT_CONSUMER_SHARE.get(business_type, 0.2)
    addressable_consumers = round(population * consumer_share)
    return {
        "block_population": population,
        "relevant_consumer_share": consumer_share,
        "addressable_consumers": addressable_consumers,
        "distribution_channels": DISTRIBUTION_CHANNELS.get(business_type, []),
        "detail": f"Within a 5-10km reach of {block_name}, an estimated {addressable_consumers:,} of the block's {population:,} residents are plausible regular customers for this category ({consumer_share * 100:.0f}% relevance share).",
    }


def get_competitor_mapping(district_key: str, block_name: str, business_type: str) -> dict:
    district, block = _resolve(district_key, block_name, business_type)
    density = block["competition_density"].get(business_type, 10)
    addressable_consumers = get_market_reach(district_key, block_name, business_type)["addressable_consumers"]
    consumers_per_competitor = addressable_consumers / density if density > 0 else addressable_consumers
    return {
        "competitor_count": density,
        "scale_ceiling": COMPETITION_DENSITY_MAX,
        "addressable_consumers_per_competitor": round(consumers_per_competitor),
        "detail": f"{density} similar businesses are observed in {block_name} (scale ceiling {COMPETITION_DENSITY_MAX}), roughly {round(consumers_per_competitor):,} addressable consumers per existing competitor.",
    }


def get_opportunity_analysis(district_key: str, block_name: str, business_type: str) -> dict:
    mapping = get_competitor_mapping(district_key, block_name, business_type)
    consumers_per_competitor = mapping["addressable_consumers_per_competitor"]
    benchmark = EXPECTED_CONSUMERS_PER_COMPETITOR.get(business_type, 10000)
    is_underserved = consumers_per_competitor > benchmark
    return {
        "is_underserved": is_underserved,
        "benchmark_consumers_per_competitor": benchmark,
        "detail": (
            f"At roughly {consumers_per_competitor:,} addressable consumers per existing competitor - above the ~{benchmark:,} this category typically supports per business - this block reads as under-served."
            if is_underserved
            else f"At roughly {consumers_per_competitor:,} addressable consumers per existing competitor - at or below the ~{benchmark:,} this category typically supports per business - this block already carries meaningful competition. Differentiation will matter more than raw demand."
        ),
    }


def get_product_market_value(district_key: str, block_name: str, business_type: str) -> dict | None:
    district, _block = _resolve(district_key, block_name, business_type)
    commodity = district["commodities"].get(business_type)
    if not commodity:
        return None
    spread_pct = (commodity["high"] - commodity["low"]) / commodity["low"] * 100
    suggested_entry_price = commodity["low"] + (commodity["current"] - commodity["low"]) * 0.6
    return {
        "unit": commodity["unit"],
        "range_low": commodity["low"],
        "range_high": commodity["high"],
        "current": commodity["current"],
        "range_spread_pct": spread_pct,
        "suggested_entry_price": suggested_entry_price,
        "detail": f"Local price for {commodity['unit']} currently runs Rs {commodity['low']}-Rs {commodity['high']}, at Rs {commodity['current']} today. A new entrant pricing near Rs {suggested_entry_price:.0f} sits below the current rate to build initial footfall without matching the low end, where existing sellers already compete on price alone.",
    }


def get_threats(district_key: str, block_name: str, business_type: str) -> dict:
    district, _block = _resolve(district_key, block_name, business_type)
    return {
        "items": THREAT_TEMPLATES.get(business_type, []),
        "seasonal_peak": district["seasonal_peak"].get(business_type, "N/A"),
    }


def get_swot(district_key: str, block_name: str, business_type: str) -> dict:
    market_reach = get_market_reach(district_key, block_name, business_type)
    opportunity = get_opportunity_analysis(district_key, block_name, business_type)
    threats = get_threats(district_key, block_name, business_type)
    return {
        "strengths": [
            f"Established local demand: {market_reach['addressable_consumers']:,} addressable consumers within reach",
            f"Peak-season demand window identified ({threats['seasonal_peak']}) to plan stock and cash around",
        ],
        "weaknesses": [
            "First-time enterprise with no operating track record for lenders to reference",
            "Working capital is likely to be the binding constraint before revenue stabilises",
        ],
        "opportunities": [opportunity["detail"]],
        "threats": threats["items"],
    }


def generate_feasibility_report(district_key: str, block_name: str, business_type: str) -> dict:
    district, _block = _resolve(district_key, block_name, business_type)
    return {
        "district": district["label"],
        "block": block_name,
        "business_type": business_type,
        "market_reach": get_market_reach(district_key, block_name, business_type),
        "opportunity_analysis": get_opportunity_analysis(district_key, block_name, business_type),
        "swot": get_swot(district_key, block_name, business_type),
        "threats": get_threats(district_key, block_name, business_type),
        "competitor_mapping": get_competitor_mapping(district_key, block_name, business_type),
        "product_market_value": get_product_market_value(district_key, block_name, business_type),
    }
