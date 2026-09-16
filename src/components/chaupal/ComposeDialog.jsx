import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Microphone, MicrophoneSlash, X, Ear } from "@phosphor-icons/react";
import { useForum } from "../../context/ForumContext";
import { useAppState } from "../../context/AppContext";
import { forumApi } from "../../lib/forumApi";
import { useDictation } from "../../lib/useDictation";
import { Button, Field, Select, TextInput, NumberInput, Spinner } from "../ui";
import { NoFeeNotice, TopicChip } from "./bits";

const thisMonth = () => new Date().toISOString().slice(0, 7);

/**
 * New post. Voice first: the mic button dictates straight into the body
 * (same browser API as the intake agent). Before sending we ask the
 * backend to check the draft - it comes back with "someone asked this
 * already" matches, the suggested topic label, and whether the post will
 * be held for a moderator - so the person can listen first, confirm the
 * label, and is never surprised by a hold.
 */
export default function ComposeDialog({ open, onClose, initial = {} }) {
  const { member, labels, openSignIn } = useForum();
  const { voiceLanguage } = useAppState();
  const navigate = useNavigate();
  const [postType, setPostType] = useState(initial.post_type || "question");
  const [title, setTitle] = useState(initial.title || "");
  const [body, setBody] = useState(initial.body || "");
  const [topic, setTopic] = useState(initial.topic || "");
  const [price, setPrice] = useState({ item: "", amount: "", unit: "", month: thisMonth() });
  const [wait, setWait] = useState({ agency: "", applied_month: "", sanctioned_month: "", disbursed_month: "" });
  const [check, setCheck] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [voiceUsed, setVoiceUsed] = useState(false);

  const dictation = useDictation({
    lang: voiceLanguage || "hi-IN",
    onText: (t) => {
      setVoiceUsed(true);
      setBody((b) => (b ? `${b} ${t}` : t));
    },
  });

  useEffect(() => {
    if (!open) return;
    setPostType(initial.post_type || "question");
    setTitle(initial.title || "");
    setBody(initial.body || "");
    setTopic(initial.topic || "");
    setCheck(null);
    setResult(null);
    setError("");
    setVoiceUsed(false);
  }, [open, initial.post_type, initial.title, initial.body, initial.topic]);

  const canSend = useMemo(() => title.trim().length >= 4 && body.trim().length >= 10, [title, body]);

  if (!open) return null;
  if (!member) {
    // Reading is open; writing needs a person behind the post.
    return (
      <Backdrop onClose={onClose} title="Post on Chaupal">
        <p className="text-[16px] text-ink-soft mb-5">Sign in with your phone to post. Others will see only your name, trade, place and stage.</p>
        <Button className="w-full" onClick={() => { onClose(); openSignIn(); }}>Sign in to post</Button>
      </Backdrop>
    );
  }

  async function runCheck() {
    if (!canSend) return;
    setBusy(true);
    setError("");
    try {
      const res = await forumApi.checkBeforePost(`${title}\n${body}`, member.trade);
      setCheck(res);
      if (!topic) setTopic(res.suggested_topic);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const payload = { post_type: postType, title: title.trim(), body: body.trim(), topic: topic || undefined, input_mode: voiceUsed ? "voice" : "text" };
      if (postType === "price_report") payload.price_report = { ...price, amount: Number(price.amount) };
      if (postType === "wait_report") payload.wait_report = { ...wait, sanctioned_month: wait.sanctioned_month || null, disbursed_month: wait.disbursed_month || null };
      const res = await forumApi.createThread(payload);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <Backdrop onClose={onClose} title={result.held ? "Posted - waiting for a moderator" : "Posted"}>
        {result.held ? (
          <p className="text-[16px] text-ink-soft mb-4">
            {result.held_reason === "scam_signals"
              ? "Your post mentions fees or guarantees, so a moderator will read it before it goes up. Warnings about scams are welcome - this just keeps the real thing out."
              : `New members' first ${labels?.newcomer_review_count || 3} posts are read by a moderator before they go up. You can already see it yourself.`}
          </p>
        ) : (
          <p className="text-[16px] text-ink-soft mb-4">It is up. {result.saarthi_reply ? "Saarthi has already left a first response with the numbers; a verified expert or a member who has done this can add to it." : ""}</p>
        )}
        {result.pii_removed?.length > 0 && <p className="text-[14px] text-clay mb-4">We removed a phone number / payment handle from your post - the forum never shows contact details.</p>}
        <Button className="w-full" onClick={() => { onClose(); navigate(`/chaupal/t/${result.thread.id}`); }}>Open my post</Button>
      </Backdrop>
    );
  }

  const postTypes = labels?.post_types || [];
  const topics = labels?.topics || [];

  return (
    <Backdrop onClose={onClose} title="Post on Chaupal">
      {error && <p className="mb-3 rounded-xl border border-clay/30 bg-clay-tint px-4 py-2.5 text-[15px] text-clay">{error}</p>}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4" role="radiogroup" aria-label="What kind of post">
        {postTypes.map((p) => (
          <button
            key={p.value}
            type="button"
            role="radio"
            aria-checked={postType === p.value}
            onClick={() => setPostType(p.value)}
            className={`rounded-xl border-2 px-3 py-2.5 text-[15px] font-semibold text-left transition ${postType === p.value ? "border-pine bg-pine-tint text-pine-dim" : "border-line text-ink hover:border-pine/50"}`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {(postType === "question" || postType === "warning") && topic === "scam" && <div className="mb-4"><NoFeeNotice /></div>}

      <div className="space-y-4">
        <Field label="One line - what is it about?" required>
          <TextInput id="compose-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={140} placeholder="e.g. Kitna loan milega 2 buffalo ke liye?" />
        </Field>

        <Field label="Say it or type it" hint="Start with your name and village - that is how people here recognise each other." required>
          <div className="relative">
            <textarea
              id="compose-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
              maxLength={4000}
              className="w-full rounded-xl border-2 border-line-strong bg-white px-4 py-3 pr-14 text-[17px] text-ink placeholder:text-ink-faint outline-none transition focus:border-pine focus:ring-4 focus:ring-pine/15"
              placeholder={dictation.listening ? "Listening..." : "Tap the mic and speak, or type here"}
            />
            {dictation.supported && (
              <button
                type="button"
                onClick={dictation.listening ? dictation.stop : dictation.start}
                aria-label={dictation.listening ? "Stop listening" : "Speak"}
                className={`absolute right-2 top-2 h-11 w-11 rounded-full flex items-center justify-center transition ${dictation.listening ? "bg-clay text-white animate-pulse" : "bg-pine text-white hover:bg-pine-dim"}`}
              >
                {dictation.listening ? <MicrophoneSlash size={22} weight="fill" /> : <Microphone size={22} weight="fill" />}
              </button>
            )}
          </div>
          {dictation.interim && <p className="mt-1 text-[14px] text-ink-faint italic">{dictation.interim}</p>}
        </Field>

        {postType === "price_report" && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="What did you buy?" required><TextInput id="price-item" value={price.item} onChange={(e) => setPrice({ ...price, item: e.target.value })} placeholder="Murrah buffalo" /></Field>
            <Field label="Unit" required><TextInput id="price-unit" value={price.unit} onChange={(e) => setPrice({ ...price, unit: e.target.value })} placeholder="animal / kg / machine" /></Field>
            <Field label="Amount paid" required><NumberInput id="price-amount" prefix="₹" value={price.amount} onChange={(e) => setPrice({ ...price, amount: e.target.value })} /></Field>
            <Field label="Month" required><TextInput id="price-month" type="month" value={price.month} onChange={(e) => setPrice({ ...price, month: e.target.value })} /></Field>
          </div>
        )}

        {postType === "wait_report" && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Agency / bank" required><TextInput id="wait-agency" value={wait.agency} onChange={(e) => setWait({ ...wait, agency: e.target.value })} placeholder="MPBCDC / Bank of Maharashtra" /></Field>
            <Field label="Applied" required><TextInput id="wait-applied" type="month" value={wait.applied_month} onChange={(e) => setWait({ ...wait, applied_month: e.target.value })} /></Field>
            <Field label="Sanctioned"><TextInput id="wait-sanctioned" type="month" value={wait.sanctioned_month} onChange={(e) => setWait({ ...wait, sanctioned_month: e.target.value })} /></Field>
            <Field label="Money received"><TextInput id="wait-disbursed" type="month" value={wait.disbursed_month} onChange={(e) => setWait({ ...wait, disbursed_month: e.target.value })} /></Field>
          </div>
        )}

        <Field label="Topic" hint={check ? "Saarthi's guess - change it if it is wrong." : "Leave blank and Saarthi will guess from what you wrote."}>
          <Select id="compose-topic" value={topic} onChange={(e) => setTopic(e.target.value)}>
            <option value="">Let Saarthi guess</option>
            {topics.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </Select>
        </Field>

        {check && (
          <div className="rounded-xl border-2 border-line bg-paper-dim p-4 space-y-3">
            {check.duplicates.length > 0 && (
              <div>
                <p className="flex items-center gap-2 text-[15px] font-semibold text-ink mb-2"><Ear size={18} weight="fill" className="text-pine" /> Someone asked this already - listen first?</p>
                <ul className="space-y-1.5">
                  {check.duplicates.map((d) => (
                    <li key={d.id}>
                      <button type="button" onClick={() => { onClose(); navigate(`/chaupal/t/${d.id}`); }} className="text-left text-[15px] text-pine-dim underline underline-offset-4">{d.title}</button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[14px] text-ink-soft flex flex-wrap items-center gap-2">
              Will be filed under <TopicChip topic={topic || check.suggested_topic} />
              {check.will_be_reviewed && <span>· a moderator reads new members' first posts before they go up</span>}
              {check.scam_signals.length > 0 && <span className="text-clay">· mentions fees/guarantees, so a moderator will read it first</span>}
              {check.pii_removed.length > 0 && <span className="text-clay">· a phone number / handle will be removed</span>}
            </p>
          </div>
        )}
      </div>

      <div className="mt-5 flex flex-col-reverse sm:flex-row gap-2 sm:justify-end">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        {!check ? (
          <Button onClick={runCheck} disabled={!canSend || busy}>{busy ? <Spinner /> : "Check & continue"}</Button>
        ) : (
          <Button onClick={submit} disabled={busy}>{busy ? <Spinner /> : "Post"}</Button>
        )}
      </div>
    </Backdrop>
  );
}

function Backdrop({ children, onClose, title }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-ink/40 p-0 sm:p-6" role="dialog" aria-modal="true" aria-labelledby="compose-title">
      <div className="w-full sm:max-w-2xl bg-white rounded-t-2xl sm:rounded-2xl shadow-xl p-6 sm:p-7 max-h-[92dvh] overflow-y-auto">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h2 id="compose-title" className="font-display text-2xl font-bold text-ink tracking-tight">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="text-ink-soft hover:text-ink p-1"><X size={22} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}
