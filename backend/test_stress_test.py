"""Tests for seasonality_data.py and stress_test.py - the worst-quarter
stress test. Hand-computed cases throughout, in the spirit of
test_deterministic.py: the reserve target and survival months are
numbers a person will act on, so they must be re-derivable by hand."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from deterministic import calc_repayment_schedule
from main import app
from seasonality_data import SEASONALITY, SHOCKS
from stress_test import run_stress_test

client = TestClient(app)

CATEGORIES = ("vendor", "dairy", "textiles", "retail", "handicrafts", "food_stall")


# ---------------------------------------------------------------------------
# Data integrity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bt", CATEGORIES)
def test_every_category_has_a_normalised_index_and_three_shocks(bt):
    idx = SEASONALITY[bt]["index"]
    assert len(idx) == 12 and all(0.5 <= x <= 1.5 for x in idx)
    assert sum(idx) == pytest.approx(12.0, abs=1e-9)  # multipliers on an average month
    assert SEASONALITY[bt]["reasoning"]
    ids = [s["id"] for s in SHOCKS[bt]]
    assert ids == ["asset_loss", "no_sales", "bad_season"]
    for s in SHOCKS[bt]:
        assert 0.0 <= s["revenue_multiplier"] <= 1.0 and s["months"] >= 1 and s["detail"]


# ---------------------------------------------------------------------------
# Core arithmetic - a flat-income sanity case, then the seasonal one
# ---------------------------------------------------------------------------

def _term_loan(**kw):
    """Term Loan Scheme terms from the PS: 8%, 84 months, 6-month holiday."""
    base = dict(business_type="dairy", principal=180_000, annual_rate_pct=8.0, tenure_months=84, moratorium_months=6,
                avg_monthly_revenue=20_000, monthly_operating_cost=12_000, start_month=1)
    base.update(kw)
    return run_stress_test(**base)


def test_horizon_is_moratorium_plus_one_seasonal_year_and_quarters_follow_calendar():
    r = _term_loan(start_month=4)  # loan starts in April
    assert r["inputs"]["horizon_months"] == 18
    assert [m["label"] for m in r["months"][:3]] == ["Apr", "May", "Jun"]
    assert r["quarters"][0]["label"] == "Apr-Jun" and r["quarters"][0]["is_moratorium_only"]
    assert r["quarters"][2]["label"] == "Oct-Dec" and not r["quarters"][2]["is_moratorium_only"]
    assert r["first_instalment_quarter"]["quarter"] == 3


def test_emi_matches_the_schedule_and_is_zero_in_the_holiday():
    r = _term_loan()
    emi = calc_repayment_schedule(180_000, 8.0, 84, 6)["monthly_emi"]
    assert r["inputs"]["monthly_emi"] == round(emi, 2)
    assert all(m["emi"] == 0 for m in r["months"][:6])
    assert all(m["emi"] == round(emi) for m in r["months"][6:])


def test_lean_quarter_shortfall_sets_the_reserve_even_when_earlier_surplus_would_cover_it():
    # Rs 20,000 in, Rs 14,000 out from January: the balance never goes
    # negative because Oct-Dec banks a surplus - but Apr-Jun of year 2 is
    # still short on its own, and that is the number to keep aside.
    r = _term_loan(avg_monthly_revenue=20_000, monthly_operating_cost=14_000, start_month=1)
    assert min(m["cumulative"] for m in r["months"]) >= 0
    assert r["worst_quarter"]["label"] == "Apr-Jun" and r["worst_quarter"]["shortfall"] > 0
    assert r["reserve_target"] == r["worst_quarter"]["shortfall"]
    assert r["verdict"] == "tight"  # under one quarter's instalments


def test_comfortable_when_surplus_always_covers_emi():
    # Rs 20,000 in, Rs 8,000 out: even the leanest dairy month (0.80 x 20,000 = 16,000)
    # leaves 8,000 before the ~Rs 2,700 EMI - never short.
    r = _term_loan(monthly_operating_cost=8_000)
    assert r["reserve_target"] == 0 and r["verdict"] == "comfortable"
    assert all(q["shortfall"] == 0 for q in r["quarters"])
    assert r["monthly_saving_during_moratorium"] == 0


def test_worst_quarter_is_the_lean_season_and_reserve_is_the_running_low_point():
    # Dairy, loan from January, revenue 15,000 avg, cost 13,000: the summer
    # quarter (Apr-Jun, index 0.85/0.80/0.80) is where the EMI cannot be met.
    r = _term_loan(avg_monthly_revenue=15_000, monthly_operating_cost=13_000, start_month=1)
    emi = r["inputs"]["monthly_emi"]
    # Quarter 3 = Jul-Sep is the first with instalments (moratorium Jan-Jun);
    # the leanest repayment quarter in the 18-month horizon is Apr-Jun of year 2.
    assert r["worst_quarter"]["label"] == "Apr-Jun"
    lean_surplus = 15_000 * (0.85 + 0.80 + 0.80) - 3 * 13_000  # = -2,250 before EMI
    assert r["worst_quarter"]["surplus_before_emi"] == pytest.approx(lean_surplus, abs=2)
    assert r["worst_quarter"]["shortfall"] == pytest.approx(3 * emi - lean_surplus, abs=3)
    # Reserve = the worst quarter's own shortfall, or the running balance's
    # low point if that is deeper - whichever is larger.
    lowest = min(m["cumulative"] for m in r["months"])
    assert r["reserve_target"] == max(r["worst_quarter"]["shortfall"], -lowest) and r["reserve_target"] > 0
    assert r["monthly_saving_during_moratorium"] == round(r["reserve_target"] / 6)
    assert r["verdict"] in ("tight", "at_risk")


def test_reserve_target_actually_prevents_a_negative_balance():
    r = _term_loan(avg_monthly_revenue=15_000, monthly_operating_cost=13_000)
    from stress_test import _simulate
    replay = _simulate(r["inputs"]["horizon_months"], 1, r["season"]["index"], 15_000, 13_000, r["inputs"]["monthly_emi"], 6, opening_cash=r["reserve_target"])
    assert min(m["cumulative"] for m in replay) >= -1  # rounding only


# ---------------------------------------------------------------------------
# Shocks
# ---------------------------------------------------------------------------

def test_shocks_start_at_first_instalment_and_report_survival_both_ways():
    r = _term_loan(avg_monthly_revenue=18_000, monthly_operating_cost=12_000)
    assert [s["id"] for s in r["shocks"]] == ["asset_loss", "no_sales", "bad_season"]
    for s in r["shocks"]:
        assert s["starts_in_month"] == 7  # month after the 6-month holiday
        # reserve_needed is the running low point under the shock; the base
        # reserve (which may be quarter-based and larger) counts against it.
        assert s["extra_reserve_over_base"] == max(0, s["reserve_needed"] - r["reserve_target"])
        assert s["survives_with_base_reserve"] == (s["survival_months_with_reserve"] is None)
        # Having the base reserve can only delay, never hasten, the day the money runs out.
        w, wr = s["survival_months_without_reserve"], s["survival_months_with_reserve"]
        assert wr is None or w is None or wr >= w
    no_sales = next(s for s in r["shocks"] if s["id"] == "no_sales")
    # Two months of zero milk income with costs continuing: 2 x 12,000 + 2 x EMI
    # against whatever the holiday months banked - the balance must dip.
    assert no_sales["survival_months_without_reserve"] is not None


def test_one_time_shock_cost_lands_in_the_first_shock_month():
    r = run_stress_test("textiles", 100_000, 8.0, 84, 6, 20_000, 10_000, 1)
    from seasonality_data import get_shocks
    from stress_test import _simulate
    machine = next(s for s in get_shocks("textiles") if s["id"] == "asset_loss")
    sim = _simulate(18, 1, r["season"]["index"], 20_000, 10_000, r["inputs"]["monthly_emi"], 6, 0.0, machine, 6)
    assert sim[6]["one_time_cost"] == 8_000 and sim[7]["one_time_cost"] == 0
    assert sim[6]["revenue"] == round(20_000 * r["season"]["index"][6] * 0.60)


def test_one_time_cost_in_months_scales_with_operating_cost():
    from seasonality_data import get_shocks
    from stress_test import _simulate
    spoil = next(s for s in get_shocks("retail") if s["id"] == "asset_loss")
    idx = SEASONALITY["retail"]["index"]
    sim = _simulate(3, 1, idx, 30_000, 16_000, 0.0, 0, 0.0, spoil, 0)
    assert sim[0]["one_time_cost"] == 8_000  # 0.5 x 16,000


# ---------------------------------------------------------------------------
# Validation and endpoint
# ---------------------------------------------------------------------------

def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        run_stress_test("poultry", 100_000, 8.0, 84, 6, 20_000, 10_000, 1)
    with pytest.raises(ValueError):
        _term_loan(start_month=13)


def test_endpoint_round_trip_and_validation():
    body = {"business_type": "dairy", "principal": 180000, "annual_rate_pct": 8.0, "tenure_months": 84, "moratorium_months": 6,
            "avg_monthly_revenue": 15000, "monthly_operating_cost": 13000, "start_month": 1}
    res = client.post("/api/stress-test", json=body)
    assert res.status_code == 200
    out = res.json()
    assert out["worst_quarter"]["label"] == "Apr-Jun" and out["season"]["provenance"] == "ASSUMPTION"
    assert len(out["shocks"]) == 3 and out["reserve_target"] > 0

    assert client.post("/api/stress-test", json={**body, "principal": 0}).status_code == 400
    assert client.post("/api/stress-test", json={**body, "start_month": 0}).status_code == 400
    assert client.post("/api/stress-test", json={**body, "business_type": "poultry"}).status_code == 422
