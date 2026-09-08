"""Location & Infrastructure Engine - 15% of the overall score. Reads the
illustrative per-block infrastructure scores from city_data.py (provenance
DEMO, documented there) plus the category's own infrastructure emphasis
from business_category_config.py for the business-specific sub-score - the
same block never scores identically for every business category.
"""

from __future__ import annotations

from business_category_config import get_business_category_config
from confidence_engine import feature_confidence
from data_providers import infrastructure_provider
from viability_config import LOCATION_SUB_WEIGHTS, NEUTRAL_FALLBACK_SCORE

_BASE_INFRA_KEYS = ["accessibility", "transport", "market_proximity", "electricity", "water", "connectivity"]


def compute_location_infrastructure(district_key: str, block_name: str, business_type: str) -> dict:
    envelope = infrastructure_provider(district_key, block_name)
    if envelope["status"] != "OK":
        return {
            "score": NEUTRAL_FALLBACK_SCORE,
            "confidence": 0.0,
            "features": {},
            "missing": ["location_infrastructure"],
            "data_quality": envelope,
        }

    infra = envelope["data"]
    conf = feature_confidence(envelope["provenance"])

    category = get_business_category_config(business_type)
    emphasis = [k for k in (category["infrastructure_emphasis"] if category else []) if k in infra]
    business_specific_score = (
        round(sum(infra[k] for k in emphasis) / len(emphasis), 2)
        if emphasis
        else round(sum(infra[k] for k in _BASE_INFRA_KEYS) / len(_BASE_INFRA_KEYS), 2)
    )

    component_scores = {k: infra[k] for k in _BASE_INFRA_KEYS}
    component_scores["business_specific_infrastructure"] = business_specific_score

    score = sum(component_scores[k] * LOCATION_SUB_WEIGHTS[k] for k in LOCATION_SUB_WEIGHTS)

    features = {
        k: {"value": v, "normalized_score": v, "source": envelope["source"], "confidence": conf, "provenance": envelope["provenance"]}
        for k, v in component_scores.items()
    }

    return {
        "score": round(score, 2),
        "confidence": conf,
        "features": features,
        "missing": [],
        "data_quality": envelope,
    }
