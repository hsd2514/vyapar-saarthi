"""Central, versioned configuration for the Hyper-Local Viability Engine.

Every weight, threshold, and confidence baseline used anywhere in the
viability engine modules (market_demand_engine.py, competition_engine.py,
location_engine.py, resource_engine.py, risk_engine.py,
financial_fit_engine.py, recommendation_engine.py) lives here - never
scattered inline - so one file fully determines a scoring run.
VIABILITY_ENGINE_VERSION plus the weight snapshot below are embedded in
every analysis response (see viability_engine.run_analysis), so a future
change to these numbers never silently changes how an already-returned
result should be read.

These are domain-informed baseline weights, not trained ML hyperparameters
- see README's "Machine Learning Boundary" section for why.
"""

from __future__ import annotations

VIABILITY_ENGINE_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Top-level dimension weights (spec: six viability dimensions).
# ---------------------------------------------------------------------------
VIABILITY_WEIGHTS = {
    "market_demand": 0.25,
    "financial_fit": 0.20,
    "competition": 0.15,
    "location_infrastructure": 0.15,
    "resource_availability": 0.10,
    "risk_seasonality": 0.15,
}
assert abs(sum(VIABILITY_WEIGHTS.values()) - 1.0) < 1e-9, "VIABILITY_WEIGHTS must sum to 1.0"

# Market Demand sub-weights.
MARKET_DEMAND_SUB_WEIGHTS = {
    "population_potential": 0.20,
    "demand_estimate": 0.20,
    "target_customer_fit": 0.15,
    "growth_trend": 0.15,
    "market_activity": 0.15,
    "purchasing_power": 0.15,
}
assert abs(sum(MARKET_DEMAND_SUB_WEIGHTS.values()) - 1.0) < 1e-9

# Location & Infrastructure sub-weights.
LOCATION_SUB_WEIGHTS = {
    "accessibility": 0.20,
    "transport": 0.15,
    "market_proximity": 0.15,
    "electricity": 0.15,
    "water": 0.10,
    "connectivity": 0.10,
    "business_specific_infrastructure": 0.15,
}
assert abs(sum(LOCATION_SUB_WEIGHTS.values()) - 1.0) < 1e-9

# Provenance -> baseline confidence (0-1). A feature's confidence is
# anchored to this table - documented here so it is never an unexplained
# per-call guess. USER_PROVIDED is highest (the entrepreneur's own figures);
# DEMO (today's only data source - see city_data.py) sits in the middle:
# structured and internally consistent, but explicitly not live/verified.
PROVENANCE_BASE_CONFIDENCE = {
    "VERIFIED_EXTERNAL": 0.95,
    "USER_PROVIDED": 0.90,
    "ESTIMATED": 0.60,
    "ASSUMPTION": 0.40,
    "DEMO": 0.55,
    "UNAVAILABLE": 0.0,
}

# Hard safety-gate thresholds (spec: hard constraints must never be hidden
# by a weighted average). Configurable - not buried in recommendation_engine.py.
HARD_CONSTRAINTS = {
    "min_dscr": 1.2,                 # a commonly used conservative repayment-capacity threshold, not an official regulatory figure
    "min_confidence": 0.40,          # below this, evidence is too thin to advise on
    "max_debt_burden_ratio": 0.50,   # existing EMI / monthly household income
    "critical_infrastructure_score": 25,  # location score below this (with real confidence behind it) reads as operationally unviable
}

# Risk severity bands (0-100 risk score -> label). Configurable.
RISK_SEVERITY_BANDS = [
    (0, 20, "VERY_LOW"),
    (21, 40, "LOW"),
    (41, 60, "MODERATE"),
    (61, 80, "HIGH"),
    (81, 100, "VERY_HIGH"),
]

# Recommendation thresholds. Configurable - see recommendation_engine.py for
# how these combine with hard constraints (constraints can only downgrade a
# score-based verdict, never upgrade one).
RECOMMENDATION_THRESHOLDS = {
    "proceed_min_score": 75,
    "proceed_with_caution_min_score": 60,
    "reduce_scale_market_min_score": 65,
}

# Used whenever a dimension has no usable data at all - a documented neutral
# midpoint, never an invented "good" or "bad" guess. Confidence for that
# dimension is set separately (and low), so the neutral score never hides
# the fact that the number is a fallback, not a measurement.
NEUTRAL_FALLBACK_SCORE = 50.0
