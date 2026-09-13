"""SQLite persistence for Vyapar Chaupal (the discussion forum).

This is the first feature in the project that keeps state across restarts
and knows who a user is. Everything else stays stateless (see main.py's
notes on share_store). SQLite via the standard library keeps the deployment
story unchanged - one process, one file, no service to run - and the schema
is small enough to read in one sitting.

Identity is a phone number, stored only as a salted hash: the forum never
needs to display or dial it, and a leaked database must not become a call
list for loan agents. Members choose a display name; what the forum shows
beside a post is name + trade + place + stage, never anything else.

Trust levels:
  0  new      - first FORUM_NEWCOMER_REVIEW_COUNT posts are held for review
  1  trusted  - auto-publish (earned by approved posts, or set by a moderator)
Roles: member | expert | moderator. Experts carry expert_role (forum_labels).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import statistics
import time
from contextlib import contextmanager
from typing import Any, Iterator

DB_PATH = os.environ.get("FORUM_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "forum.db"))
PHONE_SALT = os.environ.get("FORUM_PHONE_SALT", "vyapar-chaupal-dev-salt")
NEWCOMER_REVIEW_COUNT = int(os.environ.get("FORUM_NEWCOMER_REVIEW_COUNT", "3"))
HIDE_AFTER_FLAGS = 2
OTP_TTL_SECONDS = 5 * 60
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


def configure(path: str) -> None:
    """Point the store at a different file (tests use a temp path)."""
    global DB_PATH
    DB_PATH = path


def hash_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) > 10:
        digits = digits[-10:]
    return hashlib.sha256(f"{PHONE_SALT}:{digits}".encode()).hexdigest()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(8)}"


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    id TEXT PRIMARY KEY,
    phone_hash TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    trade TEXT NOT NULL,
    district TEXT NOT NULL,
    block TEXT NOT NULL DEFAULT '',
    stage TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    expert_role TEXT,
    trust_level INTEGER NOT NULL DEFAULT 0,
    approved_posts INTEGER NOT NULL DEFAULT 0,
    lang TEXT NOT NULL DEFAULT 'en',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS otp_codes (
    phone_hash TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    expires_at REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    author_id TEXT NOT NULL,
    post_type TEXT NOT NULL,
    trade TEXT NOT NULL,
    topic TEXT NOT NULL,
    district TEXT NOT NULL,
    block TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    input_mode TEXT NOT NULL DEFAULT 'text',
    lang TEXT NOT NULL DEFAULT 'en',
    status TEXT NOT NULL DEFAULT 'published',
    held_reason TEXT,
    reply_count INTEGER NOT NULL DEFAULT 0,
    expert_answered INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_threads_list ON threads(status, created_at DESC);
CREATE TABLE IF NOT EXISTS replies (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    author_id TEXT,
    kind TEXT NOT NULL,
    body TEXT NOT NULL,
    official INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'published',
    held_reason TEXT,
    provenance TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_replies_thread ON replies(thread_id, created_at);
CREATE TABLE IF NOT EXISTS price_reports (
    id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    trade TEXT NOT NULL,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    unit TEXT NOT NULL,
    district TEXT NOT NULL,
    block TEXT NOT NULL DEFAULT '',
    month TEXT NOT NULL,
    thread_id TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS wait_reports (
    id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    district TEXT NOT NULL,
    block TEXT NOT NULL DEFAULT '',
    agency TEXT NOT NULL,
    applied_month TEXT NOT NULL,
    sanctioned_month TEXT,
    disbursed_month TEXT,
    thread_id TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reporter_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(target_type, target_id, reporter_id)
);
CREATE TABLE IF NOT EXISTS connect_requests (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    requester_id TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at REAL NOT NULL,
    UNIQUE(thread_id, requester_id)
);
"""


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def _row(r: sqlite3.Row | None) -> dict | None:
    return dict(r) if r is not None else None


