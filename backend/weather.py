"""Real-time weather advisory module — Vyapar Saarthi.

Fetches a 3-day forecast from Open-Meteo (free, no API key, no auth) and
applies a deterministic rule table to produce plain-language stocking advice
per business category.

Design constraints (same as deterministic.py):
- No LLM call anywhere in this file.
- Every rule is an explicit Python lambda/condition with a human-readable
  trigger_description so the UI can show the exact number that fired it.
- All financial/inventory decisions come from the table below, not inference.
- On any network failure the module returns available=False without raising.
"""

from __future__ import annotations

import urllib.error
import urllib.request
import json
from datetime import datetime, timezone
from typing import Literal

# ---------------------------------------------------------------------------
# Open-Meteo endpoint and parameter set
# ---------------------------------------------------------------------------
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 3
REQUEST_TIMEOUT_S = 8  # venue wifi may be slow; fail-fast if unreachable


def fetch_forecast(lat: float, lon: float) -> dict | None:
    """
    Call Open-Meteo and return parsed JSON, or None on any error.

    Requested variables (daily):
      - precipitation_probability_max  (%  0-100)
      - temperature_2m_max             (°C)

    Returns a dict like:
    {
      "daily": {
        "time": ["2026-09-07", "2026-09-08", "2026-09-09"],
        "precipitation_probability_max": [72, 45, 20],
        "temperature_2m_max": [30.1, 31.5, 32.0]
      }
    }
    or None on failure.
    """
    params = (
        f"latitude={lat}&longitude={lon}"
        f"&daily=precipitation_probability_max,temperature_2m_max"
        f"&forecast_days={FORECAST_DAYS}"
        f"&timezone=Asia%2FKolkata"
    )
    url = f"{OPEN_METEO_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Deterministic rule table
# ---------------------------------------------------------------------------
# Each rule entry:
#   affected      – bool: is weather meaningful for this business type?
#   rules         – list of rule dicts, each with:
#       condition          – callable(precip_probs: list[int], temps: list[float]) -> (triggered: bool, detail: str)
#                            Returns (False, "") when not triggered.
#       severity           – "warning" | "info"
#       advice             – plain language stocking recommendation
#
# Rules are evaluated in order; ALL matching rules are returned (not just first).

SeverityT = Literal["warning", "info"]


def _max_precip_rule(threshold: int, advice: str, severity: SeverityT = "warning"):
    """Factory: fire when max 3-day rain probability exceeds threshold%."""
    def condition(precip_probs: list, temps: list) -> tuple[bool, str]:
        if not precip_probs:
            return False, ""
        peak = max(precip_probs)
        peak_idx = precip_probs.index(peak)
        if peak > threshold:
            return True, f"Rain probability {peak}% on day {peak_idx + 1} exceeds {threshold}% threshold"
        return False, ""
    return {"condition": condition, "severity": severity, "advice": advice}


def _max_temp_rule(threshold: float, advice: str, severity: SeverityT = "warning"):
    """Factory: fire when max 3-day temperature exceeds threshold °C."""
    def condition(precip_probs: list, temps: list) -> tuple[bool, str]:
        if not temps:
            return False, ""
        peak = max(temps)
        peak_idx = temps.index(peak)
        if peak > threshold:
            return True, f"Max temperature {peak:.1f}°C on day {peak_idx + 1} exceeds {threshold}°C threshold"
        return False, ""
    return {"condition": condition, "severity": severity, "advice": advice}


