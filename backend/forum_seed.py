"""Seed Vyapar Chaupal with realistic demo content.

    cd backend && uv run python forum_seed.py

Creates a handful of members (one moderator, two verified experts, several
entrepreneurs at different stages), a spread of threads across the label
axes, Saarthi's take on each question, a few expert and experience
replies, and enough price / wait-time reports for the summaries to show
something. Every seeded member's display name ends in "(demo)" so nobody
mistakes them for real people. Safe to run once on an empty database; it
refuses to run twice.

Demo sign-ins (OTP is echoed by the API when Twilio is not configured):
  +919100000001  moderator          +919100000002  RSETI trainer (expert)
  +919100000003  bank officer       +919100000010..19  entrepreneurs
"""

from __future__ import annotations

import asyncio

import forum_saarthi
import forum_store as store

MEMBERS = [
    # phone, name, trade, district, block, stage, role, expert_role
    ("+919100000001", "Sunita (demo)", "dairy", "latur", "Latur", "repaid", "moderator", None),
    ("+919100000002", "Prakash Sir, RSETI (demo)", "dairy", "latur", "Latur", "repaid", "expert", "rseti_trainer"),
    ("+919100000003", "Bank of Maharashtra Ausa (demo)", "dairy", "latur", "Ausa", "repaid", "expert", "bank_officer"),
    ("+919100000010", "Ramesh (demo)", "dairy", "latur", "Ausa", "repaying", "member", None),
    ("+919100000011", "Savita (demo)", "dairy", "latur", "Nilanga", "sanctioned", "member", None),
    ("+919100000012", "Imran (demo)", "textiles", "latur", "Latur", "running", "member", None),
    ("+919100000013", "Kavita (demo)", "textiles", "sitapur", "Biswan", "thinking", "member", None),
    ("+919100000014", "Deepak (demo)", "retail", "indore", "Mhow", "repaying", "member", None),
    ("+919100000015", "Balaji (demo)", "goat", "latur", "Renapur", "applied", "member", None),
    ("+919100000016", "Meena (demo)", "food_stall", "indore", "Rau", "running", "member", None),
    ("+919100000017", "Anil (demo)", "dairy", "latur", "Chakur", "struggling", "member", None),
]

THREADS = [
    # author phone, post_type, topic, title, body, replies: [(phone, kind, body)]
    ("+919100000011", "question", "loan_scheme",
     "2 buffaloes ke liye kitna loan milega? Mere paas 25,000 hai",
     "Mahamandal office bola 10% margin do. Mere paas 25,000 saved hai. Do Murrah buffalo lena hai Nilanga me. Kitna project cost banega aur kaunsa scheme?",
     [("+919100000003", "expert", "With Rs 25,000 as margin the scheme math gives a Rs 2,50,000 project. NABARD's 2026-27 unit cost for two Murrah buffaloes is Rs 2,72,300 including one month feed and insurance, so you are about Rs 22,000 short. Either add margin, or take one graded Murrah and one Pandharpuri (unit cost Rs 1,67,400 for two Pandharpuri). Bring the animal insurance quote with the application - we cannot sanction without it."),
      ("+919100000010", "experience", "Maine bhi 2 buffalo se start kiya Ausa me. Feed ka paisa pehle rakh lo - pehle 2 mahine doodh kam aata hai aur kharcha poora hota hai. Society 32 rupaye/litre deti hai 6.5 fat pe.")]),
    ("+919100000015", "question", "bank_process",
     "Applied in January, still no sanction - is this normal?",
     "I applied for a goat unit (10+1) through the corporation in January. The office says file is with the bank. It is September now. Is this normal for Latur? What can I do without paying anyone?",
     [("+919100000003", "expert", "Eight months is long but not unusual when the file moves corporation to bank. Ask the corporation office for the bank branch and the file number, then visit that branch with your ID and ask the manager for the status in writing. Do not pay anyone who says they can speed it up - nobody can."),
      ("+919100000010", "experience", "Mera bhi 7 mahine laga tha sanction ke baad paisa aane me. Branch me jaake manager se milna zaroori hai, phone pe kuch nahi hota.")]),
    ("+919100000017", "question", "repayment",
     "Buffalo died in July, EMI due next week - what should I do?",
     "One of my two buffaloes died in July. Insurance claim is filed but not paid yet. Instalment of 9,400 is due next week and milk income is half. I do not want to default. Who do I talk to?",
     [("+919100000003", "expert", "Go to the branch before the due date with the insurance claim receipt and the vet's death certificate. Ask in writing for a one-instalment rescheduling on account of livestock loss - it is within the manager's discretion and the paperwork you have is exactly what they need. Paying part of the instalment now shows intent."),
      ("+919100000002", "expert", "Also file the claim follow-up with the insurance company's district office, not just the agent. Claims settle faster with a written reminder. Keep the second animal's insurance current - this is the moment it lapses if you are short of cash.")]),
    ("+919100000012", "experience", "selling",
     "Wedding season pays for the whole year - plan stock in August",
     "Third year running a tailoring unit in Latur. October to February is 60% of the year's income. I buy fabric stock in August when it is cheap and keep two months of EMI aside from the wedding money. Summer is dead; do not take a big loan instalment that starts in April.",
     []),
    ("+919100000014", "question", "suppliers",
     "Wholesale supplier for kirana in Mhow - who do you use?",
     "Starting a general store in Mhow. The distributor I met wants full advance. Is that normal? Which wholesale market do people here buy from?",
     [("+919100000016", "peer", "Rau me hum Siyaganj (Indore) se late hain, weekly. Pehli baar advance maangte hain, teen mahine baad credit dete hain agar payment time pe ho.")]),
    ("+919100000013", "question", "training",
     "Kya loan se pehle koi training zaroori hai?",
     "Biswan me silai ka kaam start karna hai. Bank wale bole training certificate lao. Kaunsi training aur kahan se?",
     [("+919100000002", "expert", "Yes - finish the free RSETI course first. Every district has one; the tailoring course is 30 days, residential, no fee, and the certificate is what the bank is asking for. Sitapur's RSETI is run by the lead bank; ask at any branch for the next batch date.")]),
    ("+919100000010", "warning", "scam",
     "Fake 'approval letter' asking Rs 2,550 processing fee - do not pay",
     "Got a WhatsApp message with a MUDRA approval letter for 5 lakh asking 2,550 processing fee first. Called the bank - they said it is fake. No scheme charges any fee before sanction.",
     [("+919100000003", "expert", "Correct. No government scheme takes a fee before sanction and none use agents. Forward such messages to the PIB Fact Check number and delete them.")]),
    ("+919100000016", "looking_for", "selling",
     "Need 15 litres buffalo milk daily for snack stall in Rau",
     "My stall in Rau uses about 15 litres a day for tea and kheer. Looking for a dairy member within 20 km who can supply daily at society rate.",
     []),
    ("+919100000010", "price_report", "prices",
     "Paid 1,05,000 for a Murrah in Ausa (Aug 2026)",
     "8 litre yield, second calving, from Udgir market. Transport 2,000 extra.",
     []),
]

