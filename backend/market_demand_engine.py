"""Market Demand Engine - 25% of the overall viability score.

Combines whatever demand-related features are actually available for a
(district, block, business_type) into a single 0-100 score. A feature with
no real data source (growth_trend, market_activity, purchasing_power - none
of which city_data.py tracks) is left out of the weighted average entirely
rather than invented, and is listed in `missing` so it also drags the
dimension's confidence down via confidence_engine.dimension_confidence.
"""

from __future__ import annotations

from city_data import CITY_DATA, RELEVANT_CONSUMER_SHARE
from confidence_engine import dimension_confidence, feature_confidence
from data_providers import market_demand_provider
from normalization import normalize_linear
from viability_config import MARKET_DEMAND_SUB_WEIGHTS, NEUTRAL_FALLBACK_SCORE

# Normalization ceilings computed from the dataset itself (documented
# assumption, not a guessed constant): the highest addressable-consumer
# figure achievable across today's serviced blocks/categories, and the
# highest relevant-consumer-share among today's categories. Recomputes
# automatically if city_data.py's data changes.
_MAX_BLOCK_POPULATION = max(
    (block["population"] for district in CITY_DATA.values() for block in district["blocks"].values()),
    default=100000,
)
_MAX_CONSUMER_SHARE = max(RELEVANT_CONSUMER_SHARE.values(), default=0.6)
_POPULATION_POTENTIAL_CEILING = _MAX_BLOCK_POPULATION * _MAX_CONSUMER_SHARE


def compute_market_demand(district_key: str, block_name: str, business_type: str) -> dict:
    envelope = market_demand_provider(district_key, block_name, business_type)
    if envelope["status"] != "OK":
        return {
            "score": NEUTRAL_FALLBACK_SCORE,
            "confidence": 0.0,
            "features": {},
            "missing": ["market_demand"],
            "data_quality": envelope,
        }

    reach = envelope["data"]
    addressable_consumers = reach["addressable_consumers"]
    consumer_share = reach["relevant_consumer_share"]
    conf = feature_confidence(envelope["provenance"])

    population_score = normalize_linear(addressable_consumers, 0, _POPULATION_POTENTIAL_CEILING)
    target_fit_score = normalize_linear(consumer_share, 0, _MAX_CONSUMER_SHARE)

    # population_potential and demand_estimate both derive from the same
    # addressable-consumer figure today (no separate demand-forecast data
    # source exists yet) - recorded as two named features, each with its own
    # entry, so a future distinct demand-estimate source can slot in without
    # changing this function's output shape.
    features = {
        "population_potential": {"value": addressable_consumers, "normalized_score": population_score, "source": envelope["source"], "confidence": conf, "provenance": envelope["provenance"]},
        "demand_estimate": {"value": addressable_consumers, "normalized_score": population_score, "source": envelope["source"], "confidence": conf, "provenance": envelope["provenance"]},
        "target_customer_fit": {"value": consumer_share, "normalized_score": target_fit_score, "source": envelope["source"], "confidence": conf, "provenance": envelope["provenance"]},
    }
    missing = ["growth_trend", "market_activity", "purchasing_power"]

    used_weights = {k: MARKET_DEMAND_SUB_WEIGHTS[k] for k in features}
    weight_total = sum(used_weights.values())
    score = (
        sum(features[k]["normalized_score"] * used_weights[k] for k in features) / weight_total
        if weight_total else NEUTRAL_FALLBACK_SCORE
    )

    conf_dim = dimension_confidence([f["confidence"] for f in features.values()], expected_feature_count=len(MARKET_DEMAND_SUB_WEIGHTS))

    return {
        "score": round(score, 2),
        "confidence": conf_dim,
        "features": features,
        "missing": missing,
        "data_quality": envelope,
    }
