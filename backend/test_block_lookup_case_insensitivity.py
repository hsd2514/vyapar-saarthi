"""Regression tests for a real bug: block names reach the backend with
inconsistent casing (an exact web dropdown always sends "Nilanga", but a
voice-extracted value - from either the browser voice agent or the Twilio
phone flow - can come back lowercased, e.g. "nilanga"). The three block
lookups this affects (city_data.get_block, city_data.get_infrastructure,
geospatial.get_block_centroid) were exact-match dict lookups, so a
lowercased block name silently failed and every downstream feature
(feasibility report, viability engine, geospatial radius) quietly went
missing rather than erroring - discovered via a real phone-call-generated
share link that came back with feasibility: null.
"""

from city_data import get_block, get_infrastructure
from geospatial import get_block_centroid
from deterministic import generate_feasibility_report


def test_get_block_is_case_insensitive():
    exact = get_block("latur", "Nilanga")
    lowercase = get_block("latur", "nilanga")
    uppercase = get_block("latur", "NILANGA")
    assert exact is not None
    assert lowercase == exact
    assert uppercase == exact


def test_get_block_tolerates_surrounding_whitespace():
    assert get_block("latur", "  Nilanga  ") == get_block("latur", "Nilanga")


def test_get_block_returns_none_for_genuinely_unknown_block():
    assert get_block("latur", "not-a-real-block") is None


def test_get_infrastructure_is_case_insensitive():
    exact = get_infrastructure("Nilanga")
    lowercase = get_infrastructure("nilanga")
    assert exact is not None
    assert lowercase == exact


def test_get_block_centroid_is_case_insensitive():
    exact = get_block_centroid("Nilanga")
    lowercase = get_block_centroid("nilanga")
    assert exact is not None
    assert lowercase == exact


def test_feasibility_report_succeeds_with_lowercase_block_name():
    """The actual bug: a phone-call-extracted block name ('nilanga') must
    still produce a real feasibility report, not silently return nothing."""
    report = generate_feasibility_report("latur", "nilanga", "retail")
    assert report["market_reach"]["addressable_consumers"] > 0