WEATHER_RULES: dict[str, dict] = {
    "vendor": {
        "affected": True,
        "rules": [
            _max_precip_rule(
                60,
                "Reduce fresh perishable stock by ~30%: high rain/humidity accelerates spoilage of vegetables and fruit.",
                "warning",
            ),
            _max_temp_rule(
                38,
                "Move stock to shade or temporary cold storage; at this temperature leafy vegetables may wilt within 4-6 hours.",
                "warning",
            ),
        ],
    },
    "dairy": {
        "affected": True,
        "rules": [
            _max_temp_rule(
                38,
                "Heat stress typically reduces bovine milk yield 5-15%. Plan for lower collection volume and inform regular buyers early.",
                "warning",
            ),
            _max_precip_rule(
                60,
                "Heavy rain may disrupt collection routes. Maintain a 1-day buffer stock of processed/packaged products where possible.",
                "info",
            ),
        ],
    },
    "food_stall": {
        "affected": True,
        "rules": [
            _max_precip_rule(
                60,
                "Rain likely to reduce outdoor footfall. Prepare fewer perishable ingredients (raw dough, cut vegetables) for the next 1-2 days.",
                "warning",
            ),
            _max_temp_rule(
                38,
                "Extreme heat increases spoilage risk for cooked food within 2 hours. Plan smaller batch sizes and avoid dairy-heavy preparations.",
                "warning",
            ),
        ],
    },
    "tailoring": {
        "affected": False,
        "rules": [],
        "note": "Weather has minimal direct impact on tailoring operations. No stocking adjustment needed.",
    },
    "retail": {
        "affected": False,
        "rules": [],
        "note": "Weather has minimal direct impact on kirana/retail stocking. Seasonal demand patterns (festive calendar) are the stronger driver.",
    },
    "handicrafts": {
        "affected": False,
        "rules": [],
        "note": "Weather has minimal direct impact on handicraft production or sales. No stocking adjustment needed.",
    },
}


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------

def apply_weather_rules(
    business_type: str,
    precip_probs: list[int],
    temps: list[float],
) -> list[dict]:
    """
    Evaluate all rules for a business type against the 3-day forecast arrays.
    Returns a list of triggered-rule dicts (empty list = no advisories).
    Each returned dict has: severity, trigger_description, advice.
    """
    spec = WEATHER_RULES.get(business_type)
    if spec is None or not spec.get("affected"):
        return []
    triggered = []
    for rule in spec.get("rules", []):
        fired, detail = rule["condition"](precip_probs, temps)
        if fired:
            triggered.append({
                "severity": rule["severity"],
                "trigger_description": detail,
                "advice": rule["advice"],
            })
    return triggered


# ---------------------------------------------------------------------------
# High-level function called by main.py
# ---------------------------------------------------------------------------

def get_weather_advisory(lat: float, lon: float, district_label: str, business_type: str) -> dict:
    """
    Fetch weather + apply rules. Returns a fully-formed response dict that
    main.py can return directly as JSON.

    On network failure: returns {"available": False, "reason": "..."}.
    """
    raw = fetch_forecast(lat, lon)
    if raw is None:
        return {
            "available": False,
            "reason": "Weather data temporarily unavailable — Open-Meteo could not be reached. Check network connectivity.",
        }

    try:
        daily = raw["daily"]
        times: list[str] = daily["time"]
        precip_probs: list[int] = daily["precipitation_probability_max"]
        temps: list[float] = daily["temperature_2m_max"]
    except (KeyError, TypeError):
        return {
            "available": False,
            "reason": "Unexpected response format from Open-Meteo.",
        }

    # Build per-day summary for the UI to display verbatim
    forecast_days = [
        {
            "date": times[i],
            "precip_prob_pct": precip_probs[i] if i < len(precip_probs) else None,
            "temp_max_c": round(temps[i], 1) if i < len(temps) else None,
        }
        for i in range(min(FORECAST_DAYS, len(times)))
    ]

    spec = WEATHER_RULES.get(business_type, {})
    weather_affected = spec.get("affected", False)
    triggered_rules = apply_weather_rules(business_type, precip_probs, temps)

    response = {
        "available": True,
        "district": district_label,
        "coords": {"lat": lat, "lon": lon},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "forecast_days": forecast_days,
        "weather_affected": weather_affected,
        "triggered_rules": triggered_rules,
        "data_source": "Open-Meteo (open-meteo.com) — free, no API key, 3-day daily forecast",
    }
    if not weather_affected:
        response["note"] = spec.get("note", "Weather has minimal impact on this business type.")

    return response
