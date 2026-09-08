"""Tests for share_store.py and its two consumers: the web app's own
/api/summary/share endpoint (main.py) and the Twilio call-completion
report link (twilio_ivr.py's _build_report_share_link).
"""

from fastapi.testclient import TestClient

import share_store
import twilio_ivr
from agent import ProfilePatch
from main import app

client = TestClient(app)


def test_create_and_get_share_round_trips():
    result = share_store.create_share({"profile": {"district": "latur"}}, "http://localhost:5173")
    assert result["share_url"].startswith("http://localhost:5173/#/view/")
    entry = share_store.get_share(result["share_id"])
    assert entry is not None
    assert entry["payload"]["profile"]["district"] == "latur"


def test_get_share_returns_none_for_unknown_id():
    assert share_store.get_share("does-not-exist") is None


def test_get_share_returns_none_and_evicts_expired_entry(monkeypatch):
    result = share_store.create_share({"profile": {}}, "http://localhost:5173")
    # Force this specific entry to look expired without waiting 24 hours.
    share_store.SHARE_STORE[result["share_id"]]["expires_at"] = 0
    assert share_store.get_share(result["share_id"]) is None
    assert result["share_id"] not in share_store.SHARE_STORE


def test_web_share_endpoint_create_and_retrieve():
    create_resp = client.post(
        "/api/summary/share?frontend_origin=http://localhost:5173",
        json={"profile": {"district": "sitapur"}, "operations": {}},
    )
    assert create_resp.status_code == 200
    share_id = create_resp.json()["share_id"]

    get_resp = client.get(f"/api/summary/share/{share_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["profile"]["district"] == "sitapur"


def test_web_share_endpoint_404_for_unknown_id():
    resp = client.get("/api/summary/share/totally-made-up-id")
    assert resp.status_code == 404


def test_build_report_share_link_returns_none_for_incomplete_profile():
    incomplete = ProfilePatch(district="latur", business_type="vendor")  # missing block + margin capital
    assert twilio_ivr._build_report_share_link(incomplete) is None


def test_build_report_share_link_builds_real_report_for_complete_profile():
    complete = ProfilePatch(district="latur", block="Ausa", business_type="vendor", available_margin_capital=100000)
    url = twilio_ivr._build_report_share_link(complete)
    assert url is not None
    assert url.startswith(twilio_ivr.FRONTEND_ORIGIN)

    share_id = url.rsplit("/", 1)[-1]
    entry = share_store.get_share(share_id)
    assert entry is not None
    assert entry["payload"]["profile"]["businessType"] == "vendor"
    assert entry["payload"]["structuring"]["max_loan_amount"] == 900_000  # 90% of the PS's own ₹10L worked example
    assert entry["payload"]["feasibility"] is not None
