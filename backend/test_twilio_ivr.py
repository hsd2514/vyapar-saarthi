"""Tests for the Twilio phone-call (IVR) integration. Uses TestClient
against the real router - the intake agent call itself is not mocked, so
these only exercise paths that don't require a live LLM key (the "no
speech heard" re-prompt paths) plus the pure helper function and the
signature-verification gate. Full conversational-turn coverage needs a
configured AGENT_MODEL + API key and is exercised manually, same as the
rest of the intake agent's LLM paths.
"""

from twilio.request_validator import RequestValidator
from fastapi.testclient import TestClient

import twilio_ivr
from main import app
from twilio_ivr import _strip_for_speech

client = TestClient(app)


def test_strip_for_speech_removes_markdown():
    assert _strip_for_speech("**one lakh** rupees") == "one lakh rupees"
    assert _strip_for_speech("# heading\nnext line") == " heading next line"
    assert _strip_for_speech("`code` and _emphasis_") == "code and emphasis"


def test_strip_for_speech_leaves_plain_text_untouched():
    assert _strip_for_speech("Sitapur mein sabzi bechta hoon") == "Sitapur mein sabzi bechta hoon"


def test_gather_with_no_speech_result_reprompts_without_calling_llm(monkeypatch):
    """When Twilio posts an empty SpeechResult (caller said nothing
    intelligible), the endpoint must re-prompt without needing the LLM at
    all. Signature verification is skipped here (TWILIO_AUTH_TOKEN patched
    empty) since this test is about the re-prompt logic, not the
    signature gate - that's covered separately below."""
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "")
    resp = client.post("/api/twilio/gather", data={"CallSid": "CAtest123", "SpeechResult": ""})
    assert resp.status_code == 200
    assert "Sorry, I did not catch that" in resp.text
    assert "<Gather" in resp.text


def test_gather_response_is_valid_twiml_content_type(monkeypatch):
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "")
    resp = client.post("/api/twilio/gather", data={"CallSid": "CAtest456", "SpeechResult": ""})
    assert resp.headers["content-type"].startswith("application/xml")


def test_unsigned_request_rejected_when_auth_token_configured(monkeypatch):
    """Once TWILIO_AUTH_TOKEN is set (as it must be on any real deployment),
    a webhook call with no/invalid X-Twilio-Signature header must be
    rejected - this is what stops a public endpoint from being spoofed into
    injecting fake call turns."""
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "test-auth-token")
    resp = client.post("/api/twilio/gather", data={"CallSid": "CAtest789", "SpeechResult": ""})
    assert resp.status_code == 403


def test_correctly_signed_request_is_accepted(monkeypatch):
    """A request signed the way Twilio actually signs it (RequestValidator
    with the shared auth token) must pass verification."""
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "test-auth-token")
    validator = RequestValidator("test-auth-token")
    url = "http://testserver/api/twilio/gather"
    params = {"CallSid": "CAtestsigned", "SpeechResult": ""}
    signature = validator.compute_signature(url, params)
    resp = client.post("/api/twilio/gather", data=params, headers={"X-Twilio-Signature": signature})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Outbound "call me" endpoint - Twilio's own REST client is mocked so these
# tests never place a real phone call or spend real Twilio credit.
# ---------------------------------------------------------------------------

def test_call_me_rejects_when_credentials_missing(monkeypatch):
    monkeypatch.setattr(twilio_ivr, "TWILIO_ACCOUNT_SID", "")
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(twilio_ivr, "TWILIO_PHONE_NUMBER", "+15550000000")
    resp = client.post("/api/twilio/call-me", json={"to": "+15551234567"})
    assert resp.status_code == 500
    assert "TWILIO_ACCOUNT_SID" in resp.json()["detail"]


def test_call_me_rejects_when_public_base_url_missing(monkeypatch):
    monkeypatch.setattr(twilio_ivr, "TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(twilio_ivr, "TWILIO_PHONE_NUMBER", "+15550000000")
    monkeypatch.setattr(twilio_ivr, "PUBLIC_BASE_URL", "")
    resp = client.post("/api/twilio/call-me", json={"to": "+15551234567"})
    assert resp.status_code == 500
    assert "TWILIO_PUBLIC_BASE_URL" in resp.json()["detail"]


def test_call_me_places_call_with_correct_params(monkeypatch):
    monkeypatch.setattr(twilio_ivr, "TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(twilio_ivr, "TWILIO_PHONE_NUMBER", "+15550000000")
    monkeypatch.setattr(twilio_ivr, "PUBLIC_BASE_URL", "https://example.ngrok-free.dev")

    captured = {}

    class FakeCall:
        sid = "CAfake123"
        status = "queued"

    class FakeCallsResource:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeCall()

    class FakeTwilioClient:
        def __init__(self, *a, **kw):
            self.calls = FakeCallsResource()

    monkeypatch.setattr(twilio_ivr, "TwilioClient", FakeTwilioClient)

    resp = client.post("/api/twilio/call-me", json={"to": "+15551234567"})
    assert resp.status_code == 200
    assert resp.json() == {"call_sid": "CAfake123", "status": "queued"}
    assert captured["to"] == "+15551234567"
    assert captured["from_"] == "+15550000000"
    assert captured["url"] == "https://example.ngrok-free.dev/api/twilio/voice"


def test_call_me_surfaces_twilio_errors_as_502(monkeypatch):
    monkeypatch.setattr(twilio_ivr, "TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setattr(twilio_ivr, "TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setattr(twilio_ivr, "TWILIO_PHONE_NUMBER", "+15550000000")
    monkeypatch.setattr(twilio_ivr, "PUBLIC_BASE_URL", "https://example.ngrok-free.dev")

    class FakeCallsResource:
        def create(self, **kwargs):
            raise RuntimeError("unverified number on trial account")

    class FakeTwilioClient:
        def __init__(self, *a, **kw):
            self.calls = FakeCallsResource()

    monkeypatch.setattr(twilio_ivr, "TwilioClient", FakeTwilioClient)

    resp = client.post("/api/twilio/call-me", json={"to": "+15551234567"})
    assert resp.status_code == 502
    assert "unverified number" in resp.json()["detail"]
