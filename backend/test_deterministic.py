"""Tests for deterministic.py - every financial calculation and rule in
this app. This file is the most important test coverage in the repo: the
whole pitch is that these numbers are auditable and re-derivable by hand,
so every function here should be checked against a hand-computed case, not
just "it ran without crashing"."""

from __future__ import annotations

import pytest

from city_data import BUSINESS_TYPES, CITY_DATA
from deterministic import (
    MICRO_FINANCE_SCHEME,
    TERM_LOAN_SCHEME,
    calc_emi,
    calc_financial_structuring,
    calc_repayment_schedule,
    calc_working_capital_by_phase,
    generate_feasibility_report,
)


# ---------------------------------------------------------------------------
# calc_financial_structuring
# ---------------------------------------------------------------------------

def test_financial_structuring_matches_the_ps_worked_example():
    """The PS's own example: margin Rs 1,00,000 -> project cost Rs 10,00,000
    -> loan Rs 9,00,000, and that project cost lands in the Term Loan tier."""
    result = calc_financial_structuring(100_000)
    assert result["project_cost"] == pytest.approx(1_000_000)
    assert result["max_loan_amount"] == pytest.approx(900_000)
    assert result["scheme"]["id"] == "term_loan"
    assert result["loan_capped"] is False


def test_financial_structuring_micro_finance_tier():
    """A small margin capital should land in Micro Finance, not Term Loan."""
    result = calc_financial_structuring(10_000)
    assert result["project_cost"] == pytest.approx(100_000)
    assert result["scheme"]["id"] == "micro_finance"
    assert result["max_loan_amount"] == pytest.approx(90_000)


def test_financial_structuring_at_the_micro_finance_boundary():
    """Project cost exactly at Rs 1,40,000 (margin = 14,000) is defined by
    the PS as still Micro Finance ('up to Rs 1.4 lakh'), not Term Loan."""
    result = calc_financial_structuring(14_000)
    assert result["project_cost"] == pytest.approx(140_000)
    assert result["scheme"]["id"] == "micro_finance"


def test_financial_structuring_just_above_the_micro_finance_boundary():
    """One rupee of margin more should tip into Term Loan."""
    result = calc_financial_structuring(14_001)
    assert result["scheme"]["id"] == "term_loan"


def test_financial_structuring_above_the_50_lakh_ceiling_matches_no_scheme():
    """Margin capital implying a project cost over Rs 50,00,000 should
    return scheme=None rather than silently picking a tier."""
    result = calc_financial_structuring(6_000_000)
    assert result["project_cost"] > TERM_LOAN_SCHEME["project_cost_max"]
    assert result["scheme"] is None
    assert result["max_loan_amount"] is None


def test_financial_structuring_caps_the_loan_at_the_tier_ceiling():
    """A margin capital just under the Micro Finance project-cost ceiling
    should produce an uncapped loan very close to (but under) the tier's
    loan cap - and loan_capped should only be True once 90% of project cost
    actually exceeds the cap."""
    # project cost 1,39,999 -> 90% = 125,999.1, just over the 125,000 cap
    result = calc_financial_structuring(13_999.9)
    assert result["scheme"]["id"] == "micro_finance"
    assert result["max_loan_amount"] == pytest.approx(MICRO_FINANCE_SCHEME["loan_cap"])
    assert result["loan_capped"] is True


# ---------------------------------------------------------------------------
# calc_emi
# ---------------------------------------------------------------------------

def test_calc_emi_against_a_hand_computed_value():
    """EMI for Rs 100,000 at 12% p.a. over 12 months should be close to the
    textbook answer of ~Rs 8,884.88 (standard reducing-balance formula)."""
    emi = calc_emi(100_000, 12.0, 12)
    assert emi == pytest.approx(8884.88, rel=1e-3)


def test_calc_emi_zero_interest_is_a_flat_split():
    """At 0% interest, EMI should just be principal / tenure_months."""
    emi = calc_emi(120_000, 0.0, 12)
    assert emi == pytest.approx(10_000)


# ---------------------------------------------------------------------------
# calc_repayment_schedule
# ---------------------------------------------------------------------------

