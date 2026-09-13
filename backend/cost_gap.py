"""Required cost vs eligible cost - the gap the margin-money formula hides.

The scheme rule sizes a project from the applicant's cash: margin / 10%.
The bank sizes it from the activity's unit cost. When the second number is
bigger than the first the applicant starts short, and NBCFDC's evaluations
show what happens next - 46% needed more credit after the loan, a third of
them from a moneylender. This module puts both numbers side by side, works
out the gap, and offers the three honest ways to close it: bring more
margin, take a smaller unit, or stack a subsidy scheme.

It also asks the question no calculator asks - where the 10% is coming
from - because Maharashtra's own SCA report says most beneficiaries borrow
it from a moneylender and then prioritise that lender over the scheme.

Pure arithmetic on deterministic.py, schemes.py and unit_cost_data.py.
No LLM, no live data.
"""

from __future__ import annotations

from deterministic import calc_financial_structuring, calc_repayment_schedule
from schemes import GOV_SCHEMES
from unit_cost_data import get_unit_cost_profile, get_unit_cost_profiles

MARGIN_SOURCES = ("savings", "family", "moneylender", "not_arranged")

# Flat monthly rate informal lenders in this segment commonly charge, used
# only as the default the user can change; the result always states it.
DEFAULT_MONEYLENDER_MONTHLY_RATE_PCT = 3.0
DEFAULT_MONEYLENDER_TENURE_MONTHS = 12


def _scaled_items(profile: dict, scale_count: int | None) -> tuple[list[dict], int]:
    """Items at the chosen scale. per_unit items scale linearly from the
    profile's reference count; fixed items do not."""
    scale = profile.get("scale")
    if not scale:
        return [dict(i) for i in profile["items"]], 1
    ref = scale["count"]
    n = ref if scale_count is None else max(scale["min"], min(scale["max"], int(scale_count)))
    out = []
    for i in profile["items"]:
        amount = round(i["amount"] * n / ref) if i["per_unit"] else i["amount"]
        out.append({**i, "amount": amount})
    return out, n


def required_project_cost(profile: dict, scale_count: int | None = None, include_optional: bool = True) -> dict:
    items, n = _scaled_items(profile, scale_count)
    capital = sum(i["amount"] for i in items if i["kind"] == "capital")
    working = sum(i["amount"] for i in items if i["kind"] == "working_capital")
    optional = sum(i["amount"] for i in items if i["kind"] == "optional")
    total = capital + working + (optional if include_optional else 0)
    return {
        "items": items,
        "scale_count": n,
        "capital_total": capital,
        "working_capital_total": working,
        "optional_total": optional,
        "optional_included": include_optional,
        "project_cost": total,
    }


def _moneylender_cost(margin: float, monthly_rate_pct: float, tenure_months: int, scheme_emi: float | None) -> dict:
    """Flat interest on the original principal every month - how informal
    lending in this segment is actually priced - plus straight-line
    principal repayment. The point is the stacked monthly outgo: this
    instalment lands from month one, before the business earns and while
    the scheme loan is still in its holiday."""
    monthly_interest = margin * monthly_rate_pct / 100.0
    monthly_principal = margin / tenure_months if tenure_months > 0 else margin
    monthly_outgo = monthly_interest + monthly_principal
    total_interest = monthly_interest * tenure_months
    return {
        "monthly_rate_pct": monthly_rate_pct,
        "tenure_months": tenure_months,
        "monthly_interest": round(monthly_interest, 2),
        "monthly_outgo": round(monthly_outgo, 2),
        "total_interest": round(total_interest, 2),
        "interest_as_pct_of_margin": round(total_interest / margin * 100, 1) if margin > 0 else None,
        "scheme_monthly_emi": round(scheme_emi, 2) if scheme_emi is not None else None,
        "combined_monthly_after_moratorium": round(monthly_outgo + (scheme_emi or 0), 2),
        "assumption": "flat interest on the original amount every month, principal repaid evenly over the tenure",
    }


def _subsidy_closers(business_type: str, required_cost: float, gap: float) -> list[dict]:
    """Real subsidy schemes that apply to this category at this project
    size, with the subsidy each would put against the gap. Same catalogue
    schemes.py ranks; nothing invented here."""
    out = []
    for s in GOV_SCHEMES:
        if s["subsidy_pct"] <= 0:
            continue
        if s["business_types"] is not None and business_type not in s["business_types"]:
            continue
        if not (s["project_cost_min"] <= required_cost <= s["project_cost_max"]):
            continue
        estimated = round(required_cost * s["subsidy_pct"] / 100.0)
        out.append({
            "id": s["id"],
            "name": s["name"],
            "subsidy_pct": s["subsidy_pct"],
            "estimated_subsidy": estimated,
            "covers_gap": estimated >= gap,
            "note": s["note"],
            "portal_url": s["portal_url"],
        })
    out.sort(key=lambda x: -x["estimated_subsidy"])
    return out


