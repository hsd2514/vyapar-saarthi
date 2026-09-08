"""Confidence Engine - how much to trust a computed dimension score, kept
entirely separate from the score itself. Combines:

1. Completeness - how many of a dimension's expected features actually had
   usable data.
2. Source quality - how trustworthy each available feature's provenance is
   (viability_config.PROVENANCE_BASE_CONFIDENCE).

This is a documented, deliberately simple combination - not a trained model.
Freshness/geographic-precision/cross-source-consistency (spec's fuller
confidence model) aren't separately modelled yet because every current data
source is a single static snapshot with no timestamps or competing sources
to compare against; the hook is here (dimension_confidence takes a list of
per-feature confidences) for those signals to feed in once real, timestamped,
multi-source data exists.
"""

from __future__ import annotations

from viability_config import PROVENANCE_BASE_CONFIDENCE


def feature_confidence(provenance: str) -> float:
    """A single feature's confidence is anchored to its provenance."""
    return PROVENANCE_BASE_CONFIDENCE.get(provenance, 0.0)


def dimension_confidence(feature_confidences: list[float], expected_feature_count: int) -> float:
    """A dimension's confidence = (average confidence of the features that
    were actually available) x (completeness = available / expected).
    A dimension backed by 1 of 5 expected features at 0.9 confidence each is
    NOT 0.9 confident overall - missing features must drag the score down,
    not be silently ignored."""
    if expected_feature_count <= 0 or not feature_confidences:
        return 0.0
    completeness = min(len(feature_confidences) / expected_feature_count, 1.0)
    average_source_confidence = sum(feature_confidences) / len(feature_confidences)
    return round(average_source_confidence * completeness, 4)


def overall_confidence(dimension_confidences: dict[str, float], weights: dict[str, float]) -> float:
    """Overall confidence is the viability-weight-weighted average of each
    dimension's own confidence - a dimension that carries more weight in the
    final score also carries more weight in how confident the result is
    overall."""
    total_weight = sum(weights.get(k, 0.0) for k in dimension_confidences)
    if total_weight <= 0:
        return 0.0
    weighted_sum = sum(dimension_confidences[k] * weights.get(k, 0.0) for k in dimension_confidences)
    return round(weighted_sum / total_weight, 4)