# ---------------------------------------------------------------------------
# Auth: OTP + bearer sessions
# ---------------------------------------------------------------------------

def create_otp(phone: str) -> str:
    code = f"{secrets.randbelow(10**6):06d}"
    with _conn() as conn:
        conn.execute(
            "INSERT INTO otp_codes(phone_hash, code, expires_at, attempts) VALUES (?,?,?,0) "
            "ON CONFLICT(phone_hash) DO UPDATE SET code=excluded.code, expires_at=excluded.expires_at, attempts=0",
            (hash_phone(phone), code, time.time() + OTP_TTL_SECONDS),
        )
    return code


def verify_otp(phone: str, code: str) -> bool:
    ph = hash_phone(phone)
    with _conn() as conn:
        row = _row(conn.execute("SELECT * FROM otp_codes WHERE phone_hash=?", (ph,)).fetchone())
        if not row or row["expires_at"] < time.time() or row["attempts"] >= 5:
            return False
        if not secrets.compare_digest(row["code"], code.strip()):
            conn.execute("UPDATE otp_codes SET attempts=attempts+1 WHERE phone_hash=?", (ph,))
            return False
        conn.execute("DELETE FROM otp_codes WHERE phone_hash=?", (ph,))
        return True


def create_session(member_id: str) -> str:
    token = secrets.token_urlsafe(24)
    with _conn() as conn:
        conn.execute("INSERT INTO sessions(token, member_id, expires_at) VALUES (?,?,?)", (token, member_id, time.time() + SESSION_TTL_SECONDS))
    return token


def member_for_token(token: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT m.* FROM sessions s JOIN members m ON m.id = s.member_id WHERE s.token=? AND s.expires_at > ?",
            (token, time.time()),
        ).fetchone()
        return _row(row)


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

def get_member_by_phone(phone: str) -> dict | None:
    with _conn() as conn:
        return _row(conn.execute("SELECT * FROM members WHERE phone_hash=?", (hash_phone(phone),)).fetchone())


def get_member(member_id: str) -> dict | None:
    with _conn() as conn:
        return _row(conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone())


def upsert_member(phone: str, *, display_name: str, trade: str, district: str, block: str, stage: str, lang: str = "en") -> dict:
    existing = get_member_by_phone(phone)
    with _conn() as conn:
        if existing:
            conn.execute(
                "UPDATE members SET display_name=?, trade=?, district=?, block=?, stage=?, lang=? WHERE id=?",
                (display_name, trade, district, block, stage, lang, existing["id"]),
            )
            member_id = existing["id"]
        else:
            member_id = _new_id("m")
            conn.execute(
                "INSERT INTO members(id, phone_hash, display_name, trade, district, block, stage, lang, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (member_id, hash_phone(phone), display_name, trade, district, block, stage, lang, time.time()),
            )
    return get_member(member_id)  # type: ignore[return-value]


def set_member_role(phone: str, role: str, expert_role: str | None = None) -> dict | None:
    """Used at startup to apply FORUM_MODERATOR_PHONES / FORUM_EXPERT_PHONES
    from .env, and by moderators. Roles are never self-assigned."""
    m = get_member_by_phone(phone)
    if not m:
        return None
    with _conn() as conn:
        conn.execute("UPDATE members SET role=?, expert_role=?, trust_level=1 WHERE id=?", (role, expert_role, m["id"]))
    return get_member(m["id"])


def set_member_role_by_id(member_id: str, role: str, expert_role: str | None = None) -> dict | None:
    with _conn() as conn:
        conn.execute("UPDATE members SET role=?, expert_role=?, trust_level=1 WHERE id=?", (role, expert_role, member_id))
    return get_member(member_id)


