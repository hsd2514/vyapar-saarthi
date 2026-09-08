import { useEffect, useRef, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { Button, Badge, Spinner } from "./ui";
import Markdown from "./Markdown";

export default function FeasibilityAdvisorChat({ district, block, businessType }) {
  const { feasibilityChat, feasibilityChatHistory, pushFeasibilityChat, setFeasibilityChatHistory, resetFeasibilityChat } = useAppState();
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);
  const reportKeyRef = useRef(`${district}|${block}|${businessType}`);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [feasibilityChat, thinking]);

  // The conversation is about a specific (district, block, businessType)
  // report - if the entrepreneur goes back and changes any of those, the
  // old conversation would be talking about a report that's no longer on
  // screen, so clear it rather than carrying it over to the new one.
  useEffect(() => {
    const key = `${district}|${block}|${businessType}`;
    if (reportKeyRef.current !== key) {
      reportKeyRef.current = key;
      resetFeasibilityChat();
    }
  }, [district, block, businessType, resetFeasibilityChat]);

  async function send(message) {
    if (!message.trim() || thinking) return;
    setError("");
    setThinking(true);
    pushFeasibilityChat({ role: "user", text: message });
    setInput("");
    try {
      const res = await api.feasibilityChat(message, feasibilityChatHistory, district, block, businessType);
      setFeasibilityChatHistory(res.history);
      pushFeasibilityChat({ role: "agent", text: res.reply_text });
    } catch (e) {
      setError(e.message || "Could not reach the feasibility advisor.");
    } finally {
      setThinking(false);
    }
  }

  const suggestions = [
    "Why does this block read as under-served or competitive?",
    "What if I picked a different block nearby?",
    "Which business category would suit me best here?",
  ];

  return (
    <div className="paper-card rounded-2xl p-5 sm:p-7 flex flex-col h-full min-h-95 max-h-[85vh]">
      <div className="flex items-center justify-between mb-3">
        <p className="font-display text-base font-semibold">Ask Saarthi about this report</p>
        <Badge tone="neutral">Remembers this conversation</Badge>
      </div>

      <div ref={scrollRef} className="flex-1 min-h-50 overflow-y-auto scrollbar-thin space-y-3 pr-1 mb-4">
        {feasibilityChat.length === 0 && !thinking && (
          <div className="space-y-2">
            <p className="text-sm text-ink-faint mb-3">Ask a follow-up, or try one of these - the agent calls the same real data behind this report to answer, including for other blocks or categories you ask about.</p>
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="block w-full text-left rounded-lg border border-line px-3 py-2 text-sm text-ink-soft hover:border-pine/50 hover:bg-pine-tint/30 transition"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {feasibilityChat.map((entry, i) => (
          <div key={i} className={`flex ${entry.role === "agent" ? "justify-start" : "justify-end"}`}>
            <div
              className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                entry.role === "agent" ? "bg-pine-tint text-ink border border-pine/20" : "bg-paper-dim text-ink border border-line"
              }`}
            >
              {entry.role === "agent" ? <Markdown>{entry.text}</Markdown> : entry.text}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="flex justify-start">
            <div className="rounded-xl px-4 py-2.5 text-sm bg-pine-tint border border-pine/20 flex items-center gap-2 text-ink-soft">
              <Spinner className="text-pine" /> Checking the data...
            </div>
          </div>
        )}
      </div>

      {error && <div className="mb-3 rounded-lg border border-clay/30 bg-clay-tint px-3.5 py-2.5 text-sm text-[#7a1f28]">{error}</div>}

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Ask about this block, competitors, pricing..."
          className="flex-1 rounded-lg border border-line-strong bg-paper px-3.5 py-2.5 text-sm outline-none focus:border-pine focus:ring-4 focus:ring-pine/10"
        />
        <Button variant="secondary" onClick={() => send(input)} disabled={thinking}>
          Send
        </Button>
      </div>
    </div>
  );
}
