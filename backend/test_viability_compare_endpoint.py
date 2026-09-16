"""Tests for GET /api/viability/compare - the batch endpoint
BusinessComparisonPanel uses to add a sortable viability-score column to
its "compare all 6 categories" table.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_viability_compare_returns_all_six_business_types():
    resp = client.get("/api/viability/compare", params={"district": "latur", "block": "Nilanga", "available_margin_capital": 100000})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["by_type"].keys()) == {"vendor", "dairy", "textiles", "retail", "handicrafts", "food_stall"}


def test_viability_compare_scores_are_in_0_100_range():
    resp = client.get("/api/viability/compare", params={"district": "latur", "block": "Nilanga", "available_margin_capital": 100000})
    for entry in resp.json()["by_type"].values():
        assert entry is not None
        assert 0 <= entry["overall_score"] <= 100
        assert isinstance(entry["recommendation"], str)


def test_viability_compare_is_case_insensitive_on_block_name():
    """Regression guard for the same casing bug fixed in city_data.get_block -
    this batch endpoint must not reintroduce it."""
    resp = client.get("/api/viability/compare", params={"district": "latur", "block": "nilanga", "available_margin_capital": 100000})
    assert resp.status_code == 200
    assert all(v is not None for v in resp.json()["by_type"].values())


def test_viability_compare_rejects_unknown_district():
    resp = client.get("/api/viability/compare", params={"district": "not-a-district", "block": "Nilanga", "available_margin_capital": 100000})
    assert resp.status_code == 400
