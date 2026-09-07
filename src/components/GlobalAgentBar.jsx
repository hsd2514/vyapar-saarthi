/**
 * GlobalAgentBar — a persistent "Ask Saarthi" entry point visible on every
 * screen, not just the two pages that happened to embed a chat panel.
 * Floats bottom-right, opens a slide-over with the agent that actually has
 * context for wherever the user currently is:
 *   - on the Feasibility Report itself, use the feasibility advisor (it
 *     needs district/block/business_type, which that page already has)
 *   - everywhere else, use the financial/scheme advisor (self-contained -
 *     it only needs numbers the user gives it in the conversation)
 */
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import FeasibilityAdvisorChat from "./FeasibilityAdvisorChat";
import FinancialAdvisorChat from "./FinancialAdvisorChat";

export default function GlobalAgentBar() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { profile } = useAppState();

  const canUseFeasibilityChat =
    location.pathname === "/feasibility" && profile.district && profile.block && profile.businessType;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Ask Saarthi"
        className={`no-print fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full bg-pine px-5 py-3.5 text-white shadow-lg shadow-pine/25 transition hover:bg-pine-dim ${
          open ? "scale-0 opacity-0 pointer-events-none" : "scale-100 opacity-100"
        }`}
      >
        <ChatIcon />
        <span className="text-[15px] font-semibold">Ask Saarthi</span>
      </button>

      {open && (
        <div className="no-print fixed inset-0 z-40 flex items-end justify-end sm:items-stretch">
          <button
            type="button"
            aria-label="Close"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-ink/30 backdrop-blur-[1px]"
          />
          <div className="relative w-full sm:w-[420px] sm:max-w-[92vw] h-[85vh] sm:h-full bg-paper sm:border-l border-line shadow-2xl flex flex-col rise-in">
            <div className="flex items-center justify-between px-4 py-3 border-b border-line bg-white shrink-0">
              <p className="font-display font-bold text-ink">Ask Saarthi</p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close chat"
                className="h-9 w-9 flex items-center justify-center rounded-full text-ink-soft hover:bg-paper-dim transition"
              >
                <CloseIcon />
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4">
              {canUseFeasibilityChat ? (
                <FeasibilityAdvisorChat district={profile.district} block={profile.block} businessType={profile.businessType} />
              ) : (
                <FinancialAdvisorChat />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ChatIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
