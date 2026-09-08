"""Financial Fit Engine - 20% of the overall score. Deterministic arithmetic
only - reuses deterministic.py's calc_financial_structuring/calc_emi rather
than recomputing project cost, loan amount, or EMI. Never invents a missing
income/expense/revenue figure: each missing optional field is listed in
`missing_fields` and reduces this dimension's confidence instead.
"""

from __future__ import annotations

from deterministic import calc_emi, calc_financial_structuring
from normalization import normalize_linear
from viability_config import HARD_CONSTRAINTS, NEUTRAL_FALLBACK_SCORE

_OPTIONAL_FIELDS = ["monthly_income", "monthly_expenses", "existing_emi", "expected_revenue", "operating_expenses"]


def compute_financial_fit(
    available_margin_capital: float,
    monthly_income: float | None,
    monthly_expenses: float | None,
    existing_emi: float | None,
    expected_revenue: float | None,
    operating_expenses: float | None,
) -> dict:
    structuring = calc_financial_structuring(available_margin_capital)
    project_cost = structuring["project_cost"]
    max_loan = structuring["max_loan_amount"]
    scheme = structuring["scheme"]

    new_emi = 0.0
    if scheme and max_loan:
        new_emi = calc_emi(max_loan, scheme["annual_rate_pct"], scheme["tenure_months"])

    values = {
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "existing_emi": existing_emi,
        "expected_revenue": expected_revenue,
        "operating_expenses": operating_expenses,
    }
    missing_fields = [f for f in _OPTIONAL_FIELDS if values[f] is None]

    disposable_income = None
    if monthly_income is not None and monthly_expenses is not None and existing_emi is not None:
        disposable_income = monthly_income - monthly_expenses - existing_emi

    business_surplus = None
    if expected_revenue is not None and operating_expenses is not None:
        business_surplus = expected_revenue - operating_expenses

    post_loan_surplus = None
    if disposable_income is not None and business_surplus is not None:
        post_loan_surplus = disposable_income + business_surplus - new_emi

    total_emi = (existing_emi or 0.0) + new_emi

    dscr = None
    if disposable_income is not None and business_surplus is not None and total_emi > 0:
        dscr = (disposable_income + business_surplus) / total_emi

    debt_burden_ratio = None
    if monthly_income and existing_emi is not None and monthly_income > 0:
        debt_burden_ratio = existing_emi / monthly_income

    completeness = (len(_OPTIONAL_FIELDS) - len(missing_fields)) / len(_OPTIONAL_FIELDS)

    if post_loan_surplus is not None:
        surplus_ratio = post_loan_surplus / total_emi if total_emi > 0 else 1.0
        score = normalize_linear(surplus_ratio, -1.0, 1.5)
    elif business_surplus is not None:
        band = total_emi if total_emi else 1.0
        score = normalize_linear(business_surplus, -band, band * 2)
    else:
        score = NEUTRAL_FALLBACK_SCORE

    confidence = round(0.90 * completeness, 4)

    insufficient_repayment_capacity = dscr is not None and dscr < HARD_CONSTRAINTS["min_dscr"]
    high_debt_burden = debt_burden_ratio is not None and debt_burden_ratio > HARD_CONSTRAINTS["max_debt_burden_ratio"]

    return {
        "score": round(score, 2),
        "confidence": confidence,
        "project_cost": project_cost,
        "max_loan_amount": max_loan,
        "new_emi": round(new_emi, 2),
        "disposable_income": disposable_income,
        "business_surplus": business_surplus,
        "post_loan_surplus": post_loan_surplus,
        "dscr": round(dscr, 3) if dscr is not None else None,
        "debt_burden_ratio": round(debt_burden_ratio, 3) if debt_burden_ratio is not None else None,
        "insufficient_repayment_capacity": insufficient_repayment_capacity,
        "high_debt_burden": high_debt_burden,
        "missing_fields": missing_fields,
    }