PRICE_REPORTS = [
    # phone, trade, item, amount, unit, district, block, month
    ("+919100000010", "dairy", "Murrah buffalo", 105000, "animal", "latur", "Ausa", "2026-08"),
    ("+919100000011", "dairy", "Murrah buffalo", 118000, "animal", "latur", "Nilanga", "2026-07"),
    ("+919100000017", "dairy", "Murrah buffalo", 98000, "animal", "latur", "Chakur", "2026-06"),
    ("+919100000010", "dairy", "Concentrate feed", 32, "kg", "latur", "Ausa", "2026-08"),
    ("+919100000011", "dairy", "Concentrate feed", 31, "kg", "latur", "Nilanga", "2026-08"),
    ("+919100000012", "textiles", "Sewing machine (Usha industrial)", 16500, "machine", "latur", "Latur", "2026-05"),
    ("+919100000015", "goat", "Osmanabadi doe", 9500, "animal", "latur", "Renapur", "2026-07"),
]

WAIT_REPORTS = [
    # phone, district, block, agency, applied, sanctioned, disbursed
    ("+919100000010", "latur", "Ausa", "MPBCDC", "2024-11", "2025-03", "2025-09"),
    ("+919100000011", "latur", "Nilanga", "MPBCDC", "2025-08", "2026-01", None),
    ("+919100000017", "latur", "Chakur", "MPBCDC", "2024-06", "2024-10", "2025-05"),
    ("+919100000015", "latur", "Renapur", "MPBCDC", "2026-01", None, None),
    ("+919100000014", "indore", "Mhow", "MPBCDC", "2025-02", "2025-04", "2025-07"),
]


async def seed() -> None:
    store.init_db()
    if store.counts()["members"]:
        print("Forum already has members - refusing to seed twice.")
        return

    by_phone: dict[str, dict] = {}
    for phone, name, trade, district, block, stage, role, expert_role in MEMBERS:
        m = store.upsert_member(phone, display_name=name, trade=trade, district=district, block=block, stage=stage)
        if role != "member":
            m = store.set_member_role(phone, role, expert_role) or m
        else:
            store.set_trust_level(m["id"], 1)
        by_phone[phone] = store.get_member(m["id"])  # type: ignore[assignment]

    for phone, post_type, topic, title, body, replies in THREADS:
        author = by_phone[phone]
        t = store.create_thread(author=author, post_type=post_type, trade=author["trade"], topic=topic, district=author["district"],
                                block=author["block"], title=title, body=body, input_mode="text", lang="en", status="published", held_reason=None)
        if post_type == "question":
            facts = forum_saarthi.build_facts(topic=topic, trade=author["trade"], district=author["district"], block=author["block"], text=f"{title}\n{body}")
            text = await forum_saarthi.phrase(facts, f"{title}\n{body}")
            store.add_reply(thread_id=t["id"], author=None, kind="saarthi", body=text, provenance={"items": facts["provenance"]})
        for rphone, kind, rbody in replies:
            store.add_reply(thread_id=t["id"], author=by_phone[rphone], kind=kind, body=rbody, official=(kind == "expert"))

    for phone, trade, item, amount, unit, district, block, month in PRICE_REPORTS:
        store.add_price_report(member_id=by_phone[phone]["id"], trade=trade, item=item, amount=amount, unit=unit, district=district, block=block, month=month)
    for phone, district, block, agency, applied, sanctioned, disbursed in WAIT_REPORTS:
        store.add_wait_report(member_id=by_phone[phone]["id"], district=district, block=block, agency=agency,
                              applied_month=applied, sanctioned_month=sanctioned, disbursed_month=disbursed)

    print("Seeded:", store.counts())


if __name__ == "__main__":
    asyncio.run(seed())
