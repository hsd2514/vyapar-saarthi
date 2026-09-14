"""Safety layer for Vyapar Chaupal: PII redaction, scam-pattern detection,
and near-duplicate detection.

Threat model, from PIB Fact Check bulletins (2025-26): fake MUDRA / PMEGP
"approval letters" circulate on WhatsApp demanding a Rs 2,550-36,500
"processing fee". Any space where rural borrowers gather will attract
agents selling guaranteed sanction. The forum therefore has no direct
messages, strips contact handles from posts, and holds anything that reads
like a fee-for-approval pitch for a moderator before it is published.

Everything here is deterministic and auditable - regexes and keyword lists,
not a model - so a held post can always be explained to its author.
"""

from __future__ import annotations

import re

# Indian mobile numbers (10 digits starting 6-9, optional +91/0 prefix and
# separators), UPI handles, 12-digit Aadhaar-shaped strings, and long
# digit runs that look like bank account numbers.
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_UPI_RE = re.compile(r"\b[\w.\-]{2,}@(?:ybl|oksbi|okaxis|okhdfcbank|okicici|paytm|upi|apl|ibl|axl|sbi|hdfcbank|icici|kotak|fbl|jio|airtel)\b", re.I)
_AADHAAR_RE = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_ACCOUNT_RE = re.compile(r"(?<!\d)\d{11,18}(?!\d)")

REDACTED = "[number removed]"


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Returns (clean_text, kinds_removed). Order matters: the 11-18 digit
    account pattern would otherwise eat an Aadhaar-shaped string first."""
    kinds: list[str] = []
    clean = text
    for kind, pattern in (("upi", _UPI_RE), ("phone", _PHONE_RE), ("aadhaar", _AADHAAR_RE), ("account", _ACCOUNT_RE)):
        clean, n = pattern.subn(REDACTED, clean)
        if n:
            kinds.append(kind)
    return clean, kinds


# Phrases that, in this segment, almost only appear in fee-for-approval
# pitches. Hindi/Marathi in Roman transliteration because that is how posts
# arrive. A single hit holds the post; a warning-type post from the author
# about a scam is expected to hit these too - moderators publish those.
_SCAM_PATTERNS: list[str] = [
    "processing fee", "processing charge", "file charge", "registration fee",
    "guaranteed loan", "guaranteed sanction", "guarantee sanction", "100% sanction", "100% approval",
    "approval letter", "sanction letter received", "pay first", "pehle fees", "pehle paisa", "advance fee",
    "agent se", "dalal", "contact me for loan", "loan chahiye to call", "whatsapp me",
    "instant loan", "loan in 24 hours", "loan in 2 days", "without document",
]


def scam_signals(text: str) -> list[str]:
    lowered = text.casefold()
    return [p for p in _SCAM_PATTERNS if p in lowered]


_TOKEN_RE = re.compile(r"[a-z0-9ऀ-ॿ]{3,}")
_STOP = {"the", "and", "for", "with", "hai", "hain", "kya", "koi", "mera", "meri", "aur", "this", "that", "from", "have", "how", "much", "what", "kitna", "kitne"}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.casefold()) if t not in _STOP}


def similarity(a: str, b: str) -> float:
    """Overlap coefficient of content tokens: shared / size of the smaller
    set. Chosen over Jaccard because the realistic case is a short new
    question against a longer existing post - Jaccard punishes the length
    difference, overlap does not. Crude, runs with no model, and catches
    the common case - the same question about the same thing asked three
    days apart in the same trade."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def find_duplicates(text: str, candidates: list[dict], threshold: float = 0.6, min_shared: int = 3, limit: int = 3) -> list[dict]:
    """candidates: dicts with at least id, title, body. Returns the most
    similar ones above threshold (and sharing at least min_shared content
    tokens, so two-word posts cannot match everything), best first. The
    caller decides what to do with them - the forum shows "someone asked
    this already, listen first" rather than blocking, because listening is
    the product."""
    query = _tokens(text)
    scored = []
    for c in candidates:
        other = f"{c.get('title', '')} {c.get('body', '')}"
        s = similarity(text, other)
        if s >= threshold and len(query & _tokens(other)) >= min_shared:
            scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [dict(c, similarity=round(s, 2)) for s, c in scored[:limit]]
