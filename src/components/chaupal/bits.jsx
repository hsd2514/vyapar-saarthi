import { SealCheck, Robot, Storefront, MapPin, Flag } from "@phosphor-icons/react";
import { useForum } from "../../context/ForumContext";

/* Small shared pieces for Chaupal screens. Everything identity-related
   goes through <Who/> so the rule "trade + place + stage, nothing else" is
   enforced in exactly one place. */

const TOPIC_TONE = {
  scam: "bg-clay-tint text-clay border-clay/30",
  repayment: "bg-gold-tint text-gold border-gold/40",
};

export function Chip({ children, tone = "neutral", className = "" }) {
  const tones = {
    neutral: "bg-paper-dim text-ink-soft border-line-strong",
    pine: "bg-pine-tint text-pine-dim border-pine/30",
    good: "bg-good-tint text-good-dim border-good/30",
    gold: "bg-gold-tint text-gold border-gold/40",
    clay: "bg-clay-tint text-clay border-clay/30",
  };
  return <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[13px] font-semibold ${tones[tone]} ${className}`}>{children}</span>;
}

export function TopicChip({ topic }) {
  const { lookup } = useForum();
  const cls = TOPIC_TONE[topic] || "bg-pine-tint text-pine-dim border-pine/30";
  return <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[13px] font-semibold ${cls}`}>{lookup.topic[topic] || topic}</span>;
}

export function PostTypeChip({ type }) {
  const { lookup } = useForum();
  const tone = type === "warning" ? "clay" : type === "experience" ? "good" : type === "looking_for" ? "gold" : "neutral";
  return <Chip tone={tone}>{lookup.postType[type] || type}</Chip>;
}

/** The only way a person is described anywhere on the forum. */
export function Who({ author, compact = false }) {
  const { lookup } = useForum();
  if (!author) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[14px] font-semibold text-pine-dim">
        <Robot size={16} weight="fill" /> Saarthi (engine)
      </span>
    );
  }
  const isExpert = author.role === "expert";
  const isMod = author.role === "moderator";
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 text-[14px] text-ink-soft">
      <span className="font-semibold text-ink">{author.display_name}</span>
      {isExpert && (
        <span className="inline-flex items-center gap-1 rounded-md bg-gold-tint text-gold border border-gold/40 px-1.5 py-0.5 text-[12px] font-bold">
          <SealCheck size={13} weight="fill" /> {lookup.expertRole[author.expert_role] || "Verified"}
        </span>
      )}
      {isMod && <span className="rounded-md bg-paper-dim border border-line-strong px-1.5 py-0.5 text-[12px] font-bold">Moderator</span>}
      {!compact && (
        <>
          <span className="inline-flex items-center gap-1"><Storefront size={14} /> {lookup.trade[author.trade] || author.trade}</span>
          <span className="inline-flex items-center gap-1"><MapPin size={14} /> {author.block ? `${author.block}, ` : ""}{lookup.district[author.district] || author.district}</span>
          <span>· {lookup.stage[author.stage] || author.stage}</span>
        </>
      )}
    </span>
  );
}

export function timeAgo(ts) {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  if (s < 30 * 86400) return `${Math.round(s / 86400)} d ago`;
  return new Date(ts * 1000).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function NoFeeNotice() {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border-2 border-clay/30 bg-clay-tint px-4 py-3 text-[15px] text-ink leading-snug">
      <Flag size={20} weight="fill" className="text-clay shrink-0 mt-0.5" />
      <span>
        <strong>No government loan scheme charges a fee before sanction, and none use agents.</strong> Anyone asking for money first is a scam - report the post.
      </span>
    </div>
  );
}
