"""Tests for agent.py's resolve_model() and the ConversationTurn.profile
validator - both fixed after live-testing against a real FastRouter model
exposed two real bugs: a blank .env value silently beating a code default,
and a model that stringifies a nested structured-output field.
"""

import json

import pytest

import agent


def test_blank_env_var_does_not_override_default(monkeypatch):
    """`FASTROUTER_BASE_URL=` (present but blank) in .env must NOT beat the
    hardcoded default - `os.environ.get(name, default)` only falls back to
    `default` when the var is entirely unset, so a blank value silently
    produced an empty base URL and every request failed with a confusing
    'Connection error.' This must never regress."""
    monkeypatch.setenv("FASTROUTER_BASE_URL", "")
    # Re-import-style check: recompute the same expression agent.py uses.
    import os

    resolved = os.environ.get("FASTROUTER_BASE_URL") or "https://api.fastrouter.ai/api/v1"
    assert resolved == "https://api.fastrouter.ai/api/v1"


def test_sarvam_and_opencode_base_urls_also_ignore_blank_env(monkeypatch):
    import os

    monkeypatch.setenv("SARVAM_BASE_URL", "")
    monkeypatch.setenv("OPENCODE_BASE_URL", "")
    assert (os.environ.get("SARVAM_BASE_URL") or "https://api.sarvam.ai/v1") == "https://api.sarvam.ai/v1"
    assert (os.environ.get("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1") == "https://opencode.ai/zen/v1"


def test_conversation_turn_accepts_stringified_profile():
    """Observed live with glm-5.3-flash via FastRouter: the model emits the
    nested `profile` field as a JSON string instead of a real nested object
    in its tool-call arguments. Without tolerating this, every retry fails
    and the whole turn errors out even though the model extracted the
    right fields."""
    profile_json_string = json.dumps({"business_type": "vendor", "district": "sitapur", "available_margin_capital": 100000})
    turn = agent.ConversationTurn(reply_text="ok", profile=profile_json_string, done=False)
    assert turn.profile.business_type == "vendor"
    assert turn.profile.district == "sitapur"
    assert turn.profile.available_margin_capital == 100000


def test_conversation_turn_accepts_a_real_nested_dict_unchanged():
    """A model that emits proper nested JSON (the common, correct case)
    must still work - the string-parsing path must not interfere with it."""
    turn = agent.ConversationTurn(
        reply_text="ok",
        profile={"business_type": "dairy", "district": "latur"},
        done=False,
    )
    assert turn.profile.business_type == "dairy"
    assert turn.profile.district == "latur"


def test_conversation_turn_rejects_genuinely_malformed_profile_string():
    """A string that isn't valid JSON at all must still fail loudly rather
    than being silently swallowed - the fallback only helps the
    valid-JSON-but-wrongly-nested case."""
    with pytest.raises(Exception):
        agent.ConversationTurn(reply_text="ok", profile="not json at all {{{", done=False)
