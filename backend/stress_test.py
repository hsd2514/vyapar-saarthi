"""Worst-quarter stress test for a loan repayment plan.

The repayment schedule (deterministic.calc_repayment_schedule) says what
is due each quarter. This module asks whether the business can pay it in
the quarter it actually falls - by laying the category's seasonal income
pattern (seasonality_data.py) over the calendar months the loan runs
through - and then what happens if something goes wrong.

Two numbers come out that a person can act on:

  reserve_target   - the larger of (a) the worst repayment quarter's own
                     shortfall - what that quarter's income fails to cover
                     of its instalment - and (b) the cushion that keeps
                     the running balance from ever going below zero across
                     the free period plus one seasonal year of repayments.
                     (a) is there because households do not bank every
                     surplus rupee; the lean quarter has to be covered on
                     its own. Divided by the moratorium months, it is
                     "save this much a month during the holiday".
  survival_months  - under each named shock (an animal dies, two months
                     with no sales, a bad season), how many months from
                     the loan start before the balance goes negative -
                     with the reserve and without it - and how much more
                     reserve would be needed to ride the shock out.

Timing is deliberately pessimistic and stated: each shock starts in the
first month an instalment is due, the moment the field evidence says
borrowers are least prepared for (Field et al., AER 2013: grace periods
raise investment and default together).

Pure arithmetic. No LLM, no live data.
"""

from __future__ import annotations

from deterministic import calc_repayment_schedule
from seasonality_data import MONTH_ABBR, PROVENANCE, get_seasonality, get_shocks

REPAYMENT_MONTHS_IN_HORIZON = 12


def _label_span(cal_months: list[int]) -> str:
    """'Jul-Sep' for [7, 8, 9]; 'Dec-Feb' across a year end."""
    if not cal_months:
        return ""
    return f"{MONTH_ABBR[cal_months[0] - 1]}-{MONTH_ABBR[cal_months[-1] - 1]}" if len(cal_months) > 1 else MONTH_ABBR[cal_months[0] - 1]


def _simulate(
    horizon: int,
    start_month: int,
    index: list[float],
    avg_revenue: float,
    operating_cost: float,
    monthly_emi: float,
    moratorium_months: int,
    opening_cash: float = 0.0,
    shock: dict | None = None,
    shock_start: int = 0,
) -> list[dict]:
    """Month-by-month cash for `horizon` months from the loan start."""
    months = []
    balance = opening_cash
    for m in range(horizon):
        cal = (start_month - 1 + m) % 12 + 1
        revenue = avg_revenue * index[cal - 1]
        cost = operating_cost
        one_time = 0.0
        if shock and shock_start <= m < shock_start + shock["months"]:
            revenue *= shock["revenue_multiplier"]
            cost *= shock["cost_multiplier"]
            if m == shock_start:
                one_time = shock.get("one_time_cost", 0) or 0
                one_time += (shock.get("one_time_cost_months", 0) or 0) * operating_cost
        emi = 0.0 if m < moratorium_months else monthly_emi
        net = revenue - cost - emi - one_time
        balance += net
        months.append({
            "month": m + 1,
            "calendar_month": cal,
            "label": MONTH_ABBR[cal - 1],
            "revenue": round(revenue),
            "operating_cost": round(cost),
            "emi": round(emi),
            "one_time_cost": round(one_time),
            "net": round(net),
            "cumulative": round(balance),
            "is_moratorium": m < moratorium_months,
        })
    return months


def _reserve_needed(months: list[dict]) -> float:
    """The smallest opening cushion that keeps the running balance >= 0."""
    lowest = min(m["cumulative"] for m in months) if months else 0
    return float(max(0, -lowest))


def _survival(months: list[dict]) -> int | None:
    """First month the balance goes negative, or None if it never does."""
    for m in months:
        if m["cumulative"] < 0:
            return m["month"]
    return None


