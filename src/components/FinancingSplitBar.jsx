import { formatINR } from "../data/constants";

/**
 * The single most explanatory visual in this tool: how a small amount of
 * the entrepreneur's own cash unlocks a much larger project.
 *
 * Own margin money is drawn solid; borrowed money is hatched, so "money I
 * have" and "money I owe" are distinguishable at a glance rather than by
 * reading a legend. When a scheme's loan cap bites, the uncovered
 * remainder is drawn as a third, explicitly-labelled segment instead of
 * being quietly dropped - that gap is real money the entrepreneur would
 * still have to find.
 */
export default function FinancingSplitBar({ marginCapital, loanAmount, projectCost }) {
  const margin = Number(marginCapital) || 0;
  const loan = Number(loanAmount) || 0;
  const total = Number(projectCost) || 0;
  if (total <= 0) return null;

  const gap = Math.max(0, total - margin - loan);
  const pct = (v) => (v / total) * 100;

  return (
    <div>
      <div className="mb-4">
        <p className="text-[17px] text-ink-soft">You can start a business worth</p>
        <p className="figure text-[44px] sm:text-[56px] font-bold text-ink mt-1">{formatINR(total)}</p>
      </div>

      <div
        className="flex h-11 w-full overflow-hidden rounded-lg border border-line-strong"
        role="img"
        aria-label={`Financing split: ${formatINR(margin)} your margin money, ${formatINR(loan)} scheme loan${gap > 0 ? `, ${formatINR(gap)} not covered` : ""}`}
      >
        <div
          className="bg-pine transition-[width] duration-700 ease-out"
          style={{ width: `${pct(margin)}%` }}
          title={`Your margin money: ${formatINR(margin)}`}
        />
        <div
          className="hatch-loan border-l border-white/40 transition-[width] duration-700 ease-out"
          style={{ width: `${pct(loan)}%` }}
          title={`Scheme loan: ${formatINR(loan)}`}
        />
        {gap > 0 && (
          <div
            className="bg-paper-dim border-l border-line-strong transition-[width] duration-700 ease-out"
            style={{ width: `${pct(gap)}%` }}
            title={`Not covered: ${formatINR(gap)}`}
          />
        )}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Leg swatch={<span className="h-4 w-4 rounded bg-pine inline-block shrink-0" />} label="Your own money" value={formatINR(margin)} share={`${pct(margin).toFixed(0)}%`} />
        <Leg swatch={<span className="h-4 w-4 rounded hatch-loan inline-block shrink-0" />} label="Loan from the scheme" value={formatINR(loan)} share={`${pct(loan).toFixed(0)}%`} />
        {gap > 0 ? (
          <Leg
            swatch={<span className="h-4 w-4 rounded bg-paper-dim border border-line-strong inline-block shrink-0" />}
            label="You must still arrange"
            value={formatINR(gap)}
            share={`${pct(gap).toFixed(0)}%`}
            warn
          />
        ) : (
          <div className="text-[16px] text-ink-soft self-center leading-snug">
            You put in 10 rupees, the scheme puts in 90.
          </div>
        )}
      </div>
    </div>
  );
}

function Leg({ swatch, label, value, share, warn = false }) {
  return (
    <div className={`rounded-xl border-2 px-4 py-3 ${warn ? "border-clay/30 bg-clay-tint" : "border-line bg-white"}`}>
      <div className="flex items-center gap-2 mb-1.5">
        {swatch}
        <span className="text-[15px] text-ink-soft leading-tight">{label}</span>
        <span className="ml-auto text-[14px] font-semibold text-ink-faint">{share}</span>
      </div>
      <p className={`figure text-[24px] font-bold ${warn ? "text-clay" : "text-ink"}`}>{value}</p>
    </div>
  );
}
