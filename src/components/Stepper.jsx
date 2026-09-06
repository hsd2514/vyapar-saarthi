import { useNavigate, useLocation } from "react-router-dom";
import { Microphone, Storefront, Coins, CalendarCheck, FileText, Check } from "@phosphor-icons/react";
import { useAppState } from "../context/AppContext";

/* Step names are what the user is actually doing, in plain words - not the
   module names from the spec. "Repayment Plan" means nothing to someone
   who has never taken a loan; "What you'll pay back" does. */
export const STEPS = [
  { path: "/intake", label: "Tell us about you", short: "1", Icon: Microphone },
  { path: "/feasibility", label: "Will it work here?", short: "2", Icon: Storefront },
  { path: "/financial-plan", label: "How much you can get", short: "3", Icon: Coins },
  { path: "/repayment-plan", label: "What you'll pay back", short: "4", Icon: CalendarCheck },
  { path: "/summary", label: "Your plan", short: "5", Icon: FileText },
];

export default function Stepper() {
  const location = useLocation();
  const navigate = useNavigate();
  const { furthestStep } = useAppState();
  const currentIndex = STEPS.findIndex((s) => s.path === location.pathname);

  const stepState = (idx) => ({
    isActive: idx === currentIndex,
    isDone: idx < currentIndex || idx <= furthestStep,
    isComplete: idx < currentIndex,
    isReachable: idx <= furthestStep || idx <= currentIndex,
  });

  return (
    <>
      {/* Desktop: persistent left rail */}
      <nav aria-label="Your progress" className="no-print hidden lg:flex lg:flex-col lg:sticky lg:top-0 lg:h-dvh border-r border-line bg-white px-5 py-7">
        <div className="flex items-center gap-3 mb-8">
          <div className="h-11 w-11 rounded-xl bg-pine text-white flex items-center justify-center font-display font-bold text-xl shrink-0">व</div>
          <div className="leading-tight">
            <p className="font-display font-bold text-ink text-lg tracking-tight">Vyapar Saarthi</p>
            <p className="text-sm text-ink-soft">Plan your business</p>
          </div>
        </div>

        <ol className="flex-1 flex flex-col gap-1.5">
          {STEPS.map((step, idx) => {
            const { isActive, isDone, isComplete, isReachable } = stepState(idx);
            const { Icon } = step;
            return (
              <li key={step.path}>
                <button
                  type="button"
                  disabled={!isReachable}
                  onClick={() => isReachable && navigate(step.path)}
                  aria-current={isActive ? "step" : undefined}
                  className={`w-full flex items-center gap-3 rounded-xl px-3 py-3 text-left transition ${
                    isActive
                      ? "bg-pine text-white"
                      : isReachable
                      ? "text-ink hover:bg-paper-dim cursor-pointer"
                      : "text-ink-faint opacity-55 cursor-not-allowed"
                  }`}
                >
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
                      isActive ? "bg-white/20 text-white" : isComplete ? "bg-good text-white" : isDone ? "bg-pine-tint text-pine" : "bg-paper-dim text-ink-faint"
                    }`}
                  >
                    {isComplete ? <Check size={18} weight="bold" /> : <Icon size={19} weight={isActive ? "fill" : "regular"} />}
                  </span>
                  <span className="text-[15px] font-semibold leading-tight">{step.label}</span>
                </button>
              </li>
            );
          })}
        </ol>

        <p className="text-sm text-ink-soft leading-relaxed border-t border-line pt-4 mt-5">
          Every rupee shown here is worked out by a fixed formula, so a bank can check it.
        </p>
      </nav>

      {/* Mobile: compact top bar showing where you are, in words */}
      <nav aria-label="Your progress" className="no-print lg:hidden border-b border-line bg-white sticky top-0 z-20">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="h-9 w-9 rounded-lg bg-pine text-white flex items-center justify-center font-display font-bold shrink-0">व</div>
          <p className="font-display font-bold text-ink text-base tracking-tight">Vyapar Saarthi</p>
          <span className="ml-auto text-sm text-ink-soft">
            Step {Math.max(1, currentIndex + 1)} of {STEPS.length}
          </span>
        </div>
        <div className="px-4 pb-3">
          <p className="text-[15px] font-semibold text-ink mb-2">{STEPS[Math.max(0, currentIndex)]?.label}</p>
          <div className="flex gap-1.5">
            {STEPS.map((step, idx) => {
              const { isActive, isDone } = stepState(idx);
              return <span key={step.path} className={`h-1.5 flex-1 rounded-full ${isActive ? "bg-pine" : isDone ? "bg-pine/35" : "bg-paper-dim"}`} />;
            })}
          </div>
        </div>
      </nav>
    </>
  );
}
