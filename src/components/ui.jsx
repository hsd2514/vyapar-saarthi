export function Card({ children, className = "", ...props }) {
  return (
    <div className={`paper-card rounded-2xl p-5 sm:p-7 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function SectionLabel({ children }) {
  return <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-pine-dim/80 mb-2">{children}</p>;
}

export function PageHeader({ eyebrow, title, description }) {
  return (
    <div className="mb-8 sm:mb-10">
      {eyebrow && <SectionLabel>{eyebrow}</SectionLabel>}
      <h1 className="font-display text-3xl sm:text-4xl font-semibold text-ink tracking-tight text-balance">{title}</h1>
      {description && <p className="mt-2.5 text-ink-soft text-[15px] sm:text-base max-w-2xl leading-relaxed">{description}</p>}
    </div>
  );
}

export function Field({ label, hint, required, children }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-ink mb-1.5">
        {label} {required && <span className="text-clay">*</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-xs text-ink-faint">{hint}</span>}
    </label>
  );
}

const inputBase =
  "w-full rounded-lg border border-line-strong bg-paper px-3.5 py-2.5 text-[15px] text-ink placeholder:text-ink-faint/70 outline-none transition focus:border-pine focus:ring-4 focus:ring-pine/10";

export function TextInput(props) {
  return <input className={inputBase} {...props} />;
}

export function Select({ children, ...props }) {
  return (
    <select className={inputBase + " appearance-none bg-paper"} {...props}>
      {children}
    </select>
  );
}

export function NumberInput({ prefix, suffix, className = "", ...props }) {
  return (
    <div className="relative">
      {prefix && <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint text-[15px]">{prefix}</span>}
      <input type="number" inputMode="decimal" className={`${inputBase} ${prefix ? "pl-10" : ""} ${suffix ? "pr-14" : ""} num ${className}`} {...props} />
      {suffix && <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-ink-faint text-sm">{suffix}</span>}
    </div>
  );
}

export function Checkbox({ label, ...props }) {
  return (
    <label className="flex items-start gap-2.5 rounded-lg border border-line px-3.5 py-2.5 cursor-pointer hover:border-pine/50 hover:bg-pine-tint/30 transition has-checked:border-pine has-checked:bg-pine-tint/50">
      <input type="checkbox" className="mt-0.5 h-4 w-4 shrink-0 accent-[#0fa968]" {...props} />
      <span className="text-sm text-ink leading-snug">{label}</span>
    </label>
  );
}

export function Button({ variant = "primary", className = "", children, ...props }) {
  const variants = {
    primary: "bg-pine text-paper hover:bg-pine-dim shadow-sm disabled:bg-ink-faint/40 disabled:cursor-not-allowed",
    secondary: "bg-transparent text-ink border border-line-strong hover:border-pine hover:text-pine-dim",
    ghost: "bg-transparent text-ink-soft hover:text-ink",
  };
  return (
    <button className={`inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold tracking-tight transition ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function Badge({ tone = "pine", children }) {
  const tones = {
    pine: "bg-pine-tint text-pine-dim border-pine/30",
    gold: "bg-gold-tint text-[#7a5a12] border-gold/40",
    clay: "bg-clay-tint text-[#7a2f14] border-clay/30",
    neutral: "bg-paper-dim text-ink-soft border-line-strong",
  };
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold font-mono ${tones[tone]}`}>{children}</span>;
}

export function StatRow({ label, value, mono = true }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2 border-b border-line last:border-b-0">
      <span className="text-sm text-ink-soft">{label}</span>
      <span className={`text-[15px] font-semibold text-ink ${mono ? "num" : ""}`}>{value}</span>
    </div>
  );
}

export function Spinner({ className = "" }) {
  return (
    <span
      className={`inline-block h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin ${className}`}
      aria-hidden="true"
    />
  );
}
