"""Seasonal income patterns and named shocks, per business category.

Rural enterprise income is not flat - financial-diary studies put the
best month at up to 2.6x the worst - but every EMI calculator assumes it
is. The stress test (stress_test.py) lays these monthly patterns over the
repayment schedule to find the quarter where the instalment is bigger than
the surplus, then runs the three shocks below.

Provenance: ASSUMPTION. These are documented, plausible shapes, not
measured series. Each index is twelve multipliers Jan-Dec on an average
month (they sum to 12.0, asserted in test_stress_test.py), with the
reasoning next to it so it can be argued with. Replace with Agmarknet /
milk-union procurement history per district when that is wired in; the
shape of this file does not change.

Shocks are parameterised so the arithmetic is the same for every
category: revenue multiplier, cost multiplier, how many months it lasts,
and any one-time cost. Labels are what the person would call it.
"""

from __future__ import annotations

PROVENANCE = "ASSUMPTION"

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SEASONALITY: dict[str, dict] = {
    "dairy": {
        "index": [1.10, 1.10, 1.00, 0.85, 0.80, 0.80, 0.90, 0.95, 1.00, 1.15, 1.15, 1.20],
        "reasoning": "Buffalo and cow yield falls in the summer heat (Apr-Jun) and recovers with the monsoon; winter is the flush season and Diwali (Oct-Nov) lifts demand for milk and sweets.",
    },
    "textiles": {
        "index": [1.30, 1.20, 0.80, 0.85, 1.00, 0.70, 0.65, 0.75, 0.90, 1.20, 1.35, 1.30],
        "reasoning": "Wedding season (Nov-Feb) and Diwali carry most of a tailoring unit's year; the monsoon months (Jun-Aug) are the leanest, with almost no occasion orders.",
    },
    "retail": {
        "index": [1.00, 0.95, 1.00, 1.00, 1.00, 0.95, 0.90, 0.90, 1.00, 1.20, 1.15, 0.95],
        "reasoning": "A kirana shop is the steadiest of the six; Diwali (Oct-Nov) lifts sales and the monsoon (Jul-Aug) softens them as rural cash is tight before the kharif harvest.",
    },
    "vendor": {
        "index": [1.15, 1.10, 1.05, 0.95, 0.80, 0.80, 0.85, 0.90, 1.00, 1.15, 1.15, 1.10],
        "reasoning": "Vegetable and fruit supply is abundant and cheap from the rabi harvest (Nov-Feb); summer heat (May-Jun) thins both supply and footfall; the monsoon disrupts transport.",
    },
    "food_stall": {
        "index": [1.15, 1.10, 1.00, 0.95, 0.95, 0.85, 0.80, 0.85, 1.05, 1.20, 1.10, 1.00],
        "reasoning": "Festival and fair season (Sep-Nov) and the winter months are strong for snack stalls; the monsoon (Jun-Aug) keeps customers home.",
    },
    "handicrafts": {
        "index": [1.10, 1.00, 0.95, 0.90, 0.90, 0.75, 0.70, 0.85, 1.05, 1.35, 1.30, 1.15],
        "reasoning": "Gifting and exhibition orders cluster around Diwali and the winter fair season (Oct-Jan); the monsoon quarter brings few orders and little tourist footfall.",
    },
}

