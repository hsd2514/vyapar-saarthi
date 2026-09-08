"""Tests for the Hyper-Local Business Viability Engine
(viability_engine.py + the six *_engine.py modules it orchestrates).

Mirrors test_deterministic.py's philosophy: every important number should be
checked against what it should actually be, not just "it ran without
crashing" - but for this engine, "never fabricates data and never crashes on
bad/missing/extreme input" is itself a first-class requirement (see
viability_config.py's NEUTRAL_FALLBACK_SCORE and every engine's UNAVAILABLE
handling), so several tests below check exactly that.
"""

from __future__ import annotations

import pytest

import viability_engine
from confidence_engine import dimension_confidence, feature_confidence, overall_confidence
from financial_fit_engine import compute_financial_fit
from geospatial import haversine_distance_km
from recommendation_engine import evaluate_hard_constraints, recommend
from risk_engine import compute_risk_seasonality
from viability_config import HARD_CONSTRAINTS, VIABILITY_WEIGHTS

DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS = "latur", "Ausa", "dairy"


# ---------------------------------------------------------------------------
# 1. Weight sum
# ---------------------------------------------------------------------------

def test_viability_weights_sum_to_one():
    assert sum(VIABILITY_WEIGHTS.values()) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 2. Score range
# ---------------------------------------------------------------------------

def test_overall_score_and_every_dimension_score_in_0_100():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 50_000)
    assert 0 <= result["overall_score"] <= 100
    for dim in result["dimensions"].values():
        assert 0 <= dim["score"] <= 100
        assert 0 <= dim["confidence"] <= 1


# ---------------------------------------------------------------------------
# 3/4. Missing data - no financial inputs at all
# ---------------------------------------------------------------------------

def test_missing_financial_data_reduces_confidence_not_fabricated():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 50_000)
    fin = result["financial_summary"]
    assert fin["missing_fields"] == ["monthly_income", "monthly_expenses", "existing_emi", "expected_revenue", "operating_expenses"]
    assert fin["disposable_income"] is None
    assert fin["business_surplus"] is None
    assert fin["dscr"] is None
    assert any(m.startswith("financial.") for m in result["missing_information"])


# ---------------------------------------------------------------------------
# 5. No competitor data available (unknown block)
# ---------------------------------------------------------------------------

def test_no_competitor_data_returns_unavailable_not_zero_competitors():
    result = viability_engine.run_analysis(DEMO_DISTRICT, "NotARealBlock", DEMO_BUSINESS, 50_000)
    competition = result["dimension_details"]["competition"]
    assert competition["competitor_count"] is None  # never fabricated as 0
    assert competition["confidence"] == 0.0
    assert "competition" in result["missing_information"]


# ---------------------------------------------------------------------------
# 6. Partial competitor data (valid block, still returns full envelope)
# ---------------------------------------------------------------------------

def test_valid_block_returns_competitor_data_with_provenance_demo():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 50_000)
    competition = result["dimension_details"]["competition"]
    assert competition["competitor_count"] is not None
    assert competition["data_quality"]["provenance"] == "DEMO"
    assert competition["data_quality"]["provenance"] != "VERIFIED_EXTERNAL"


# ---------------------------------------------------------------------------
# 7. Geographic fallback / level labelling
# ---------------------------------------------------------------------------

def test_data_quality_geographic_level_is_labelled():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 50_000)
    for envelope in result["data_quality"].values():
        assert envelope["geographic_level"] in ("block", "district")


# ---------------------------------------------------------------------------
# 8. Financial fit
# ---------------------------------------------------------------------------

def test_financial_fit_formulas():
    fit = compute_financial_fit(
        available_margin_capital=100_000,
        monthly_income=20_000,
        monthly_expenses=10_000,
        existing_emi=2_000,
        expected_revenue=15_000,
        operating_expenses=6_000,
    )
    assert fit["disposable_income"] == pytest.approx(20_000 - 10_000 - 2_000)
    assert fit["business_surplus"] == pytest.approx(15_000 - 6_000)
    assert fit["post_loan_surplus"] == pytest.approx(fit["disposable_income"] + fit["business_surplus"] - fit["new_emi"])
    assert fit["missing_fields"] == []


