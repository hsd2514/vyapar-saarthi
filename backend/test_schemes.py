import pytest

from schemes import GOV_SCHEMES, match_schemes


def test_returns_all_schemes_plus_margin_money():
    results = match_schemes(200_000)
    ids = {r["id"] for r in results}
    assert ids == {s["id"] for s in GOV_SCHEMES} | {"margin_money"}


def test_sorted_descending_by_score():
    results = match_schemes(200_000)
    scores = [r["match_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_small_project_cost_favours_shishu_or_margin_money():
    results = match_schemes(40_000)
    top = results[0]
    assert top["id"] in {"mudra_shishu", "margin_money", "pm_svanidhi"}


def test_large_project_cost_favours_stand_up_india():
    results = match_schemes(5_000_000)
    top_ids = [r["id"] for r in results[:2]]
    assert "stand_up_india" in top_ids


def test_score_breakdown_sums_to_match_score():
    results = match_schemes(300_000)
    for r in results:
        assert r["match_score"] == pytest.approx(sum(r["score_breakdown"].values()), abs=0.1)


def test_score_within_bounds():
    for cost in [10_000, 100_000, 1_000_000, 10_000_000]:
        for r in match_schemes(cost):
            assert 0 <= r["match_score"] <= 100


def test_portal_urls_present():
    for r in match_schemes(500_000):
        assert r["portal_url"].startswith("https://")


def test_in_band_flag_correct_for_extremes():
    results = match_schemes(30_000)
    shishu = next(r for r in results if r["id"] == "mudra_shishu")
    assert shishu["in_band"] is True
    stand_up = next(r for r in results if r["id"] == "stand_up_india")
    assert stand_up["in_band"] is False


def test_business_type_specific_scheme_ranks_above_same_scheme_for_wrong_category():
    """PM SVANidhi is built for vendors - a vendor's category_match score for it
    should beat a handicrafts business's category_match score for the same
    scheme, at the same project cost."""
    vendor_results = match_schemes(30_000, business_type="vendor")
    handicrafts_results = match_schemes(30_000, business_type="handicrafts")
    vendor_svanidhi = next(r for r in vendor_results if r["id"] == "pm_svanidhi")
    handicrafts_svanidhi = next(r for r in handicrafts_results if r["id"] == "pm_svanidhi")
    assert vendor_svanidhi["score_breakdown"]["category_match"] > handicrafts_svanidhi["score_breakdown"]["category_match"]


def test_dairy_scheme_only_targets_dairy():
    results = match_schemes(200_000)
    deds = next(r for r in results if r["id"] == "deds_dairy")
    assert deds["business_types"] == ["dairy"]


def test_general_purpose_scheme_has_no_business_type_restriction():
    results = match_schemes(200_000)
    pmegp = next(r for r in results if r["id"] == "pmegp")
    assert pmegp["business_types"] is None


def test_category_specific_schemes_present_for_each_business_type():
    """Every one of the app's 6 business categories should have at least one
    scheme in the catalogue that is either general-purpose or built specifically
    for it - never a category left with zero real matches."""
    all_types = {"vendor", "dairy", "textiles", "retail", "handicrafts", "food_stall"}
    covered = set()
    for scheme in GOV_SCHEMES:
        if scheme["business_types"] is None:
            covered |= all_types
        else:
            covered |= set(scheme["business_types"])
    assert covered == all_types
