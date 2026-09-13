import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Flag, Microphone, MicrophoneSlash, SealCheck, Handshake } from "@phosphor-icons/react";
import { useForum } from "../context/ForumContext";
import { useAppState } from "../context/AppContext";
import { forumApi } from "../lib/forumApi";
import { useDictation } from "../lib/useDictation";
import { Card, Button, Spinner } from "../components/ui";
import { Who, TopicChip, PostTypeChip, NoFeeNotice, timeAgo } from "../components/chaupal/bits";

const KIND_LABEL = {
  saarthi: "Saarthi's take",
  expert: "Expert answer",
  experience: "From experience",
  peer: "Reply",
};

const KIND_STYLE = {
  saarthi: "border-pine/30 bg-pine-tint",
  expert: "border-gold/40 bg-gold-tint",
  experience: "border-good/30 bg-good-tint",
  peer: "border-line bg-white",
};

/**
 * One thread. Replies are grouped by who they are from - the engine first,
 * then verified experts, then lived experience, then everyone else - the
 * order the field evidence says readers actually want.
 */
export default function ChaupalThread() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { member, openSignIn, lookup } = useForum();
  const { voiceLanguage } = useAppState();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [body, setBody] = useState("");
  const [kind, setKind] = useState("peer");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [connectMsg, setConnectMsg] = useState("");
  const [voiceUsed, setVoiceUsed] = useState(false);

  const dictation = useDictation({ lang: voiceLanguage || "hi-IN", onText: (t) => { setVoiceUsed(true); setBody((b) => (b ? `${b} ${t}` : t)); } });

  const load = useCallback(() => {
    forumApi.getThread(id).then(setData).catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (member) setKind(member.role === "expert" ? "expert" : "peer");
  }, [member]);

  async function send() {
    if (!member) return openSignIn();
    setBusy(true);
    setNotice("");
    try {
      const res = await forumApi.addReply(id, { body: body.trim(), kind, input_mode: voiceUsed ? "voice" : "text" });
      setBody("");
      setVoiceUsed(false);
      setNotice(res.held ? "Thanks - a moderator will read it before it goes up." : "");
      load();
    } catch (e) {
      setNotice(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function report(targetType, targetId) {
    if (!member) return openSignIn();
    const reason = window.prompt("Why? (scam / abuse / wrong_info / spam / other)", "scam");
    if (!reason) return;
    try {
      const res = await forumApi.report(targetType, targetId, reason.trim());
      setNotice(res.hidden ? "Reported - hidden until a moderator looks at it." : "Reported. Thank you.");
      load();
    } catch (e) {
      setNotice(e.message);
    }
  }

  async function connect() {
    if (!member) return openSignIn();
    setBusy(true);
    try {
      await forumApi.connect(id, connectMsg.trim());
      setNotice("Sent to a moderator, who will introduce you both. No phone numbers are shared here.");
      setConnectMsg("");
    } catch (e) {
      setNotice(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <Card className="max-w-3xl text-center py-14">
        <p className="text-[17px] text-ink-soft mb-5">{error}</p>
        <Link to="/chaupal" className="text-pine-dim font-semibold underline underline-offset-4">Back to Chaupal</Link>
      </Card>
    );
  }
  if (!data) return <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft"><Spinner className="text-pine" /> Loading...</Card>;

  const { thread, replies } = data;
  const held = thread.status !== "published";

  return (
    <div className="max-w-3xl">
      <button type="button" onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-ink-soft hover:text-ink mb-4">
        <ArrowLeft size={18} /> Back
      </button>

      {held && (
        <div className="mb-4 rounded-xl border-2 border-gold/40 bg-gold-tint px-4 py-3 text-[15px] text-ink">
          {thread.status === "pending" ? "Only you can see this until a moderator reads it." : `This post is ${thread.status}.`}
        </div>
      )}

      <Card>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <PostTypeChip type={thread.post_type} />
          <TopicChip topic={thread.topic} />
          {thread.input_mode === "voice" && <span className="inline-flex items-center gap-1 text-[13px] text-ink-soft"><Microphone size={14} weight="fill" /> spoken</span>}
          <span className="ml-auto text-[13px] text-ink-faint">{timeAgo(thread.created_at)}</span>
        </div>
        <h1 className="font-display text-[26px] sm:text-3xl font-bold text-ink tracking-tight leading-tight text-balance">{thread.title}</h1>
        <p className="mt-3 text-[17px] text-ink leading-relaxed whitespace-pre-line">{thread.body}</p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <Who author={thread.author} />
          <button type="button" onClick={() => report("thread", thread.id)} className="inline-flex items-center gap-1 text-[14px] text-ink-soft hover:text-clay"><Flag size={15} /> Report</button>
        </div>
        {(thread.topic === "scam" || thread.topic === "loan_scheme" || thread.topic === "bank_process") && <div className="mt-4"><NoFeeNotice /></div>}
      </Card>

      {thread.post_type === "looking_for" && member && member.id !== thread.author_id && (
        <div className="mt-4 rounded-2xl border-2 border-gold/40 bg-gold-tint p-4 sm:p-5">
          <p className="flex items-center gap-2 text-[16px] font-semibold text-ink mb-2"><Handshake size={20} weight="fill" className="text-gold" /> Can you help with this?</p>
          <p className="text-[14.5px] text-ink-soft mb-3">Say what you can offer. A moderator introduces you both - no phone numbers in the forum.</p>
          <textarea id="connect-msg" value={connectMsg} onChange={(e) => setConnectMsg(e.target.value)} rows={2} maxLength={500}
            className="w-full rounded-xl border-2 border-line-strong bg-white px-4 py-3 text-[16px] text-ink outline-none focus:border-pine focus:ring-4 focus:ring-pine/15" placeholder="e.g. I run a sweet shop in Renapur, can take 20 litres daily" />
          <div className="mt-2 flex justify-end"><Button onClick={connect} disabled={busy || connectMsg.trim().length < 5}>Ask to connect</Button></div>
        </div>
      )}

      <section className="mt-6">
        <h2 className="font-display text-xl sm:text-2xl font-bold text-ink tracking-tight mb-3">{replies.length} {replies.length === 1 ? "reply" : "replies"}</h2>
        <ul className="space-y-3">
          {replies.map((r) => (
            <li key={r.id} className={`rounded-2xl border-2 p-4 sm:p-5 ${KIND_STYLE[r.kind] || KIND_STYLE.peer} ${r.status !== "published" ? "opacity-70" : ""}`}>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className={`inline-flex items-center gap-1 text-[13px] font-bold uppercase tracking-wide ${r.kind === "expert" ? "text-gold" : r.kind === "saarthi" ? "text-pine-dim" : r.kind === "experience" ? "text-good-dim" : "text-ink-soft"}`}>
                  {r.kind === "expert" && <SealCheck size={14} weight="fill" />}
                  {KIND_LABEL[r.kind] || r.kind}
                </span>
                {r.status !== "published" && <span className="text-[12px] text-ink-faint">(waiting for a moderator)</span>}
                <span className="ml-auto text-[13px] text-ink-faint">{timeAgo(r.created_at)}</span>
              </div>
              <p className="text-[16.5px] text-ink leading-relaxed whitespace-pre-line">{r.body}</p>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <Who author={r.author} />
                {r.kind !== "saarthi" && <button type="button" onClick={() => report("reply", r.id)} className="inline-flex items-center gap-1 text-[13px] text-ink-soft hover:text-clay"><Flag size={14} /> Report</button>}
              </div>
              {r.kind === "saarthi" && r.provenance?.items?.length > 0 && (
                <details className="mt-3 text-[13px] text-ink-soft">
                  <summary className="cursor-pointer font-semibold">Where these numbers come from</summary>
                  <ul className="mt-1.5 space-y-0.5">
                    {r.provenance.items.map((p, i) => (
                      <li key={i}>
                        <span className="font-mono text-[12px] rounded bg-white/70 px-1 py-0.5 mr-1.5">{p.provenance}</span>
                        {p.source}{p.assumption ? ` - assuming ${p.assumption}` : ""}{p.n ? ` (${p.n} reports)` : ""}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-6 paper-card rounded-2xl p-4 sm:p-5">
        <h3 className="font-display text-lg font-bold text-ink mb-2">Add to this</h3>
        {!member ? (
          <Button variant="secondary" onClick={() => openSignIn()}>Sign in to reply</Button>
        ) : (
          <>
            <div className="flex flex-wrap gap-2 mb-3" role="radiogroup" aria-label="Kind of reply">
              {[
                ["peer", "Reply"],
                ["experience", "I have done this"],
                ...(member.role === "expert" ? [["expert", `Expert answer (${lookup.expertRole[member.expert_role] || "verified"})`]] : []),
              ].map(([k, label]) => (
                <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}
                  className={`rounded-xl border-2 px-3 py-2 text-[15px] font-semibold transition ${kind === k ? "border-pine bg-pine-tint text-pine-dim" : "border-line text-ink hover:border-pine/50"}`}>
                  {label}
                </button>
              ))}
            </div>
            <div className="relative">
              <textarea id="reply-body" value={body} onChange={(e) => setBody(e.target.value)} rows={4} maxLength={3000}
                className="w-full rounded-xl border-2 border-line-strong bg-white px-4 py-3 pr-14 text-[16.5px] text-ink placeholder:text-ink-faint outline-none focus:border-pine focus:ring-4 focus:ring-pine/15"
                placeholder={dictation.listening ? "Listening..." : "Speak or type. Say your name and village first."} />
              {dictation.supported && (
                <button type="button" onClick={dictation.listening ? dictation.stop : dictation.start} aria-label={dictation.listening ? "Stop" : "Speak"}
                  className={`absolute right-2 top-2 h-11 w-11 rounded-full flex items-center justify-center ${dictation.listening ? "bg-clay text-white animate-pulse" : "bg-pine text-white hover:bg-pine-dim"}`}>
                  {dictation.listening ? <MicrophoneSlash size={22} weight="fill" /> : <Microphone size={22} weight="fill" />}
                </button>
              )}
            </div>
            {dictation.interim && <p className="mt-1 text-[14px] text-ink-faint italic">{dictation.interim}</p>}
            <div className="mt-3 flex items-center justify-between gap-3">
              <p className="text-[13.5px] text-ink-faint">Phone numbers and payment handles are removed automatically.</p>
              <Button onClick={send} disabled={busy || body.trim().length < 2}>{busy ? <Spinner /> : "Post reply"}</Button>
            </div>
          </>
        )}
        {notice && <p className="mt-3 text-[15px] text-ink-soft">{notice}</p>}
      </section>
    </div>
  );
}
