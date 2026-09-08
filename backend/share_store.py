"""In-memory shareable-report store, used by both the web app's own
"share a link to my summary" feature (main.py's /api/summary/share) and
the Twilio call flow (twilio_ivr.py generates one automatically the
moment a phone call finishes, so the report is viewable in a browser
afterward without asking the caller to read anything back over voice).

Pulled out into its own module specifically so twilio_ivr.py can create a
share without importing from main.py (which itself imports twilio_ivr.py
to register its router - that would be a circular import).

Storage: plain in-memory dict. Cleared on server restart (acceptable for
a demo - see main.py's original comment on this). Entries expire after
SHARE_TTL_SECONDS; main.py's background task prunes them periodically via
cleanup_expired().
"""

from __future__ import annotations

import secrets
import time
from typing import Any

SHARE_STORE: dict[str, dict[str, Any]] = {}
SHARE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def create_share(payload: dict, frontend_origin: str) -> dict:
    """Stores `payload` and returns {share_id, share_url, expires_at}.
    share_url uses the HashRouter fragment format (#/view/<id>) the
    frontend's SharedSummaryView route expects."""
    share_id = secrets.token_urlsafe(8)
    created_at = time.time()
    expires_at = created_at + SHARE_TTL_SECONDS
    SHARE_STORE[share_id] = {
        "payload": payload,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    share_url = f"{frontend_origin.rstrip('/')}/#/view/{share_id}"
    return {"share_id": share_id, "share_url": share_url, "expires_at": expires_at}


def get_share(share_id: str) -> dict | None:
    """Returns the stored entry (with 'payload' and 'expires_at' keys), or
    None if unknown or expired (lazily removing it in the expired case)."""
    entry = SHARE_STORE.get(share_id)
    if entry is None:
        return None
    if time.time() > entry["expires_at"]:
        SHARE_STORE.pop(share_id, None)
        return None
    return entry


def cleanup_expired() -> None:
    cutoff = time.time() - SHARE_TTL_SECONDS
    stale = [sid for sid, entry in SHARE_STORE.items() if entry["created_at"] < cutoff]
    for sid in stale:
        SHARE_STORE.pop(sid, None)