def public_member(m: dict | None) -> dict | None:
    """What other members see: never the phone hash, never the id of the
    session. Trade + place + stage is the whole identity by design."""
    if not m:
        return None
    return {
        "id": m["id"],
        "display_name": m["display_name"],
        "trade": m["trade"],
        "district": m["district"],
        "block": m["block"],
        "stage": m["stage"],
        "role": m["role"],
        "expert_role": m["expert_role"],
        "trust_level": m["trust_level"],
    }


# ---------------------------------------------------------------------------
# Threads
# ---------------------------------------------------------------------------

def create_thread(*, author: dict, post_type: str, trade: str, topic: str, district: str, block: str, title: str, body: str, input_mode: str, lang: str, status: str, held_reason: str | None) -> dict:
    tid = _new_id("t")
    with _conn() as conn:
        conn.execute(
            "INSERT INTO threads(id, author_id, post_type, trade, topic, district, block, title, body, input_mode, lang, status, held_reason, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, author["id"], post_type, trade, topic, district, block, title, body, input_mode, lang, status, held_reason, time.time()),
        )
    return get_thread(tid)  # type: ignore[return-value]


def get_thread(thread_id: str) -> dict | None:
    with _conn() as conn:
        t = _row(conn.execute("SELECT * FROM threads WHERE id=?", (thread_id,)).fetchone())
        if not t:
            return None
        t["author"] = public_member(_row(conn.execute("SELECT * FROM members WHERE id=?", (t["author_id"],)).fetchone()))
        return t


def list_threads(*, trade: str | None = None, topic: str | None = None, stage: str | None = None, district: str | None = None,
                 post_type: str | None = None, status: str = "published", limit: int = 50, offset: int = 0) -> list[dict]:
    where, params = ["t.status = ?"], [status]
    if trade:
        where.append("t.trade = ?"); params.append(trade)
    if topic:
        where.append("t.topic = ?"); params.append(topic)
    if district:
        where.append("t.district = ?"); params.append(district)
    if post_type:
        where.append("t.post_type = ?"); params.append(post_type)
    if stage:
        where.append("m.stage = ?"); params.append(stage)
    sql = (
        "SELECT t.*, m.display_name, m.trade AS author_trade, m.district AS author_district, m.block AS author_block, "
        "m.stage AS author_stage, m.role AS author_role, m.expert_role AS author_expert_role, m.trust_level AS author_trust "
        "FROM threads t JOIN members m ON m.id = t.author_id WHERE " + " AND ".join(where) +
        " ORDER BY t.created_at DESC LIMIT ? OFFSET ?"
    )
    params += [limit, offset]
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    out = []
    for r in rows:
        author = {
            "id": r["author_id"], "display_name": r.pop("display_name"), "trade": r.pop("author_trade"),
            "district": r.pop("author_district"), "block": r.pop("author_block"), "stage": r.pop("author_stage"),
            "role": r.pop("author_role"), "expert_role": r.pop("author_expert_role"), "trust_level": r.pop("author_trust"),
        }
        r["author"] = author
        out.append(r)
    return out


