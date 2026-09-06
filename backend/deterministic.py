"""Pure, deterministic financial logic. No LLM call happens in this file -
every function here is plain arithmetic or a lookup-table rule, and every
output is traceable back to its formula. The LLM layer (agent.py) only
collects input and phrases advisory text; it never computes these numbers.
"""

from __future__ import annotations

from datetime import date

from city_data import (
    BUSINESS_COMMODITY_MAP,
    CITY_DATA,
    COMPETITION_DENSITY_MAX,
    VIABILITY_WEIGHTS,
    pick_commodity,
)

SCHEMES = [
    {
        "id": "mudra_shishu",
        "name": "PM Mudra Yojana - Shishu",
        "agency": "Ministry of MSME / Member Lending Institutions",
        "max_loan": 50000,
        "rule_text": "Annual turnover must be at or below Rs 5,00,000 (Shishu category covers loans up to Rs 50,000).",
        "rule": lambda p: p["monthly_revenue"] * 12 <= 500000,
        "eligible_types": None,
        "documents": [
            "Filled Mudra loan application form",
            "Identity proof (Aadhaar / Voter ID / PAN)",
            "Address proof",
            "Passport-size photographs",
            "Business existence/address proof (shop registration, vendor certificate, or self-declaration)",
            "Last 6 months' bank statement (if account exists)",
        ],
    },
    {
        "id": "mudra_kishor",
        "name": "PM Mudra Yojana - Kishor",
        "agency": "Ministry of MSME / Member Lending Institutions",
        "max_loan": 500000,
        "rule_text": "Annual turnover must be above Rs 5,00,000 and up to Rs 25,00,000 (Kishor category covers loans of Rs 50,000-5,00,000).",
        "rule": lambda p: 500000 < p["monthly_revenue"] * 12 <= 2500000,
        "eligible_types": None,
        "documents": [
            "Filled Mudra loan application form",
            "Identity & address proof",
            "Business registration / trade licence, if available",
            "Last 12 months' bank statement",
            "Quotation for machinery/stock to be financed",
            "2 years' business income estimate or ITR (if filed)",
        ],
    },
    {
        "id": "pmegp",
        "name": "PMEGP (Prime Minister's Employment Generation Programme)",
        "agency": "KVIC / State KVIB / DIC",
        "max_loan": 2500000,
        "rule_text": "Applies to new or recently-set-up (under 3 years) manufacturing/service micro-enterprises in eligible categories (handicrafts, tailoring, food processing, dairy processing).",
        "rule": lambda p: p["years_in_operation"] < 3
        and p["business_type"] in ("handicrafts", "tailoring", "food_stall", "dairy"),
        "eligible_types": ["handicrafts", "tailoring", "food_stall", "dairy"],
        "documents": [
            "Project report / business plan with cost estimate",
            "Identity & address proof",
            "Educational qualification certificate (min. 8th pass for projects above Rs 10 lakh)",
            "Caste/category certificate, if applicable (for subsidy slab)",
            "EDP training certificate, if completed",
            "No prior loan under PMEGP/PMRY/REGP declaration",
        ],
    },
    {
        "id": "shg_credit",
        "name": "SHG-Linked Bank Credit (NRLM/DAY-NRLM)",
        "agency": "NABARD / State Rural Livelihood Mission",
        "max_loan": 1000000,
        "rule_text": "Available to women-led or SHG-affiliated micro-enterprises with annual turnover up to Rs 12,00,000, prioritising rural and semi-urban units.",
        "rule": lambda p: p["monthly_revenue"] * 12 <= 1200000,
        "eligible_types": None,
        "documents": [
            "SHG membership certificate / group savings passbook",
            "Identity & address proof",
            "Group resolution recommending the loan",
            "Micro business plan with revenue estimate",
            "Bank passbook of SHG savings account",
        ],
    },
    {
        "id": "stand_up_india",
        "name": "Stand-Up India",
        "agency": "SIDBI / Scheduled Commercial Banks",
        "max_loan": 10000000,
        "rule_text": "For enterprises with at least 1 year of operating history and annual turnover of Rs 3,00,000 or more, seeking loans between Rs 10 lakh and Rs 1 crore for greenfield expansion.",
        "rule": lambda p: p["monthly_revenue"] * 12 >= 300000 and p["years_in_operation"] >= 1,
        "eligible_types": None,
        "documents": [
            "Detailed project report for expansion",
            "Identity & address proof",
            "Proof of SC/ST or woman entrepreneur status (category priority, not exclusive)",
            "Last 2 years' financial statements or bank statements",
            "Collateral / guarantee cover details (CGFSI eligible)",
        ],
    },
]


def calc_break_even(fixed_costs: float, variable_cost_per_unit: float, price_per_unit: float) -> dict:
    contribution_margin = price_per_unit - variable_cost_per_unit
    contribution_margin_pct = (contribution_margin / price_per_unit * 100) if price_per_unit > 0 else 0
    is_viable = contribution_margin > 0
    break_even_units = fixed_costs / contribution_margin if is_viable else None
    break_even_revenue = break_even_units * price_per_unit if is_viable else None
    return {
        "contribution_margin": contribution_margin,
        "contribution_margin_pct": contribution_margin_pct,
        "is_viable": is_viable,
        "break_even_units": break_even_units,
        "break_even_revenue": break_even_revenue,
    }


