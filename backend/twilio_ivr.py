"""Phone-call access to the same voice intake agent the web app uses -
no smartphone, no app, no literacy needed, just a phone call. This is the
"IVR" half of the PS's voice-first vision that the web app alone can't
deliver: it dials a real number, Twilio transcribes what the caller says,
the SAME intake agent (agent.py's get_intake_agent) processes it exactly
as it would a browser voice turn, and Twilio speaks the reply back.

Design:
- Twilio calls are stateless HTTP webhooks - each turn is a fresh POST with
  no server-side session by default. We key an in-memory conversation store
  by Twilio's CallSid (unique per call) to give the call the same "memory
  across turns" property the web voice agent gets from AppContext/localStorage.
- Every inbound webhook is verified against Twilio's request signature
  (X-Twilio-Signature) so a public endpoint can't be spoofed into injecting
  fake call turns.
- The LLM logic is NOT duplicated here - this module only turns TwiML/form
  data into the same (message, history, profile) shape agent.py already
  accepts, and turns its ConversationTurn reply back into TwiML.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from pydantic_ai import ModelMessagesTypeAdapter
from twilio.request_validator import RequestValidator
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Gather, VoiceResponse

from agent import ConversationTurn, ProfilePatch, get_intake_agent
from deterministic import calc_financial_structuring, generate_feasibility_report
from share_store import create_share

# Deliberately verbose, demo-friendly logging - every step of a call shows
# up as its own line (call started, what the caller said, what Saarthi
# replied, call ended) so watching `uv run fastapi dev` in a terminal
# during a live demo tells the whole story without opening a debugger.
#
# uvicorn's default logging config only attaches handlers to its OWN
# loggers ("uvicorn", "uvicorn.access", "uvicorn.error") - it never adds a
# handler to the root logger. A plain `logging.getLogger("twilio_ivr")`
# with no handler of its own silently produces nothing under `fastapi dev`,
# even at INFO level - the access log lines you do see are uvicorn's, not
# ours. Attaching our own StreamHandler (and setting propagate=False so it
# doesn't ALSO try, and possibly duplicate through, a root handler some
# other setup might add) makes this print unconditionally, regardless of
# whatever logging config the ASGI server happens to use.
logger = logging.getLogger("twilio_ivr")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(_handler)

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

# The public URL Twilio should fetch TwiML from once an OUTBOUND call is
# answered. Unlike the inbound webhooks above (where Twilio tells us the
# request URL), triggering an outbound call means WE tell Twilio where to
# find /api/twilio/voice - and Twilio can't reach localhost, so this must be
# the current public tunnel/deployment URL (e.g. the ngrok URL while
# developing). Set this in .env each time the tunnel URL changes.
PUBLIC_BASE_URL = os.environ.get("TWILIO_PUBLIC_BASE_URL", "")

# Where the shareable report link (auto-created the moment a call finishes)
# should point - the frontend app's own origin, not the backend's. Defaults
# to the local dev server since presenting a demo usually means the web app
# is open on the same machine right next to this terminal.
FRONTEND_ORIGIN = os.environ.get("TWILIO_FRONTEND_ORIGIN", "http://localhost:5173")

# Twilio's <Gather input="speech"> speech-to-text supports these locales for
# the languages this app cares about. Marathi (mr-IN) is not in Twilio's
# supported speech-recognition locale list as of this writing, unlike the
# browser's Web Speech API used on the web app - so a Marathi caller is
# recognised under hi-IN, same as the web app already treats code-mixed
# Marathi/Hindi speech: the LLM extracts meaning regardless of which
# recognition locale picked up the audio.
GATHER_LANGUAGE = os.environ.get("TWILIO_GATHER_LANGUAGE", "hi-IN")
SAY_VOICE_LANGUAGE = os.environ.get("TWILIO_SAY_LANGUAGE", "hi-IN")

_CALL_TTL_SECONDS = 30 * 60  # a call that goes stale for 30 minutes is abandoned


@dataclass
class _CallSession:
    history: list[dict] = field(default_factory=list)
    profile: ProfilePatch = field(default_factory=ProfilePatch)
    last_active: float = field(default_factory=time.time)


_CALL_SESSIONS: dict[str, _CallSession] = {}


def _cleanup_stale_calls() -> None:
    cutoff = time.time() - _CALL_TTL_SECONDS
    stale = [sid for sid, s in _CALL_SESSIONS.items() if s.last_active < cutoff]
    for sid in stale:
        _CALL_SESSIONS.pop(sid, None)


def _strip_for_speech(text: str) -> str:
    """Same markdown-stripping the web app's TTS does - a phone call must
    never read '**' or '#' characters aloud."""
    return "".join(ch for ch in text if ch not in "*_`#").replace("\n", " ")


def _build_report_share_link(profile: ProfilePatch) -> str | None:
    """Called the moment a call finishes (turn.done). Computes the same
    deterministic financial structuring + feasibility report the web app's
    Financial Plan / Feasibility Report screens show, packages it the same
    shape the frontend's SharedSummaryView already knows how to render, and
    stores it via share_store - so the caller's report is a browser link
    away instead of something that has to be read back over voice.

    Returns None (and logs why) if the profile isn't complete enough to
    compute a report from - this should only happen if turn.done is somehow
    True without every field filled, which the intake agent's own system
    prompt is supposed to prevent."""
    if not (profile.district and profile.block and profile.business_type and profile.available_margin_capital):
        logger.info("⚠️  Call marked done but profile incomplete - skipping report link. profile=%s", profile.model_dump_json())
        return None

    structuring = calc_financial_structuring(profile.available_margin_capital)
    try:
        feasibility = generate_feasibility_report(profile.district, profile.block, profile.business_type)
    except ValueError as exc:
        logger.info("⚠️  Could not build feasibility report for share link: %s", exc)
        feasibility = None

    payload = {
        "profile": {
            "businessType": profile.business_type,
            "district": profile.district,
            "block": profile.block,
            "village": profile.village or "",
            "availableMarginCapital": str(profile.available_margin_capital),
        },
        "operations": {},
        "structuring": structuring,
        "schedule": None,
        "working_capital": None,
        "feasibility": feasibility,
        "advisory": None,
        "contacts": [],
    }
    result = create_share(payload, FRONTEND_ORIGIN)
    return result["share_url"]


router = APIRouter(prefix="/api/twilio", tags=["twilio"])


async def _verify_twilio_signature(request: Request) -> None:
    """Reject any webhook that isn't genuinely from Twilio. Skipped only if
    TWILIO_AUTH_TOKEN isn't set (local dev before credentials are configured) -
    that case still works end-to-end, it's just unauthenticated, and is never
    the state a deployed instance should be left in."""
    if not TWILIO_AUTH_TOKEN:
        return
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    form = await request.form()
    url = str(request.url)
    if not validator.validate(url, dict(form), signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


@router.post("/voice")
async def twilio_voice(request: Request):
    """The webhook Twilio calls the instant someone dials the number.
    Starts a fresh call session and asks the intake agent for its opening line."""
    await _verify_twilio_signature(request)
    _cleanup_stale_calls()
    form = await request.form()
    call_sid = form.get("CallSid", "")
    caller = form.get("From", "unknown")
    direction = form.get("Direction", "unknown")

    logger.info("📞 CALL STARTED  sid=%s  from=%s  direction=%s", call_sid, caller, direction)

    result = await get_intake_agent().run(
        "(start of conversation - greet me and ask your first question)"
    )
    turn: ConversationTurn = result.output
    history = ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")
    _CALL_SESSIONS[call_sid] = _CallSession(history=history, profile=turn.profile)

    logger.info("🤖 SAARTHI (opening)  sid=%s  \"%s\"", call_sid, turn.reply_text)

    vr = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/api/twilio/gather",
        method="POST",
        language=GATHER_LANGUAGE,
        speech_timeout="auto",
    )
    gather.say(_strip_for_speech(turn.reply_text), language=SAY_VOICE_LANGUAGE)
    vr.append(gather)
    # If the caller says nothing at all, re-prompt once instead of silently hanging up.
    vr.say("Sorry, I did not hear anything. Please call back when you are ready.", language=SAY_VOICE_LANGUAGE)
    return Response(content=str(vr), media_type="application/xml")


@router.post("/gather")
async def twilio_gather(request: Request):
    """Every subsequent turn: Twilio POSTs the transcribed SpeechResult here.
    Runs the same intake agent with this call's accumulated history, then
    either asks the next question or reads back the closing line and hangs up."""
    await _verify_twilio_signature(request)
    form = await request.form()
    call_sid = form.get("CallSid", "")
    speech_result = form.get("SpeechResult", "")
    speech_confidence = form.get("Confidence", "?")

    session = _CALL_SESSIONS.get(call_sid)
    if session is None:
        # Session expired or server restarted mid-call - start over gracefully
        # rather than crashing the call.
        logger.info("⚠️  SESSION MISSING, restarting fresh  sid=%s", call_sid)
        session = _CallSession()
        _CALL_SESSIONS[call_sid] = session

    vr = VoiceResponse()
    if not speech_result:
        logger.info("🔇 NO SPEECH HEARD  sid=%s", call_sid)
        gather = Gather(input="speech", action="/api/twilio/gather", method="POST", language=GATHER_LANGUAGE, speech_timeout="auto")
        gather.say("Sorry, I did not catch that. Could you say it again?", language=SAY_VOICE_LANGUAGE)
        vr.append(gather)
        return Response(content=str(vr), media_type="application/xml")

    logger.info("🗣️  CALLER  sid=%s  confidence=%s  \"%s\"", call_sid, speech_confidence, speech_result)

    message_history = ModelMessagesTypeAdapter.validate_python(session.history) if session.history else []
    prompt = f"Known so far: {session.profile.model_dump_json()}\nSpeaker just said: {speech_result}"
    result = await get_intake_agent().run(prompt, message_history=message_history)
    turn: ConversationTurn = result.output

    session.history = ModelMessagesTypeAdapter.dump_python(result.all_messages(), mode="json")
    session.profile = turn.profile
    session.last_active = time.time()

    logger.info("🤖 SAARTHI  sid=%s  done=%s  profile=%s  \"%s\"", call_sid, turn.done, turn.profile.model_dump_json(), turn.reply_text)

    if turn.done:
        vr.say(_strip_for_speech(turn.reply_text), language=SAY_VOICE_LANGUAGE)
        vr.say(
            "Your feasibility report and loan details are ready on the Vyapar Saarthi website. Thank you, goodbye.",
            language=SAY_VOICE_LANGUAGE,
        )
        vr.hangup()

        share_url = _build_report_share_link(turn.profile)
        logger.info("✅ CALL COMPLETE  sid=%s  final_profile=%s", call_sid, turn.profile.model_dump_json())
        if share_url:
            logger.info("📄 REPORT READY  %s", share_url)

        _CALL_SESSIONS.pop(call_sid, None)
    else:
        gather = Gather(input="speech", action="/api/twilio/gather", method="POST", language=GATHER_LANGUAGE, speech_timeout="auto")
        gather.say(_strip_for_speech(turn.reply_text), language=SAY_VOICE_LANGUAGE)
        vr.append(gather)
        vr.say("Sorry, I did not hear anything. Please call back when you are ready.", language=SAY_VOICE_LANGUAGE)

    return Response(content=str(vr), media_type="application/xml")


# ---------------------------------------------------------------------------
# Outbound "call me" - triggered by a button in the app instead of the user
# having to dial a Twilio number themselves. More reliable for a prototype
# demo than relying on someone actually placing an inbound call (which on a
# Twilio trial account only works to/from a verified caller ID, and depends
# on the tunnel being reachable at exactly the moment they dial). This
# reuses the SAME /api/twilio/voice and /api/twilio/gather webhooks above
# once the call connects - no conversation logic is duplicated.
# ---------------------------------------------------------------------------

class CallMeRequest(BaseModel):
    to: str  # E.164 format, e.g. "+919876543210"


class CallMeResponse(BaseModel):
    call_sid: str
    status: str


@router.post("/call-me", response_model=CallMeResponse)
def call_me(req: CallMeRequest):
    """Places an outbound call from the Twilio number to `req.to`. On a
    Twilio trial account, `req.to` MUST already be a verified caller ID in
    the Twilio console (Phone Numbers -> Verified Caller IDs) - Twilio
    rejects unverified destinations on trial accounts, this is not
    something this code can work around."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER):
        raise HTTPException(
            status_code=500,
            detail="TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER must all be set in .env to place outbound calls.",
        )
    if not PUBLIC_BASE_URL:
        raise HTTPException(
            status_code=500,
            detail="TWILIO_PUBLIC_BASE_URL is not set - Twilio needs a public URL (e.g. your ngrok tunnel) to fetch TwiML from once the call is answered.",
        )

    logger.info("📲 OUTBOUND CALL TRIGGERED  to=%s  from=%s", req.to, TWILIO_PHONE_NUMBER)

    client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try:
        call = client.calls.create(
            to=req.to,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{PUBLIC_BASE_URL.rstrip('/')}/api/twilio/voice",
            method="POST",
        )
    except Exception as exc:  # pragma: no cover - surfaced to the UI as a toast
        logger.error("❌ OUTBOUND CALL FAILED  to=%s  error=%s", req.to, exc)
        raise HTTPException(status_code=502, detail=f"Twilio call creation failed: {exc}") from exc

    logger.info("📲 OUTBOUND CALL QUEUED  sid=%s  status=%s", call.sid, call.status)
    return CallMeResponse(call_sid=call.sid, status=call.status)
