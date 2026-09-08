"""Hyper-Local Business Viability Engine - orchestrator.

Ties the six dimension engines together into the standardized viability
result: overall_score, confidence, recommendation, per-dimension
score/weight/confidence, opportunity gaps, named risks, financial summary,
data quality/provenance, hard constraints, an explainability contribution
breakdown, and missing_information. Tags the result with the exact engine
version + weight snapshot used (viability_config.py), so a future weight
change never silently changes how an already-returned result reads.

The AI layer (agent.py's viability explainer) only narrates this object -
it never changes any number produced here.
"""

from __future__ import annotations

from competition_engine import compute_competition
from confidence_engine import overall_confidence
from financial_fit_engine import compute_financial_fit
from location_engine import compute_location_infrastructure
from market_demand_engine import compute_market_demand
from recommendation_engine import evaluate_hard_constraints, recommend
from resource_engine import compute_resource_availability
from risk_engine import compute_risk_seasonality
from viability_config import VIABILITY_ENGINE_VERSION, VIABILITY_WEIGHTS


def run_analysis(
    district_key: str,
    block_name: str,
    business_type: str,
    available_margin_capital: float,
    monthly_income: float | None = None,
    monthly_expenses: float | None = None,
    existing_emi: float | None = None,
    expected_revenue: float | None = None,
    operating_expenses: float | None = None,
) -> dict:
    financial_fit = compute_financial_fit(
        available_margin_capital, monthly_income, monthly_expenses, existing_emi, expected_revenue, operating_expenses
    )
    market_demand = compute_market_demand(district_key, block_name, business_type)
    competition = compute_competition(district_key, block_name, business_type)
    location = compute_location_infrastructure(district_key, block_name, business_type)
    resources = compute_resource_availability(business_type)
    risk = compute_risk_seasonality(district_key, block_name, business_type, financial_fit.get("debt_burden_ratio"))

    dimensions = {
        "market_demand": market_demand,
        "financial_fit": financial_fit,
        "competition": competition,
        "location_infrastructure": location,
        "resource_availability": resources,
        "risk_seasonality": risk,
    }

    dimension_confidences = {k: v["confidence"] for k, v in dimensions.items()}
    confidence = overall_confidence(dimension_confidences, VIABILITY_WEIGHTS)
    overall_score = sum(dimensions[k]["score"] * VIABILITY_WEIGHTS[k] for k in VIABILITY_WEIGHTS)

    explainability = {
        "total": round(overall_score, 2),
        "contributions": [
            {
                "dimension": k,
                "score": dimensions[k]["score"],
                "weight": VIABILITY_WEIGHTS[k],
                "contribution": round(dimensions[k]["score"] * VIABILITY_WEIGHTS[k], 2),
            }
            for k in VIABILITY_WEIGHTS
        ],
    }

    hard_constraints = evaluate_hard_constraints(financial_fit, confidence, resources, location)
    recommendation = recommend(overall_score, confidence, market_demand["score"], financial_fit["score"], hard_constraints)

    missing_information: list[str] = []
    for k, v in dimensions.items():
        missing_information.extend(v.get("missing") or [])
    missing_information.extend(f"financial.{f}" for f in financial_fit.get("missing_fields", []))

    opportunity_gaps = []
    if competition.get("opportunity_gap_score") is not None:
        opportunity_gaps.append({
            "opportunity": (
                f"{'High' if competition['is_underserved'] else 'Limited'} observed demand relative to "
                f"{competition['competitor_count']} observed competitor(s) in {block_name}."
            ),
            "evidence": [competition.get("opportunity_gap_detail")],
            "confidence": competition["confidence"],
            "geographic_level": "block",
        })

    return {
        "engine_version": VIABILITY_ENGINE_VERSION,
        "weights_used": dict(VIABILITY_WEIGHTS),
        "overall_score": round(overall_score, 2),
        "confidence": confidence,
        "recommendation": recommendation["state"],
        "recommendation_summary": recommendation["summary"],
        "dimensions": {
            k: {"score": dimensions[k]["score"], "weight": VIABILITY_WEIGHTS[k], "confidence": dimensions[k]["confidence"]}
            for k in dimensions
        },
        "dimension_details": dimensions,
        "opportunity_gaps": opportunity_gaps,
        "risks": risk.get("risks", []),
        "financial_summary": financial_fit,
        "data_quality": {k: dimensions[k]["data_quality"] for k in dimensions if dimensions[k].get("data_quality")},
        "hard_constraints": hard_constraints,
        "explainability": explainability,
        "missing_information": sorted(set(missing_information)),
    }
