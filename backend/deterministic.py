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
            f"Project cost is Rs {project_cost:,.0f}, at or below the Rs 1,40,000 ceiling "
            f"for the Micro Finance Scheme."
        )
    elif project_cost <= TERM_LOAN_SCHEME["project_cost_max"]:
        scheme = TERM_LOAN_SCHEME
        rule_text = (
            f"Project cost is Rs {project_cost:,.0f}, above Rs 1,40,000 and at or below "
            f"Rs 50,00,000, qualifying for the Term Loan Scheme."
        )
    else:
        scheme = None
        rule_text = (
            f"Project cost is Rs {project_cost:,.0f}, above the Rs 50,00,000 ceiling this "
            f"router supports - no scheme tier matches at this margin capital."
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
        "assumption": "No payment is due during the moratorium and interest is not capitalised during it - EMI is computed on the original principal over the remaining tenure once repayment begins.",
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
# ---------------------------------------------------------------------------

def generate_feasibility_report(district_key: str, block_name: str, business_type: str) -> dict:
    district = CITY_DATA[district_key]
    block = get_block(district_key, block_name)
    if not block:
        raise ValueError(f"Unknown block '{block_name}' in district '{district_key}'")

    population = block["population"]
    density = block["competition_density"].get(business_type, 10)
    commodity = district["commodities"].get(business_type)
    seasonal_peak = district["seasonal_peak"].get(business_type, "N/A")
    consumer_share = RELEVANT_CONSUMER_SHARE.get(business_type, 0.2)

    # 1. Market Reach
    addressable_consumers = round(population * consumer_share)
    market_reach = {
        "block_population": population,
        "relevant_consumer_share": consumer_share,
        "addressable_consumers": addressable_consumers,
        "distribution_channels": DISTRIBUTION_CHANNELS.get(business_type, []),
        "detail": f"Within a 5-10km reach of {block_name}, an estimated {addressable_consumers:,} of the block's {population:,} residents are plausible regular customers for this category ({consumer_share * 100:.0f}% relevance share).",
    }

    # 5. Competitor Mapping (numbered per PS order, computed before 2/3/4 since they reference it)
    consumers_per_competitor = addressable_consumers / density if density > 0 else addressable_consumers
    competitor_mapping = {
        "competitor_count": density,
        "scale_ceiling": COMPETITION_DENSITY_MAX,
        "addressable_consumers_per_competitor": round(consumers_per_competitor),
        "detail": f"{density} similar businesses are observed in {block_name} (scale ceiling {COMPETITION_DENSITY_MAX}), roughly {round(consumers_per_competitor):,} addressable consumers per existing competitor.",
    }

    # 2. Opportunity Analysis
    is_underserved = consumers_per_competitor > 3000
    opportunity = {
        "is_underserved": is_underserved,
        "detail": (
            f"At roughly {round(consumers_per_competitor):,} addressable consumers per existing competitor, this block reads as under-served for this category."
            if is_underserved
            else f"At roughly {round(consumers_per_competitor):,} addressable consumers per existing competitor, this block already carries meaningful competition for this category - differentiation will matter more than raw demand."
        ),
    }

    # 6. Product Market Value
    pricing = None
    if commodity:
        spread_pct = (commodity["high"] - commodity["low"]) / commodity["low"] * 100
        suggested_entry_price = commodity["low"] + (commodity["current"] - commodity["low"]) * 0.6
        pricing = {
            "unit": commodity["unit"],
            "range_low": commodity["low"],
            "range_high": commodity["high"],
            "current": commodity["current"],
            "range_spread_pct": spread_pct,
            "suggested_entry_price": suggested_entry_price,
            "detail": f"Local price for {commodity['unit']} currently runs Rs {commodity['low']}-Rs {commodity['high']}, at Rs {commodity['current']} today. A new entrant pricing near Rs {suggested_entry_price:.0f} sits below the current rate to build initial footfall without matching the low end, where existing sellers already compete on price alone.",
        }

    # 3. SWOT
    swot = {
        "strengths": [
            f"Established local demand: {addressable_consumers:,} addressable consumers within reach",
            f"Peak-season demand window identified ({seasonal_peak}) to plan stock and cash around",
        ],
        "weaknesses": [
            "First-time enterprise with no operating track record for lenders to reference",
            "Working capital is likely to be the binding constraint before revenue stabilises",
        ],
        "opportunities": [opportunity["detail"]],
        "threats": THREAT_TEMPLATES.get(business_type, []),
    }

    # 4. Threats Identification (surfaced again standalone per the PS's explicit numbered list)
    threats = {
        "items": THREAT_TEMPLATES.get(business_type, []),
        "seasonal_peak": seasonal_peak,
    }

    return {
        "district": district["label"],
        "block": block_name,
        "business_type": business_type,
        "market_reach": market_reach,
        "opportunity_analysis": opportunity,
        "swot": swot,
        "threats": threats,
        "competitor_mapping": competitor_mapping,
        "product_market_value": pricing,
    }