def recent_threads_for_dedupe(trade: str, days: int = 90, limit: int = 200) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, body, created_at FROM threads WHERE trade=? AND status='published' AND created_at > ? ORDER BY created_at DESC LIMIT ?",
            (trade, time.time() - days * 86400, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def set_thread_status(thread_id: str, status: str, held_reason: str | None = None) -> dict | None:
    with _conn() as conn:
        conn.execute("UPDATE threads SET status=?, held_reason=? WHERE id=?", (status, held_reason, thread_id))
    return get_thread(thread_id)


def set_thread_topic(thread_id: str, topic: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE threads SET topic=? WHERE id=?", (topic, thread_id))


# ---------------------------------------------------------------------------
# Replies
# ---------------------------------------------------------------------------

def add_reply(*, thread_id: str, author: dict | None, kind: str, body: str, official: bool = False, status: str = "published",
              held_reason: str | None = None, provenance: dict | None = None) -> dict:
    rid = _new_id("r")
    with _conn() as conn:
        conn.execute(
            "INSERT INTO replies(id, thread_id, author_id, kind, body, official, status, held_reason, provenance, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rid, thread_id, author["id"] if author else None, kind, body, int(official), status, held_reason,
             json.dumps(provenance) if provenance else None, time.time()),
        )
        if status == "published":
            conn.execute("UPDATE threads SET reply_count = reply_count + 1 WHERE id=?", (thread_id,))
            if kind == "expert":
                conn.execute("UPDATE threads SET expert_answered = 1 WHERE id=?", (thread_id,))
    return get_reply(rid)  # type: ignore[return-value]


def get_reply(reply_id: str) -> dict | None:
    with _conn() as conn:
        r = _row(conn.execute("SELECT * FROM replies WHERE id=?", (reply_id,)).fetchone())
        if not r:
            return None
        r["provenance"] = json.loads(r["provenance"]) if r["provenance"] else None
        r["author"] = public_member(_row(conn.execute("SELECT * FROM members WHERE id=?", (r["author_id"],)).fetchone())) if r["author_id"] else None
        return r


def list_replies(thread_id: str, include_hidden: bool = False) -> list[dict]:
    with _conn() as conn:
        sql = "SELECT * FROM replies WHERE thread_id=?" + ("" if include_hidden else " AND status='published'") + " ORDER BY created_at ASC"
        rows = [dict(r) for r in conn.execute(sql, (thread_id,)).fetchall()]
        members: dict[str, dict | None] = {}
        for r in rows:
            r["provenance"] = json.loads(r["provenance"]) if r["provenance"] else None
            aid = r["author_id"]
            if aid and aid not in members:
                members[aid] = public_member(_row(conn.execute("SELECT * FROM members WHERE id=?", (aid,)).fetchone()))
            r["author"] = members.get(aid) if aid else None
    # Order within a thread is by role, not time: the engine's first response,
    # then verified experts, then lived experience, then everything else.
    # Recency inside each group.
    rank = {"saarthi": 0, "expert": 1, "experience": 2, "peer": 3}
    rows.sort(key=lambda r: (rank.get(r["kind"], 9), r["created_at"]))
    return rows


def set_reply_status(reply_id: str, status: str, held_reason: str | None = None) -> dict | None:
    with _conn() as conn:
        before = _row(conn.execute("SELECT * FROM replies WHERE id=?", (reply_id,)).fetchone())
        if not before:
            return None
        conn.execute("UPDATE replies SET status=?, held_reason=? WHERE id=?", (status, held_reason, reply_id))
        was_pub, now_pub = before["status"] == "published", status == "published"
        if was_pub != now_pub:
            delta = 1 if now_pub else -1
            conn.execute("UPDATE threads SET reply_count = reply_count + ? WHERE id=?", (delta, before["thread_id"]))
            if before["kind"] == "expert" and now_pub:
                conn.execute("UPDATE threads SET expert_answered = 1 WHERE id=?", (before["thread_id"],))
    return get_reply(reply_id)


# ---------------------------------------------------------------------------
# Trust bookkeeping
# ---------------------------------------------------------------------------

def record_approved_post(member_id: str) -> None:
    """Every published post counts; once a newcomer has NEWCOMER_REVIEW_COUNT
    published posts they auto-publish from then on."""
    with _conn() as conn:
        conn.execute("UPDATE members SET approved_posts = approved_posts + 1 WHERE id=?", (member_id,))
        conn.execute(
            "UPDATE members SET trust_level = 1 WHERE id=? AND trust_level = 0 AND approved_posts >= ?",
            (member_id, NEWCOMER_REVIEW_COUNT),
        )


def set_trust_level(member_id: str, level: int) -> None:
    with _conn() as conn:
        conn.execute("UPDATE members SET trust_level=? WHERE id=?", (level, member_id))


# ---------------------------------------------------------------------------
# Flags (reports)
# ---------------------------------------------------------------------------

def add_flag(*, target_type: str, target_id: str, reporter_id: str, reason: str) -> int:
    """Returns the total distinct flags on the target after this one. Two
    independent reports hide a post pending review - a low bar on purpose,
    because the failure mode we fear (a scam pitch staying up) costs more
    than the one we accept (a legitimate post hidden for a day)."""
    with _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO flags(id, target_type, target_id, reporter_id, reason, created_at) VALUES (?,?,?,?,?,?)",
                (_new_id("f"), target_type, target_id, reporter_id, reason, time.time()),
            )
        except sqlite3.IntegrityError:
            pass  # same member flagging twice counts once
        n = conn.execute("SELECT COUNT(*) FROM flags WHERE target_type=? AND target_id=?", (target_type, target_id)).fetchone()[0]
        if n >= HIDE_AFTER_FLAGS:
            table = "threads" if target_type == "thread" else "replies"
            conn.execute(f"UPDATE {table} SET status='hidden', held_reason='flagged' WHERE id=? AND status='published'", (target_id,))
        return int(n)


