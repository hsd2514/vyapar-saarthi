"""Vyapar Chaupal - the discussion forum's HTTP surface.

Design summary (see the design note this was built from): a moderated,
label-first Q&A where every question gets an engine-generated first reply
(forum_saarthi.py), verified experts wear badges and own the "answer" slot,
members are identified by trade + place + stage only, and the crowd's own
price and wait-time reports are aggregated back into the app as
USER_REPORTED data. No direct messages, contact handles are stripped from
posts, and fee-for-approval language is held for a moderator.

Phone-call (IVR) access is deliberately out of scope for now.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from city_data import CITY_DATA
import forum_store as store
from forum_labels import (
    EXPERT_ROLE_VALUES,
    EXPERT_ROLES,
    POST_TYPE_VALUES,
    POST_TYPES,
    STAGE_VALUES,
    STAGES,
    TOPIC_VALUES,
    TOPICS,
    TRADE_VALUES,
    TRADES,
    guess_topic,
)
from forum_safety import find_duplicates, redact_pii, scam_signals
import forum_saarthi

logger = logging.getLogger("forum")
router = APIRouter(prefix="/api/forum", tags=["forum"])

# Comma-separated phone numbers from .env. A member whose phone is listed
# gets the role the moment they verify - the only way roles are assigned
# apart from a moderator doing it by hand. FORUM_EXPERT_PHONES entries are
# "phone:expert_role" (see forum_labels.EXPERT_ROLES).
_MOD_PHONES = {store.hash_phone(p) for p in os.environ.get("FORUM_MODERATOR_PHONES", "").split(",") if p.strip()}
_EXPERT_PHONES: dict[str, str] = {}
for entry in os.environ.get("FORUM_EXPERT_PHONES", "").split(","):
    if ":" in entry:
        phone, role = entry.split(":", 1)
        if role.strip() in EXPERT_ROLE_VALUES:
            _EXPERT_PHONES[store.hash_phone(phone)] = role.strip()

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.environ.get("TWILIO_PHONE_NUMBER", "")


# ---------------------------------------------------------------------------
# Auth plumbing
# ---------------------------------------------------------------------------

def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def current_member(authorization: str | None = Header(default=None)) -> dict:
    token = _bearer(authorization)
    member = store.member_for_token(token) if token else None
    if not member:
        raise HTTPException(status_code=401, detail="Please sign in with your phone number first.")
    return member


def optional_member(authorization: str | None = Header(default=None)) -> dict | None:
    token = _bearer(authorization)
    return store.member_for_token(token) if token else None


def require_moderator(member: dict = Depends(current_member)) -> dict:
    if member["role"] != "moderator":
        raise HTTPException(status_code=403, detail="Moderators only.")
    return member


def _is_mod(member: dict | None) -> bool:
    return bool(member and member["role"] == "moderator")


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

@router.get("/labels")
def labels():
    return {
        "trades": TRADES,
        "stages": STAGES,
        "topics": TOPICS,
        "post_types": POST_TYPES,
        "expert_roles": EXPERT_ROLES,
        "districts": [{"key": k, "label": d["label"], "blocks": list(d["blocks"].keys())} for k, d in CITY_DATA.items()],
        "newcomer_review_count": store.NEWCOMER_REVIEW_COUNT,
    }


# ---------------------------------------------------------------------------
# OTP sign-in
# ---------------------------------------------------------------------------

class OtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=16)


def _send_sms(phone: str, body: str) -> bool:
    if not (TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM):
        return False
    try:
        from twilio.rest import Client as TwilioClient
        TwilioClient(TWILIO_SID, TWILIO_TOKEN).messages.create(to=phone, from_=TWILIO_FROM, body=body)
        return True
    except Exception as exc:  # pragma: no cover - network
        logger.warning("OTP SMS failed: %s", exc)
        return False


@router.post("/auth/otp")
def request_otp(req: OtpRequest):
    """Sends a 6-digit code by SMS when Twilio is configured. Without
    Twilio (local dev, judges' demo) the code is returned in the response
    and logged - clearly flagged as dev_otp so nobody mistakes it for a
    production path."""
    code = store.create_otp(req.phone)
    sent = _send_sms(req.phone, f"Vyapar Chaupal code: {code}. Valid 5 minutes. Never share it.")
    if sent:
        return {"sent": True}
    logger.info("DEV OTP for %s: %s", req.phone[-4:].rjust(10, "*"), code)
    return {"sent": False, "dev_otp": code, "note": "SMS not configured - use this code."}


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=40)
    trade: str
    district: str
    block: str = ""
    stage: str
    lang: str = "en"


class VerifyRequest(BaseModel):
    phone: str
    code: str
    profile: ProfileIn | None = None


def _validate_profile(p: ProfileIn) -> None:
    if p.trade not in TRADE_VALUES:
        raise HTTPException(400, "Unknown trade.")
    if p.stage not in STAGE_VALUES:
        raise HTTPException(400, "Unknown stage.")
    if p.district not in CITY_DATA:
        raise HTTPException(400, "Unknown district.")


@router.post("/auth/verify")
def verify_otp(req: VerifyRequest):
    member = store.get_member_by_phone(req.phone)
    # A new number with no profile yet: check the code but keep it alive,
    # because the client will send it once more with the profile filled in.
    if member is None and req.profile is None:
        if not store.verify_otp(req.phone, req.code, consume=False):
            raise HTTPException(status_code=400, detail="That code is wrong or has expired. Ask for a new one.")
        return {"needs_profile": True}
    if not store.verify_otp(req.phone, req.code):
        raise HTTPException(status_code=400, detail="That code is wrong or has expired. Ask for a new one.")
    if member is None:
        _validate_profile(req.profile)
        member = store.upsert_member(req.phone, **req.profile.model_dump())
    elif req.profile is not None:
        _validate_profile(req.profile)
        member = store.upsert_member(req.phone, **req.profile.model_dump())

    ph = store.hash_phone(req.phone)
    if ph in _MOD_PHONES and member["role"] != "moderator":
        member = store.set_member_role(req.phone, "moderator") or member
    elif ph in _EXPERT_PHONES and member["role"] == "member":
        member = store.set_member_role(req.phone, "expert", _EXPERT_PHONES[ph]) or member

    token = store.create_session(member["id"])
    return {"token": token, "member": store.public_member(member)}


@router.get("/me")
def me(member: dict = Depends(current_member)):
    return store.public_member(member)


# ---------------------------------------------------------------------------
# Threads
# ---------------------------------------------------------------------------

@router.get("/threads")
def list_threads(trade: str | None = None, topic: str | None = None, stage: str | None = None, district: str | None = None,
                 post_type: str | None = None, limit: int = 50, offset: int = 0):
    return {"threads": store.list_threads(trade=trade, topic=topic, stage=stage, district=district, post_type=post_type,
                                          limit=min(limit, 100), offset=offset)}


class CheckRequest(BaseModel):
    body: str
    trade: str | None = None


@router.post("/threads/check")
def check_before_post(req: CheckRequest, member: dict = Depends(current_member)):
    """Pre-post preview: 'someone asked this already - listen first', the
    suggested topic label, and whether the post would be held. Listening
    is the product; this is the nudge that makes it happen."""
    trade = req.trade or member["trade"]
    clean, removed = redact_pii(req.body)
    return {
        "suggested_topic": guess_topic(clean),
        "duplicates": find_duplicates(clean, store.recent_threads_for_dedupe(trade)),
        "pii_removed": removed,
        "scam_signals": scam_signals(clean),
        "will_be_reviewed": member["trust_level"] == 0 and member["role"] == "member",
    }


class PriceReportIn(BaseModel):
    item: str = Field(min_length=2, max_length=80)
    amount: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=30)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")


class WaitReportIn(BaseModel):
    agency: str = Field(min_length=2, max_length=80)
    applied_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    sanctioned_month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    disbursed_month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class ThreadIn(BaseModel):
    post_type: str
    title: str = Field(min_length=4, max_length=140)
    body: str = Field(min_length=10, max_length=4000)
    topic: str | None = None
    trade: str | None = None
    district: str | None = None
    block: str | None = None
    input_mode: Literal["text", "voice"] = "text"
    lang: str = "en"
    price_report: PriceReportIn | None = None
    wait_report: WaitReportIn | None = None


def _decide_status(member: dict, signals: list[str]) -> tuple[str, str | None]:
    if signals:
        return "pending", "scam_signals"
    if member["role"] == "member" and member["trust_level"] == 0:
        return "pending", "newcomer_review"
    return "published", None


@router.post("/threads")
async def create_thread(req: ThreadIn, member: dict = Depends(current_member)):
    if req.post_type not in POST_TYPE_VALUES:
        raise HTTPException(400, "Unknown post type.")
    trade = req.trade or member["trade"]
    district = req.district or member["district"]
    block = req.block if req.block is not None else member["block"]
    if trade not in TRADE_VALUES or district not in CITY_DATA:
        raise HTTPException(400, "Unknown trade or district.")

    title, _ = redact_pii(req.title)
    body, removed = redact_pii(req.body)
    signals = scam_signals(f"{title} {body}")
    topic = req.topic if req.topic in TOPIC_VALUES else guess_topic(f"{title} {body}")
    if req.post_type == "warning" and not req.topic:
        topic = "scam"
    status, held_reason = _decide_status(member, signals)

    thread = store.create_thread(
        author=member, post_type=req.post_type, trade=trade, topic=topic, district=district, block=block or "",
        title=title, body=body, input_mode=req.input_mode, lang=req.lang, status=status, held_reason=held_reason,
    )
    if status == "published":
        store.record_approved_post(member["id"])

    if req.post_type == "price_report" and req.price_report:
        store.add_price_report(member_id=member["id"], trade=trade, district=district, block=block or "", thread_id=thread["id"], **req.price_report.model_dump())
    if req.post_type == "wait_report" and req.wait_report:
        store.add_wait_report(member_id=member["id"], district=district, block=block or "", thread_id=thread["id"], **req.wait_report.model_dump())

    saarthi_reply = None
    if req.post_type == "question":
        facts = forum_saarthi.build_facts(topic=topic, trade=trade, district=district, block=block or "", text=f"{title}\n{body}")
        text = await forum_saarthi.phrase(facts, f"{title}\n{body}")
        saarthi_reply = store.add_reply(thread_id=thread["id"], author=None, kind="saarthi", body=text, provenance={"items": facts["provenance"]})

    return {
        "thread": store.get_thread(thread["id"]),
        "saarthi_reply": saarthi_reply,
        "pii_removed": removed,
        "held": status == "pending",
        "held_reason": held_reason,
        "duplicates": find_duplicates(f"{title} {body}", [t for t in store.recent_threads_for_dedupe(trade) if t["id"] != thread["id"]]),
    }


@router.get("/threads/{thread_id}")
def get_thread(thread_id: str, member: dict | None = Depends(optional_member)):
    thread = store.get_thread(thread_id)
    if not thread:
        raise HTTPException(404, "Post not found.")
    is_author = bool(member and member["id"] == thread["author_id"])
    if thread["status"] != "published" and not (is_author or _is_mod(member)):
        raise HTTPException(404, "Post not found.")
    replies = store.list_replies(thread_id, include_hidden=_is_mod(member))
    if not _is_mod(member) and member:
        # An author can see their own held replies, nobody else's.
        replies = [r for r in store.list_replies(thread_id, include_hidden=True) if r["status"] == "published" or r["author_id"] == member["id"]]
        replies.sort(key=lambda r: ({"saarthi": 0, "expert": 1, "experience": 2, "peer": 3}.get(r["kind"], 9), r["created_at"]))
    return {"thread": thread, "replies": replies, "can_moderate": _is_mod(member)}


class ReplyIn(BaseModel):
    body: str = Field(min_length=2, max_length=3000)
    kind: Literal["experience", "peer", "expert"] = "peer"
    input_mode: Literal["text", "voice"] = "text"


@router.post("/threads/{thread_id}/replies")
def add_reply(thread_id: str, req: ReplyIn, member: dict = Depends(current_member)):
    thread = store.get_thread(thread_id)
    if not thread or thread["status"] not in ("published", "pending"):
        raise HTTPException(404, "Post not found.")
    if req.kind == "expert" and member["role"] != "expert":
        raise HTTPException(403, "Only verified experts can post an expert answer. Share it as your experience instead.")
    body, removed = redact_pii(req.body)
    signals = scam_signals(body)
    status, held_reason = _decide_status(member, signals)
    reply = store.add_reply(thread_id=thread_id, author=member, kind=req.kind, body=body, official=(req.kind == "expert"),
                            status=status, held_reason=held_reason)
    if status == "published":
        store.record_approved_post(member["id"])
    return {"reply": reply, "held": status == "pending", "held_reason": held_reason, "pii_removed": removed}


class ConnectIn(BaseModel):
    message: str = Field(min_length=5, max_length=500)


@router.post("/threads/{thread_id}/connect")
def connect(thread_id: str, req: ConnectIn, member: dict = Depends(current_member)):
    """For 'Looking for a buyer / supplier' posts. The request goes to a
    moderator, who introduces the two parties - no phone numbers change
    hands inside the forum."""
    thread = store.get_thread(thread_id)
    if not thread or thread["post_type"] != "looking_for":
        raise HTTPException(400, "Connect requests only work on 'Looking for' posts.")
    if thread["author_id"] == member["id"]:
        raise HTTPException(400, "That is your own post.")
    msg, _ = redact_pii(req.message)
    return {"request": store.add_connect_request(thread_id=thread_id, requester_id=member["id"], message=msg)}


class ReportIn(BaseModel):
    target_type: Literal["thread", "reply"]
    target_id: str
    reason: Literal["scam", "abuse", "wrong_info", "spam", "other"]


@router.post("/report")
def report(req: ReportIn, member: dict = Depends(current_member)):
    n = store.add_flag(target_type=req.target_type, target_id=req.target_id, reporter_id=member["id"], reason=req.reason)
    return {"flags": n, "hidden": n >= store.HIDE_AFTER_FLAGS}


# ---------------------------------------------------------------------------
# Crowd data - standalone entry points (the same tables also fill from
# price_report / wait_report post types above)
# ---------------------------------------------------------------------------

@router.post("/price-report")
def price_report(req: PriceReportIn, member: dict = Depends(current_member)):
    return store.add_price_report(member_id=member["id"], trade=member["trade"], district=member["district"], block=member["block"], **req.model_dump())


@router.get("/price-summary")
def price_summary(trade: str | None = None, item: str | None = None, district: str | None = None):
    return {"summary": store.price_summary(trade=trade, item=item, district=district), "provenance": "USER_REPORTED",
            "note": "Reported by members. Shown beside, never instead of, the official unit cost."}


@router.post("/wait-report")
def wait_report(req: WaitReportIn, member: dict = Depends(current_member)):
    return store.add_wait_report(member_id=member["id"], district=member["district"], block=member["block"], **req.model_dump())


@router.get("/wait-summary")
def wait_summary(district: str | None = None, agency: str | None = None):
    return {"summary": store.wait_summary(district=district, agency=agency), "provenance": "USER_REPORTED"}


# ---------------------------------------------------------------------------
# Moderation
# ---------------------------------------------------------------------------

@router.get("/mod/queue")
def mod_queue(_: dict = Depends(require_moderator)):
    return store.moderation_queue()


class ModAction(BaseModel):
    action: Literal["approve", "reject", "hide"]


@router.post("/mod/threads/{thread_id}")
def mod_thread(thread_id: str, req: ModAction, _: dict = Depends(require_moderator)):
    status = {"approve": "published", "reject": "rejected", "hide": "hidden"}[req.action]
    thread = store.set_thread_status(thread_id, status, None if status == "published" else req.action)
    if not thread:
        raise HTTPException(404, "Post not found.")
    if status == "published":
        store.record_approved_post(thread["author_id"])
    return {"thread": thread}


@router.post("/mod/replies/{reply_id}")
def mod_reply(reply_id: str, req: ModAction, _: dict = Depends(require_moderator)):
    status = {"approve": "published", "reject": "rejected", "hide": "hidden"}[req.action]
    reply = store.set_reply_status(reply_id, status, None if status == "published" else req.action)
    if not reply:
        raise HTTPException(404, "Reply not found.")
    if status == "published" and reply["author_id"]:
        store.record_approved_post(reply["author_id"])
    return {"reply": reply}


class ConnectAction(BaseModel):
    action: Literal["approve", "decline"]


@router.post("/mod/connects/{connect_id}")
def mod_connect(connect_id: str, req: ConnectAction, _: dict = Depends(require_moderator)):
    store.set_connect_status(connect_id, "approved" if req.action == "approve" else "declined")
    return {"ok": True}


class RoleIn(BaseModel):
    role: Literal["member", "expert", "moderator"]
    expert_role: str | None = None


@router.post("/mod/members/{member_id}/role")
def mod_role(member_id: str, req: RoleIn, _: dict = Depends(require_moderator)):
    target = store.get_member(member_id)
    if not target:
        raise HTTPException(404, "Member not found.")
    if req.role == "expert" and req.expert_role not in EXPERT_ROLE_VALUES:
        raise HTTPException(400, "expert_role required for experts.")
    updated = store.set_member_role_by_id(member_id, req.role, req.expert_role if req.role == "expert" else None)
    return {"member": store.public_member(updated)}
