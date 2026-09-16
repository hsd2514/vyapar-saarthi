import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ChatCircleText, SealCheck, Microphone, Plus, ShieldCheck } from "@phosphor-icons/react";
import { useForum } from "../context/ForumContext";
import { useAppState } from "../context/AppContext";
import { forumApi } from "../lib/forumApi";
import { Card, PageHeader, Button, Spinner } from "../components/ui";
import { Who, TopicChip, PostTypeChip, timeAgo } from "../components/chaupal/bits";
import ComposeDialog from "../components/chaupal/ComposeDialog";
import CrowdPanel from "../components/chaupal/CrowdPanel";

/**
 * Chaupal home: the list. Designed for listening, not posting - filters
 * come first, the compose button second, and the default view is "people
 * in my trade" rather than everything. Reading needs no sign-in.
 */
export default function Chaupal() {
  const { member, labels, labelsError, openSignIn, signOut } = useForum();
  const { profile, t } = useAppState();
  const [params, setParams] = useSearchParams();
  const [threads, setThreads] = useState(null);
  const [error, setError] = useState("");
  const [composeOpen, setComposeOpen] = useState(false);

  // Filters live in the URL so a filtered view is shareable and survives
  // navigating into a thread and back.
  const filters = useMemo(
    () => ({
      trade: params.get("trade") ?? (member?.trade || profile.businessType || ""),
      topic: params.get("topic") || "",
      stage: params.get("stage") || "",
      district: params.get("district") ?? (member?.district || profile.district || ""),
      post_type: params.get("post_type") || "",
    }),
    [params, member, profile.businessType, profile.district]
  );

  const setFilter = useCallback(
    (key, value) => {
      const next = new URLSearchParams(params);
      if (value) next.set(key, value);
      else next.set(key, "");
      setParams(next, { replace: true });
    },
    [params, setParams]
  );

  useEffect(() => {
    setThreads(null);
    forumApi
      .listThreads(filters)
      .then((r) => setThreads(r.threads))
      .catch((e) => setError(e.message));
  }, [filters]);

  // Entry from the feasibility / financial pages: ?compose=question&topic=...
  const composeInitial = useMemo(
    () => ({ post_type: params.get("compose") || "question", topic: params.get("topic") || "", title: params.get("title") || "" }),
    [params]
  );
  useEffect(() => {
    if (params.get("compose")) setComposeOpen(true);
  }, [params]);

  function closeCompose() {
    setComposeOpen(false);
    if (params.get("compose")) {
      const next = new URLSearchParams(params);
      next.delete("compose");
      next.delete("title");
      setParams(next, { replace: true });
    }
  }

  const trades = labels?.trades || [];
  const topics = labels?.topics || [];
  const stages = labels?.stages || [];
  const districts = labels?.districts || [];
  const postTypes = labels?.post_types || [];

  return (
    <div className="max-w-4xl">
      <PageHeader eyebrow={t("chaupal.eyebrow")} title={t("chaupal.title")} description={t("chaupal.description")} />

      <div className="flex flex-wrap items-center gap-2 mb-5">
        <Button onClick={() => (member ? setComposeOpen(true) : openSignIn(() => setComposeOpen(true)))}>
          <Plus size={20} weight="bold" /> Ask or share
        </Button>
        <Button variant="secondary" onClick={() => setComposeOpen(true)} className="hidden sm:inline-flex">
          <Microphone size={20} weight="fill" /> Speak it
        </Button>
        <div className="ml-auto flex items-center gap-3 text-[15px] text-ink-soft">
          {member ? (
            <>
              <span className="hidden sm:inline"><Who author={member} compact /></span>
              {member.role === "moderator" && (
                <Link to="/chaupal/mod" className="inline-flex items-center gap-1 font-semibold text-pine-dim underline underline-offset-4"><ShieldCheck size={16} /> Moderate</Link>
              )}
              <button type="button" onClick={signOut} className="underline underline-offset-4">Sign out</button>
            </>
          ) : (
            <button type="button" onClick={() => openSignIn()} className="font-semibold text-pine-dim underline underline-offset-4">Sign in</button>
          )}
        </div>
      </div>

      {labelsError && <Card className="border-clay/30 bg-clay-tint text-clay text-[16px] mb-5">Chaupal is not reachable right now. Is the backend running?</Card>}

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5 mb-4">
        <FilterSelect id="f-trade" label="Trade" value={filters.trade} onChange={(v) => setFilter("trade", v)} options={trades} allLabel="All trades" />
        <FilterSelect id="f-district" label="District" value={filters.district} onChange={(v) => setFilter("district", v)} options={districts.map((d) => ({ value: d.key, label: d.label }))} allLabel="All districts" />
        <FilterSelect id="f-topic" label="Topic" value={filters.topic} onChange={(v) => setFilter("topic", v)} options={topics} allLabel="All topics" />
        <FilterSelect id="f-stage" label="Their stage" value={filters.stage} onChange={(v) => setFilter("stage", v)} options={stages} allLabel="Any stage" />
        <FilterSelect id="f-type" label="Kind" value={filters.post_type} onChange={(v) => setFilter("post_type", v)} options={postTypes} allLabel="All kinds" />
      </div>

      <CrowdPanel trade={filters.trade} district={filters.district} />

      {error && <Card className="border-clay/30 bg-clay-tint text-clay text-[16px]">Could not load posts: {error}</Card>}
      {!threads && !error && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft"><Spinner className="text-pine" /> Loading...</Card>
      )}
      {threads && threads.length === 0 && (
        <Card className="text-center py-12">
          <p className="text-[17px] text-ink-soft mb-4">Nothing here yet for these filters. Widen them, or be the first.</p>
          <Button variant="secondary" onClick={() => { setFilter("topic", ""); setFilter("stage", ""); setFilter("post_type", ""); }}>Show all topics</Button>
        </Card>
      )}

      {threads && threads.length > 0 && (
        <ul className="space-y-3">
          {threads.map((th) => (
            <li key={th.id}>
              <Link to={`/chaupal/t/${th.id}`} className="block paper-card rounded-2xl p-4 sm:p-5 hover:border-pine/50 transition">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <PostTypeChip type={th.post_type} />
                  <TopicChip topic={th.topic} />
                  {th.input_mode === "voice" && <span className="inline-flex items-center gap-1 text-[13px] text-ink-soft"><Microphone size={14} weight="fill" /> spoken</span>}
                  <span className="ml-auto text-[13px] text-ink-faint">{timeAgo(th.created_at)}</span>
                </div>
                <h3 className="font-display text-[19px] sm:text-xl font-bold text-ink tracking-tight leading-snug text-balance">{th.title}</h3>
                <p className="mt-1.5 text-[15px] text-ink-soft leading-snug line-clamp-2">{th.body}</p>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <Who author={th.author} />
                  <span className="inline-flex items-center gap-3 text-[14px] text-ink-soft">
                    <span className="inline-flex items-center gap-1"><ChatCircleText size={16} /> {th.reply_count}</span>
                    {th.expert_answered ? <span className="inline-flex items-center gap-1 text-gold font-semibold"><SealCheck size={16} weight="fill" /> Expert answered</span> : null}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-8 text-[14px] text-ink-soft leading-relaxed max-w-2xl">
        People here are shown as name, trade, place and stage - nothing else. There are no private messages, contact details are removed from posts, and
        posts that mention fees or guarantees are read by a moderator first.
      </p>

      <ComposeDialog open={composeOpen} onClose={closeCompose} initial={composeInitial} />
    </div>
  );
}

function FilterSelect({ id, label, value, onChange, options, allLabel }) {
  return (
    <label className="block">
      <span className="block text-[13px] font-semibold text-ink-soft mb-1">{label}</span>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border-2 border-line-strong bg-white px-3 py-2 text-[15px] text-ink outline-none focus:border-pine focus:ring-4 focus:ring-pine/15"
      >
        <option value="">{allLabel}</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