# Three shocks per category. `one_time_cost_months` is a one-off cost
# expressed in months of operating cost (so it scales with the business);
# `one_time_cost` is an absolute rupee figure where that is more honest.
SHOCKS: dict[str, list[dict]] = {
    "dairy": [
        {"id": "asset_loss", "label": "One animal dies or goes dry", "revenue_multiplier": 0.50, "cost_multiplier": 0.85, "months": 6, "one_time_cost": 0,
         "detail": "Half the milk for six months until the animal is replaced; feed cost falls a little. Insurance, if it was kept up, pays the replacement."},
        {"id": "no_sales", "label": "Society stops buying for two months", "revenue_multiplier": 0.0, "cost_multiplier": 1.0, "months": 2, "one_time_cost": 0,
         "detail": "A quality rejection or a dispute with the collection centre - the animals still eat."},
        {"id": "bad_season", "label": "Drought: fodder scarce, yield down", "revenue_multiplier": 0.70, "cost_multiplier": 1.25, "months": 4, "one_time_cost": 0,
         "detail": "Yield drops and fodder has to be bought at a premium for a season."},
    ],
    "textiles": [
        {"id": "asset_loss", "label": "Main machine breaks down", "revenue_multiplier": 0.60, "cost_multiplier": 1.0, "months": 2, "one_time_cost": 8_000,
         "detail": "Two months at reduced output plus a repair or replacement motor."},
        {"id": "no_sales", "label": "Two months with no orders", "revenue_multiplier": 0.0, "cost_multiplier": 1.0, "months": 2, "one_time_cost": 0,
         "detail": "Rent and helper still have to be paid."},
        {"id": "bad_season", "label": "A weak wedding season", "revenue_multiplier": 0.65, "cost_multiplier": 1.0, "months": 4, "one_time_cost": 0,
         "detail": "The season that pays for the year comes in a third short."},
    ],
    "retail": [
        {"id": "asset_loss", "label": "Stock spoils or is stolen", "revenue_multiplier": 0.80, "cost_multiplier": 1.0, "months": 1, "one_time_cost_months": 0.5,
         "detail": "Half a month's stock written off and a month of thin shelves."},
        {"id": "no_sales", "label": "Shop shut for two months", "revenue_multiplier": 0.0, "cost_multiplier": 0.6, "months": 2, "one_time_cost": 0,
         "detail": "Illness or a family event; rent continues, purchases stop."},
        {"id": "bad_season", "label": "Bad harvest, customers buy on credit", "revenue_multiplier": 0.70, "cost_multiplier": 1.0, "months": 4, "one_time_cost": 0,
         "detail": "Cash sales fall for a season while the village waits for the next crop."},
    ],
    "vendor": [
        {"id": "asset_loss", "label": "Cart damaged, stock lost", "revenue_multiplier": 0.70, "cost_multiplier": 1.0, "months": 1, "one_time_cost": 10_000,
         "detail": "A month of reduced selling and a repair bill."},
        {"id": "no_sales", "label": "Two months off the road", "revenue_multiplier": 0.0, "cost_multiplier": 0.3, "months": 2, "one_time_cost": 0,
         "detail": "Illness or a municipal drive; most costs stop with the sales."},
        {"id": "bad_season", "label": "Price crash or monsoon supply break", "revenue_multiplier": 0.65, "cost_multiplier": 1.0, "months": 3, "one_time_cost": 0,
         "detail": "Margins vanish for a season."},
    ],
    "food_stall": [
        {"id": "asset_loss", "label": "Stall moved by the municipality", "revenue_multiplier": 0.50, "cost_multiplier": 1.0, "months": 2, "one_time_cost": 5_000,
         "detail": "Two months rebuilding footfall at a new spot."},
        {"id": "no_sales", "label": "Closed for two months", "revenue_multiplier": 0.0, "cost_multiplier": 0.4, "months": 2, "one_time_cost": 0,
         "detail": "Illness or a family event; raw material purchases stop, some fixed costs continue."},
        {"id": "bad_season", "label": "A long monsoon", "revenue_multiplier": 0.70, "cost_multiplier": 1.0, "months": 3, "one_time_cost": 0,
         "detail": "Customers stay home for a season."},
    ],
    "handicrafts": [
        {"id": "asset_loss", "label": "A big order cancelled, material wasted", "revenue_multiplier": 0.50, "cost_multiplier": 1.0, "months": 2, "one_time_cost_months": 1.0,
         "detail": "A month of material spent on work that is not paid for."},
        {"id": "no_sales", "label": "Two months with no orders", "revenue_multiplier": 0.0, "cost_multiplier": 0.7, "months": 2, "one_time_cost": 0,
         "detail": "Between seasons; some material cost still goes out."},
        {"id": "bad_season", "label": "No exhibitions this season", "revenue_multiplier": 0.60, "cost_multiplier": 1.0, "months": 4, "one_time_cost": 0,
         "detail": "The fair season that brings most orders does not happen."},
    ],
}


def get_seasonality(business_type: str) -> dict | None:
    return SEASONALITY.get(business_type)


def get_shocks(business_type: str) -> list[dict]:
    return SHOCKS.get(business_type, [])
