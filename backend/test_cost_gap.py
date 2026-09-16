"""Tests for unit_cost_data.py and cost_gap.py - the required-vs-eligible
project cost feature. Like test_deterministic.py, every case is checked
against a hand-computed figure: the whole point of this feature is that
the number on screen is the bank's own number, re-derivable by hand."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cost_gap import calc_cost_gap, required_project_cost
from main import app
from unit_cost_data import DAIRY_VARIANTS, ESTIMATED_PROFILES, PROVENANCE_ESTIMATED, PROVENANCE_VERIFIED, get_unit_cost_profile

client = TestClient(app)

# NABARD Maharashtra Unit Cost 2026-27, "Total Outlay" per 2-animal unit,
# read straight off pp. 35-42 of the booklet. The shed is excluded there.
BOOKLET_TOTALS = {
    "murrah": 272_300,
    "hf_crossbred": 217_840,
    "gir": 209_400,
    "tharparkar": 186_960,
    "jersey_crossbred": 165_400,
    "pandharpuri": 167_400,
    "haryana_rathi": 163_020,
    "non_descript": 131_320,
}


# ---------------------------------------------------------------------------
# Data integrity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key,total", BOOKLET_TOTALS.items())
def test_dairy_variant_reconciles_to_booklet_total_outlay(key, total):
    profile = get_unit_cost_profile("dairy", key)
    assert profile is not None and profile["provenance"] == PROVENANCE_VERIFIED
    without_shed = required_project_cost(profile, include_optional=False)["project_cost"]
    assert without_shed == total


def test_dairy_shed_is_the_only_optional_line_and_is_derived_not_booklet():
    for v in DAIRY_VARIANTS:
        optional = [i for i in v["items"] if i["kind"] == "optional"]
        assert len(optional) == 1 and "shed" in optional[0]["name"].lower()
        assert optional[0]["amount"] == 120 * 400  # 60 sq ft/animal x 2 @ Rs 400


def test_every_app_category_has_a_profile_and_non_dairy_is_labelled_estimated():
    for bt in ("vendor", "dairy", "textiles", "retail", "handicrafts", "food_stall"):
        p = get_unit_cost_profile(bt)
        assert p is not None, bt
        assert p["provenance"] == (PROVENANCE_VERIFIED if bt == "dairy" else PROVENANCE_ESTIMATED)
        assert all(i["amount"] > 0 for i in p["items"])
    for profiles in ESTIMATED_PROFILES.values():
        for p in profiles:
            assert "not an official" in p["source"]


def test_unknown_variant_falls_back_to_first_profile():
    assert get_unit_cost_profile("dairy", "no-such-breed")["key"] == "murrah"
    assert get_unit_cost_profile("poultry") is None


# ---------------------------------------------------------------------------
# Scaling
# ---------------------------------------------------------------------------

def test_scaling_one_animal_halves_per_unit_lines_and_keeps_fixed_ones():
    murrah = get_unit_cost_profile("dairy", "murrah")
    two = required_project_cost(murrah, 2, include_optional=False)
    one = required_project_cost(murrah, 1, include_optional=False)
    assert two["project_cost"] == 272_300
    assert one["project_cost"] == 136_150  # every dairy line is per-animal
    tailoring = get_unit_cost_profile("textiles")
    one_machine = required_project_cost(tailoring, 1)
    machine_line = next(i for i in one_machine["items"] if "Sewing machine" in i["name"])
    interlock = next(i for i in one_machine["items"] if "Interlock" in i["name"])
    assert machine_line["amount"] == 16_500 and interlock["amount"] == 20_000


def test_scale_is_clamped_to_profile_bounds():
    murrah = get_unit_cost_profile("dairy", "murrah")
    assert required_project_cost(murrah, 0)["scale_count"] == 1
    assert required_project_cost(murrah, 99)["scale_count"] == 10


# ---------------------------------------------------------------------------
# The gap and its closers - the briefing's worked example
# ---------------------------------------------------------------------------

def test_worked_example_two_buffaloes_on_twenty_thousand_margin():
    r = calc_cost_gap("dairy", 20_000, "murrah", include_optional=False)
    assert r["status"] == "OK"
    assert r["eligible"]["project_cost"] == 200_000
    assert r["required"]["project_cost"] == 272_300
    assert r["gap"]["amount"] == 72_300 and not r["gap"]["covered"]

    closers = {c["id"]: c for c in r["closers"]}
    # 1. bring 10% of the real cost
    assert closers["raise_margin"]["margin_needed"] == 27_230
    assert closers["raise_margin"]["extra_margin"] == 7_230
    # 2. one buffalo (Rs 1,36,150) fits inside the Rs 2,00,000 eligibility
    assert closers["scale_down"]["fits"] and closers["scale_down"]["scale_count"] == 1
    assert closers["scale_down"]["required_project_cost"] == 136_150
    # 3. NABARD's dairy subsidy at 25% of Rs 2,72,300 covers the Rs 72,300 gap (just)
    deds = next(s for s in closers["stack_subsidy"]["schemes"] if s["id"] == "deds_dairy")
    assert deds["estimated_subsidy"] == 68_075 and deds["covers_gap"] is False
    pmegp = next(s for s in closers["stack_subsidy"]["schemes"] if s["id"] == "pmegp")
    assert pmegp["estimated_subsidy"] == 68_075


def test_gap_is_covered_when_margin_is_enough_and_scale_down_is_omitted():
    r = calc_cost_gap("dairy", 40_000, "murrah")  # eligible 4,00,000 vs required 3,20,300 with shed
    assert r["gap"]["covered"] and r["gap"]["amount"] == 0 and r["gap"]["surplus"] == 79_700
    assert [c["id"] for c in r["closers"]] == ["raise_margin", "stack_subsidy"]
    assert r["closers"][0]["extra_margin"] == 0


def test_scale_down_reports_when_even_the_smallest_unit_does_not_fit():
    r = calc_cost_gap("dairy", 5_000, "murrah", include_optional=False)  # eligible 50,000
    sd = next(c for c in r["closers"] if c["id"] == "scale_down")
    assert not sd["fits"] and sd["scale_count"] == 1 and sd["gap_at_smallest"] == 86_150


def test_optional_shed_toggle_changes_required_cost():
    with_shed = calc_cost_gap("dairy", 20_000, "murrah", include_optional=True)["required"]["project_cost"]
    without = calc_cost_gap("dairy", 20_000, "murrah", include_optional=False)["required"]["project_cost"]
    assert with_shed - without == 48_000


def test_available_variants_listed_for_the_breed_picker():
    r = calc_cost_gap("dairy", 20_000)
    keys = [v["key"] for v in r["profile"]["available_variants"]]
    assert keys[0] == "murrah" and "non_descript" in keys and len(keys) == 8


# ---------------------------------------------------------------------------
# Where the 10% comes from
# ---------------------------------------------------------------------------

def test_moneylender_margin_shows_true_cost_stacked_on_scheme_emi():
    r = calc_cost_gap("dairy", 20_000, "murrah", margin_source="moneylender", moneylender_monthly_rate_pct=3.0, moneylender_tenure_months=12)
    ml = r["margin_source"]["moneylender"]
    assert ml["monthly_interest"] == 600.0                      # 3% of 20,000, every month
    assert ml["total_interest"] == 7_200.0 and ml["interest_as_pct_of_margin"] == 36.0
    assert ml["monthly_outgo"] == pytest.approx(600 + 20_000 / 12, abs=0.01)
    assert ml["scheme_monthly_emi"] is not None
    assert ml["combined_monthly_after_moratorium"] == pytest.approx(ml["monthly_outgo"] + ml["scheme_monthly_emi"], abs=0.01)


def test_savings_margin_has_no_moneylender_block():
    r = calc_cost_gap("dairy", 20_000, "murrah", margin_source="savings")
    assert r["margin_source"] == {"source": "savings"}


def test_invalid_margin_source_rejected():
    with pytest.raises(ValueError):
        calc_cost_gap("dairy", 20_000, margin_source="lottery")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

def test_endpoint_round_trip_and_validation():
    res = client.post("/api/cost-gap", json={"business_type": "dairy", "available_margin_capital": 20000, "variant_key": "murrah", "include_optional": False})
    assert res.status_code == 200
    body = res.json()
    assert body["gap"]["amount"] == 72_300 and body["profile"]["provenance"] == "VERIFIED_EXTERNAL"

    assert client.post("/api/cost-gap", json={"business_type": "dairy", "available_margin_capital": 0}).status_code == 400
    assert client.post("/api/cost-gap", json={"business_type": "poultry", "available_margin_capital": 20000}).status_code == 422
    assert client.post("/api/cost-gap", json={"business_type": "dairy", "available_margin_capital": 20000, "margin_source": "lottery"}).status_code == 422

    est = client.post("/api/cost-gap", json={"business_type": "retail", "available_margin_capital": 10000}).json()
    assert est["profile"]["provenance"] == "ESTIMATED" and est["required"]["project_cost"] == 167_000