# ---------------------------------------------------------------------------
# Moderation queue
# ---------------------------------------------------------------------------

def moderation_queue() -> dict:
    with _conn() as conn:
        threads = [dict(r) for r in conn.execute("SELECT * FROM threads WHERE status IN ('pending','hidden') ORDER BY created_at ASC").fetchall()]
        replies = [dict(r) for r in conn.execute("SELECT * FROM replies WHERE status IN ('pending','hidden') ORDER BY created_at ASC").fetchall()]
        connects = [dict(r) for r in conn.execute("SELECT * FROM connect_requests WHERE status='pending' ORDER BY created_at ASC").fetchall()]
        unanswered = [dict(r) for r in conn.execute(
            "SELECT * FROM threads WHERE status='published' AND post_type='question' AND expert_answered=0 AND created_at < ? ORDER BY created_at ASC LIMIT 50",
            (time.time() - 48 * 3600,),
        ).fetchall()]
        for coll in (threads, unanswered):
            for t in coll:
                t["author"] = public_member(_row(conn.execute("SELECT * FROM members WHERE id=?", (t["author_id"],)).fetchone()))
        for r in replies:
            r["provenance"] = json.loads(r["provenance"]) if r["provenance"] else None
            r["author"] = public_member(_row(conn.execute("SELECT * FROM members WHERE id=?", (r["author_id"],)).fetchone())) if r["author_id"] else None
    return {"threads": threads, "replies": replies, "connect_requests": connects, "unanswered_over_48h": unanswered}


# ---------------------------------------------------------------------------
# Crowd data: price reports and wait-time reports
# ---------------------------------------------------------------------------

def add_price_report(*, member_id: str, trade: str, item: str, amount: float, unit: str, district: str, block: str, month: str, thread_id: str | None = None) -> dict:
    pid = _new_id("p")
    with _conn() as conn:
        conn.execute(
            "INSERT INTO price_reports(id, member_id, trade, item, amount, unit, district, block, month, thread_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (pid, member_id, trade, item.strip(), amount, unit, district, block, month, thread_id, time.time()),
        )
        return dict(conn.execute("SELECT * FROM price_reports WHERE id=?", (pid,)).fetchone())


