import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { OPERATIONS_BENCHMARKS, formatINR } from "../data/constants";
import { Card, PageHeader, Section, TileGrid, FigureTile, Field, NumberInput, Badge, Spinner } from "../components/ui";
import StepFooter from "../components/StepFooter";

export default function RepaymentPlan() {
  const { profile, operations, updateOperations, markStepReached } = useAppState();
  const navigate = useNavigate();
  const autoFilledFor = useRef(null);

  const [structuring, setStructuring] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [workingCapital, setWorkingCapital] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const benchmark = OPERATIONS_BENCHMARKS[profile.businessType];
    if (!benchmark || autoFilledFor.current === profile.businessType) return;
    autoFilledFor.current = profile.businessType;
    const patch = {};
    Object.keys(benchmark).forEach((key) => {
      if (operations[key] === "" || operations[key] === undefined) patch[key] = String(benchmark[key]);
    });
    if (Object.keys(patch).length) updateOperations(patch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.businessType]);

  useEffect(() => {
    if (!profile.availableMarginCapital) return;
    setLoading(true);
    api
      .financialStructuring(Number(profile.availableMarginCapital))
      .then((s) => {
        setStructuring(s);
        if (!s.scheme) return null;
        return api.repaymentSchedule(s.max_loan_amount, s.scheme.annual_rate_pct, s.scheme.tenure_months, s.scheme.moratorium_months);
      })
      .then((sched) => setSchedule(sched))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profile.availableMarginCapital]);

  useEffect(() => {
    if (!schedule || !operations.monthlyOperationalCost) return;
    api
      .workingCapital(Number(operations.monthlyOperationalCost), Number(operations.inventoryDays) || 0, Number(operations.receivableDays) || 0, schedule.monthly_emi)
      .then(setWorkingCapital)
      .catch((e) => setError(e.message));
  }, [schedule, operations.monthlyOperationalCost, operations.inventoryDays, operations.receivableDays]);

  if (!profile.availableMarginCapital) {
    return (
      <Card className="max-w-3xl text-center py-14">
        <p className="text-[17px] text-ink-soft mb-5">Please finish the earlier steps first.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go back to the first step
        </button>
      </Card>
    );
  }

  const maxQuarterAmount = schedule ? Math.max(...schedule.quarters.map((q) => q.amount_due), 1) : 1;

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Step 4 of 5"
        title="What you'll pay back, and when"
        description="You don't pay anything for the first few months. After that, the same amount every month until the loan is finished."
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Working out your payments...
        </Card>
      )}
      {error && <Card className="border-clay/30 bg-clay-tint text-clay text-[17px] mb-6">Sorry, we could not load this right now. Please check your internet and try again.</Card>}

      {structuring && !structuring.scheme && !loading && (
        <Card className="text-center py-10">
          <p className="text-ink-soft">No scheme matched your amount, so there is nothing to repay yet. Go back and try a different amount.</p>
        </Card>
      )}

      {schedule && (
        <div className="space-y-6">
          <Card className="rise-in">
            <p className="text-[17px] text-ink-soft">You will pay every month</p>
            <p className="figure text-[44px] sm:text-[56px] font-bold text-ink mt-1">{formatINR(schedule.monthly_emi)}</p>
            <p className="text-[17px] text-ink-soft mt-3 mb-6 leading-relaxed">
              But not right away. You pay <b className="text-ink">nothing for the first {schedule.moratorium_months} months</b> while the business gets going. After that, this
              amount every month for {schedule.repayment_months} months.
            </p>

            <TileGrid min="200px">
              <FigureTile label="Loan you take" value={formatINR(schedule.principal)} />
              <FigureTile label="Extra you pay as interest" value={formatINR(schedule.total_interest)} tone="gold" />
              <FigureTile label="Total you give back" value={formatINR(schedule.total_repayment)} note="loan plus interest, over the full time" />
            </TileGrid>

            <p className="mt-7 mb-3 text-[17px] font-semibold text-ink">Every three months, this is what's due</p>
            <div className="space-y-2">
              {schedule.quarters.map((q, i) => (
                <div key={q.quarter} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-[15px] text-ink-soft">Month {i * 3 + 1}-{i * 3 + 3}</span>
                  <div className="flex-1 h-9 relative">
                    {q.is_moratorium_only ? (
                      <div className="h-full w-full flex items-center px-3 text-[15px] font-semibold text-gold border-2 border-dashed border-gold/50 bg-gold-tint rounded-lg">
                        Nothing to pay
                      </div>
                    ) : (
                      <div
                        className="h-full bg-pine rounded-lg flex items-center px-3 text-[15px] font-semibold text-white transition-[width] duration-700 ease-out"
                        style={{ width: `${Math.max(40, (q.amount_due / maxQuarterAmount) * 100)}%`, transitionDelay: `${i * 25}ms` }}
                      >
                        {formatINR(q.amount_due)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <p className="mt-5 pt-5 border-t border-line text-[15px] text-ink-soft leading-relaxed">{schedule.assumption}</p>
          </Card>

          <Section title="Money you need every month to run it" className="rise-in" style={{ "--rise-delay": "100ms" }}>
            <p className="text-[17px] text-ink-soft mb-5 leading-relaxed">
              We've filled in what a business like yours usually spends. Change these if you know your own numbers better.
            </p>
            <div className="grid sm:grid-cols-3 gap-5 mb-6">
              <Field label="Monthly running cost" hint="Rent, stock, helper's pay, electricity">
                <NumberInput prefix="₹" min="0" value={operations.monthlyOperationalCost} onChange={(e) => updateOperations({ monthlyOperationalCost: e.target.value })} />
              </Field>
              <Field label="Days stock sits unsold" hint="From buying it to selling it">
                <NumberInput suffix="days" min="0" value={operations.inventoryDays} onChange={(e) => updateOperations({ inventoryDays: e.target.value })} />
              </Field>
              <Field label="Days to get paid" hint="After the customer takes the goods">
                <NumberInput suffix="days" min="0" value={operations.receivableDays} onChange={(e) => updateOperations({ receivableDays: e.target.value })} />
              </Field>
            </div>

            {workingCapital && (
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="rounded-2xl border-2 border-gold/35 bg-gold-tint p-5">
                  <Badge tone="gold">First {schedule.moratorium_months} months</Badge>
                  <p className="mt-4 figure text-[38px] font-bold text-ink">{formatINR(workingCapital.monthly_cash_needed_during_moratorium)}</p>
                  <p className="text-[16px] text-ink-soft mt-2 leading-snug">a month, just to run the business. No loan payment yet.</p>
                </div>
                <div className="rounded-2xl border-2 border-pine/30 bg-pine-tint p-5">
                  <Badge tone="pine">From month {schedule.moratorium_months + 1}</Badge>
                  <p className="mt-4 figure text-[38px] font-bold text-ink">{formatINR(workingCapital.monthly_cash_needed_after_moratorium)}</p>
                  <p className="text-[16px] text-ink-soft mt-2 leading-snug">
                    a month, because the {formatINR(schedule.monthly_emi)} loan payment starts.
                  </p>
                </div>
              </div>
            )}
          </Section>
        </div>
      )}

      <StepFooter backTo="/financial-plan" nextTo="/summary" nextLabel="See my full plan" onNext={() => markStepReached(4)} />
    </div>
  );
}
