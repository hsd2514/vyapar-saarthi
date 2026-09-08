"""Reusable 0-100 normalization helpers shared by every scoring engine, so
normalization logic is never duplicated or allowed to drift per-engine.
Any threshold passed to these functions must come from viability_config.py
or be computed from the existing dataset (documented at the call site) -
never an unexplained magic number inline.
"""

from __future__ import annotations


def normalize_linear(value: float, min_value: float, max_value: float) -> float:
    """Linear 0-100 normalization, clipped to the [min_value, max_value] band.
    Falls back to a neutral 50 if the band is degenerate (max <= min)."""
    if max_value <= min_value:
        return 50.0
    clipped = max(min_value, min(value, max_value))
    return round((clipped - min_value) / (max_value - min_value) * 100, 2)


def normalize_inverse_linear(value: float, min_value: float, max_value: float) -> float:
    """Like normalize_linear, but a higher raw value means a lower score
    (e.g. distance, volatility, competitor density) - 100 at min_value,
    0 at max_value."""
    return round(100 - normalize_linear(value, min_value, max_value), 2)


def normalize_percentile(value: float, sample: list[float]) -> float:
    """Percentile-rank normalization against a real sample of comparable
    values, per the spec's 'percentile normalization when sufficient data
    exists' guidance. Falls back to a neutral 50 if the sample is too small
    to be statistically meaningful (fewer than 3 points)."""
    if len(sample) < 3:
        return 50.0
    sorted_sample = sorted(sample)
    rank = sum(1 for s in sorted_sample if s <= value)
    return round(rank / len(sorted_sample) * 100, 2)
