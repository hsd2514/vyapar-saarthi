"""Tests for the Twilio phone-call (IVR) integration. Uses TestClient
against the real router - the intake agent call itself is not mocked, so
these only exercise paths that don't require a live LLM key (the "no
speech heard" re-prompt paths) plus the pure helper function. Full
conversational-turn coverage needs a configured AGENT_MODEL + API key and
is exercised manually, same as the rest of the intake agent's LLM paths.
"""

from fastapi.testclient import TestClient

from main import app
from twilio_ivr import _strip_for_speech

client = TestClient(app)


def test_strip_for_speech_removes_markdown():
    assert _strip_for_speech("**one lakh** rupees") == "one lakh rupees"
    assert _strip_for_speech("# heading\nnext line") == " heading next line"
    assert _strip_for_speech("`code` and _emphasis_") == "code and emphasis"


def test_strip_for_speech_leaves_plain_text_untouched():
    assert _strip_for_speech("Sitapur mein sabzi bechta hoon") == "Sitapur mein sabzi bechta hoon"


def test_gather_with_no_speech_result_reprompts_without_calling_llm():
    """When Twilio posts an empty SpeechResult (caller said nothing
    intelligible), the endpoint must re-prompt without needing the LLM at
    all - this must work even with no API key configured."""
    resp = client.post("/api/twilio/gather", data={"CallSid": "CAtest123", "SpeechResult": ""})
    assert resp.status_code == 200
    assert "Sorry, I did not catch that" in resp.text
    assert "<Gather" in resp.text


def test_gather_response_is_valid_twiml_content_type():
    resp = client.post("/api/twilio/gather", data={"CallSid": "CAtest456", "SpeechResult": ""})
    assert resp.headers["content-type"].startswith("application/xml")
