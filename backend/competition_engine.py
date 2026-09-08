"""Competition Engine - 15% of the overall score - plus the Opportunity Gap
Engine. More competitors is NOT automatically bad: both scores read
competition together with demand via consumers-per-competitor against the
category's own expected benchmark (city_data.EXPECTED_CONSUMERS_PER_COMPETITOR),
the same comparison deterministic.get_opportunity_analysis already makes -
reused here rather than recomputed, so the two never disagree.
"""

from __future__ import annotations

from confidence_engine import feature_confidence
from data_providers import competitor_provider
from deterministic import get_opportunity_analysis
from normalization import normalize_inverse_linear, normalize_linear
from viability_config import NEUTRAL_FALLBACK_SCORE


def compute_competition(district_key: str, block_name: str, business_type: str) -> dict:
    envelope = competitor_provider(district_key, block_name, business_type)
    if envelope["status"] != "OK":
        return {
            "score": NEUTRAL_FALLBACK_SCORE,
            "confidence": 0.0,
            "opportunity_gap_score": None,
            "opportunity_gap_detail": None,
            "is_underserved": None,
            "competitor_count": None,
            "consumers_per_competitor": None,
            "missing": ["competition"],
            "data_quality": envelope,
        }

    mapping = envelope["data"]
    competitor_count = mapping["competitor_count"]
    scale_ceiling = mapping["scale_ceiling"]
    consumers_per_competitor = mapping["addressable_consumers_per_competitor"]

    # district_key/block_name/business_type are already known-valid here
    # (competitor_provider only returns status="OK" for a valid combination),
    # so this call can't raise.
    opportunity = get_opportunity_analysis(district_key, block_name, business_type)
    benchmark = opportunity["benchmark_consumers_per_competitor"]

    # DemandIndex: how consumers-per-competitor compares to what this
    # category typically supports per business - above benchmark reads
    # under-served (score above 50), below it reads crowded (below 50).
    demand_index = normalize_linear(consumers_per_competitor, 0, benchmark * 2)

    # Raw density: fewer competitors relative to the block's observed
    # competition ceiling scores higher.
    density_score = normalize_inverse_linear(competitor_count, 0, scale_ceiling)

    # CompetitionScore blends both views: density alone isn't enough - a
    # dense-but-under-served block should not read as purely "bad", and a
    # sparse-but-already-saturated one should not read as purely "good".
    competition_score = round((density_score * 0.4) + (demand_index * 0.6), 2)

    opportunity_gap_score = round(demand_index - (100 - density_score), 2)

    conf = feature_confidence(envelope["provenance"])

    return {
        "score": competition_score,
        "confidence": conf,
        "density_score": density_score,
        "demand_index": demand_index,
        "opportunity_gap_score": opportunity_gap_score,
        "opportunity_gap_detail": opportunity["detail"],
        "is_underserved": opportunity["is_underserved"],
        "competitor_count": competitor_count,
        "consumers_per_competitor": consumers_per_competitor,
        "missing": [],
        "data_quality": envelope,
    }