def calc_cost_gap(
    business_type: str,
    available_margin_capital: float,
    variant_key: str | None = None,
    scale_count: int | None = None,
    include_optional: bool = True,
    margin_source: str = "savings",
    moneylender_monthly_rate_pct: float = DEFAULT_MONEYLENDER_MONTHLY_RATE_PCT,
    moneylender_tenure_months: int = DEFAULT_MONEYLENDER_TENURE_MONTHS,
) -> dict:
    if margin_source not in MARGIN_SOURCES:
        raise ValueError(f"margin_source must be one of {MARGIN_SOURCES}")

    eligible = calc_financial_structuring(available_margin_capital)
    profile = get_unit_cost_profile(business_type, variant_key)
    if profile is None:
        return {
            "status": "UNAVAILABLE",
            "eligible": eligible,
            "profile": None,
            "required": None,
            "gap": None,
            "closers": [],
            "margin_source": {"source": margin_source},
            "note": "No unit cost profile for this category yet. Ask the bank branch for the activity's unit cost before applying.",
        }

    required = required_project_cost(profile, scale_count, include_optional)
    req_cost = required["project_cost"]
    elig_cost = eligible["project_cost"]
    gap_amount = max(0.0, req_cost - elig_cost)

    # Closer 1 - bring the margin the required cost actually needs.
    margin_needed = req_cost * 0.10
    raise_margin = {
        "id": "raise_margin",
        "margin_needed": round(margin_needed),
        "extra_margin": round(max(0.0, margin_needed - available_margin_capital)),
        "structuring_at_needed_margin": calc_financial_structuring(margin_needed),
    }

    # Closer 2 - the largest unit that fits the eligible project cost.
    scale_down = None
    scale = profile.get("scale")
    if scale and gap_amount > 0:
        fit = None
        for n in range(required["scale_count"] - 1, scale["min"] - 1, -1):
            alt = required_project_cost(profile, n, include_optional)
            if alt["project_cost"] <= elig_cost:
                fit = alt
                break
        smallest = required_project_cost(profile, scale["min"], include_optional)
        scale_down = {
            "id": "scale_down",
            "unit": scale["label"],
            "fits": fit is not None,
            "scale_count": fit["scale_count"] if fit else scale["min"],
            "required_project_cost": fit["project_cost"] if fit else smallest["project_cost"],
            "gap_at_smallest": round(max(0.0, smallest["project_cost"] - elig_cost)),
        }

    # Closer 3 - real subsidy schemes for this category at this size.
    stack_subsidy = {
        "id": "stack_subsidy",
        "schemes": _subsidy_closers(business_type, req_cost, gap_amount),
    }

    # Where the 10% comes from.
    scheme_emi = None
    if eligible.get("scheme") and eligible.get("max_loan_amount"):
        sch = eligible["scheme"]
        scheme_emi = calc_repayment_schedule(eligible["max_loan_amount"], sch["annual_rate_pct"], sch["tenure_months"], sch["moratorium_months"])["monthly_emi"]
    margin_info: dict = {"source": margin_source}
    if margin_source == "moneylender":
        margin_info["moneylender"] = _moneylender_cost(available_margin_capital, moneylender_monthly_rate_pct, moneylender_tenure_months, scheme_emi)

    return {
        "status": "OK",
        "eligible": eligible,
        "profile": {
            "key": profile["key"],
            "label": profile["label"],
            "unit_label": profile["unit_label"],
            "provenance": profile["provenance"],
            "source": profile["source"],
            "note": profile.get("note"),
            "scale": profile.get("scale"),
            "available_variants": [
                {"key": p["key"], "label": p["label"], "project_cost": required_project_cost(p, None, include_optional)["project_cost"]}
                for p in get_unit_cost_profiles(business_type)
            ],
        },
        "required": required,
        "gap": {
            "amount": round(gap_amount),
            "covered": gap_amount <= 0,
            "surplus": round(max(0.0, elig_cost - req_cost)),
            "pct_of_required": round(gap_amount / req_cost * 100, 1) if req_cost > 0 else 0.0,
        },
        "closers": [c for c in (raise_margin, scale_down, stack_subsidy) if c is not None],
        "margin_source": margin_info,
    }
