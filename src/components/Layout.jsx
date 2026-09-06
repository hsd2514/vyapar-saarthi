import Stepper from "./Stepper";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="no-print border-b border-line">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-md bg-pine text-paper flex items-center justify-center font-display font-semibold text-base">व</div>
            <div className="leading-tight">
              <p className="font-display font-semibold text-ink text-[17px] tracking-tight">Vyapar Saarthi</p>
              <p className="text-[11px] text-ink-faint font-mono tracking-wide">VOICE CREDIT-READINESS ASSISTANT</p>
            </div>
          </div>
        </div>
      </header>
      <Stepper />
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 sm:px-6 py-8 sm:py-12">{children}</main>
      <footer className="no-print border-t border-line py-6">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 text-xs text-ink-faint">
          <span>Voice collects your details; every financial figure is still a deterministic Python calculation, never an LLM guess.</span>
        </div>
      </footer>
    </div>
  );
}
