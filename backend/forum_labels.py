"""Label taxonomy for Vyapar Chaupal (the discussion forum).

Every post carries three label axes - Trade, Stage, Topic - plus a post
type. This is not decoration: the field evidence the forum is designed on
(Avaaj Otalo, CHI 2010) found 85% of rural users wanted topic-wise
browsing and 77% valued *listening to people like them* over posting.
Labels are how a listener finds "someone in my trade, at my stage, with my
problem". Trade and Stage come from the member's profile; Topic is guessed
from the post text (keyword heuristic here, LLM-refined in forum_router.py
when a model is configured) and confirmed by the poster.

Deliberately absent: caste, religion, income. Identity on the forum is
trade + place + stage, nothing else.
"""

from __future__ import annotations

from city_data import BUSINESS_TYPES

# Trades = the app's own business categories plus the farm-allied activities
# the NABARD Maharashtra unit-cost booklet (2026-27) covers, so a goat or
# poultry entrepreneur has a room even before the app's feasibility engine
# has demand data for them.
TRADES: list[dict] = [*BUSINESS_TYPES] + [
    {"value": "goat", "label": "Goat / Sheep Rearing"},
    {"value": "poultry", "label": "Poultry"},
    {"value": "other", "label": "Other"},
]
TRADE_VALUES = {t["value"] for t in TRADES}

# Where the member is in the loan journey. Self-declared; the app can later
# verify milestones it actually knows about (a share-link report, a
# repayment ledger) and upgrade trust_level - see forum_store.py.
STAGES: list[dict] = [
    {"value": "thinking", "label": "Still thinking"},
    {"value": "applied", "label": "Applied, waiting"},
    {"value": "sanctioned", "label": "Sanctioned, waiting for money"},
    {"value": "running", "label": "Running (under 1 year)"},
    {"value": "repaying", "label": "Repaying"},
    {"value": "repaid", "label": "Fully repaid"},
    {"value": "struggling", "label": "Closed / struggling"},
]
STAGE_VALUES = {s["value"] for s in STAGES}

TOPICS: list[dict] = [
    {"value": "loan_scheme", "label": "Loan & scheme"},
    {"value": "bank_process", "label": "Bank / SCA process"},
    {"value": "prices", "label": "Prices & costs"},
    {"value": "selling", "label": "Selling & buyers"},
    {"value": "suppliers", "label": "Suppliers & inputs"},
    {"value": "repayment", "label": "Repayment trouble"},
    {"value": "training", "label": "Training & skills"},
    {"value": "operations", "label": "Animals, machines & daily running"},
    {"value": "scam", "label": "Scam alert"},
]
TOPIC_VALUES = {t["value"] for t in TOPICS}

POST_TYPES: list[dict] = [
    {"value": "question", "label": "Question"},
    {"value": "experience", "label": "My experience"},
    {"value": "price_report", "label": "Price I paid"},
    {"value": "wait_report", "label": "How long my loan took"},
    {"value": "looking_for", "label": "Looking for a buyer / supplier"},
    {"value": "warning", "label": "Warning"},
]
POST_TYPE_VALUES = {p["value"] for p in POST_TYPES}

# Verified roles wear a badge and get the "expert answer" slot on threads.
# The field study is unambiguous on this: 65% of users wanted answers from
# a credentialed source and nobody wanted peer-only; when the credentialed
# slot went quiet, the forum died. Members can never self-assign these.
EXPERT_ROLES: list[dict] = [
    {"value": "bank_officer", "label": "Bank officer"},
    {"value": "sca_officer", "label": "SCA / corporation officer"},
    {"value": "rseti_trainer", "label": "RSETI trainer"},
    {"value": "crp_ep", "label": "CRP-EP (enterprise mentor)"},
    {"value": "vet_kvk", "label": "Vet / KVK scientist"},
]
EXPERT_ROLE_VALUES = {r["value"] for r in EXPERT_ROLES}

# Keyword heuristic for the Topic axis - deliberately simple and auditable.
# Hindi/Marathi terms are included in Roman transliteration because that is
# how most typed posts arrive (see agent.py's system prompts). The LLM pass
# in forum_router.py can override this when a model is configured; when it
# is not, this is the whole classifier and it must not be embarrassing.
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "scam": ["scam", "fraud", "fake", "agent", "processing fee", "guarantee", "guaranteed", "approval letter", "dalal", "dhokha", "fees pehle", "fee pehle"],
    "repayment": ["emi", "instalment", "installment", "default", "overdue", "kist", "hafta", "repay", "bounce", "cannot pay", "nahi de pa", "moratorium"],
    "loan_scheme": ["loan", "scheme", "yojana", "subsidy", "margin", "nbcfdc", "nsfdc", "mudra", "pmegp", "term loan", "micro finance", "karz", "karj"],
    "bank_process": ["bank", "sanction", "disburse", "document", "kagaz", "certificate", "branch", "manager", "sca", "corporation", "mahamandal", "visit", "chakkar"],
    "prices": ["price", "cost", "rate", "bhav", "kimat", "kitne ka", "kitna", "rs", "rupee", "lakh", "expensive", "mehnga", "cheap"],
    "selling": ["sell", "buyer", "customer", "dairy society", "vendor", "market", "bechna", "grahak", "kharidar", "demand", "order"],
    "suppliers": ["supplier", "fodder", "chara", "feed", "raw material", "wholesale", "machine dealer", "stock", "kachcha maal"],
    "training": ["training", "rseti", "course", "sikhna", "seekh", "prashikshan", "skill", "certificate course", "edp"],
    "operations": ["animal", "buffalo", "bhains", "cow", "gai", "goat", "bakri", "chicken", "murgi", "disease", "bimar", "vet", "doctor", "machine", "sewing", "silai", "shed", "milk yield", "doodh"],
}


def guess_topic(text: str) -> str:
    """Cheap, explainable first guess at the Topic axis. Scam and repayment
    win ties on purpose - they are the two topics where a wrong label has a
    real cost (a scam post landing in 'prices' is exactly what an agent
    wants; a repayment-trouble post landing anywhere public defeats the
    pre-moderated room it belongs in)."""
    lowered = text.casefold()
    best, best_score = "loan_scheme", 0
    for topic, words in _TOPIC_KEYWORDS.items():
        score = sum(1 for w in words if w in lowered)
        if score > best_score:
            best, best_score = topic, score
    return best


def label_for(values: list[dict], value: str) -> str:
    for entry in values:
        if entry["value"] == value:
            return entry["label"]
    return value
