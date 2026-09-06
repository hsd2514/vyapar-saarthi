import Stepper from "./Stepper";

export default function Layout({ children }) {
  return (
    <div className="min-h-dvh grid grid-rows-[auto_1fr] lg:grid-rows-1 lg:grid-cols-[272px_1fr]">
      <Stepper />
      <div className="flex flex-col min-w-0">
        <main className="flex-1 w-full max-w-6xl mx-auto px-5 sm:px-8 lg:px-12 py-8 sm:py-12 lg:py-14">{children}</main>
        <footer className="no-print border-t border-line py-6">
          <div className="max-w-6xl mx-auto px-5 sm:px-8 lg:px-12 text-[15px] text-ink-soft lg:hidden">
            Voice collects your details. Every financial figure is still a deterministic Python calculation, never an LLM guess.
          </div>
        </footer>
      </div>
    </div>
  );
}
