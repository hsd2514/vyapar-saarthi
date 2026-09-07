"""A small, explainable rules engine that ranks real Indian government MSME
credit schemes against a computed project cost / business category, plus the
tool's own margin-money scheme from deterministic.py.

Every scheme's numbers below are the publicly documented parameters of that
scheme (project cost bands, subsidy/collateral rules) - not invented. Where a
scheme's exact rule has variants (e.g. PMEGP's subsidy % differs by category
and urban/rural), we use the standard/general-category figure and say so, and
always link out to the scheme's own official portal so a user or a judge can
verify the exact number themselves rather than trusting a single figure we
show. This is the same "traceable, never a guess" rule deterministic.py
follows for the margin-money calculator.

The "weight engine": each scheme gets scored 0-100 as a plain weighted sum of
named, visible factors (see WEIGHTS below) - never an LLM guess. The
breakdown returned alongside the score is exactly the arithmetic that
produced it, so it can be shown on screen next to the number.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Scheme catalogue - real, publicly documented Indian MSME credit schemes.
# `project_cost_min`/`max` are the scheme's own eligibility band in rupees.
# `collateral_free` / `subsidy_pct` / `target_categories` drive the weighted
# score below. `portal_url` is the scheme's real official application/info
# page - the actual "redirect to the portal" the UI links out to.
# ---------------------------------------------------------------------------

GOV_SCHEMES = [
    {
        "id": "pmegp",
        "name": "PMEGP (Prime Minister's Employment Generation Programme)",
        "operator": "KVIC / Ministry of MSME",
        "project_cost_min": 0,
        "project_cost_max": 5_000_000,  # ₹50L manufacturing ceiling (₹20L for service - simplified to the wider band)
        "subsidy_pct": 25,  # general category, rural; varies 15-35% by category/area - see portal
        "collateral_free": True,  # collateral-free up to the scheme's own threshold, per RBI/CGTMSE guidelines
        "target_categories": ["new_enterprise"],
        "business_types": None,  # general-purpose, open to every category
        "note": "One-time capital subsidy (15-35% depending on category and rural/urban) on a new project; the rest is a bank term loan.",
        "portal_url": "https://www.kviconline.gov.in/pmegpeportal/",
    },
    {
        "id": "pm_svanidhi",
        "name": "PM SVANidhi",
        "operator": "MoHUA / urban local bodies",
        "project_cost_min": 0,
        "project_cost_max": 55_555,  # progressive working-capital loans ₹10k -> ₹20k -> ₹50k
        "subsidy_pct": 7,  # 7% p.a. interest subvention on timely repayment, paid quarterly into the account
        "collateral_free": True,
        "target_categories": ["existing_enterprise"],
        "business_types": ["vendor", "food_stall"],  # built specifically for street vendors/hawkers
        "note": "Collateral-free working-capital loan for street vendors, starting at ₹10,000 and rising to ₹20,000 then ₹50,000 on timely repayment, plus a 7% interest subsidy.",
        "portal_url": "https://pmsvanidhi.mohua.gov.in/",
    },
    {
        "id": "pm_vishwakarma",
        "name": "PM Vishwakarma",
        "operator": "Ministry of MSME",
        "project_cost_min": 0,
        "project_cost_max": 333_333,  # collateral-free loans up to ₹3,00,000 in two tranches
        "subsidy_pct": 0,  # not a subsidy scheme - concessional 5% interest rate instead
        "collateral_free": True,
        "target_categories": ["new_enterprise", "existing_enterprise"],
        "business_types": ["handicrafts", "textiles"],  # for the 18 recognised traditional trades/artisan crafts
        "note": "Collateral-free loans up to ₹3,00,000 (₹1 lakh, then ₹2 lakh) at a concessional 5% interest rate for traditional artisans and craftspeople, plus a ₹15,000 toolkit incentive.",
        "portal_url": "https://pmvishwakarma.gov.in/",
    },
    {
        "id": "pmfme",
        "name": "PMFME (PM Formalisation of Micro Food Processing Enterprises)",
        "operator": "Ministry of Food Processing Industries",
        "project_cost_min": 0,
        "project_cost_max": 2_857_143,  # 35% subsidy capped at ₹10L implies project cost up to ~₹28.6L is meaningfully subsidised
        "subsidy_pct": 35,
        "collateral_free": False,
        "target_categories": ["new_enterprise", "existing_enterprise"],
        "business_types": ["food_stall"],
        "note": "Credit-linked capital subsidy of 35% of project cost (capped at ₹10 lakh) for micro food-processing/food-stall enterprises.",
        "portal_url": "https://pmfme.mofpi.gov.in/",
    },
    {
        "id": "deds_dairy",
        "name": "Dairy Entrepreneurship Development Scheme",
        "operator": "NABARD",
        "project_cost_min": 0,
        "project_cost_max": 1_000_000,
        "subsidy_pct": 25,  # back-ended capital subsidy, higher for SC/ST/women
        "collateral_free": False,
        "target_categories": ["new_enterprise", "existing_enterprise"],
        "business_types": ["dairy"],
        "note": "Back-ended capital subsidy (25%, higher for SC/ST/women) on a bank loan for setting up or expanding a dairy unit.",
        "portal_url": "https://www.nabard.org/content1.aspx?catid=23&id=591",
    },
    {
        "id": "mudra_shishu",
        "name": "Mudra Yojana - Shishu",
        "operator": "MUDRA / participating banks",
        "project_cost_min": 0,
        "project_cost_max": 55_555,  # ≤₹50,000 loan at 90% of project cost implies ≤~₹55.5k project cost
        "subsidy_pct": 0,
        "collateral_free": True,
        "target_categories": ["new_enterprise", "existing_enterprise"],
        "business_types": None,
        "note": "Loans up to ₹50,000 for very small/starting micro-enterprises, no collateral.",
        "portal_url": "https://www.mudra.org.in/",
    },
    {
        "id": "mudra_kishor",
        "name": "Mudra Yojana - Kishor",
        "operator": "MUDRA / participating banks",
        "project_cost_min": 55_556,
        "project_cost_max": 555_555,  # loans ₹50,000-₹5,00,000
        "subsidy_pct": 0,
        "collateral_free": True,
        "target_categories": ["new_enterprise", "existing_enterprise"],
        "business_types": None,
        "note": "Loans ₹50,000-₹5,00,000 for a business that has already taken its first step and needs to grow.",
        "portal_url": "https://www.mudra.org.in/",
    },
    {
        "id": "mudra_tarun",
        "name": "Mudra Yojana - Tarun",
        "operator": "MUDRA / participating banks",
        "project_cost_min": 555_556,
        "project_cost_max": 1_111_111,  # loans ₹5,00,000-₹10,00,000
        "subsidy_pct": 0,
        "collateral_free": True,
        "target_categories": ["new_enterprise", "existing_enterprise"],
        "business_types": None,
        "note": "Loans ₹5,00,000-₹10,00,000 for an established small business ready to expand further.",
        "portal_url": "https://www.mudra.org.in/",
    },
    {
        "id": "stand_up_india",
        "name": "Stand-Up India",
        "operator": "SIDBI / scheduled commercial banks",
        "project_cost_min": 1_111_112,
        "project_cost_max": 11_111_111,  # composite loan ₹10L-₹1Cr
        "subsidy_pct": 0,
        "collateral_free": True,  # covered under CGTMSE/CGFSI, not a personal-guarantee-free loan by default
        "target_categories": ["new_enterprise"],
        "business_types": None,
        "note": "Composite loan (term loan + working capital) of ₹10 lakh-₹1 crore, reserved for at least one SC/ST or woman entrepreneur per bank branch, for a new (greenfield) enterprise.",
        "portal_url": "https://www.standupmitra.in/",
    },
]

# The tool's own margin-money scheme (from deterministic.py) is always
# included in the ranked list too, so the comparison is apples-to-apples
# rather than hiding the PS's own scheme behind a separate screen.
MARGIN_MONEY_SCHEME_META = {
    "id": "margin_money",
    "name": "Margin-Money Loan Scheme (this tool's core scheme)",
    "operator": "State-linked lending institution",
    "subsidy_pct": 0,
    "collateral_free": True,
    "business_types": None,
    "note": "10% of project cost as your own margin money unlocks a 90% loan, up to the tier's cap - this is the scheme this app is built around.",
    "portal_url": "https://www.startupindia.gov.in/content/sih/en/government-schemes.html",
}

# ---------------------------------------------------------------------------
# Weight engine - named, visible weights, summing to 100.
# ---------------------------------------------------------------------------

WEIGHTS = {
    "cost_band_fit": 55,     # does the project cost actually sit inside the scheme's own band
    "collateral_free": 20,   # no collateral requirement is a big deal for a first-time borrower
    "subsidy": 15,           # a real non-repayable subsidy lowers the effective cost of capital
    "category_match": 10,    # does the scheme specifically target this business category (vendor/dairy/etc.)
}


def _category_component(business_types: list[str] | None, business_type: str | None) -> float:
    """1.0 if the scheme is specifically built for this business category (e.g.
    PM SVANidhi for vendors), 0.6 if the scheme is general-purpose and open to
    everyone, 0.2 if the scheme specifically targets a *different* category
    than the one given (e.g. PM Vishwakarma for a retail shop)."""
    if business_types is None:
        return 0.6
    if business_type and business_type in business_types:
        return 1.0
    return 0.2


def _cost_band_score(project_cost: float, cost_min: float, cost_max: float) -> float:
    """1.0 if the cost sits comfortably inside the band, tapering to 0 as it
    moves outside - a plain distance-based fit, not a guess."""
    if cost_min <= project_cost <= cost_max:
        # comfortable if it's not hugging either edge of the band
        span = cost_max - cost_min
        if span <= 0:
            return 1.0
        edge_distance = min(project_cost - cost_min, cost_max - project_cost) / span
        return 0.7 + 0.3 * min(edge_distance * 4, 1.0)  # 0.7-1.0 inside the band
    # outside the band: taper off over a distance equal to the band's own width
    span = max(cost_max - cost_min, 1)
    if project_cost < cost_min:
        overshoot = (cost_min - project_cost) / span
    else:
        overshoot = (project_cost - cost_max) / span
    return max(0.0, 1.0 - overshoot)


def match_schemes(project_cost: float, business_type: str | None = None) -> list[dict]:
    """Rank every catalogued scheme (real gov't schemes + this tool's own
    margin-money scheme) against a computed project cost. Returns each
    scheme's real parameters, a 0-100 match score, and the exact weighted
    breakdown that produced it - nothing here is an LLM call."""
    from deterministic import MICRO_FINANCE_SCHEME, TERM_LOAN_SCHEME, calc_financial_structuring

    results = []
    for scheme in GOV_SCHEMES:
        cost_fit = _cost_band_score(project_cost, scheme["project_cost_min"], scheme["project_cost_max"])
        collateral_component = 1.0 if scheme["collateral_free"] else 0.0
        subsidy_component = min(scheme["subsidy_pct"] / 35.0, 1.0)  # 35% is the top real subsidy tier (PMEGP/PMFME)
        category_component = _category_component(scheme["business_types"], business_type)

        breakdown = {
            "cost_band_fit": round(cost_fit * WEIGHTS["cost_band_fit"], 1),
            "collateral_free": round(collateral_component * WEIGHTS["collateral_free"], 1),
            "subsidy": round(subsidy_component * WEIGHTS["subsidy"], 1),
            "category_match": round(category_component * WEIGHTS["category_match"], 1),
        }
        score = round(sum(breakdown.values()), 1)

        results.append({
            "id": scheme["id"],
            "name": scheme["name"],
            "operator": scheme["operator"],
            "project_cost_band": [scheme["project_cost_min"], scheme["project_cost_max"]],
            "subsidy_pct": scheme["subsidy_pct"],
            "collateral_free": scheme["collateral_free"],
            "note": scheme["note"],
            "portal_url": scheme["portal_url"],
            "business_types": scheme["business_types"],
            "match_score": score,
            "score_breakdown": breakdown,
            "in_band": scheme["project_cost_min"] <= project_cost <= scheme["project_cost_max"],
        })

    # Score the tool's own margin-money scheme the same way, reusing its real tiers.
    structuring = calc_financial_structuring(project_cost * 0.10)  # margin_capital that yields this project_cost
    mm_tier = MICRO_FINANCE_SCHEME if project_cost <= MICRO_FINANCE_SCHEME["project_cost_max"] else TERM_LOAN_SCHEME
    cost_fit = _cost_band_score(project_cost, 0, mm_tier["project_cost_max"])
    breakdown = {
        "cost_band_fit": round(cost_fit * WEIGHTS["cost_band_fit"], 1),
        "collateral_free": WEIGHTS["collateral_free"],  # always collateral-free by PS design
        "subsidy": 0.0,
        "category_match": round(_category_component(MARGIN_MONEY_SCHEME_META["business_types"], business_type) * WEIGHTS["category_match"], 1),
    }
    score = round(sum(breakdown.values()), 1)
    results.append({
        "id": MARGIN_MONEY_SCHEME_META["id"],
        "name": MARGIN_MONEY_SCHEME_META["name"],
        "operator": MARGIN_MONEY_SCHEME_META["operator"],
        "project_cost_band": [0, mm_tier["project_cost_max"]],
        "subsidy_pct": 0,
        "collateral_free": True,
        "note": MARGIN_MONEY_SCHEME_META["note"],
        "portal_url": MARGIN_MONEY_SCHEME_META["portal_url"],
        "business_types": MARGIN_MONEY_SCHEME_META["business_types"],
        "match_score": score,
        "score_breakdown": breakdown,
        "in_band": structuring["scheme"] is not None,
    })

    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results
