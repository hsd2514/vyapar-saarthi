"""Official unit costs - what a bank appraises a project against.

Every year NABARD's State Level Unit Cost Committee publishes an indicative
cost per activity ("2 Murrah buffaloes = Rs 2,72,300") that bank branches
use to size loans. Applicants almost never see it: 83% (Haryana) and 49%
(Maharashtra) of scheme beneficiaries in NBCFDC's own evaluations did not
know their activity's unit cost, and 43-46% said their loan turned out
insufficient. This file puts that sheet in the applicant's hands.

Two provenance levels, and the UI must always show which one applies:

  VERIFIED_EXTERNAL - transcribed line-by-line from NABARD Maharashtra RO,
      "Unit Cost 2026-27" (SLUCC meeting 10 Apr 2026, publication
      E.RO.MH/27/2). Dairy only, for now - the booklet is Farm Sector.
  ESTIMATED - indicative profiles for the non-farm categories this app
      serves (kirana, tailoring, food stall, vendor, handicrafts), built
      from the app's own OPERATIONS_BENCHMARKS and typical equipment
      prices. Not an official sheet. Replace with DIC / MSME-DI project
      profiles when sourced; the structure below does not change.

Same style as city_data.py: static, auditable, no live fetch. Costs are
indicative (+/-20% per the booklet's own note) and never presented as exact.

Profile shape:
  scale       - the thing you can have more or fewer of ("animals"), with
                the booklet's reference count and a floor
  items       - each with `kind` (capital | working_capital | optional) and
                `per_unit` (True = scales with `scale.count`, False = fixed).
                `optional` items are things a first-timer usually needs but
                the booklet lists separately (a shed) - included in the
                required cost by default, shown so they can be dropped.
"""

from __future__ import annotations

PROVENANCE_VERIFIED = "VERIFIED_EXTERNAL"
PROVENANCE_ESTIMATED = "ESTIMATED"

NABARD_MH_2026_27 = {
    "source": "NABARD Maharashtra RO, Unit Cost 2026-27 (SLUCC 10 Apr 2026, E.RO.MH/27/2)",
    "financial_year": "2026-27",
    "state": "Maharashtra",
    "tolerance_pct": 20,
}


def _dairy_variant(key: str, label: str, animal_cost: int, yield_lpd: int, concentrate_kg: int, concentrate_cost: int,
                   fodder_cost: int, insurance: int, vet: int, equipment_per_animal: int = 1000,
                   vet_label: str = "Veterinary aid @ Rs 2,000 per animal per year") -> dict:
    """One 2-animal dairy unit exactly as the booklet itemises it, plus the
    shed the booklet says "may be financed in addition" (120 sq ft for two
    animals @ Rs 400/sq ft, its lower bound). Every rupee here is on the
    booklet's page; the only derived figure is the shed line."""
    return {
        "key": key,
        "label": label,
        "unit_label": "2 animals",
        "scale": {"label": "animals", "count": 2, "min": 1, "max": 10},
        "provenance": PROVENANCE_VERIFIED,
        "source": NABARD_MH_2026_27["source"],
        "yield_litres_per_day": yield_lpd,
        "items": [
            {"name": f"{label} (avg {yield_lpd} L/day) @ Rs {animal_cost:,} each", "amount": animal_cost * 2, "kind": "capital", "per_unit": True},
            {"name": "Milking equipment @ Rs 1,000 per animal", "amount": equipment_per_animal * 2, "kind": "capital", "per_unit": True},
            {"name": f"Concentrate feed, one month ({concentrate_kg} kg @ Rs 30/kg)", "amount": concentrate_cost, "kind": "working_capital", "per_unit": True},
            {"name": "Green fodder, one month", "amount": fodder_cost, "kind": "working_capital", "per_unit": True},
            {"name": "Animal insurance @ 5% of animal cost", "amount": insurance, "kind": "working_capital", "per_unit": True},
            {"name": vet_label, "amount": vet, "kind": "working_capital", "per_unit": True},
            {"name": "Cattle shed, 60 sq ft per animal @ Rs 400/sq ft (skip if you have one)", "amount": 48_000, "kind": "optional", "per_unit": True},
        ],
        "note": "Animal price rises Rs 5,000-12,000 for every extra litre of daily yield; transport is extra. Animals must be certified free of TB, JD and Brucellosis.",
    }


# Booklet pp. 35-42. Totals (without shed) reconcile to the booklet's
# "Total Outlay" line for each variant - asserted in test_unit_cost.py.
DAIRY_VARIANTS: list[dict] = [
    _dairy_variant("murrah", "Graded Murrah / Surti buffalo", 120_000, 8, 180, 10_800, 3_500, 12_000, 4_000),
    # p.35 itemises three working-capital lines (Rs 22,840) under a printed
    # subtotal of Rs 25,840 and a total outlay of Rs 2,17,840. The total is
    # what a bank appraises against, so the Rs 3,000 the page does not
    # itemise is carried as its own labelled line rather than dropped.
    _dairy_variant("hf_crossbred", "Crossbred Holstein Friesian cow", 95_000, 12, 189, 11_340, 4_500, 7_000, 3_000,
                   vet_label="Veterinary / miscellaneous (in booklet subtotal, not itemised)"),
    _dairy_variant("gir", "Gir (desi) cow", 90_000, 10, 165, 9_900, 4_500, 9_000, 4_000),
    _dairy_variant("tharparkar", "Tharparkar (desi) cow", 80_000, 8, 141, 8_460, 4_500, 8_000, 4_000),
    _dairy_variant("jersey_crossbred", "Crossbred Jersey cow", 70_000, 12, 170, 9_900, 3_000, 6_500, 4_000),
    _dairy_variant("pandharpuri", "Pandharpuri buffalo", 70_000, 6, 150, 9_900, 4_500, 7_000, 4_000),
    _dairy_variant("haryana_rathi", "Haryana / Rathi (desi) cow", 70_000, 6, 117, 7_020, 3_000, 7_000, 4_000),
    _dairy_variant("non_descript", "Konkan Kapila / non-descript cow", 55_000, 4, 144, 4_320, 3_500, 5_500, 4_000, equipment_per_animal=2000),
]