def price_summary(*, trade: str | None = None, item: str | None = None, district: str | None = None, days: int = 180) -> list[dict]:
    """Aggregates per (trade, item, unit, district). Reported beside - never
    instead of - the official unit cost; the caller tags it USER_REPORTED."""
    where, params = ["created_at > ?"], [time.time() - days * 86400]
    if trade:
        where.append("trade=?"); params.append(trade)
    if item:
        where.append("LOWER(item)=LOWER(?)"); params.append(item)
    if district:
        where.append("district=?"); params.append(district)
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM price_reports WHERE " + " AND ".join(where), params).fetchall()]
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["trade"], r["item"].casefold(), r["unit"], r["district"]), []).append(r)
    out = []
    for (tr, _it, unit, dist), rs in groups.items():
        amounts = [r["amount"] for r in rs]
        out.append({
            "trade": tr, "item": rs[0]["item"], "unit": unit, "district": dist,
            "n": len(rs), "median": statistics.median(amounts), "min": min(amounts), "max": max(amounts),
            "latest_month": max(r["month"] for r in rs),
            "provenance": "USER_REPORTED",
        })
    out.sort(key=lambda g: (-g["n"], g["item"]))
    return out


def _month_diff(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    try:
        ya, ma = (int(x) for x in a.split("-")[:2])
        yb, mb = (int(x) for x in b.split("-")[:2])
    except ValueError:
        return None
    return (yb - ya) * 12 + (mb - ma)


def add_wait_report(*, member_id: str, district: str, block: str, agency: str, applied_month: str, sanctioned_month: str | None,
                    disbursed_month: str | None, thread_id: str | None = None) -> dict:
    wid = _new_id("w")
    with _conn() as conn:
        conn.execute(
            "INSERT INTO wait_reports(id, member_id, district, block, agency, applied_month, sanctioned_month, disbursed_month, thread_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (wid, member_id, district, block, agency.strip(), applied_month, sanctioned_month, disbursed_month, thread_id, time.time()),
        )
        return dict(conn.execute("SELECT * FROM wait_reports WHERE id=?", (wid,)).fetchone())


def wait_summary(*, district: str | None = None, agency: str | None = None) -> list[dict]:
    where, params = ["1=1"], []
    if district:
        where.append("district=?"); params.append(district)
    if agency:
        where.append("LOWER(agency)=LOWER(?)"); params.append(agency)
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM wait_reports WHERE " + " AND ".join(where), params).fetchall()]
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["district"], r["agency"].casefold()), []).append(r)
    out = []
    for (dist, _ag), rs in groups.items():
        to_sanction = [d for d in (_month_diff(r["applied_month"], r["sanctioned_month"]) for r in rs) if d is not None and d >= 0]
        to_money = [d for d in (_month_diff(r["sanctioned_month"], r["disbursed_month"]) for r in rs) if d is not None and d >= 0]
        out.append({
            "district": dist, "agency": rs[0]["agency"], "n": len(rs),
            "median_months_to_sanction": statistics.median(to_sanction) if to_sanction else None,
            "median_months_sanction_to_money": statistics.median(to_money) if to_money else None,
            "still_waiting": sum(1 for r in rs if not r["disbursed_month"]),
            "provenance": "USER_REPORTED",
        })
    out.sort(key=lambda g: -g["n"])
    return out


# ---------------------------------------------------------------------------
# Connect requests ("Looking for" posts) - contact goes through a moderator,
# never as an open phone number in a post.
# ---------------------------------------------------------------------------

def add_connect_request(*, thread_id: str, requester_id: str, message: str) -> dict:
    cid = _new_id("c")
    with _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO connect_requests(id, thread_id, requester_id, message, created_at) VALUES (?,?,?,?,?)",
                (cid, thread_id, requester_id, message, time.time()),
            )
        except sqlite3.IntegrityError:
            row = conn.execute("SELECT * FROM connect_requests WHERE thread_id=? AND requester_id=?", (thread_id, requester_id)).fetchone()
            return dict(row)
        return dict(conn.execute("SELECT * FROM connect_requests WHERE id=?", (cid,)).fetchone())


def set_connect_status(connect_id: str, status: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE connect_requests SET status=? WHERE id=?", (status, connect_id))


def counts() -> dict[str, Any]:
    with _conn() as conn:
        return {
            "members": conn.execute("SELECT COUNT(*) FROM members").fetchone()[0],
            "threads": conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0],
            "replies": conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0],
        }
