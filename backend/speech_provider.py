"""Speech provider interface - preparation only (not wired into the live
voice pipeline this phase; the app's voice intake still uses the browser's
own Web Speech API for STT/TTS, unchanged). This gives a documented adapter
shape for a future backend-side Sarvam integration without making Sarvam
mandatory or touching the current voice flow.

Real Sarvam endpoints this would call once SARVAM_API_KEY is set (see
https://docs.sarvam.ai - subject to Sarvam's own versioning):
- POST https://api.sarvam.ai/speech-to-text        (Saarika models; Saaras for
  code-mixed Indic speech translation-while-transcribing)
- POST https://api.sarvam.ai/text-to-speech         (Bulbul models)
Both take an `api-subscription-key` header, not a Bearer token - different
from the OpenAI-compatible chat endpoint agent.py already uses for
`sarvam:<model>` chat models.

SARVAM_API_KEY must never be read or referenced from any frontend code -
this module is backend-only, matching how the key is already handled in
agent.py.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class SpeechProvider(ABC):
    """Adapter interface a real backend-side speech provider would implement.
    Not called by any live endpoint yet - see module docstring."""

    @abstractmethod
    def speech_to_text(self, audio_bytes: bytes, language: str) -> dict:
        """Returns {"text": str, "status": "OK"} or {"status": "UNAVAILABLE", "reason": str}."""

    @abstractmethod
    def text_to_speech(self, text: str, language: str) -> dict:
        """Returns {"audio_bytes": bytes, "status": "OK"} or {"status": "UNAVAILABLE", "reason": str}."""


class MockSpeechProvider(SpeechProvider):
    """Always reports itself unavailable - used when no real provider is
    configured, so the app never pretends to have a working speech backend
    it doesn't have."""

    def speech_to_text(self, audio_bytes: bytes, language: str) -> dict:
        return {"status": "UNAVAILABLE", "reason": "No speech provider configured for this phase."}

    def text_to_speech(self, text: str, language: str) -> dict:
        return {"status": "UNAVAILABLE", "reason": "No speech provider configured for this phase."}


class SarvamProvider(SpeechProvider):
    """Documented stub for a future real integration. Deliberately raises
    NotImplementedError rather than returning a fake success - implementing
    this is out of this phase's scope (see README's Phase 3 notes)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SARVAM_API_KEY")

    def speech_to_text(self, audio_bytes: bytes, language: str) -> dict:
        if not self.api_key:
            return {"status": "UNAVAILABLE", "reason": "SARVAM_API_KEY is not set."}
        raise NotImplementedError("Sarvam speech-to-text integration is prepared but not implemented this phase.")

    def text_to_speech(self, text: str, language: str) -> dict:
        if not self.api_key:
            return {"status": "UNAVAILABLE", "reason": "SARVAM_API_KEY is not set."}
        raise NotImplementedError("Sarvam text-to-speech integration is prepared but not implemented this phase.")


def get_speech_provider() -> SpeechProvider:
    """Returns a real provider only if SARVAM_API_KEY is set, else the mock -
    never silently fabricates availability."""
    if os.environ.get("SARVAM_API_KEY"):
        return SarvamProvider()
    return MockSpeechProvider()