# ---------------------------------------------------------------------------
# 9. DSCR + safe division by zero
# ---------------------------------------------------------------------------

def test_dscr_zero_division_is_safe_not_a_crash():
    # Margin capital large enough that project cost exceeds both scheme
    # tiers -> scheme is None -> new_emi stays 0; existing_emi=0 too ->
    # total_emi=0 -> DSCR must be None, never a ZeroDivisionError.
    fit = compute_financial_fit(
        available_margin_capital=10_000_000,
        monthly_income=20_000,
        monthly_expenses=10_000,
        existing_emi=0,
        expected_revenue=5_000,
        operating_expenses=2_000,
    )
    assert fit["dscr"] is None


def test_dscr_below_threshold_flags_insufficient_repayment_capacity():
    fit = compute_financial_fit(
        available_margin_capital=100_000,
        monthly_income=5_000,
        monthly_expenses=4_900,
        existing_emi=0,
        expected_revenue=100,
        operating_expenses=90,
    )
    assert fit["dscr"] is not None
    assert fit["dscr"] < HARD_CONSTRAINTS["min_dscr"]
    assert fit["insufficient_repayment_capacity"] is True


# ---------------------------------------------------------------------------
# 10. Risk calculation
# ---------------------------------------------------------------------------

def test_risk_seasonality_returns_named_risks_and_score_in_range():
    risk = compute_risk_seasonality(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, debt_burden_ratio=0.3)
    assert 0 <= risk["score"] <= 100
    assert len(risk["risks"]) > 0
    for item in risk["risks"]:
        assert "category" in item and "severity" in item and "explanation" in item


def test_risk_engine_handles_unknown_location_without_crashing():
    risk = compute_risk_seasonality("latur", "NotARealBlock", DEMO_BUSINESS, debt_burden_ratio=None)
    assert risk["score"] == 50.0
    assert risk["confidence"] == 0.0


# ---------------------------------------------------------------------------
# 11. Hard constraints
# ---------------------------------------------------------------------------

def test_hard_constraint_downgrades_recommendation_even_with_high_score():
    financial_fit = {"insufficient_repayment_capacity": True, "dscr": 0.4, "high_debt_burden": False}
    location = {"score": 80, "confidence": 0.6}
    resources = {"checklist": []}
    constraints = evaluate_hard_constraints(financial_fit, confidence=0.8, resource_availability=resources, location_infrastructure=location)
    flags = {c["flag"] for c in constraints}
    assert "INSUFFICIENT_REPAYMENT_CAPACITY" in flags

    verdict = recommend(overall_score=90, confidence=0.8, market_demand_score=80, financial_fit_score=30, hard_constraints=constraints)
    assert verdict["state"] == "HIGH_RISK"  # never PROCEED despite the high score


def test_low_confidence_forces_insufficient_evidence_regardless_of_score():
    constraints = evaluate_hard_constraints(
        financial_fit={"insufficient_repayment_capacity": False, "high_debt_burden": False},
        confidence=0.1,
        resource_availability={"checklist": []},
        location_infrastructure={"score": 80, "confidence": 0.6},
    )
    verdict = recommend(overall_score=95, confidence=0.1, market_demand_score=90, financial_fit_score=90, hard_constraints=constraints)
    assert verdict["state"] == "INSUFFICIENT_EVIDENCE"


# ---------------------------------------------------------------------------
# 12. Recommendation logic (score-based, no constraints)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "score,confidence,market,fin,expected",
    [
        (80, 0.7, 70, 70, "PROCEED"),
        (65, 0.7, 70, 70, "PROCEED_WITH_CAUTION"),
        (68, 0.7, 70, 40, "REDUCE_SCALE"),
        (40, 0.7, 30, 30, "VALIDATE_FIRST"),
    ],
)
def test_recommendation_thresholds(score, confidence, market, fin, expected):
    verdict = recommend(score, confidence, market, fin, hard_constraints=[])
    assert verdict["state"] == expected


