import { useNavigate, useLocation } from "react-router-dom";
import { useAppState } from "../context/AppContext";

export const STEPS = [
  { path: "/intake", label: "Voice Intake", short: "1" },
  { path: "/calculators", label: "Calculators", short: "2" },
  { path: "/viability", label: "Viability Score", short: "3" },
  { path: "/schemes", label: "Scheme Matching", short: "4" },
  { path: "/summary", label: "Summary", short: "5" },
];

export default function Stepper() {
  const location = useLocation();
  const navigate = useNavigate();
  const { furthestStep } = useAppState();
  const currentIndex = STEPS.findIndex((s) => s.path === location.pathname);

  return (
    <nav className="no-print border-b border-line bg-paper/95 backdrop-blur sticky top-0 z-20">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <ol className="flex items-stretch justify-between py-3 sm:py-4">
          {STEPS.map((step, idx) => {
            const isActive = idx === currentIndex;
            const isDone = idx < currentIndex || idx <= furthestStep;
            const isReachable = idx <= furthestStep || idx <= currentIndex;
            return (
              <li key={step.path} className="flex flex-1 items-center last:flex-none">
                <button
                  type="button"
                  disabled={!isReachable}
                  onClick={() => isReachable && navigate(step.path)}
                  className={["group flex items-center gap-2 rounded-full px-1.5 py-1 sm:px-2 transition-colors", isReachable ? "cursor-pointer" : "cursor-not-allowed opacity-40"].join(" ")}
                >
                  <span
                    className={[
                      "flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-full border text-xs sm:text-sm font-semibold font-mono transition-all",
                      isActive
                        ? "bg-pine text-paper border-pine shadow-[0_0_0_3px_rgba(15,169,104,0.18)]"
                        : isDone
                        ? "bg-pine-tint text-pine-dim border-pine/40"
                        : "bg-transparent text-ink-faint border-line-strong",
                    ].join(" ")}
                  >
                    {step.short}
                  </span>
                  <span className={["hidden sm:inline text-sm font-medium tracking-tight", isActive ? "text-ink" : isDone ? "text-ink-soft" : "text-ink-faint"].join(" ")}>{step.label}</span>
                </button>
                {idx < STEPS.length - 1 && <span className={["mx-1.5 sm:mx-3 h-px flex-1", idx < currentIndex || idx < furthestStep ? "bg-pine/40" : "bg-line"].join(" ")} />}
              </li>
            );
          })}
        </ol>
      </div>
    </nav>
  );
}
