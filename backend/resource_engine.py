"""Resource Availability Engine - 10% of the overall score. Business-specific
by design (business_category_config.py) - NOT the same checklist for every
business. No real per-block resource-availability data source exists
anywhere in this app yet, so this never invents availability: it returns
the category's resource checklist with every item marked UNAVAILABLE, a
documented neutral fallback score, and low confidence, and feeds
"resource_availability" into missing_information rather than faking a score.
"""

from __future__ import annotations

from business_category_config import get_business_category_config
from viability_config import NEUTRAL_FALLBACK_SCORE

# Low but non-zero: the checklist itself (which resources actually matter
# for this category) is real, curated content, even though this app has no
# way to measure whether any specific one is actually available locally yet.
RESOURCE_DATA_CONFIDENCE = 0.15


def compute_resource_availability(business_type: str) -> dict:
    category = get_business_category_config(business_type)
    if not category:
        return {
            "score": NEUTRAL_FALLBACK_SCORE,
            "confidence": 0.0,
            "checklist": [],
            "missing": ["resource_availability"],
        }

    checklist = [
        {
            **item,
            "status": "UNAVAILABLE",
            "note": "No verified local resource-availability data source yet - validate this locally before investing.",
        }
        for item in category["resource_checklist"]
    ]

    return {
        "score": NEUTRAL_FALLBACK_SCORE,
        "confidence": RESOURCE_DATA_CONFIDENCE,
        "checklist": checklist,
        "missing": ["resource_availability"],
    }
