"""Per-business-category configuration: which resources and infrastructure
actually matter for that category - deliberately NOT the same list for
every business. resource_engine.py and location_engine.py read this rather
than hard-coding a category's needs inline.

`relevant_risk_categories` is descriptive metadata for a future
category-specific risk-weighting pass (risk_engine.py doesn't filter by it
yet, since every category currently shares the same real data sources for
risk) - kept here now so the category profile is complete and the field
doesn't need to be bolted on later.

Scoped to the 6 categories city_data.py actually has demand/competition/
pricing data for (vendor, dairy, textiles, retail, handicrafts, food_stall).
Poultry/Small Manufacturing/Services are not yet serviced - adding their
configs without any backing demand data would create a category that always
reads UNAVAILABLE, which is worse than not offering it yet.
"""

from __future__ import annotations

BUSINESS_CATEGORY_CONFIG: dict[str, dict] = {
    "vendor": {
        "label": "Vegetable / Fruit Vendor",
        "resource_checklist": [
            {"key": "wholesale_mandi_access", "label": "Wholesale mandi / haat access"},
            {"key": "transport_for_stock", "label": "Transport to carry daily stock"},
            {"key": "storage_or_cold_chain", "label": "Basic storage for perishables"},
            {"key": "customer_footfall_location", "label": "A high-footfall selling spot"},
        ],
        "relevant_risk_categories": ["demand_volatility", "supply_chain_risk", "seasonality", "market_competition_risk"],
        "infrastructure_emphasis": ["market_proximity", "transport"],
        "seasonality_sensitivity": "HIGH",
    },
    "dairy": {
        "label": "Dairy (Milk & Products)",
        "resource_checklist": [
            {"key": "feed_availability", "label": "Cattle feed availability"},
            {"key": "veterinary_access", "label": "Veterinary service access"},
            {"key": "water_availability", "label": "Reliable water supply"},
            {"key": "livestock_availability", "label": "Livestock availability/cost"},
            {"key": "milk_collection_point", "label": "Nearby milk collection point"},
            {"key": "labour_availability", "label": "Labour for daily care/milking"},
        ],
        "relevant_risk_categories": ["input_cost_volatility", "supply_chain_risk", "climate_risk", "buyer_concentration"],
        "infrastructure_emphasis": ["water", "electricity"],
        "seasonality_sensitivity": "MODERATE",
    },
    "textiles": {
        "label": "Textiles & Tailoring",
        "resource_checklist": [
            {"key": "fabric_suppliers", "label": "Fabric/raw material suppliers"},
            {"key": "sewing_equipment", "label": "Sewing/tailoring equipment"},
            {"key": "electricity_availability", "label": "Reliable electricity"},
            {"key": "skilled_labour", "label": "Skilled tailoring labour"},
            {"key": "customer_demand_channel", "label": "Route to customers (shop/orders)"},
        ],
        "relevant_risk_categories": ["seasonality", "input_cost_volatility", "buyer_concentration"],
        "infrastructure_emphasis": ["electricity", "connectivity"],
        "seasonality_sensitivity": "HIGH",
    },
    "retail": {
        "label": "Retail / Kirana Shop",
        "resource_checklist": [
            {"key": "wholesale_access", "label": "Wholesale supplier access"},
            {"key": "transport_for_stock", "label": "Transport for restocking"},
            {"key": "electricity_availability", "label": "Reliable electricity"},
            {"key": "storage_space", "label": "Storage space for stock"},
            {"key": "customer_access", "label": "Easy customer access/footfall"},
        ],
        "relevant_risk_categories": ["market_competition_risk", "input_cost_volatility", "operational_risk"],
        "infrastructure_emphasis": ["market_proximity", "accessibility"],
        "seasonality_sensitivity": "MODERATE",
    },
    "handicrafts": {
        "label": "Handicrafts",
        "resource_checklist": [
            {"key": "raw_material_sourcing", "label": "Raw material sourcing"},
            {"key": "skilled_artisan_labour", "label": "Skilled artisan labour"},
            {"key": "sales_channel", "label": "Mela/emporium/online sales channel"},
            {"key": "workspace", "label": "Workspace for production"},
        ],
        "relevant_risk_categories": ["seasonality", "buyer_concentration", "demand_volatility"],
        "infrastructure_emphasis": ["connectivity", "market_proximity"],
        "seasonality_sensitivity": "HIGH",
    },
    "food_stall": {
        "label": "Food Stall / Snacks",
        "resource_checklist": [
            {"key": "raw_material_supply", "label": "Daily raw material supply"},
            {"key": "electricity_or_fuel", "label": "Electricity or cooking fuel access"},
            {"key": "storage_perishables", "label": "Storage for perishable stock"},
            {"key": "high_footfall_location", "label": "High-footfall selling location"},
            {"key": "compliance_basics", "label": "Basic food-safety compliance"},
        ],
        "relevant_risk_categories": ["demand_volatility", "seasonality", "operational_risk"],
        "infrastructure_emphasis": ["market_proximity", "electricity"],
        "seasonality_sensitivity": "HIGH",
    },
}


def get_business_category_config(business_type: str) -> dict | None:
    return BUSINESS_CATEGORY_CONFIG.get(business_type)