def calc_pricing_check(unit_cost: float, desired_margin_pct: float, market_price: float) -> dict:
    cost_plus_price = unit_cost * (1 + desired_margin_pct / 100)
    gap_vs_market = market_price - cost_plus_price
    gap_vs_market_pct = (gap_vs_market / cost_plus_price * 100) if cost_plus_price > 0 else 0
    verdict = "insufficient_data"
    if unit_cost > 0 and market_price > 0:
        verdict = "room_to_compete" if cost_plus_price <= market_price else "needs_adjustment"
    margin_at_market_price = ((market_price - unit_cost) / unit_cost * 100) if unit_cost > 0 else 0
    return {
        "cost_plus_price": cost_plus_price,
        "gap_vs_market": gap_vs_market,
        "gap_vs_market_pct": gap_vs_market_pct,
        "verdict": verdict,
        "margin_at_market_price": margin_at_market_price,
    }


def calc_working_capital(monthly_expenses: float, inventory_days: float, receivable_days: float) -> dict:
    daily_expense = monthly_expenses / 30
    cash_cycle_days = inventory_days + receivable_days
    working_capital_needed = daily_expense * cash_cycle_days
    return {
        "daily_expense": daily_expense,
        "cash_cycle_days": cash_cycle_days,
        "working_capital_needed": working_capital_needed,
    }


def compute_viability_score(district_key: str, business_type: str, reference_date: date | None = None) -> dict:
    reference_date = reference_date or date.today()
    district = CITY_DATA[district_key]
    weights = VIABILITY_WEIGHTS.get(business_type, {"price": 0.34, "competition": 0.33, "season": 0.33})

    picked = pick_commodity(district_key, business_type)
    if picked:
        commodity_key, rng = picked
        price_position_raw = (rng["current"] - rng["low"]) / (rng["high"] - rng["low"]) if rng["high"] > rng["low"] else 0.5
        price_position_raw = min(1, max(0, price_position_raw))
        price_detail = f"Current Rs {rng['current']}/{rng['unit']} within range Rs {rng['low']}-Rs {rng['high']} ({commodity_key.replace('_', ' ')})"
    else:
        price_position_raw = 0.5
        price_detail = "No commodity price data for this business type in this district"
    price_score = price_position_raw * 100

    density = district["competition_density"].get(business_type, 10)
    density_ratio = min(1, density / COMPETITION_DENSITY_MAX)
    competition_score = (1 - density_ratio) * 100

    seasonal_peak_label = district["seasonal_peak"].get(business_type, "N/A")
    # Approximate seasonal multiplier: months near Oct-Nov (harvest/festival) score high.
    month = reference_date.month
    season_curve = {1: 0.7, 2: 0.65, 3: 0.7, 4: 0.7, 5: 0.65, 6: 0.6, 7: 0.6, 8: 0.72, 9: 0.88, 10: 1.0, 11: 0.95, 12: 0.82}
    season_multiplier = season_curve.get(month, 0.7)
    season_score = season_multiplier * 100

    price_contribution = price_score * weights["price"]
    competition_contribution = competition_score * weights["competition"]
    season_contribution = season_score * weights["season"]
    final_score = round(min(100, max(0, price_contribution + competition_contribution + season_contribution)))

    return {
        "district": district["label"],
        "business_type": business_type,
        "weights": weights,
        "final_score": final_score,
        "breakdown": [
            {
                "key": "price",
                "label": "Commodity price position",
                "detail": price_detail,
                "raw_value": price_score,
                "weight": weights["price"],
                "contribution": price_contribution,
            },
            {
                "key": "competition",
                "label": "Block-level competition density",
                "detail": f"{density} similar businesses observed (scale ceiling {COMPETITION_DENSITY_MAX})",
                "raw_value": competition_score,
                "weight": weights["competition"],
                "contribution": competition_contribution,
            },
            {
                "key": "season",
                "label": "Seasonal demand proximity",
                "detail": f"Nearest peak: {seasonal_peak_label}",
                "raw_value": season_score,
                "weight": weights["season"],
                "contribution": season_contribution,
            },
        ],
    }


def match_schemes(monthly_revenue: float, years_in_operation: float, business_type: str) -> list[dict]:
    profile = {
        "monthly_revenue": monthly_revenue,
        "years_in_operation": years_in_operation,
        "business_type": business_type,
    }
    results = []
    for scheme in SCHEMES:
        type_ok = scheme["eligible_types"] is None or business_type in scheme["eligible_types"]
        rule_ok = scheme["rule"](profile)
        results.append(
            {
                "id": scheme["id"],
                "name": scheme["name"],
                "agency": scheme["agency"],
                "max_loan": scheme["max_loan"],
                "rule_text": scheme["rule_text"],
                "documents": scheme["documents"],
                "eligible": bool(type_ok and rule_ok),
            }
        )
    return results
