import { useEffect, useState } from "react";
import { X } from "@phosphor-icons/react";
import { useForum } from "../../context/ForumContext";
import { useAppState } from "../../context/AppContext";
import { forumApi } from "../../lib/forumApi";
import { Button, Field, Select, TextInput, Spinner } from "../ui";

/**
 * Phone OTP sign-in. First-timers also fill the four things the forum
 * shows beside their name: what they do, where, and how far along they
 * are. Nothing else is asked - by design (see forum_labels.py).
 *
 * When the backend has no SMS provider it returns the code in the
 * response (dev_otp); we show it inline, clearly marked, so a demo never
 * stalls on a text message that will not arrive.
 */
export default function SignInDialog() {
  const { labels, signInOpen, closeSignIn, signIn, pendingAction } = useForum();
  const { profile } = useAppState();
  const [step, setStep] = useState("phone"); // phone -> code -> profile
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [devOtp, setDevOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ display_name: "", trade: "", district: "", block: "", stage: "thinking" });

  // Pre-fill trade/place from the wizard's own profile when we have one.
  useEffect(() => {
    if (!signInOpen) return;
    setStep("phone");
    setCode("");
    setDevOtp("");
    setError("");
    setForm((f) => ({
      ...f,
      trade: f.trade || profile.businessType || "",
      district: f.district || profile.district || "",
      block: f.block || profile.block || "",
    }));
  }, [signInOpen, profile.businessType, profile.district, profile.block]);

  if (!signInOpen) return null;

  const districts = labels?.districts || [];
  const blocks = districts.find((d) => d.key === form.district)?.blocks || [];

  async function sendCode(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await forumApi.requestOtp(phone.trim());
      if (res.dev_otp) setDevOtp(res.dev_otp);
      setStep("code");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function verify(e, withProfile = false) {
    e?.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await forumApi.verifyOtp(phone.trim(), code.trim(), withProfile ? form : null);
      if (res.needs_profile) {
        setStep("profile");
        return;
      }
      signIn(res.token, res.member);
      pendingAction?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-ink/40 p-0 sm:p-6" role="dialog" aria-modal="true" aria-labelledby="signin-title">
      <div className="w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-xl p-6 sm:p-7 max-h-[92dvh] overflow-y-auto">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 id="signin-title" className="font-display text-2xl font-bold text-ink tracking-tight">Join Chaupal</h2>
            <p className="text-[15px] text-ink-soft mt-1">Your number is never shown to anyone. Others see only your name, trade, place and stage.</p>
          </div>
          <button type="button" onClick={closeSignIn} aria-label="Close" className="text-ink-soft hover:text-ink p-1">
            <X size={22} />
          </button>
        </div>

        {error && <p className="mb-3 rounded-xl border border-clay/30 bg-clay-tint px-4 py-2.5 text-[15px] text-clay">{error}</p>}

        {step === "phone" && (
          <form onSubmit={sendCode} className="space-y-4">
            <Field label="Mobile number" required>
              <TextInput id="chaupal-phone" type="tel" inputMode="tel" placeholder="+91 98765 43210" value={phone} onChange={(e) => setPhone(e.target.value)} required minLength={10} autoFocus />
            </Field>
            <Button type="submit" className="w-full" disabled={busy}>{busy ? <Spinner /> : "Send code"}</Button>
          </form>
        )}

        {step === "code" && (
          <form onSubmit={(e) => verify(e, false)} className="space-y-4">
            {devOtp && (
              <p className="rounded-xl border border-gold/40 bg-gold-tint px-4 py-2.5 text-[15px] text-ink">
                SMS is not set up on this server, so here is your code: <strong className="figure text-[18px] tracking-widest">{devOtp}</strong>
              </p>
            )}
            <Field label="6-digit code" hint={`Sent to ${phone}`} required>
              <TextInput id="chaupal-code" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} required autoFocus />
            </Field>
            <Button type="submit" className="w-full" disabled={busy || code.length !== 6}>{busy ? <Spinner /> : "Continue"}</Button>
            <button type="button" onClick={() => setStep("phone")} className="w-full text-[15px] text-ink-soft underline underline-offset-4">Change number</button>
          </form>
        )}

        {step === "profile" && (
          <form onSubmit={(e) => verify(e, true)} className="space-y-4">
            <p className="text-[15px] text-ink-soft">First time here - tell others who they are talking to.</p>
            <Field label="Your name (as others will see it)" required>
              <TextInput id="chaupal-name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} required minLength={2} maxLength={40} autoFocus />
            </Field>
            <Field label="Your trade" required>
              <Select id="chaupal-trade" value={form.trade} onChange={(e) => setForm({ ...form, trade: e.target.value })} required>
                <option value="">Choose</option>
                {(labels?.trades || []).map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="District" required>
                <Select id="chaupal-district" value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value, block: "" })} required>
                  <option value="">Choose</option>
                  {districts.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
                </Select>
              </Field>
              <Field label="Block">
                <Select id="chaupal-block" value={form.block} onChange={(e) => setForm({ ...form, block: e.target.value })}>
                  <option value="">Any</option>
                  {blocks.map((b) => <option key={b} value={b}>{b}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Where are you in the loan journey?" required>
              <Select id="chaupal-stage" value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })} required>
                {(labels?.stages || []).map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </Select>
            </Field>
            <Button type="submit" className="w-full" disabled={busy || !form.display_name || !form.trade || !form.district}>{busy ? <Spinner /> : "Join"}</Button>
          </form>
        )}
      </div>
    </div>
  );
}