# ---------------------------------------------------------------------------
# 13. Opportunity gap
# ---------------------------------------------------------------------------

def test_opportunity_gap_present_for_a_valid_combination():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 50_000)
    assert len(result["opportunity_gaps"]) == 1
    gap = result["opportunity_gaps"][0]
    assert gap["geographic_level"] == "block"
    assert 0 <= gap["confidence"] <= 1


# ---------------------------------------------------------------------------
# 14. Confidence calculation
# ---------------------------------------------------------------------------

def test_feature_confidence_anchored_to_provenance():
    assert feature_confidence("USER_PROVIDED") > feature_confidence("DEMO")
    assert feature_confidence("UNAVAILABLE") == 0.0


def test_dimension_confidence_penalizes_incompleteness():
    full = dimension_confidence([0.9, 0.9, 0.9], expected_feature_count=3)
    partial = dimension_confidence([0.9], expected_feature_count=3)
    assert partial < full


def test_overall_confidence_is_weight_weighted():
    dims = {"market_demand": 1.0, "financial_fit": 0.0, "competition": 1.0, "location_infrastructure": 1.0, "resource_availability": 1.0, "risk_seasonality": 1.0}
    conf = overall_confidence(dims, VIABILITY_WEIGHTS)
    assert conf == pytest.approx(1.0 - VIABILITY_WEIGHTS["financial_fit"])


# ---------------------------------------------------------------------------
# 15. Invalid location
# ---------------------------------------------------------------------------

def test_invalid_district_never_crashes():
    result = viability_engine.run_analysis("not_a_district", "Nowhere", DEMO_BUSINESS, 50_000)
    assert 0 <= result["overall_score"] <= 100
    assert result["recommendation"] == "INSUFFICIENT_EVIDENCE"


# ---------------------------------------------------------------------------
# 16. Negative financial inputs
# ---------------------------------------------------------------------------

def test_negative_financial_inputs_do_not_crash():
    fit = compute_financial_fit(
        available_margin_capital=-50_000,
        monthly_income=-1000,
        monthly_expenses=500,
        existing_emi=0,
        expected_revenue=-200,
        operating_expenses=100,
    )
    assert isinstance(fit["score"], float)
    assert 0 <= fit["score"] <= 100


# ---------------------------------------------------------------------------
# 17. Extremely large values
# ---------------------------------------------------------------------------

def test_extremely_large_capital_does_not_crash():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 10_000_000_000)
    assert 0 <= result["overall_score"] <= 100
    assert result["financial_summary"]["max_loan_amount"] is None  # beyond both scheme tiers - never fabricated


# ---------------------------------------------------------------------------
# 18. Missing/unknown business category
# ---------------------------------------------------------------------------

def test_unknown_business_category_never_crashes():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, "poultry", 50_000)
    assert 0 <= result["overall_score"] <= 100
    assert result["dimension_details"]["resource_availability"]["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Geospatial
# ---------------------------------------------------------------------------

def test_haversine_known_distance():
    # Mumbai to Pune, roughly 120km apart (real, well-known distance).
    d = haversine_distance_km(19.0760, 72.8777, 18.5204, 73.8567)
    assert 100 < d < 160


def test_haversine_same_point_is_zero():
    assert haversine_distance_km(18.4088, 76.5604, 18.4088, 76.5604) == 0


# ---------------------------------------------------------------------------
# Engine version / auditability
# ---------------------------------------------------------------------------

def test_result_is_tagged_with_engine_version_and_weight_snapshot():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 50_000)
    assert result["engine_version"] == "1.0.0"
    assert result["weights_used"] == VIABILITY_WEIGHTS


def test_explainability_contributions_sum_to_overall_score():
    result = viability_engine.run_analysis(DEMO_DISTRICT, DEMO_BLOCK, DEMO_BUSINESS, 50_000)
    total_contribution = sum(c["contribution"] for c in result["explainability"]["contributions"])
    assert total_contribution == pytest.approx(result["overall_score"], abs=0.05)