def test_repayment_schedule_moratorium_quarters_have_zero_due():
    schedule = calc_repayment_schedule(principal=90_000, annual_rate_pct=6.5, tenure_months=36, moratorium_months=3)
    moratorium_quarters = [q for q in schedule["quarters"] if q["is_moratorium_only"]]
    assert len(moratorium_quarters) == 1  # the first quarter is fully within the 3-month moratorium
    assert moratorium_quarters[0]["amount_due"] == 0
    assert moratorium_quarters[0]["repayment_months"] == 0


def test_repayment_schedule_quarters_sum_to_total_repayment():
    """The sum of every quarter's amount_due should equal monthly_emi *
    repayment_months (i.e. total_repayment), within floating-point rounding."""
    schedule = calc_repayment_schedule(principal=900_000, annual_rate_pct=8.0, tenure_months=84, moratorium_months=6)
    quarters_sum = sum(q["amount_due"] for q in schedule["quarters"])
    assert quarters_sum == pytest.approx(schedule["total_repayment"], rel=1e-9)
    assert quarters_sum == pytest.approx(schedule["monthly_emi"] * schedule["repayment_months"], rel=1e-9)


def test_repayment_schedule_covers_every_month_of_the_tenure():
    """Every month in tenure_months should be accounted for across the
    quarters - none dropped, none double-counted."""
    schedule = calc_repayment_schedule(principal=90_000, annual_rate_pct=6.5, tenure_months=36, moratorium_months=3)
    total_months_covered = sum(q["months_covered"] for q in schedule["quarters"])
    assert total_months_covered == 36


def test_repayment_schedule_total_interest_is_repayment_minus_principal():
    schedule = calc_repayment_schedule(principal=90_000, annual_rate_pct=6.5, tenure_months=36, moratorium_months=3)
    assert schedule["total_interest"] == pytest.approx(schedule["total_repayment"] - schedule["principal"])


# ---------------------------------------------------------------------------
# calc_working_capital_by_phase
# ---------------------------------------------------------------------------

def test_working_capital_after_moratorium_is_before_plus_emi():
    result = calc_working_capital_by_phase(monthly_operational_cost=10_000, inventory_days=15, receivable_days=5, monthly_emi=3_000)
    assert result["monthly_cash_needed_after_moratorium"] - result["monthly_cash_needed_during_moratorium"] == pytest.approx(3_000)


def test_working_capital_cash_cycle_days_is_inventory_plus_receivable():
    result = calc_working_capital_by_phase(monthly_operational_cost=10_000, inventory_days=15, receivable_days=5, monthly_emi=0)
    assert result["cash_cycle_days"] == 20


# ---------------------------------------------------------------------------
# generate_feasibility_report
# ---------------------------------------------------------------------------

def test_feasibility_report_raises_for_an_unknown_block():
    with pytest.raises(ValueError):
        generate_feasibility_report("latur", "NotARealBlock", "vendor")


def test_feasibility_report_raises_for_an_unknown_district():
    with pytest.raises(ValueError):
        generate_feasibility_report("not_a_real_district", "Latur", "vendor")


@pytest.mark.parametrize("district_key", list(CITY_DATA.keys()))
@pytest.mark.parametrize("business_type", [bt["value"] for bt in BUSINESS_TYPES])
def test_feasibility_report_addressable_consumers_never_exceed_population(district_key, business_type):
    """Sanity check across every district/business-type combination: the
    number of people the report says could be customers should never exceed
    the block's actual population."""
    district = CITY_DATA[district_key]
    for block_name in district["blocks"]:
        report = generate_feasibility_report(district_key, block_name, business_type)
        assert report["market_reach"]["addressable_consumers"] <= report["market_reach"]["block_population"]


def test_feasibility_report_opportunity_signal_is_not_constant():
    """Regression test for a real bug caught earlier: the under-served
    threshold used to be a flat number that made every single combination
    read as under-served. There should be genuine variety across blocks."""
    district_key = "latur"
    business_type = "vendor"
    signals = {
        block_name: generate_feasibility_report(district_key, block_name, business_type)["opportunity_analysis"]["is_underserved"]
        for block_name in CITY_DATA[district_key]["blocks"]
    }
    assert len(set(signals.values())) > 1, "Expected a mix of under-served and competitive signals, got a constant"
