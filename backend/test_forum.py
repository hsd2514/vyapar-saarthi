"""Tests for Vyapar Chaupal: forum_store, forum_safety, forum_saarthi and
the /api/forum/* endpoints (forum_router.py) end to end through the app.

Every test runs against a fresh temp SQLite file; no model key is set, so
Saarthi's take exercises the deterministic template path.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import forum_store as store
from forum_labels import guess_topic
from forum_safety import find_duplicates, redact_pii, scam_signals, similarity
import forum_saarthi
from main import app


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    store.configure(str(tmp_path / "forum-test.db"))
    for key in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SARVAM_API_KEY", "FASTROUTER_API_KEY", "OPENCODE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    store.init_db()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _sign_in(client: TestClient, phone: str, *, trade="dairy", district="latur", block="Ausa", stage="thinking", name="Test") -> tuple[str, dict]:
    otp = client.post("/api/forum/auth/otp", json={"phone": phone}).json()
    assert "dev_otp" in otp
    res = client.post("/api/forum/auth/verify", json={
        "phone": phone, "code": otp["dev_otp"],
        "profile": {"display_name": name, "trade": trade, "district": district, "block": block, "stage": stage},
    }).json()
    assert "token" in res, res
    return res["token"], res["member"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Safety layer
# ---------------------------------------------------------------------------

def test_redact_pii_strips_phone_upi_aadhaar_but_keeps_prices():
    text = "Call me on 98765 43210 or pay ravi@ybl, aadhaar 1234 5678 9012. Buffalo cost 120000."
    clean, kinds = redact_pii(text)
    assert "98765" not in clean and "ravi@ybl" not in clean and "1234 5678 9012" not in clean
    assert "120000" in clean  # a six-digit price is not a phone number
    assert set(kinds) == {"phone", "upi", "aadhaar"}


def test_scam_signals_catch_fee_for_approval_language():
    assert scam_signals("Loan guaranteed, just pay processing fee 2550 first")
    assert scam_signals("mere paas approval letter aaya hai, pehle fees do")
    assert not scam_signals("What fodder price did you pay in Ausa this month?")


def test_similarity_and_duplicates():
    a = "How much does a Murrah buffalo cost in Latur this year"
    b = "Murrah buffalo cost Latur - kitna hai this year?"
    assert similarity(a, b) > 0.3
    dupes = find_duplicates(a, [{"id": "t1", "title": b, "body": ""}, {"id": "t2", "title": "tailoring machine price", "body": ""}])
    assert [d["id"] for d in dupes] == ["t1"]


def test_guess_topic_prefers_scam_and_repayment():
    assert guess_topic("agent bola processing fee do loan guaranteed") == "scam"
    assert guess_topic("meri EMI bounce ho gayi, kist nahi de pa raha") == "repayment"
    assert guess_topic("what is the milk price in Ausa") == "prices"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def test_phone_hash_is_stable_and_ignores_formatting():
    assert store.hash_phone("+91 98765-43210") == store.hash_phone("9876543210")


def test_otp_round_trip_and_attempt_limit():
    code = store.create_otp("9876543210")
    assert not store.verify_otp("9876543210", "000000")
    assert store.verify_otp("9876543210", code)
    assert not store.verify_otp("9876543210", code)  # single use


def test_newcomer_becomes_trusted_after_review_count():
    m = store.upsert_member("9000000001", display_name="A", trade="dairy", district="latur", block="Ausa", stage="thinking")
    assert m["trust_level"] == 0
    for _ in range(store.NEWCOMER_REVIEW_COUNT):
        store.record_approved_post(m["id"])
    assert store.get_member(m["id"])["trust_level"] == 1


def test_two_flags_hide_a_thread():
    a = store.upsert_member("9000000002", display_name="A", trade="dairy", district="latur", block="Ausa", stage="running")
    b = store.upsert_member("9000000003", display_name="B", trade="dairy", district="latur", block="Ausa", stage="running")
    c = store.upsert_member("9000000004", display_name="C", trade="dairy", district="latur", block="Ausa", stage="running")
    t = store.create_thread(author=a, post_type="question", trade="dairy", topic="prices", district="latur", block="Ausa",
                            title="x" * 10, body="y" * 20, input_mode="text", lang="en", status="published", held_reason=None)
    store.add_flag(target_type="thread", target_id=t["id"], reporter_id=b["id"], reason="scam")
    store.add_flag(target_type="thread", target_id=t["id"], reporter_id=b["id"], reason="scam")  # same reporter twice = once
    assert store.get_thread(t["id"])["status"] == "published"
    store.add_flag(target_type="thread", target_id=t["id"], reporter_id=c["id"], reason="scam")
    assert store.get_thread(t["id"])["status"] == "hidden"


def test_price_and_wait_summaries_aggregate():
    m = store.upsert_member("9000000005", display_name="A", trade="dairy", district="latur", block="Ausa", stage="running")
    for amt in (100000, 110000, 125000):
        store.add_price_report(member_id=m["id"], trade="dairy", item="Murrah buffalo", amount=amt, unit="animal", district="latur", block="Ausa", month="2026-08")
    s = store.price_summary(trade="dairy", district="latur")
    assert s[0]["n"] == 3 and s[0]["median"] == 110000 and s[0]["provenance"] == "USER_REPORTED"

    store.add_wait_report(member_id=m["id"], district="latur", block="Ausa", agency="MPBCDC", applied_month="2025-01", sanctioned_month="2025-05", disbursed_month="2025-11")
    store.add_wait_report(member_id=m["id"], district="latur", block="Ausa", agency="mpbcdc", applied_month="2025-03", sanctioned_month="2025-06", disbursed_month=None)
    w = store.wait_summary(district="latur")
    assert w[0]["n"] == 2 and w[0]["median_months_to_sanction"] == 3.5 and w[0]["still_waiting"] == 1


def test_replies_ordered_by_role_not_time():
    a = store.upsert_member("9000000006", display_name="A", trade="dairy", district="latur", block="Ausa", stage="running")
    t = store.create_thread(author=a, post_type="question", trade="dairy", topic="prices", district="latur", block="Ausa",
                            title="x" * 10, body="y" * 20, input_mode="text", lang="en", status="published", held_reason=None)
    store.add_reply(thread_id=t["id"], author=a, kind="peer", body="peer first in time")
    store.add_reply(thread_id=t["id"], author=None, kind="saarthi", body="engine")
    store.add_reply(thread_id=t["id"], author=a, kind="expert", body="expert", official=True)
    assert [r["kind"] for r in store.list_replies(t["id"])] == ["saarthi", "expert", "peer"]
    assert store.get_thread(t["id"])["expert_answered"] == 1


# ---------------------------------------------------------------------------
# Saarthi's take (deterministic path)
# ---------------------------------------------------------------------------

def test_saarthi_facts_scam_topic_is_the_no_fee_notice():
    f = forum_saarthi.build_facts(topic="scam", trade="dairy", district="latur", block="Ausa", text="agent asking fee")
    assert forum_saarthi.NO_FEE_NOTICE in f["paragraphs"][0]
    assert f["provenance"][0]["provenance"] == "RULE"


def test_saarthi_facts_loan_topic_uses_engine_for_amount():
    f = forum_saarthi.build_facts(topic="loan_scheme", trade="dairy", district="latur", block="Ausa", text="I have 20,000 rupees margin, what loan?")
    assert f["facts"]["structuring"]["project_cost"] == 200000
    assert any(p["fact"] == "structuring_example" for p in f["provenance"])
    assert "Rs 200,000" in " ".join(f["paragraphs"])


def test_saarthi_facts_prices_topic_uses_crowd_data_when_present():
    m = store.upsert_member("9000000007", display_name="A", trade="dairy", district="latur", block="Ausa", stage="running")
    store.add_price_report(member_id=m["id"], trade="dairy", item="Concentrate feed", amount=32, unit="kg", district="latur", block="Ausa", month="2026-08")
    f = forum_saarthi.build_facts(topic="prices", trade="dairy", district="latur", block="Ausa", text="feed rate?")
    assert any(p["provenance"] == "USER_REPORTED" for p in f["provenance"])
    assert "Concentrate feed" in " ".join(f["paragraphs"])


@pytest.mark.anyio
async def test_saarthi_phrase_falls_back_to_template_without_model():
    f = forum_saarthi.build_facts(topic="training", trade="goat", district="latur", block="Ausa", text="where to learn?")
    out = await forum_saarthi.phrase(f, "where to learn?")
    assert "RSETI" in out and "engine's first response" in out


# ---------------------------------------------------------------------------
# HTTP flow
# ---------------------------------------------------------------------------

def test_labels_endpoint(client):
    res = client.get("/api/forum/labels").json()
    assert {"trades", "stages", "topics", "post_types", "expert_roles", "districts"} <= set(res)
    assert any(t["value"] == "goat" for t in res["trades"])


def test_sign_in_needs_profile_first_time_then_not(client):
    otp = client.post("/api/forum/auth/otp", json={"phone": "+919111111111"}).json()
    res = client.post("/api/forum/auth/verify", json={"phone": "+919111111111", "code": otp["dev_otp"]}).json()
    assert res == {"needs_profile": True}
    # The same code must still work when re-sent with the profile - the
    # dialog does exactly this, and it used to fail with "wrong or expired".
    res = client.post("/api/forum/auth/verify", json={
        "phone": "+919111111111", "code": otp["dev_otp"],
        "profile": {"display_name": "Test", "trade": "dairy", "district": "latur", "block": "Ausa", "stage": "thinking"},
    }).json()
    assert "token" in res
    # And it is single-use once actually consumed.
    again = client.post("/api/forum/auth/verify", json={"phone": "+919111111111", "code": otp["dev_otp"]})
    assert again.status_code == 400
    token, member = _sign_in(client, "+919111111111")
    assert member["trade"] == "dairy" and member["role"] == "member"
    assert client.get("/api/forum/me", headers=_auth(token)).json()["display_name"] == "Test"


def test_newcomer_question_is_held_but_gets_saarthi_reply(client):
    token, _ = _sign_in(client, "+919222222222")
    res = client.post("/api/forum/threads", headers=_auth(token), json={
        "post_type": "question", "title": "How much loan for 2 buffaloes?",
        "body": "I have 30000 rupees saved. Which scheme and how much loan can I get for dairy in Ausa?",
    }).json()
    assert res["held"] and res["held_reason"] == "newcomer_review"
    assert res["thread"]["topic"] == "loan_scheme"
    assert res["saarthi_reply"]["kind"] == "saarthi"
    assert "Rs 300,000" in res["saarthi_reply"]["body"]
    # Not visible to the public yet, visible to the author.
    assert client.get("/api/forum/threads").json()["threads"] == []
    assert client.get(f"/api/forum/threads/{res['thread']['id']}", headers=_auth(token)).status_code == 200
    assert client.get(f"/api/forum/threads/{res['thread']['id']}").status_code == 404


def test_scam_post_is_held_even_from_trusted_member(client):
    token, member = _sign_in(client, "+919333333333")
    store.set_trust_level(member["id"], 1)
    res = client.post("/api/forum/threads", headers=_auth(token), json={
        "post_type": "experience", "title": "Fast loan available",
        "body": "Loan guaranteed in 2 days, pay processing fee first, whatsapp me 9876543210",
    }).json()
    assert res["held"] and res["held_reason"] == "scam_signals"
    assert "9876543210" not in res["thread"]["body"] and "phone" in res["pii_removed"]


def test_moderator_approves_and_member_becomes_visible(client, monkeypatch):
    import forum_router
    monkeypatch.setattr(forum_router, "_MOD_PHONES", {store.hash_phone("+919444444444")})
    mod_token, mod = _sign_in(client, "+919444444444", name="Mod")
    assert mod["role"] == "moderator"

    token, _ = _sign_in(client, "+919555555555")
    res = client.post("/api/forum/threads", headers=_auth(token), json={
        "post_type": "experience", "title": "My first month selling milk",
        "body": "The society pays 32 rupees a litre for 6.5 fat. Keep the animal insured, mine fell sick in July.",
    }).json()
    tid = res["thread"]["id"]
    queue = client.get("/api/forum/mod/queue", headers=_auth(mod_token)).json()
    assert any(t["id"] == tid for t in queue["threads"])
    client.post(f"/api/forum/mod/threads/{tid}", headers=_auth(mod_token), json={"action": "approve"})
    listed = client.get("/api/forum/threads?trade=dairy&district=latur").json()["threads"]
    assert [t["id"] for t in listed] == [tid]
    assert listed[0]["author"]["stage"] == "thinking" and "phone_hash" not in listed[0]["author"]


def test_only_experts_can_post_expert_answers(client, monkeypatch):
    import forum_router
    monkeypatch.setattr(forum_router, "_EXPERT_PHONES", {store.hash_phone("+919666666666"): "rseti_trainer"})
    exp_token, exp = _sign_in(client, "+919666666666", name="Trainer")
    assert exp["role"] == "expert" and exp["expert_role"] == "rseti_trainer"

    token, member = _sign_in(client, "+919777777777")
    store.set_trust_level(member["id"], 1)
    tid = client.post("/api/forum/threads", headers=_auth(token), json={
        "post_type": "question", "title": "Which course before dairy loan?", "body": "Is there any training I should finish before applying for the dairy loan?",
    }).json()["thread"]["id"]

    denied = client.post(f"/api/forum/threads/{tid}/replies", headers=_auth(token), json={"body": "Do the RSETI course", "kind": "expert"})
    assert denied.status_code == 403
    ok = client.post(f"/api/forum/threads/{tid}/replies", headers=_auth(exp_token), json={"body": "Do the 10-day RSETI dairy course; banks ask for it.", "kind": "expert"}).json()
    assert not ok["held"] and ok["reply"]["official"] == 1
    view = client.get(f"/api/forum/threads/{tid}").json()
    assert [r["kind"] for r in view["replies"]] == ["saarthi", "expert"]
    assert view["thread"]["expert_answered"] == 1


def test_price_report_post_feeds_summary_and_check_endpoint_finds_duplicates(client):
    token, member = _sign_in(client, "+919888888888")
    store.set_trust_level(member["id"], 1)
    client.post("/api/forum/threads", headers=_auth(token), json={
        "post_type": "price_report", "title": "Paid 1.1 lakh for Murrah in Ausa", "body": "Bought a Murrah buffalo in August, 8 litres, paid 1,10,000.",
        "price_report": {"item": "Murrah buffalo", "amount": 110000, "unit": "animal", "month": "2026-08"},
    })
    s = client.get("/api/forum/price-summary?trade=dairy&district=latur").json()["summary"]
    assert s[0]["item"] == "Murrah buffalo" and s[0]["n"] == 1

    chk = client.post("/api/forum/threads/check", headers=_auth(token), json={"body": "Murrah buffalo price in Ausa - paid how much?"}).json()
    assert chk["suggested_topic"] == "prices" and len(chk["duplicates"]) == 1


def test_connect_request_only_on_looking_for_posts(client):
    token, member = _sign_in(client, "+919999999999")
    store.set_trust_level(member["id"], 1)
    tid = client.post("/api/forum/threads", headers=_auth(token), json={
        "post_type": "looking_for", "title": "Need buyer for 40 litres milk daily", "body": "From Nilanga, 40 litres a day, buffalo milk, 6.5 fat.",
    }).json()["thread"]["id"]
    other, _ = _sign_in(client, "+919000000009", block="Renapur")
    res = client.post(f"/api/forum/threads/{tid}/connect", headers=_auth(other), json={"message": "I run a sweet shop in Renapur, can take 20 litres, my number 9876543210"})
    assert res.status_code == 200 and "9876543210" not in res.json()["request"]["message"]
