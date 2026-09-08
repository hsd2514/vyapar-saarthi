"""Risk & Seasonality Engine - 15% of the overall score.

RiskIndex is built only from risk components this app can actually derive
today: market-competition risk (competitor density vs. this category's
benchmark - deterministic.get_opportunity_analysis), price volatility (the
commodity price spread already in city_data.py), and debt burden (once
financial inputs are provided). Every other spec-listed risk category
(supply_chain_risk, climate_risk, infrastructure_reliability,
buyer_concentration, operational_risk) has no real per-block data source
yet, so it is surfaced as a qualitative named risk drawn from
city_data.THREAT_TEMPLATES (real curated content) rather than a fabricated
numeric sub-score.
"""

from __future__ import annotations

from confidence_engine import feature_confidence
from data_providers import competitor_provider, pricing_provider
from deterministic import get_opportunity_analysis, get_threats
from normalization import normalize_linear
from viability_config import NEUTRAL_FALLBACK_SCORE, RISK_SEVERITY_BANDS

RISK_SUB_WEIGHTS = {
    "market_competition_risk": 0.35,
    "price_volatility": 0.30,
    "debt_burden": 0.35,
}
assert abs(sum(RISK_SUB_WEIGHTS.values()) - 1.0) < 1e-9


def _severity(score: float) -> str:
    for low, high, label in RISK_SEVERITY_BANDS:
        if low <= score <= high:
            return label
    return "VERY_HIGH"


def compute_risk_seasonality(district_key: str, block_name: str, business_type: str, debt_burden_ratio: float | None) -> dict:
    risk_components: dict[str, dict] = {}
    named_risks: list[dict] = []

    comp_envelope = competitor_provider(district_key, block_name, business_type)
    if comp_envelope["status"] == "OK":
        # Combination already validated by competitor_provider - safe to call.
        opportunity = get_opportunity_analysis(district_key, block_name, business_type)
        crowding_risk = 0.0 if opportunity["is_underserved"] else 65.0
        risk_components["market_competition_risk"] = {
            "score": crowding_risk,
            "confidence": feature_confidence(comp_envelope["provenance"]),
            "explanation": opportunity["detail"],
            "source": comp_envelope["source"],
        }

    price_envelope = pricing_provider(district_key, block_name, business_type)
    if price_envelope["status"] == "OK":
        spread_pct = price_envelope["data"]["range_spread_pct"]
        price_risk = normalize_linear(spread_pct, 0, 100)
        risk_components["price_volatility"] = {
            "score": price_risk,
            "confidence": feature_confidence(price_envelope["provenance"]),
            "explanation": f"Local price range spans {spread_pct:.0f}% of the low price - a wider band indicates more price volatility.",
            "source": price_envelope["source"],
        }

    if debt_burden_ratio is not None:
        debt_risk = normalize_linear(debt_burden_ratio, 0, 1.0)
        risk_components["debt_burden"] = {
            "score": debt_risk,
            "confidence": feature_confidence("USER_PROVIDED"),
            "explanation": f"Existing EMI is {debt_burden_ratio * 100:.0f}% of monthly household income.",
            "source": "USER_PROVIDED",
        }

    for comp_key, comp in risk_components.items():
        named_risks.append({
            "category": comp_key,
            "severity": _severity(comp["score"]),
            "score": comp["score"],
            "explanation": comp["explanation"],
            "source": comp["source"],
            "confidence": comp["confidence"],
        })

    # Qualitative, category-specific threats - real curated content, not
    # numerically scored (no data source exists to score them against yet).
    try:
        threats = get_threats(district_key, block_name, business_type)
    except ValueError:
        threats = {"items": [], "seasonal_peak": "N/A"}

    for item in threats["items"]:
        named_risks.append({
            "category": "qualitative_threat",
            "severity": "UNSCORED",
            "score": None,
            "explanation": item,
            "source": "city_data.py (curated, illustrative)",
            "confidence": 0.55,
        })

    if threats["seasonal_peak"] and threats["seasonal_peak"] != "N/A":
        named_risks.append({
            "category": "seasonality",
            "severity": "UNSCORED",
            "score": None,
            "explanation": f"Seasonal demand peak: {threats['seasonal_peak']}. Plan stock and cash flow around this window.",
            "source": "city_data.py (curated, illustrative)",
            "confidence": 0.55,
        })

    if not risk_components:
        return {
            "score": NEUTRAL_FALLBACK_SCORE,
            "confidence": 0.0,
            "risk_index": None,
            "risks": named_risks,
            "missing": ["risk_seasonality"],
        }

    used_weights = {k: RISK_SUB_WEIGHTS[k] for k in risk_components}
    weight_total = sum(used_weights.values())
    risk_index = sum(risk_components[k]["score"] * used_weights[k] for k in risk_components) / weight_total

    completeness = len(risk_components) / len(RISK_SUB_WEIGHTS)
    avg_source_confidence = sum(c["confidence"] for c in risk_components.values()) / len(risk_components)
    confidence = round(avg_source_confidence * completeness, 4)

    return {
        "score": round(100 - risk_index, 2),
        "confidence": confidence,
        "risk_index": round(risk_index, 2),
        "risks": named_risks,
        "missing": [k for k in RISK_SUB_WEIGHTS if k not in risk_components],
    }
