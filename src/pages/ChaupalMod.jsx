import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "@phosphor-icons/react";
import { useForum } from "../context/ForumContext";
import { forumApi } from "../lib/forumApi";
import { Card, Button, Section, Spinner } from "../components/ui";
import { Who, TopicChip, PostTypeChip, timeAgo } from "../components/chaupal/bits";

/**
 * Moderator queue: held posts and replies (newcomers' first posts, anything
 * with fee/guarantee language, anything two members flagged), connect
 * requests to broker, and questions no verified expert has answered in
 * 48 hours. Plain and fast - a moderator should clear this in minutes.
 */
export default function ChaupalMod() {
  const { member } = useForum();
  const [queue, setQueue] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    forumApi.modQueue().then(setQueue).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (member?.role === "moderator") load();
  }, [member, load]);

  if (!member || member.role !== "moderator") {
    return (
      <Card className="max-w-3xl text-center py-14">
        <p className="text-[17px] text-ink-soft mb-5">Moderators only.</p>
        <Link to="/chaupal" className="text-pine-dim font-semibold underline underline-offset-4">Back to Chaupal</Link>
      </Card>
    );
  }
  if (error) return <Card className="border-clay/30 bg-clay-tint text-clay">{error}</Card>;
  if (!queue) return <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft"><Spinner className="text-pine" /> Loading...</Card>;

  const act = (fn) => async (...args) => {
    await fn(...args).catch((e) => setError(e.message));
    load();
  };
  const onThread = act(forumApi.modThread);
  const onReply = act(forumApi.modReply);
  const onConnect = act(forumApi.modConnect);

  return (
    <div className="max-w-3xl">
      <Link to="/chaupal" className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-ink-soft hover:text-ink mb-4"><ArrowLeft size={18} /> Chaupal</Link>
      <h1 className="font-display text-3xl font-bold text-ink tracking-tight flex items-center gap-2 mb-6"><ShieldCheck size={30} weight="fill" className="text-pine" /> Moderation</h1>

      <Section title={`Held posts (${queue.threads.length})`}>
        {queue.threads.length === 0 && <p className="text-ink-soft">Nothing waiting.</p>}
        <ul className="space-y-3">
          {queue.threads.map((t) => (
            <li key={t.id} className="paper-card rounded-2xl p-4">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <PostTypeChip type={t.post_type} /><TopicChip topic={t.topic} />
                <span className="text-[13px] font-semibold text-clay">{t.held_reason === "scam_signals" ? "fee / guarantee language" : t.held_reason === "flagged" ? "flagged by members" : "new member"}</span>
                <span className="ml-auto text-[13px] text-ink-faint">{timeAgo(t.created_at)}</span>
              </div>
              <p className="font-semibold text-ink text-[17px]">{t.title}</p>
              <p className="text-[15px] text-ink-soft mt-1 whitespace-pre-line">{t.body}</p>
              <div className="mt-2"><Who author={t.author} /></div>
              <div className="mt-3 flex gap-2">
                <Button onClick={() => onThread(t.id, "approve")} className="py-2 px-4 text-[15px]">Publish</Button>
                <Button variant="secondary" onClick={() => onThread(t.id, "reject")} className="py-2 px-4 text-[15px]">Reject</Button>
                <Link to={`/chaupal/t/${t.id}`} className="ml-auto self-center text-[14px] text-pine-dim underline underline-offset-4">Open</Link>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={`Held replies (${queue.replies.length})`} className="mt-8">
        {queue.replies.length === 0 && <p className="text-ink-soft">Nothing waiting.</p>}
        <ul className="space-y-3">
          {queue.replies.map((r) => (
            <li key={r.id} className="paper-card rounded-2xl p-4">
              <p className="text-[15px] text-ink whitespace-pre-line">{r.body}</p>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2"><Who author={r.author} /><Link to={`/chaupal/t/${r.thread_id}`} className="text-[14px] text-pine-dim underline underline-offset-4">Thread</Link></div>
              <div className="mt-3 flex gap-2">
                <Button onClick={() => onReply(r.id, "approve")} className="py-2 px-4 text-[15px]">Publish</Button>
                <Button variant="secondary" onClick={() => onReply(r.id, "reject")} className="py-2 px-4 text-[15px]">Reject</Button>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={`Connect requests (${queue.connect_requests.length})`} className="mt-8">
        {queue.connect_requests.length === 0 && <p className="text-ink-soft">None pending.</p>}
        <ul className="space-y-3">
          {queue.connect_requests.map((c) => (
            <li key={c.id} className="paper-card rounded-2xl p-4">
              <p className="text-[15px] text-ink">{c.message}</p>
              <p className="text-[13px] text-ink-faint mt-1">Introduce requester and poster by phone, then mark it.</p>
              <div className="mt-3 flex gap-2">
                <Button onClick={() => onConnect(c.id, "approve")} className="py-2 px-4 text-[15px]">Introduced</Button>
                <Button variant="secondary" onClick={() => onConnect(c.id, "decline")} className="py-2 px-4 text-[15px]">Decline</Button>
                <Link to={`/chaupal/t/${c.thread_id}`} className="ml-auto self-center text-[14px] text-pine-dim underline underline-offset-4">Thread</Link>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={`Questions with no expert answer for 48h (${queue.unanswered_over_48h.length})`} className="mt-8">
        {queue.unanswered_over_48h.length === 0 && <p className="text-ink-soft">All answered.</p>}
        <ul className="space-y-2">
          {queue.unanswered_over_48h.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center gap-2 text-[15px]">
              <TopicChip topic={t.topic} />
              <Link to={`/chaupal/t/${t.id}`} className="text-ink font-semibold underline underline-offset-4">{t.title}</Link>
              <span className="text-ink-faint">{timeAgo(t.created_at)}</span>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
