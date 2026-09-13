import { useEffect, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { formatINR } from "../data/constants";
import { Badge, Field, FigureTile, NumberInput, Section, Select, Spinner, TileGrid } from "./ui";

/**
 * Worst-quarter stress test.
 *
 * The repayment schedule above assumes income is the same every month. It
 * is not. This panel lays the trade's seasonal pattern over the calendar
 * months the loan runs through, shows the quarter where the instalment is
 * bigger than what the business clears, and turns that into two numbers:
 * how much to keep aside, and how many months each named shock could be
 * survived. Every figure comes from POST /api/stress-test (stress_test.py).
 */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const VERDICT = {
  comfortable: { tone: "good", label: "Every quarter covers its instalment" },
  tight: { tone: "gold", label: "One lean quarter needs a cushion" },
  at_risk: { tone: "clay", label: "The lean quarter cannot pay the instalment" },
};

export default function StressTestPanel({ structuring, schedule }) {
  const { profile, operations, updateOperations } = useAppState();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const revenue = Number(operations.expectedBusinessRevenue) || 0;
  const cost = Number(operations.monthlyOperationalCost) || 0;
  const startMonth = Number(operations.loanStartMonth) || new Date().getMonth() + 1;
  const scheme = structuring?.scheme;

  useEffect(() => {
    if (!scheme || !profile.businessType || revenue <= 0) {
      setResult(null);
      return;
    }
    setLoading(true);
    setError("");
    api
      .stressTest({
        business_type: profile.businessType,
        principal: structuring.max_loan_amount,
        annual_rate_pct: scheme.annual_rate_pct,
        tenure_months: scheme.tenure_months,
        moratorium_months: scheme.moratorium_months,
        avg_monthly_revenue: revenue,
        monthly_operating_cost: cost,
        start_month: startMonth,
        capitalise_moratorium_interest: Boolean(operations.capitaliseMoratoriumInterest),
      })
      .then(setResult)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [scheme, structuring, profile.businessType, revenue, cost, startMonth, operations.capitaliseMoratoriumInterest]);

  if (!scheme || !schedule) return null;

  return (
    <Section
      title="Can you pay it in the lean months?"
      aside={result ? <Badge tone={VERDICT[result.verdict].tone}>{VERDICT[result.verdict].label}</Badge> : null}
    >
      <p className="text-[17px] text-ink-soft mb-5 leading-relaxed max-w-2xl">
        The plan above assumes you earn the same every month. Nobody does. Tell us roughly what comes in, and we will check each instalment
        against the season it falls in.
      </p>

      <div className="grid sm:grid-cols-2 gap-5 mb-6">
        <Field label="Money coming in each month, on average" hint="Sales before any costs - a normal month, not your best">
          <NumberInput
            id="stress-revenue"
            prefix="Rs"
            min="0"
            value={operations.expectedBusinessRevenue}
            onChange={(e) => updateOperations({ expectedBusinessRevenue: e.target.value })}
          />
        </Field>
        <Field label="Month the loan will start" hint="So each instalment lands in the right season">
          <Select id="stress-start-month" value={startMonth} onChange={(e) => updateOperations({ loanStartMonth: e.target.value })}>
            {MONTHS.map((m, i) => (
              <option key={m} value={i + 1}>{m}</option>
            ))}
          </Select>
        </Field>
      </div>

      {revenue <= 0 && <p className="text-[16px] text-ink-soft">Enter what you expect to earn in a month and the check will run.</p>}
      {loading && !result && <div className="flex items-center gap-3 py-4 text-ink-soft"><Spinner className="text-pine" /> Checking the seasons...</div>}
      {error && <p className="rounded-xl border-2 border-clay/30 bg-clay-tint px-4 py-3 text-[16px] text-clay">Could not run the check right now.</p>}

      {result && (
        <div className="space-y-6">
          <Headline result={result} />

          <QuarterBars quarters={result.quarters} />

          <TileGrid min="200px">
            <FigureTile
              label="Keep this much aside"
              value={formatINR(result.reserve_target)}
              note={result.reserve_target > 0 ? "so the lean quarter can pay its instalment" : "nothing extra needed for the seasons"}
              tone={result.reserve_target > 0 ? "gold" : "good"}
              emphasis
            />
            {result.monthly_saving_during_moratorium != null && (
              <FigureTile
                label={`Save every month during the ${result.inputs.moratorium_months}-month free period`}
                value={formatINR(result.monthly_saving_during_moratorium)}
                note="and the shortfall disappears"
                tone={result.monthly_saving_during_moratorium > 0 ? "accent" : "neutral"}
              />
            )}
            <FigureTile
              label="Left over in an average month"
              value={formatINR(result.avg_monthly_surplus_after_emi)}
              note="after running costs and the instalment"
              tone={result.avg_monthly_surplus_after_emi < 0 ? "clay" : "neutral"}
            />
          </TileGrid>

          <Shocks shocks={result.shocks} reserve={result.reserve_target} />

          <p className="pt-4 border-t border-line text-[14.5px] text-ink-soft leading-relaxed">
            <strong className="text-ink">How the seasons were set:</strong> {result.season.reasoning} This is a documented assumption for your trade,
            not measured data - your own experience of lean months beats it. {result.assumption}
          </p>
        </div>
      )}
    </Section>
  );
}

function Headline({ result }) {
  const { first_instalment_quarter: first, worst_quarter: worst, inputs } = result;
  if (!first) return null;
  const emi = inputs.monthly_emi;
  const firstIsWorst = worst && worst.quarter === first.quarter;
  return (
    <div className={`rounded-2xl border-2 p-5 text-[17px] leading-relaxed ${worst?.shortfall > 0 ? "border-gold/40 bg-gold-tint" : "border-good/30 bg-good-tint"}`}>
      Your first instalment of <strong>{formatINR(emi)}</strong> a month lands in <strong>{first.label}</strong>
      {firstIsWorst ? ", your leanest quarter" : ""}.{" "}
      {worst?.shortfall > 0 ? (
        <>
          In <strong>{worst.label}</strong> the business clears {formatINR(Math.max(0, worst.surplus_before_emi))} but owes {formatINR(worst.amount_due)} -{" "}
          <strong>{formatINR(worst.shortfall)} short</strong>.
          {result.monthly_saving_during_moratorium > 0 && (
            <> Save {formatINR(result.monthly_saving_during_moratorium)} a month during the free period and it is covered.</>
          )}
        </>
      ) : (
        <>Even in <strong>{worst.label}</strong>, the leanest quarter, the business clears enough to pay.</>
      )}
    </div>
  );
}

function QuarterBars({ quarters }) {
  const max = Math.max(...quarters.map((q) => Math.max(q.surplus_before_emi, q.amount_due, 1)));
  const w = (v) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mb-3 text-[13.5px] text-ink-soft">
        <span className="inline-flex items-center gap-1.5"><span className="h-3 w-4 rounded-sm bg-good" /> What the business clears that quarter</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-3 w-4 rounded-sm bg-pine" /> Instalments due</span>
      </div>
      <ul className="space-y-2.5">
        {quarters.map((q) => (
          <li key={q.quarter} className="grid grid-cols-[76px_1fr] sm:grid-cols-[96px_1fr] gap-3 items-center">
            <span className="text-[15px] text-ink-soft leading-tight">
              <span className="block font-semibold text-ink">{q.label}</span>
              <span className="text-[12.5px]">{q.season_index >= 1.1 ? "peak" : q.season_index <= 0.9 ? "lean" : "normal"}</span>
            </span>
            <div className="space-y-1">
              <div className="h-4 rounded bg-paper-dim overflow-hidden">
                <div className={`h-full rounded ${q.surplus_before_emi < 0 ? "bg-clay" : "bg-good"}`} style={{ width: w(Math.abs(q.surplus_before_emi)) }} />
              </div>
              <div className="h-4 rounded bg-paper-dim overflow-hidden relative">
                {q.is_moratorium_only ? (
                  <span className="absolute inset-0 flex items-center px-2 text-[12px] font-semibold text-gold">free period</span>
                ) : (
                  <div className="h-full rounded bg-pine" style={{ width: w(q.amount_due) }} />
                )}
              </div>
              <p className="text-[13px] text-ink-soft figure">
                {formatINR(q.surplus_before_emi)} clears · {q.is_moratorium_only ? "nothing due" : `${formatINR(q.amount_due)} due`}
                {q.shortfall > 0 && <span className="text-clay font-semibold"> · {formatINR(q.shortfall)} short</span>}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Shocks({ shocks, reserve }) {
  return (
    <div>
      <h3 className="font-display text-xl font-bold text-ink tracking-tight mb-1">If something goes wrong</h3>
      <p className="text-[15px] text-ink-soft mb-3 max-w-2xl">
        Each one is timed for the worst moment - the month your first instalment is due. "Months" is how long the money lasts from the loan start.
      </p>
      <ul className="grid gap-3 sm:grid-cols-3">
        {shocks.map((s) => {
          const ok = s.survives_with_base_reserve;
          return (
            <li key={s.id} className={`rounded-xl border-2 p-4 ${ok ? "border-good/30 bg-good-tint" : "border-clay/30 bg-clay-tint"}`}>
              <p className="text-[16px] font-semibold text-ink leading-snug">{s.label}</p>
              <p className="text-[13.5px] text-ink-soft mt-1 leading-snug">{s.detail}</p>
              <dl className="mt-3 space-y-1 text-[14.5px]">
                <div className="flex justify-between gap-2"><dt className="text-ink-soft">With nothing aside</dt><dd className="figure font-semibold text-ink">{s.survival_months_without_reserve == null ? "survives" : `${s.survival_months_without_reserve} months`}</dd></div>
                <div className="flex justify-between gap-2"><dt className="text-ink-soft">With {formatINR(reserve)} aside</dt><dd className="figure font-semibold text-ink">{ok ? "survives" : `${s.survival_months_with_reserve} months`}</dd></div>
                {!ok && <div className="flex justify-between gap-2"><dt className="text-ink-soft">Extra needed</dt><dd className="figure font-semibold text-clay">{formatINR(s.extra_reserve_over_base)}</dd></div>}
              </dl>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
