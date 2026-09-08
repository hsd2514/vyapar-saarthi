"""Standardized data-provider envelope around the app's existing data
lookups (deterministic.py / city_data.py). Every provider function here
returns the same shape:

    {data, source, fetched_at, geographic_level, confidence, provenance, status}

Today every provider is backed by city_data.py's illustrative static
tables - explicitly documented there as NOT live pulls - so `provenance`
is always "DEMO" and `status` is "OK" (or "UNAVAILABLE" if the requested
district/block/business combination doesn't exist in city_data.py).

A real external provider (data.gov.in, Agmarknet, ...) would implement this
same envelope shape and be swapped in here once DATA_GOV_API_KEY /
AGMARKNET_API_KEY are actually set in the environment - see
is_real_data_gov_available()/is_real_agmarknet_available() below for the
documented extension point. Nothing here ever fabricates a live-looking
response when a real key is absent.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from city_data import get_block, get_infrastructure
from deterministic import get_competitor_mapping, get_market_reach, get_product_market_value
from viability_config import PROVENANCE_BASE_CONFIDENCE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _envelope(data, source: str, geographic_level: str, provenance: str, status: str = "OK", confidence: float | None = None) -> dict:
    return {
        "data": data,
        "source": source,
        "fetched_at": _now(),
        "geographic_level": geographic_level,
        "confidence": PROVENANCE_BASE_CONFIDENCE[provenance] if confidence is None else confidence,
        "provenance": provenance,
        "status": status,
    }


def is_real_data_gov_available() -> bool:
    """True once a real data.gov.in integration is wired AND DATA_GOV_API_KEY
    is set. No real integration exists yet this phase - this always reads
    the key so the extension point is real, not decorative."""
    return bool(os.environ.get("DATA_GOV_API_KEY"))


def is_real_agmarknet_available() -> bool:
    """Same extension point as is_real_data_gov_available(), for Agmarknet."""
    return bool(os.environ.get("AGMARKNET_API_KEY"))


_DEMO_SOURCE = "city_data.py (illustrative, static - see module docstring)"


def population_provider(district_key: str, block_name: str) -> dict:
    block = get_block(district_key, block_name)
    if not block:
        return _envelope(None, _DEMO_SOURCE, "block", "UNAVAILABLE", status="UNAVAILABLE", confidence=0.0)
    return _envelope({"population": block["population"]}, _DEMO_SOURCE, "block", "DEMO")


def market_demand_provider(district_key: str, block_name: str, business_type: str) -> dict:
    try:
        reach = get_market_reach(district_key, block_name, business_type)
    except ValueError:
        return _envelope(None, _DEMO_SOURCE, "block", "UNAVAILABLE", status="UNAVAILABLE", confidence=0.0)
    return _envelope(reach, _DEMO_SOURCE, "block", "DEMO")


def competitor_provider(district_key: str, block_name: str, business_type: str) -> dict:
    try:
        mapping = get_competitor_mapping(district_key, block_name, business_type)
    except ValueError:
        return _envelope(None, _DEMO_SOURCE, "block", "UNAVAILABLE", status="UNAVAILABLE", confidence=0.0)
    return _envelope(mapping, _DEMO_SOURCE, "block", "DEMO")


def pricing_provider(district_key: str, block_name: str, business_type: str) -> dict:
    try:
        pricing = get_product_market_value(district_key, block_name, business_type)
    except ValueError:
        pricing = None
    if pricing is None:
        return _envelope(None, _DEMO_SOURCE, "district", "UNAVAILABLE", status="UNAVAILABLE", confidence=0.0)
    return _envelope(pricing, _DEMO_SOURCE, "district", "DEMO")


def infrastructure_provider(district_key: str, block_name: str) -> dict:
    block = get_block(district_key, block_name)
    infra = get_infrastructure(block_name) if block else None
    if not infra:
        return _envelope(None, _DEMO_SOURCE, "block", "UNAVAILABLE", status="UNAVAILABLE", confidence=0.0)
    return _envelope(infra, _DEMO_SOURCE, "block", "DEMO")
