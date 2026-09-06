import { useNavigate, useLocation } from "react-router-dom";
import { useAppState } from "../context/AppContext";

export const STEPS = [
  { path: "/intake", label: "Voice Intake", short: "1" },
  { path: "/feasibility", label: "Feasibility Report", short: "2" },
  { path: "/financial-plan", label: "Financial Plan", short: "3" },
  { path: "/repayment-plan", label: "Repayment Plan", short: "4" },
  { path: "/summary", label: "Summary", short: "5" },
];

export default function Stepper() {
  const location = useLocation();
  const navigate = useNavigate();
  const { furthestStep } = useAppState();
  const currentIndex = STEPS.findIndex((s) => s.path === location.pathname);

  const stepState = (idx) => ({
    isActive: idx === currentIndex,
    isDone: idx < currentIndex || idx <= furthestStep,
    isReachable: idx <= furthestStep || idx <= currentIndex,
  });

  return (
    <>
      {/* Desktop: persistent left rail */}
      <nav
        aria-label="Progress"
        className="no-print hidden lg:flex lg:flex-col lg:sticky lg:top-0 lg:h-dvh border-r border-line bg-paper-dim/40 px-6 py-8"
      >
        <div className="flex items-center gap-2.5 mb-10">
          <div className="h-9 w-9 rounded-lg bg-pine text-paper flex items-center justify-center font-display font-semibold text-lg shrink-0">व</div>
          <div className="leading-tight">
            <p className="font-display font-semibold text-ink text-[16px] tracking-tight">Vyapar Saarthi</p>
            <p className="text-[10.5px] text-ink-faint font-mono tracking-wide">CREDIT-READINESS ASSISTANT</p>
          </div>
        </div>

        <ol className="flex-1 flex flex-col gap-1">
          {STEPS.map((step, idx) => {
            const { isActive, isDone, isReachable } = stepState(idx);
            return (
              <li key={step.path} className="relative">
                {idx < STEPS.length - 1 && (
                  <span
                    aria-hidden="true"
                    className={`absolute left-[19px] top-9 h-[calc(100%-4px)] w-px ${idx < currentIndex || idx < furthestStep ? "bg-pine/40" : "bg-line"}`}
                  />
                )}
                <button
                  type="button"
                  disabled={!isReachable}
                  onClick={() => isReachable && navigate(step.path)}
                  className={`relative z-10 w-full flex items-center gap-3 rounded-lg px-2.5 py-2 text-left transition ${
                    isReachable ? "cursor-pointer hover:bg-pine-tint/40" : "cursor-not-allowed opacity-40"
                  }`}
                >
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-semibold font-mono transition-all ${
                      isActive
                        ? "bg-pine text-paper border-pine shadow-[0_0_0_3px_rgba(193,68,14,0.16)]"
                        : isDone
                        ? "bg-pine-tint text-pine-dim border-pine/40"
                        : "bg-paper text-ink-faint border-line-strong"
                    }`}
                  >
                    {step.short}
                  </span>
                  <span className={`text-sm font-medium tracking-tight ${isActive ? "text-ink" : isDone ? "text-ink-soft" : "text-ink-faint"}`}>{step.label}</span>
                </button>
              </li>
            );
          })}
        </ol>

        <p className="text-[11px] text-ink-faint leading-relaxed border-t border-line pt-4 mt-6">
          Voice collects your details. Every financial figure is still a deterministic Python calculation, never an LLM guess.
        </p>
      </nav>

      {/* Mobile: condensed top bar */}
      <nav aria-label="Progress" className="no-print lg:hidden border-b border-line bg-paper/95 backdrop-blur sticky top-0 z-20">
        <div className="flex items-center gap-2.5 px-4 py-3 border-b border-line">
          <div className="h-7 w-7 rounded-md bg-pine text-paper flex items-center justify-center font-display font-semibold text-sm shrink-0">व</div>
          <p className="font-display font-semibold text-ink text-[15px] tracking-tight">Vyapar Saarthi</p>
        </div>
        <ol className="flex items-stretch justify-between px-4 py-2.5">
          {STEPS.map((step, idx) => {
            const { isActive, isDone, isReachable } = stepState(idx);
            return (
              <li key={step.path} className="flex flex-1 items-center last:flex-none">
                <button
                  type="button"
                  disabled={!isReachable}
                  onClick={() => isReachable && navigate(step.path)}
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold font-mono transition-all ${
                    isReachable ? "cursor-pointer" : "cursor-not-allowed opacity-40"
                  } ${
                    isActive
                      ? "bg-pine text-paper border-pine"
                      : isDone
                      ? "bg-pine-tint text-pine-dim border-pine/40"
                      : "bg-transparent text-ink-faint border-line-strong"
                  }`}
                >
                  {step.short}
                </button>
                {idx < STEPS.length - 1 && <span className={`mx-1.5 h-px flex-1 ${idx < currentIndex || idx < furthestStep ? "bg-pine/40" : "bg-line"}`} />}
              </li>
            );
          })}
        </ol>
      </nav>
    </>
  );
}
