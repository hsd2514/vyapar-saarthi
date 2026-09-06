export function Card({ children, className = "", ...props }) {
  return (
    <div className={`paper-card rounded-2xl p-5 sm:p-7 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function SectionLabel({ children }) {
  return <p className="text-sm font-semibold text-ink-soft mb-2">{children}</p>;
}

export function PageHeader({ eyebrow, title, description }) {
  return (
    <div className="mb-7 sm:mb-9">
      {eyebrow && <p className="text-sm font-semibold text-pine mb-2">{eyebrow}</p>}
      <h1 className="font-display text-[28px] sm:text-4xl font-bold text-ink tracking-tight text-balance leading-tight">{title}</h1>
      {description && <p className="mt-3 text-ink-soft text-[17px] max-w-2xl leading-relaxed">{description}</p>}
    </div>
  );
}

export function Field({ label, hint, required, children }) {
  return (
    <label className="block">
      <span className="block text-[16px] font-semibold text-ink mb-1.5">
        {label} {required && <span className="text-clay">*</span>}
      </span>
      {hint && <span className="mb-2 block text-[15px] text-ink-soft leading-snug">{hint}</span>}
      {children}
    </label>
  );
}

/* Big, high-contrast, thumb-friendly controls. */
const inputBase =
  "w-full rounded-xl border-2 border-line-strong bg-white px-4 py-3 text-[17px] text-ink placeholder:text-ink-faint outline-none transition focus:border-pine focus:ring-4 focus:ring-pine/15";

export function TextInput(props) {
  return <input className={inputBase} {...props} />;
}

export function Select({ children, ...props }) {
  return (
    <select className={inputBase + " appearance-none bg-white"} {...props}>
      {children}
    </select>
  );
}

export function NumberInput({ prefix, suffix, className = "", ...props }) {
  return (
    <div className="relative">
      {prefix && <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-soft text-[17px] font-semibold">{prefix}</span>}
      <input
        type="number"
        inputMode="decimal"
        className={`${inputBase} figure ${prefix ? "pl-10" : ""} ${suffix ? "pr-20" : ""} ${className}`}
        {...props}
      />
      {suffix && <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-ink-soft text-[15px]">{suffix}</span>}
    </div>
  );
}

export function Checkbox({ label, ...props }) {
  return (
    <label className="flex items-start gap-3 rounded-xl border-2 border-line px-4 py-3 cursor-pointer hover:border-pine/50 hover:bg-pine-tint transition has-checked:border-pine has-checked:bg-pine-tint">
      <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-pine" {...props} />
      <span className="text-[16px] text-ink leading-snug">{label}</span>
    </label>
  );
}

export function Button({ variant = "primary", className = "", children, ...props }) {
  const variants = {
    primary: "bg-pine text-white hover:bg-pine-dim active:scale-[0.99] shadow-sm disabled:bg-ink-faint/40 disabled:cursor-not-allowed disabled:active:scale-100",
    secondary: "bg-white text-ink border-2 border-line-strong hover:border-pine hover:text-pine-dim active:scale-[0.99]",
    ghost: "bg-transparent text-ink-soft hover:text-ink underline underline-offset-4",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-[17px] font-bold tracking-tight transition ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({ tone = "pine", children }) {
  const tones = {
    pine: "bg-pine-tint text-pine-dim border-pine/30",
    good: "bg-good-tint text-good-dim border-good/30",
    gold: "bg-gold-tint text-gold border-gold/40",
    clay: "bg-clay-tint text-clay border-clay/30",
    neutral: "bg-paper-dim text-ink-soft border-line-strong",
  };
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[14px] font-semibold ${tones[tone]}`}>{children}</span>;
}

export function StatRow({ label, value }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5 border-b border-line last:border-b-0">
      <span className="text-[16px] text-ink-soft">{label}</span>
      <span className="figure text-[18px] font-semibold text-ink text-right">{value}</span>
    </div>
  );
}

/* Supporting detail, grouped with a rule and space rather than elevation -
   elevation stays reserved for the one thing a screen is actually about. */
export function Section({ title, aside, children, className = "", ...props }) {
  return (
    <section className={`border-t border-line pt-6 ${className}`} {...props}>
      {(title || aside) && (
        <div className="flex flex-wrap items-baseline justify-between gap-3 mb-4">
          {title && <h2 className="font-display text-xl sm:text-2xl font-bold text-ink tracking-tight">{title}</h2>}
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function TileGrid({ min = "210px", children, className = "" }) {
  return (
    <div className={`grid gap-3 ${className}`} style={{ gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${min}), 1fr))` }}>
      {children}
    </div>
  );
}

export function FigureTile({ label, value, note, tone = "neutral", emphasis = false, className = "" }) {
  const tones = {
    neutral: "border-line bg-white",
    good: "border-good/30 bg-good-tint",
    accent: "border-pine/30 bg-pine-tint",
    gold: "border-gold/35 bg-gold-tint",
    clay: "border-clay/30 bg-clay-tint",
  };
  return (
    <div className={`rounded-xl border-2 p-4 ${tones[tone]} ${className}`}>
      <p className="text-[15px] text-ink-soft mb-2 leading-snug">{label}</p>
      <p className={`figure text-ink font-bold ${emphasis ? "text-[34px] sm:text-[40px]" : "text-[26px]"}`}>{value}</p>
      {note && <p className="mt-2 text-[15px] text-ink-soft leading-snug">{note}</p>}
    </div>
  );
}

export function Spinner({ className = "" }) {
  return <span className={`inline-block h-5 w-5 rounded-full border-2 border-current border-t-transparent animate-spin ${className}`} aria-hidden="true" />;
}
