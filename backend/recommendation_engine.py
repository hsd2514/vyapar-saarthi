"""Recommendation Engine - hard safety gates plus the decision-state logic.
Hard constraints can only ever downgrade a purely score-based verdict, never
upgrade one: a good market score can never overrule a dangerous DSCR.
"""

from __future__ import annotations

from viability_config import HARD_CONSTRAINTS, RECOMMENDATION_THRESHOLDS

RECOMMENDATION_LABELS = {
    "PROCEED": "The evidence supports moving forward, with the usual scheme/lender checks still to complete.",
    "PROCEED_WITH_CAUTION": "Market promising, but financing risk or a moderate concern warrants caution.",
    "VALIDATE_FIRST": "The available evidence is too thin to advise confidently - validate locally before investing.",
    "REDUCE_SCALE": "Good market signal, but financial capacity looks tight - consider a smaller starting scale.",
    "HIGH_RISK": "A critical financial or operational constraint makes this too risky to proceed as planned.",
    "INSUFFICIENT_EVIDENCE": "Not enough verified or estimated data is available yet to support a recommendation.",
}


def evaluate_hard_constraints(financial_fit: dict, confidence: float, resource_availability: dict, location_infrastructure: dict) -> list[dict]:
    constraints = []

    if financial_fit.get("insufficient_repayment_capacity"):
        constraints.append({
            "flag": "INSUFFICIENT_REPAYMENT_CAPACITY",
            "explanation": f"DSCR of {financial_fit['dscr']} is below the {HARD_CONSTRAINTS['min_dscr']} safety threshold.",
        })

    if financial_fit.get("high_debt_burden"):
        constraints.append({
            "flag": "HIGH_DEBT_BURDEN",
            "explanation": (
                f"Existing EMI is {round(financial_fit['debt_burden_ratio'] * 100)}% of monthly income, "
                f"above the {round(HARD_CONSTRAINTS['max_debt_burden_ratio'] * 100)}% safety threshold."
            ),
        })

    if confidence < HARD_CONSTRAINTS["min_confidence"]:
        constraints.append({
            "flag": "INSUFFICIENT_EVIDENCE",
            "explanation": (
                f"Overall data confidence ({round(confidence * 100)}%) is below the "
                f"{round(HARD_CONSTRAINTS['min_confidence'] * 100)}% minimum needed to advise confidently."
            ),
        })

    critical_resource_gaps = [item for item in resource_availability.get("checklist", []) if item.get("status") == "CONFIRMED_UNAVAILABLE"]
    if critical_resource_gaps:
        constraints.append({
            "flag": "CRITICAL_RESOURCE_GAP",
            "explanation": f"{len(critical_resource_gaps)} required resource(s) confirmed unavailable in this area.",
        })

    # Only fires when we have real, reasonably-confident evidence the
    # location itself lacks critical infrastructure - not merely because
    # infrastructure data is missing (that case is INSUFFICIENT_EVIDENCE).
    if location_infrastructure.get("confidence", 0) >= 0.4 and location_infrastructure.get("score", 100) < HARD_CONSTRAINTS["critical_infrastructure_score"]:
        constraints.append({
            "flag": "OPERATIONALLY_UNVIABLE",
            "explanation": f"Location infrastructure score ({location_infrastructure['score']}) is critically low for this business.",
        })

    return constraints


def recommend(overall_score: float, confidence: float, market_demand_score: float, financial_fit_score: float, hard_constraints: list[dict]) -> dict:
    flags = {c["flag"] for c in hard_constraints}

    if "INSUFFICIENT_EVIDENCE" in flags:
        state = "INSUFFICIENT_EVIDENCE"
    elif "INSUFFICIENT_REPAYMENT_CAPACITY" in flags or "OPERATIONALLY_UNVIABLE" in flags or "CRITICAL_RESOURCE_GAP" in flags:
        state = "HIGH_RISK"
    elif "HIGH_DEBT_BURDEN" in flags and market_demand_score >= RECOMMENDATION_THRESHOLDS["reduce_scale_market_min_score"]:
        state = "REDUCE_SCALE"
    elif overall_score >= RECOMMENDATION_THRESHOLDS["proceed_min_score"] and confidence >= HARD_CONSTRAINTS["min_confidence"]:
        state = "PROCEED"
    # Checked before the generic PROCEED_WITH_CAUTION threshold: a good
    # market score dragged down specifically by weak financial fit should
    # read as "reduce scale", not get lumped into a blanket "caution".
    elif market_demand_score >= RECOMMENDATION_THRESHOLDS["reduce_scale_market_min_score"] and financial_fit_score < RECOMMENDATION_THRESHOLDS["proceed_with_caution_min_score"]:
        state = "REDUCE_SCALE"
    elif overall_score >= RECOMMENDATION_THRESHOLDS["proceed_with_caution_min_score"]:
        state = "PROCEED_WITH_CAUTION"
    else:
        state = "VALIDATE_FIRST"

    return {"state": state, "summary": RECOMMENDATION_LABELS[state]}