def run_stress_test(
    business_type: str,
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    moratorium_months: int,
    avg_monthly_revenue: float,
    monthly_operating_cost: float,
    start_month: int,
    capitalise_moratorium_interest: bool = False,
) -> dict:
    season = get_seasonality(business_type)
    if season is None:
        raise ValueError(f"No seasonality profile for business_type '{business_type}'")
    if not 1 <= start_month <= 12:
        raise ValueError("start_month must be 1-12")

    schedule = calc_repayment_schedule(principal, annual_rate_pct, tenure_months, moratorium_months, capitalise_moratorium_interest)
    monthly_emi = schedule["monthly_emi"]
    index = season["index"]
    horizon = min(tenure_months, moratorium_months + REPAYMENT_MONTHS_IN_HORIZON)

    base = _simulate(horizon, start_month, index, avg_monthly_revenue, monthly_operating_cost, monthly_emi, moratorium_months)

    # Quarters aligned to the schedule's own 3-month blocks, labelled by
    # calendar season so "Jul-Sep" means July to September.
    quarters = []
    for q in schedule["quarters"]:
        first = (q["quarter"] - 1) * 3
        block = base[first:first + q["months_covered"]]
        if not block:
            break
        revenue = sum(m["revenue"] for m in block)
        cost = sum(m["operating_cost"] for m in block)
        surplus_before_emi = revenue - cost
        due = round(q["amount_due"])
        quarters.append({
            "quarter": q["quarter"],
            "label": _label_span([m["calendar_month"] for m in block]),
            "revenue": revenue,
            "operating_cost": cost,
            "surplus_before_emi": surplus_before_emi,
            "amount_due": due,
            "shortfall": max(0, due - surplus_before_emi),
            "is_moratorium_only": q["is_moratorium_only"],
            "season_index": round(sum(index[m["calendar_month"] - 1] for m in block) / len(block), 2),
        })

    repayment_quarters = [q for q in quarters if not q["is_moratorium_only"]]
    worst = min(repayment_quarters, key=lambda q: q["surplus_before_emi"] - q["amount_due"]) if repayment_quarters else None
    first_due = repayment_quarters[0] if repayment_quarters else None

    worst_quarter_shortfall = max((q["shortfall"] for q in repayment_quarters), default=0)
    reserve_target = max(float(worst_quarter_shortfall), _reserve_needed(base))
    monthly_saving = reserve_target / moratorium_months if moratorium_months > 0 else None

    # Shocks start the month the first instalment is due (or month 1 when
    # there is no free period) and are evaluated with and without the
    # base reserve already in hand.
    shock_start = moratorium_months
    shock_results = []
    for shock in get_shocks(business_type):
        without = _simulate(horizon, start_month, index, avg_monthly_revenue, monthly_operating_cost, monthly_emi, moratorium_months, 0.0, shock, shock_start)
        with_reserve = _simulate(horizon, start_month, index, avg_monthly_revenue, monthly_operating_cost, monthly_emi, moratorium_months, reserve_target, shock, shock_start)
        needed = _reserve_needed(without)
        shock_results.append({
            "id": shock["id"],
            "label": shock["label"],
            "detail": shock["detail"],
            "months": shock["months"],
            "starts_in_month": shock_start + 1,
            "survival_months_without_reserve": _survival(without),
            "survival_months_with_reserve": _survival(with_reserve),
            "reserve_needed": round(needed),
            "extra_reserve_over_base": round(max(0.0, needed - reserve_target)),
            "survives_with_base_reserve": _survival(with_reserve) is None,
        })

    lean_cal = min(range(12), key=lambda i: index[i]) + 1
    peak_cal = max(range(12), key=lambda i: index[i]) + 1
    avg_monthly_surplus = round(sum(m["net"] for m in base if not m["is_moratorium"]) / max(1, sum(1 for m in base if not m["is_moratorium"])))

    # One quarter's instalments (3 x EMI) is the line between "keep a bit
    # aside" and "this plan needs more income or a smaller loan".
    if reserve_target == 0:
        verdict = "comfortable"
    elif reserve_target <= 3 * monthly_emi:
        verdict = "tight"
    else:
        verdict = "at_risk"

    return {
        "inputs": {
            "business_type": business_type,
            "avg_monthly_revenue": avg_monthly_revenue,
            "monthly_operating_cost": monthly_operating_cost,
            "monthly_emi": round(monthly_emi, 2),
            "moratorium_months": moratorium_months,
            "start_month": start_month,
            "start_month_label": MONTH_ABBR[start_month - 1],
            "horizon_months": horizon,
        },
        "season": {
            "index": index,
            "lean_month": MONTH_ABBR[lean_cal - 1],
            "peak_month": MONTH_ABBR[peak_cal - 1],
            "reasoning": season["reasoning"],
            "provenance": PROVENANCE,
        },
        "months": base,
        "quarters": quarters,
        "worst_quarter": worst,
        "first_instalment_quarter": first_due,
        "reserve_target": round(reserve_target),
        "monthly_saving_during_moratorium": round(monthly_saving) if monthly_saving is not None else None,
        "avg_monthly_surplus_after_emi": avg_monthly_surplus,
        "shocks": shock_results,
        "verdict": verdict,
        "assumption": (
            f"Seasonal pattern is a documented assumption for this trade, not measured data. Horizon is the {moratorium_months}-month free period "
            f"plus {horizon - moratorium_months} months of repayment. Each shock is timed to start in month {shock_start + 1}, when the first instalment is due."
        ),
    }
