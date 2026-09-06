import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { OPERATIONS_BENCHMARKS, formatINR } from "../data/constants";
import { Card, PageHeader, SectionLabel, Field, NumberInput, StatRow, Badge, Spinner } from "../components/ui";
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
        <p className="text-ink-soft mb-4">Complete the earlier steps first to build your repayment plan.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go to Voice Intake
        </button>
      </Card>
    );
  }

  const maxQuarterAmount = schedule ? Math.max(...schedule.quarters.map((q) => q.amount_due), 1) : 1;

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Step 4 of 5"
        title="Repayment plan & working capital"
        description="The quarterly EMI schedule below factors in your scheme's moratorium period, and working capital is shown separately for the moratorium phase versus once repayment begins."
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Building your repayment schedule...
        </Card>
      )}
      {error && <Card className="border-clay/30 bg-clay-tint text-[#7a1f28] text-sm mb-6">Could not reach the backend: {error}</Card>}

      {structuring && !structuring.scheme && !loading && (
        <Card className="text-center py-10">
          <p className="text-ink-soft">No scheme was selected on the previous step, so no repayment schedule can be generated.</p>
        </Card>
      )}

      {schedule && (
        <div className="space-y-6">
          <Card>
            <SectionLabel>EMI & moratorium generator</SectionLabel>
            <p className="font-mono text-xs text-ink-faint mb-3">{schedule.assumption}</p>
            <div className="grid sm:grid-cols-2 gap-4 mb-5">
              <StatRow label="Loan principal" value={formatINR(schedule.principal)} />
              <StatRow label="Monthly EMI (after moratorium)" value={formatINR(schedule.monthly_emi)} />
              <StatRow label="Moratorium period" value={`${schedule.moratorium_months} months, no payment due`} mono={false} />
              <StatRow label="Total repayment over tenure" value={`${formatINR(schedule.total_repayment)} (incl. ${formatINR(schedule.total_interest)} interest)`} />
            </div>

            <p className="text-xs font-mono uppercase tracking-wide text-ink-faint mb-2">Quarterly repayment schedule</p>
            <div className="space-y-2">
              {schedule.quarters.map((q) => (
                <div key={q.quarter} className="flex items-center gap-3">
                  <span className="w-14 shrink-0 text-xs font-mono text-ink-faint">Q{q.quarter}</span>
                  <div className="flex-1 h-6 rounded-md bg-paper-dim overflow-hidden relative">
                    {q.is_moratorium_only ? (
                      <div className="h-full flex items-center px-2 text-[10.5px] font-mono text-ink-faint border border-dashed border-line-strong rounded-md">
                        moratorium - no payment due
                      </div>
                    ) : (
                      <div
                        className="h-full bg-pine rounded-md flex items-center px-2 text-[10.5px] font-mono text-paper"
                        style={{ width: `${Math.max(8, (q.amount_due / maxQuarterAmount) * 100)}%` }}
                      >
                        {formatINR(q.amount_due)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <SectionLabel>Working capital by phase</SectionLabel>
            <p className="text-sm text-ink-soft mb-4">Typical monthly operating cost is pre-filled for this business category - edit if you know your actual numbers.</p>
            <div className="grid sm:grid-cols-3 gap-4 mb-5">
              <Field label="Monthly operational cost">
                <NumberInput prefix="Rs" value={operations.monthlyOperationalCost} onChange={(e) => updateOperations({ monthlyOperationalCost: e.target.value })} />
              </Field>
              <Field label="Inventory cycle" hint="Days stock sits before sale">
                <NumberInput suffix="days" value={operations.inventoryDays} onChange={(e) => updateOperations({ inventoryDays: e.target.value })} />
              </Field>
              <Field label="Receivable days" hint="Days to collect payment">
                <NumberInput suffix="days" value={operations.receivableDays} onChange={(e) => updateOperations({ receivableDays: e.target.value })} />
              </Field>
            </div>

            {workingCapital && (
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="rounded-xl border border-line bg-paper-dim/50 p-4">
                  <Badge tone="gold">During moratorium</Badge>
                  <p className="mt-3 text-2xl font-display font-semibold num">{formatINR(workingCapital.monthly_cash_needed_during_moratorium)}</p>
                  <p className="text-xs text-ink-faint mt-1">per month - operating costs only, no EMI due yet</p>
                </div>
                <div className="rounded-xl border border-pine/25 bg-pine-tint/30 p-4">
                  <Badge tone="pine">After moratorium</Badge>
                  <p className="mt-3 text-2xl font-display font-semibold num">{formatINR(workingCapital.monthly_cash_needed_after_moratorium)}</p>
                  <p className="text-xs text-ink-faint mt-1">per month - operating costs plus the EMI installment</p>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      <StepFooter backTo="/financial-plan" nextTo="/summary" nextLabel="View Summary" onNext={() => markStepReached(4)} />
    </div>
  );
}
