"""Illustrative district/block-level data for three real Indian districts.

These figures are modeled on the general character of each district's
economy - they are NOT live Agmarknet/Census pulls. Every number here is
static and auditable; the LLM layer never invents numbers of its own, it
only narrates what's already computed from this table.
"""

from __future__ import annotations

CITY_DATA: dict[str, dict] = {
    "latur": {
        "label": "Latur, Maharashtra",
        "state": "Maharashtra",
        "district": "Latur",
        "profile_note": "Major tur dal (pigeon pea) and soybean mandi belt in the Marathwada region.",
        "blocks": {
            "Latur": {"contacts": [{"name": "Latur District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Latur CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Latur Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 482000, "competition_density": {"vendor": 12, "dairy": 7, "textiles": 5, "retail": 13, "handicrafts": 4, "food_stall": 10}},
            "Ausa": {"contacts": [{"name": "Ausa District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Ausa CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Ausa Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 168000, "competition_density": {"vendor": 8, "dairy": 5, "textiles": 3, "retail": 9, "handicrafts": 2, "food_stall": 6}},
            "Nilanga": {"contacts": [{"name": "Nilanga District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Nilanga CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Nilanga Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 154000, "competition_density": {"vendor": 7, "dairy": 4, "textiles": 3, "retail": 8, "handicrafts": 2, "food_stall": 5}},
            "Renapur": {"contacts": [{"name": "Renapur District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Renapur CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Renapur Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 98000, "competition_density": {"vendor": 5, "dairy": 3, "textiles": 2, "retail": 6, "handicrafts": 1, "food_stall": 4}},
            "Chakur": {"contacts": [{"name": "Chakur District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Chakur CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Chakur Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 112000, "competition_density": {"vendor": 6, "dairy": 3, "textiles": 2, "retail": 6, "handicrafts": 1, "food_stall": 4}},
        },
        "commodities": {
            "vendor": {"unit": "quintal (tur dal)", "low": 6200, "high": 8400, "current": 7600},
            "dairy": {"unit": "litre (milk)", "low": 32, "high": 44, "current": 40},
            "textiles": {"unit": "metre (cloth)", "low": 85, "high": 150, "current": 98},
            "retail": {"unit": "basket index", "low": 100, "high": 126, "current": 118},
            "handicrafts": {"unit": "kg (raw material)", "low": 55, "high": 130, "current": 72},
            "food_stall": {"unit": "kg (wheat flour)", "low": 27, "high": 39, "current": 30},
        },
        "seasonal_peak": {
            "vendor": "Rabi harvest arrival (Nov-Dec)", "dairy": "Diwali sweets season (Oct)",
            "textiles": "Wedding season (Nov-Feb)", "retail": "Diwali retail rush (Oct)",
            "handicrafts": "Diwali gifting season (Oct)", "food_stall": "Local yatra/jatra season (Jan-Feb)",
        },
    },
    "sitapur": {
        "label": "Sitapur, Uttar Pradesh",
        "state": "Uttar Pradesh",
        "district": "Sitapur",
        "profile_note": "Sugarcane and paddy belt in central Awadh, dense weekly haats (rural markets).",
        "blocks": {
            "Biswan": {"contacts": [{"name": "Biswan District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Biswan CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Biswan Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 210000, "competition_density": {"vendor": 14, "dairy": 6, "textiles": 4, "retail": 11, "handicrafts": 3, "food_stall": 9}},
            "Mahmoodabad": {"contacts": [{"name": "Mahmoodabad District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Mahmoodabad CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Mahmoodabad Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 176000, "competition_density": {"vendor": 11, "dairy": 5, "textiles": 3, "retail": 9, "handicrafts": 2, "food_stall": 7}},
            "Sidhauli": {"contacts": [{"name": "Sidhauli District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Sidhauli CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Sidhauli Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 165000, "competition_density": {"vendor": 10, "dairy": 5, "textiles": 3, "retail": 8, "handicrafts": 2, "food_stall": 7}},
            "Laharpur": {"contacts": [{"name": "Laharpur District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Laharpur CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Laharpur Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 132000, "competition_density": {"vendor": 8, "dairy": 4, "textiles": 2, "retail": 7, "handicrafts": 2, "food_stall": 5}},
            "Machhrehta": {"contacts": [{"name": "Machhrehta District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Machhrehta CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Machhrehta Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 89000, "competition_density": {"vendor": 6, "dairy": 3, "textiles": 2, "retail": 5, "handicrafts": 1, "food_stall": 4}},
        },
        "commodities": {
            "vendor": {"unit": "kg (tomato)", "low": 12, "high": 38, "current": 31},
            "dairy": {"unit": "litre (milk)", "low": 38, "high": 52, "current": 48},
            "textiles": {"unit": "metre (cloth)", "low": 90, "high": 160, "current": 102},
            "retail": {"unit": "basket index", "low": 98, "high": 124, "current": 116},
            "handicrafts": {"unit": "kg (raw material)", "low": 58, "high": 128, "current": 74},
            "food_stall": {"unit": "kg (wheat flour)", "low": 26, "high": 40, "current": 29},
        },
        "seasonal_peak": {
            "vendor": "Diwali produce demand (Oct)", "dairy": "Diwali sweets season (Oct)",
            "textiles": "Wedding & festival season (Oct-Nov)", "retail": "Diwali retail rush (Oct)",
            "handicrafts": "Diwali gifting season (Oct)", "food_stall": "Diwali-Chhath snacking season (Oct-Nov)",
        },
    },
    "indore": {
        "label": "Indore, Madhya Pradesh",
        "state": "Madhya Pradesh",
        "district": "Indore",
        "profile_note": "MP's largest commercial hub - dense retail, textile and namkeen (snack) trade.",
        "blocks": {
            "Sanwer": {"contacts": [{"name": "Sanwer District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Sanwer CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Sanwer Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 198000, "competition_density": {"vendor": 16, "dairy": 9, "textiles": 8, "retail": 18, "handicrafts": 5, "food_stall": 15}},
            "Depalpur": {"contacts": [{"name": "Depalpur District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Depalpur CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Depalpur Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 172000, "competition_density": {"vendor": 13, "dairy": 7, "textiles": 6, "retail": 15, "handicrafts": 4, "food_stall": 12}},
            "Mhow": {"contacts": [{"name": "Mhow District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Mhow CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Mhow Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 224000, "competition_density": {"vendor": 15, "dairy": 8, "textiles": 7, "retail": 17, "handicrafts": 5, "food_stall": 14}},
            "Hatod": {"contacts": [{"name": "Hatod District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Hatod CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Hatod Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 96000, "competition_density": {"vendor": 8, "dairy": 4, "textiles": 3, "retail": 9, "handicrafts": 2, "food_stall": 7}},
            "Rau": {"contacts": [{"name": "Rau District Bank (Sample)", "type": "Bank", "note": "Handles PMEGP and Term Loans"}, {"name": "Rau CSC Center (Sample)", "type": "CSC", "note": "Helps with PM Svanidhi"}, {"name": "Rau Mahila SHG Federation (Sample)", "type": "SHG", "note": "Handles Micro Finance"}], "population": 143000, "competition_density": {"vendor": 11, "dairy": 6, "textiles": 5, "retail": 12, "handicrafts": 3, "food_stall": 10}},
        },
        "commodities": {
            "vendor": {"unit": "quintal (soybean)", "low": 3900, "high": 5000, "current": 4600},
            "dairy": {"unit": "litre (milk)", "low": 40, "high": 54, "current": 50},
            "textiles": {"unit": "metre (cloth)", "low": 95, "high": 175, "current": 120},
            "retail": {"unit": "basket index", "low": 102, "high": 130, "current": 124},
            "handicrafts": {"unit": "kg (raw material)", "low": 60, "high": 135, "current": 80},
            "food_stall": {"unit": "kg (wheat flour)", "low": 27, "high": 41, "current": 31},
        },
        "seasonal_peak": {
            "vendor": "Navratri-Diwali produce demand (Oct)", "dairy": "Diwali sweets season (Oct)",
            "textiles": "Wedding & festival season (Oct-Feb)", "retail": "Diwali retail rush (Oct)",
            "handicrafts": "Diwali gifting season (Oct)", "food_stall": "Navratri snacking season (Sep-Oct)",
        },
    },
}

COMPETITION_DENSITY_MAX = 20

BUSINESS_TYPES = [
    {"value": "vendor", "label": "Vegetable / Fruit Vendor"},
    {"value": "dairy", "label": "Dairy (Milk & Products)"},
    {"value": "textiles", "label": "Textiles & Tailoring"},
    {"value": "retail", "label": "Retail / Kirana Shop"},
    {"value": "handicrafts", "label": "Handicrafts"},
    {"value": "food_stall", "label": "Food Stall / Snacks"},
]

# Share of a block's population that is a plausible regular customer for
# this business category, within a 5-10km reach - illustrative, not census.
RELEVANT_CONSUMER_SHARE = {
    "vendor": 0.55, "dairy": 0.35, "textiles": 0.20, "retail": 0.60, "handicrafts": 0.08, "food_stall": 0.25,
}

# Roughly how many addressable consumers a single business of this category
# can typically serve before the market reads as "saturated" for it - used
# as the benchmark for the Opportunity Analysis signal. This must scale
# with RELEVANT_CONSUMER_SHARE (a low-share category like handicrafts needs
# a much lower benchmark than a high-share category like retail), otherwise
# every block reads as under-served regardless of the real competitor count.
EXPECTED_CONSUMERS_PER_COMPETITOR = {
    "vendor": 13000, "dairy": 15000, "textiles": 12000, "retail": 13000, "handicrafts": 8000, "food_stall": 8000,
}

DISTRIBUTION_CHANNELS = {
    "vendor": ["Weekly haat / local mandi stall", "Roadside pushcart", "Standing WhatsApp order groups"],
    "dairy": ["Doorstep delivery route", "Local dairy cooperative pooling point", "Sweet shops and tea stalls as bulk buyers"],
    "textiles": ["Tailoring shop counter sales", "Wedding-season bulk stitching contracts", "Local cloth market stall"],
    "retail": ["Walk-in kirana counter", "Local wholesaler tie-up for stock", "Festive-season bulk orders"],
    "handicrafts": ["Local mela / exhibition stalls", "State government emporium consignment", "Online marketplace listing"],
    "food_stall": ["Roadside stall at a transit point", "Local mela / fair stall", "Tiffin or delivery service to nearby offices"],
}

# Named threat categories per business type - matches the PS's explicit
# ask for "supply chain bottlenecks, seasonal demand fluctuations, or
# dependency on single buyers."
THREAT_TEMPLATES = {
    "vendor": [
        "Seasonal demand fluctuation around the harvest and festival calendar",
        "Spoilage risk from limited cold storage for perishable stock",
        "Transport cost dependency on a single mandi route",
    ],
    "dairy": [
        "Feed and veterinary supply chain bottlenecks in peak summer",
        "Milk yield seasonality tied to fodder availability",
        "Price dependency on a small number of local collection points",
    ],
    "textiles": [
        "Heavy revenue concentration in the wedding/festival season, thin months otherwise",
        "Raw material (cloth) price volatility",
        "Dependency on a small number of repeat bulk-order customers",
    ],
    "retail": [
        "Margin pressure from larger retail competitors in the same block",
        "Working capital strain from bulk-stocking before festive demand",
        "Single-wholesaler dependency for stock replenishment",
    ],
    "handicrafts": [
        "Thin, seasonal demand concentrated around gifting occasions",
        "Dependency on a single trader or emporium for offtake",
        "Raw material sourcing bottlenecks in remote blocks",
    ],
    "food_stall": [
        "Perishable stock risk on low-footfall days",
        "Seasonal footfall swings around local fairs/festivals",
        "Dependency on a single high-traffic location",
    ],
}


def get_block(district_key: str, block_name: str) -> dict | None:
    """Case-insensitive, whitespace-tolerant block lookup. Block names reach
    this function from several sources with no consistent casing - a web
    dropdown always sends the exact key, but a voice-extracted value (from
    either the browser voice agent or the Twilio phone flow) can come back
    lowercased, capitalised differently, or with stray whitespace (e.g. the
    LLM extracting "nilanga" while the data's own key is "Nilanga"). An exact
    dict lookup silently failed on that mismatch - the feasibility report,
    financial structuring, and every downstream feature all quietly went
    missing rather than erroring, which is worse than being permissive here."""
    district = CITY_DATA.get(district_key)
    if not district:
        return None
    blocks = district.get("blocks", {})
    if block_name in blocks:
        return blocks[block_name]
    normalized = block_name.strip().casefold()
    for key, value in blocks.items():
        if key.casefold() == normalized:
            return value
    return None


# ---------------------------------------------------------------------------
# Illustrative per-block infrastructure scores (0-100), for the Hyper-Local
# Viability Engine's Location & Infrastructure dimension. Same "static and
# auditable, NOT a live sensor/survey feed" character as the rest of this
# file (see module docstring) - correlated with each block's population and
# its district's profile note (larger, more urban blocks score higher)
# rather than assigned arbitrarily. Exposed to the API only through
# data_providers.py, which tags every value provenance="DEMO" - never
# presented as verified/live infrastructure data.
# ---------------------------------------------------------------------------
BLOCK_INFRASTRUCTURE: dict[str, dict] = {
    # Latur district
    "Latur": {"accessibility": 78, "transport": 75, "market_proximity": 82, "electricity": 80, "water": 65, "connectivity": 70},
    "Ausa": {"accessibility": 60, "transport": 58, "market_proximity": 62, "electricity": 65, "water": 55, "connectivity": 50},
    "Nilanga": {"accessibility": 55, "transport": 52, "market_proximity": 58, "electricity": 62, "water": 50, "connectivity": 45},
    "Renapur": {"accessibility": 45, "transport": 42, "market_proximity": 48, "electricity": 55, "water": 45, "connectivity": 35},
    "Chakur": {"accessibility": 48, "transport": 45, "market_proximity": 50, "electricity": 58, "water": 48, "connectivity": 38},
    # Sitapur district
    "Biswan": {"accessibility": 62, "transport": 58, "market_proximity": 68, "electricity": 60, "water": 55, "connectivity": 48},
    "Mahmoodabad": {"accessibility": 55, "transport": 50, "market_proximity": 60, "electricity": 55, "water": 50, "connectivity": 42},
    "Sidhauli": {"accessibility": 52, "transport": 48, "market_proximity": 56, "electricity": 52, "water": 48, "connectivity": 40},
    "Laharpur": {"accessibility": 46, "transport": 42, "market_proximity": 50, "electricity": 48, "water": 44, "connectivity": 35},
    "Machhrehta": {"accessibility": 40, "transport": 36, "market_proximity": 44, "electricity": 45, "water": 40, "connectivity": 30},
    # Indore district
    "Sanwer": {"accessibility": 72, "transport": 70, "market_proximity": 75, "electricity": 82, "water": 68, "connectivity": 65},
    "Depalpur": {"accessibility": 65, "transport": 62, "market_proximity": 68, "electricity": 75, "water": 62, "connectivity": 58},
    "Mhow": {"accessibility": 80, "transport": 78, "market_proximity": 78, "electricity": 85, "water": 70, "connectivity": 72},
    "Hatod": {"accessibility": 55, "transport": 52, "market_proximity": 58, "electricity": 68, "water": 55, "connectivity": 48},
    "Rau": {"accessibility": 68, "transport": 65, "market_proximity": 70, "electricity": 78, "water": 60, "connectivity": 62},
}


def get_infrastructure(block_name: str) -> dict | None:
    """Case-insensitive for the same reason get_block() above is - a
    voice-extracted block name can arrive in different casing than this
    dict's keys."""
    if block_name in BLOCK_INFRASTRUCTURE:
        return BLOCK_INFRASTRUCTURE[block_name]
    normalized = block_name.strip().casefold()
    for key, value in BLOCK_INFRASTRUCTURE.items():
        if key.casefold() == normalized:
            return value
    return None