def _estimated(key: str, label: str, unit_label: str, scale: dict | None, items: list[dict], note: str) -> dict:
    return {
        "key": key,
        "label": label,
        "unit_label": unit_label,
        "scale": scale,
        "provenance": PROVENANCE_ESTIMATED,
        "source": "Indicative estimate from this app's operations benchmarks and typical equipment prices - not an official unit cost sheet",
        "items": items,
        "note": note,
    }


# Non-farm categories: no official sheet yet (NABARD's booklet is farm
# sector only; KVIC's PMEGP profiles are manufacturing units, not shops).
# These are deliberately modest, itemised the way a DIC officer would ask
# for them, and tagged ESTIMATED so the screen says so.
ESTIMATED_PROFILES: dict[str, list[dict]] = {
    "retail": [
        _estimated("kirana_small", "Small kirana / general store", "one shop", None, [
            {"name": "Shelving, counter, weighing scale", "amount": 35_000, "kind": "capital", "per_unit": False},
            {"name": "Refrigerator / cold drinks cooler", "amount": 22_000, "kind": "capital", "per_unit": False},
            {"name": "Opening stock (grocery, FMCG)", "amount": 90_000, "kind": "working_capital", "per_unit": False},
            {"name": "Shop deposit and first month rent", "amount": 20_000, "kind": "optional", "per_unit": False},
        ], "Distributors usually want full advance for the first three months; plan opening stock accordingly."),
    ],
    "textiles": [
        _estimated("tailoring_unit", "Tailoring unit", "per machine", {"label": "machines", "count": 2, "min": 1, "max": 6}, [
            {"name": "Sewing machine (industrial, motorised) @ Rs 16,500", "amount": 33_000, "kind": "capital", "per_unit": True},
            {"name": "Interlock / overlock machine", "amount": 20_000, "kind": "capital", "per_unit": False},
            {"name": "Cutting table, iron, scissors, fittings", "amount": 12_000, "kind": "capital", "per_unit": False},
            {"name": "Fabric and thread stock for one month", "amount": 25_000, "kind": "working_capital", "per_unit": False},
            {"name": "Shop deposit and first month rent", "amount": 15_000, "kind": "optional", "per_unit": False},
        ], "Wedding season (Oct-Feb) is most of the year's income; buy fabric in August when it is cheap."),
    ],
    "food_stall": [
        _estimated("food_stall", "Snack / tea stall", "one stall", None, [
            {"name": "Cart or counter, gas stove, cylinder, utensils", "amount": 28_000, "kind": "capital", "per_unit": False},
            {"name": "Display case, water storage, seating", "amount": 12_000, "kind": "capital", "per_unit": False},
            {"name": "Raw material for the first month", "amount": 18_000, "kind": "working_capital", "per_unit": False},
            {"name": "FSSAI registration and local licence", "amount": 3_000, "kind": "working_capital", "per_unit": False},
        ], "Cash business with daily purchases - the working-capital line is what usually runs out first."),
    ],
    "vendor": [
        _estimated("veg_vendor", "Vegetable / fruit vending", "one cart", None, [
            {"name": "Hand cart or tricycle, weighing scale, crates", "amount": 18_000, "kind": "capital", "per_unit": False},
            {"name": "Tarpaulin, lighting, storage bins", "amount": 5_000, "kind": "capital", "per_unit": False},
            {"name": "Daily stock float for two weeks", "amount": 14_000, "kind": "working_capital", "per_unit": False},
        ], "PM SVANidhi's Rs 10,000-50,000 working-capital ladder was built for exactly this activity."),
    ],
    "handicrafts": [
        _estimated("handicraft_unit", "Handicraft workshop", "one unit", None, [
            {"name": "Tools, work table, storage", "amount": 25_000, "kind": "capital", "per_unit": False},
            {"name": "Raw material for the first production cycle", "amount": 30_000, "kind": "working_capital", "per_unit": False},
            {"name": "Packaging and first exhibition / market stall", "amount": 10_000, "kind": "working_capital", "per_unit": False},
        ], "PM Vishwakarma adds a Rs 15,000 toolkit incentive for recognised traditional trades."),
    ],
}


def get_unit_cost_profiles(business_type: str) -> list[dict]:
    """All cost profiles for a category, verified ones first. Empty list if
    the category has none - the caller reports UNAVAILABLE, never guesses."""
    if business_type == "dairy":
        return DAIRY_VARIANTS
    return ESTIMATED_PROFILES.get(business_type, [])


def get_unit_cost_profile(business_type: str, variant_key: str | None = None) -> dict | None:
    profiles = get_unit_cost_profiles(business_type)
    if not profiles:
        return None
    if variant_key:
        for p in profiles:
            if p["key"] == variant_key:
                return p
    return profiles[0]
