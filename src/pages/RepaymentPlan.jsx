import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { OPERATIONS_BENCHMARKS, formatINR } from "../data/constants";
import { Card, PageHeader, Section, TileGrid, FigureTile, Field, NumberInput, Badge, Spinner } from "../components/ui";
import StepFooter from "../components/StepFooter";

export default function RepaymentPlan() {
  const { profile, operations, updateOperations, markStepReached, t } = useAppState();
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

  const isCapitalised = Boolean(operations.capitaliseMoratoriumInterest);

  useEffect(() => {
    if (!profile.availableMarginCapital) return;
    if (structuring?.scheme) {
      api
        .repaymentSchedule(
          structuring.max_loan_amount,
          structuring.scheme.annual_rate_pct,
          structuring.scheme.tenure_months,
          structuring.scheme.moratorium_months,
          isCapitalised,
        )
        .then((sched) => setSchedule(sched))
        .catch((e) => setError(e.message));
      return;
    }

    setLoading(true);
    api
      .financialStructuring(Number(profile.availableMarginCapital))
      .then((s) => {
        setStructuring(s);
        if (!s.scheme) return null;
        return api.repaymentSchedule(
          s.max_loan_amount,
          s.scheme.annual_rate_pct,
          s.scheme.tenure_months,
          s.scheme.moratorium_months,
          isCapitalised,
        );
      })
      .then((sched) => setSchedule(sched))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.availableMarginCapital, isCapitalised]);

  const handleToggleCapitalisation = (enabled) => {
    updateOperations({ capitaliseMoratoriumInterest: enabled });
  };

  useEffect(() => {
    if (!schedule || !operations.monthlyOperationalCost) return;
    api
      .workingCapital(
        Number(operations.monthlyOperationalCost),
        Number(operations.inventoryDays) || 0,
        Number(operations.receivableDays) || 0,
        schedule.monthly_emi,
      )
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
  const invDays = Math.max(0, Number(operations.inventoryDays) || 0);
  const recDays = Math.max(0, Number(operations.receivableDays) || 0);
  const monthlyCost = Number(operations.monthlyOperationalCost) || 0;

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow={t("repayment.eyebrow")}
        title={t("repayment.title")}
        description={t("repayment.description")}
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Working out your payments...
        </Card>
      )}
      {error && (
        <Card className="border-clay/30 bg-clay-tint text-clay text-[17px] mb-6">
          Sorry, we could not load this right now. Please check your internet and try again.
        </Card>
      )}

      {structuring && !structuring.scheme && !loading && (
        <Card className="text-center py-10">
          <p className="text-ink-soft">
            No scheme matched your amount, so there is nothing to repay yet. Go back and try a different amount.
          </p>
        </Card>
      )}

      {schedule && (
        <div className="space-y-6">
          <Card className="rise-in">
            {/* Moratorium Interest Capitalisation Mode Toggle */}
            <div className="mb-6 p-4 rounded-xl border border-line bg-paper flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[16px] font-bold text-ink">Interest capitalised during moratorium</span>
                  {schedule.moratorium_months === 0 ? (
                    <Badge tone="neutral">0-month moratorium</Badge>
                  ) : isCapitalised ? (
                    <Badge tone="gold">Capitalised mode</Badge>
                  ) : (
                    <Badge tone="pine">Standard mode</Badge>
                  )}
                </div>
                <p className="text-[14px] text-ink-soft leading-snug">
                  {schedule.moratorium_months === 0
                    ? "No moratorium period applies for this scheme — both calculation modes produce identical results."
                    : isCapitalised
                    ? "Simple interest accrues during the moratorium and is added to principal before repayments start."
                    : "No interest is added during the free period; repayments are calculated purely on the original loan."}
                </p>
              </div>
              <label className={`relative inline-flex items-center shrink-0 ${schedule.moratorium_months === 0 ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}>
                <input
                  type="checkbox"
                  aria-label="Interest capitalised during moratorium"
                  className="sr-only peer"
                  disabled={schedule.moratorium_months === 0}
                  checked={isCapitalised && schedule.moratorium_months > 0}
                  onChange={(e) => handleToggleCapitalisation(e.target.checked)}
                />
                <div className="w-12 h-6 bg-line-strong peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-pine/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-line after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-pine"></div>
              </label>
            </div>

            <p className="text-[17px] text-ink-soft">You will pay every month</p>
            <p className="figure text-[44px] sm:text-[56px] font-bold text-ink mt-1">{formatINR(schedule.monthly_emi)}</p>
            <p className="text-[17px] text-ink-soft mt-3 mb-6 leading-relaxed">
              But not right away. You pay{" "}
              <b className="text-ink">nothing for the first {schedule.moratorium_months} months</b> while the business gets going.
              After that, this amount every month for {schedule.repayment_months} months.
            </p>

            <TileGrid min="200px">
              <FigureTile
                label={isCapitalised && schedule.moratorium_months > 0 ? "Effective principal to repay" : "Loan you take"}
                value={formatINR(isCapitalised && schedule.moratorium_months > 0 ? schedule.effective_principal : schedule.principal)}
                note={isCapitalised && schedule.moratorium_months > 0 ? `Original loan: ${formatINR(schedule.principal)}` : undefined}
              />
              <FigureTile
                label="Extra you pay as interest"
                value={formatINR(schedule.total_interest)}
                tone="gold"
                note={isCapitalised && schedule.moratorium_months > 0 ? `Includes ${formatINR(schedule.moratorium_interest)} moratorium interest` : undefined}
              />
              <FigureTile
                label="Total you give back"
                value={formatINR(schedule.total_repayment)}
                note="loan plus interest, over the full time"
              />
            </TileGrid>

            {/* Capitalisation Audit & Impact Explanation */}
            {isCapitalised && schedule.moratorium_months > 0 && (
              <div className="my-6 p-5 rounded-2xl border-2 border-gold/40 bg-gold-tint/40 space-y-4">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">📊</span>
                    <h4 className="font-display font-bold text-[17px] text-ink">Moratorium Capitalisation Impact</h4>
                  </div>
                  <Badge tone="gold">Formula: P + (P × r × M/12)</Badge>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-left">
                  <div className="p-3 bg-white rounded-xl border border-gold/30">
                    <span className="text-[13px] text-ink-soft block font-medium">Original loan (P)</span>
                    <span className="text-[18px] font-bold text-ink figure">{formatINR(schedule.principal)}</span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-gold/30">
                    <span className="text-[13px] text-ink-soft block font-medium">Moratorium interest ({schedule.moratorium_months} mos)</span>
                    <span className="text-[18px] font-bold text-gold figure">+{formatINR(schedule.moratorium_interest)}</span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-gold/30">
                    <span className="text-[13px] text-ink-soft block font-medium">Capitalised principal (Pm)</span>
                    <span className="text-[18px] font-bold text-ink figure">{formatINR(schedule.effective_principal)}</span>
                  </div>
                  <div className="p-3 bg-white rounded-xl border border-gold/30">
                    <span className="text-[13px] text-ink-soft block font-medium">Monthly EMI increase</span>
                    <span className="text-[18px] font-bold text-clay figure">
                      +{formatINR(schedule.emi_difference)}/mo
                    </span>
                  </div>
                </div>

                <div className="text-[14px] text-ink-soft leading-relaxed pt-2 border-t border-gold/30 space-y-1">
                  <p>
                    <b className="text-ink">Why is this higher?</b> Simple interest of{" "}
                    <strong className="text-ink">{formatINR(schedule.moratorium_interest)}</strong> accrued at {schedule.annual_rate_pct}% p.a. over the {schedule.moratorium_months}-month grace period.
                    It was added to your balance, increasing your effective principal to <strong className="text-ink">{formatINR(schedule.effective_principal)}</strong>.
                  </p>
                  {schedule.total_repayment_difference > 0 && (
                    <p>
                      Overall, you will pay <strong className="text-ink">{formatINR(schedule.total_repayment_difference)}</strong> more in total over the full {schedule.repayment_months}-month repayment window compared to the non-capitalised mode ({formatINR(schedule.total_repayment)} vs {formatINR(schedule.baseline_total_repayment)}).
                    </p>
                  )}
                </div>
              </div>
            )}

            <p className="mt-7 mb-3 text-[17px] font-semibold text-ink">Every three months, this is what is due</p>
            <div className="space-y-2">
              {schedule.quarters.map((q, i) => (
                <div key={q.quarter} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-[15px] text-ink-soft">
                    Month {i * 3 + 1}-{i * 3 + 3}
                  </span>
                  <div className="flex-1 h-9 relative">
                    {q.is_moratorium_only ? (
                      <div className="h-full w-full flex items-center px-3 text-[15px] font-semibold text-gold border-2 border-dashed border-gold/50 bg-gold-tint rounded-lg">
                        Nothing to pay
                      </div>
                    ) : (
                      <div
                        className="h-full bg-pine rounded-lg flex items-center px-3 text-[15px] font-semibold text-white transition-[width] duration-700 ease-out"
                        style={{
                          width: `${Math.max(40, (q.amount_due / maxQuarterAmount) * 100)}%`,
                          transitionDelay: `${i * 25}ms`,
                        }}
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
              We have filled in what a business like yours usually spends. Change these if you know your own numbers better.
            </p>
            <div className="grid sm:grid-cols-3 gap-5 mb-6">
              <Field label="Monthly running cost" hint="Rent, stock, helper pay, electricity">
                <NumberInput
                  prefix="Rs"
                  min="0"
                  value={operations.monthlyOperationalCost}
                  onChange={(e) => updateOperations({ monthlyOperationalCost: e.target.value })}
                />
              </Field>
              <Field label="Days stock sits unsold" hint="From buying it to selling it">
                <NumberInput
                  suffix="days"
                  min="0"
                  value={operations.inventoryDays}
                  onChange={(e) => updateOperations({ inventoryDays: e.target.value })}
                />
              </Field>
              <Field label="Days to get paid" hint="After the customer takes the goods">
                <NumberInput
                  suffix="days"
                  min="0"
                  value={operations.receivableDays}
                  onChange={(e) => updateOperations({ receivableDays: e.target.value })}
                />
              </Field>
            </div>

            {workingCapital && (
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="rounded-2xl border-2 border-gold/35 bg-gold-tint p-5">
                  <Badge tone="gold">First {schedule.moratorium_months} months</Badge>
                  <p className="mt-4 figure text-[38px] font-bold text-ink">
                    {formatINR(workingCapital.monthly_cash_needed_during_moratorium)}
                  </p>
                  <p className="text-[16px] text-ink-soft mt-2 leading-snug">a month, just to run the business. No loan payment yet.</p>
                </div>
                <div className="rounded-2xl border-2 border-pine/30 bg-pine-tint p-5">
                  <Badge tone="pine">From month {schedule.moratorium_months + 1}</Badge>
                  <p className="mt-4 figure text-[38px] font-bold text-ink">
                    {formatINR(workingCapital.monthly_cash_needed_after_moratorium)}
                  </p>
                  <p className="text-[16px] text-ink-soft mt-2 leading-snug">
                    a month, because the {formatINR(schedule.monthly_emi)} loan payment starts.
                  </p>
                </div>
              </div>
            )}

            <CashCycleTimeline
              inventoryDays={invDays}
              receivableDays={recDays}
              monthlyCost={monthlyCost}
              workingCapital={workingCapital}
            />
          </Section>
        </div>
      )}

      <StepFooter backTo="/financial-plan" nextTo="/summary" nextLabel="See my full plan" onNext={() => markStepReached(4)} />
    </div>
  );
}

function CashCycleTimeline({ inventoryDays, receivableDays, monthlyCost, workingCapital }) {
  const cycleDays = inventoryDays + receivableDays;
  const totalDays = Math.max(cycleDays, 30);
  const dailyCost = monthlyCost > 0 ? monthlyCost / 30 : null;
  const gapCost = dailyCost != null ? dailyCost * cycleDays : null;
  const pct = (d) => `${((d / totalDays) * 100).toFixed(3)}%`;

  if (!workingCapital && inventoryDays === 0 && receivableDays === 0) return null;

  return (
    <div className="mt-8 rise-in" style={{ "--rise-delay": "160ms" }}>
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
        <h3 className="font-display text-[19px] sm:text-[21px] font-bold text-ink tracking-tight">
          When cash moves inside a single month
        </h3>
        {cycleDays > 0 && (
          <span className="text-[14px] font-semibold text-ink-faint tabular-nums">{cycleDays}-day cycle</span>
        )}
      </div>
      <p className="text-[15px] text-ink-soft mb-5 leading-snug max-w-xl">
        Money leaves your pocket on day 1. You will not collect it back until day{" "}
        <strong className="text-ink">{cycleDays > 0 ? cycleDays : "0"}</strong>.
        {cycleDays > 0 && " That gap is the exact stretch your working-capital covers."}
      </p>

      <div className="rounded-2xl border border-line bg-white overflow-hidden">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 pt-4 pb-3 border-b border-line bg-paper">
          <LegendDot color="#b83d0b" label="Costs go out (Day 0)" />
          {inventoryDays > 0 && <LegendDot color="#97650a" label={`Stock sold (Day ${inventoryDays})`} />}
          {cycleDays > 0 && <LegendDot color="#147052" label={`Cash arrives (Day ${cycleDays})`} />}
          {cycleDays > 0 && <LegendDot color="rgba(184,61,11,0.12)" label="Working-capital gap" hatched />}
        </div>

        <div className="px-5 pt-5 pb-1">
          <div
            className="relative h-11 rounded-xl overflow-hidden"
            style={{ background: "var(--color-paper-dim)" }}
            role="img"
            aria-label={`Cash-cycle: ${inventoryDays} inventory days + ${receivableDays} receivable days = ${cycleDays} day gap`}
          >
            {cycleDays > 0 && (
              <div
                className="absolute inset-y-0 left-0 transition-[width] duration-500 ease-out"
                style={{
                  width: pct(cycleDays),
                  backgroundImage: "repeating-linear-gradient(-45deg, rgba(184,61,11,0.08) 0 5px, rgba(184,61,11,0.17) 5px 10px)",
                  borderRight: "2.5px dashed rgba(20,112,82,0.5)",
                }}
              />
            )}

            {inventoryDays > 0 && (
              <div
                className="absolute inset-y-0 left-0 flex items-center transition-[width] duration-500 ease-out"
                style={{
                  width: pct(inventoryDays),
                  background: "rgba(151,101,10,0.25)",
                  borderRight: "2px solid rgba(151,101,10,0.65)",
                }}
              >
                {inventoryDays / totalDays > 0.14 && (
                  <span className="px-2.5 text-[13px] font-bold text-gold truncate select-none">
                    {inventoryDays}d stock
                  </span>
                )}
              </div>
            )}

            {receivableDays > 0 && (
              <div
                className="absolute inset-y-0 flex items-center transition-[left,width] duration-500 ease-out"
                style={{
                  left: pct(inventoryDays),
                  width: pct(receivableDays),
                  background: "rgba(20,112,82,0.2)",
                  borderRight: "2px solid rgba(20,112,82,0.65)",
                }}
              >
                {receivableDays / totalDays > 0.12 && (
                  <span className="px-2.5 text-[13px] font-bold text-good truncate select-none">
                    {receivableDays}d wait
                  </span>
                )}
              </div>
            )}

            <TimelinePin left="0%" color="#b83d0b" />
            {inventoryDays > 0 && inventoryDays < totalDays && (
              <TimelinePin left={pct(inventoryDays)} color="#97650a" />
            )}
            {cycleDays > 0 && cycleDays <= totalDays && (
              <TimelinePin left={pct(cycleDays)} color="#147052" />
            )}
          </div>

          <DayAxis totalDays={totalDays} inventoryDays={inventoryDays} cycleDays={cycleDays} />
        </div>

        <div className="px-5 pb-5 pt-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <EventCard
              dot="#b83d0b"
              dayLabel="Day 0"
              title="Costs leave your pocket"
              desc={
                dailyCost != null
                  ? `${formatINR(Math.round(dailyCost))} goes out every day. Over a month: ${formatINR(monthlyCost)}.`
                  : "Operating costs start flowing out from day 1."
              }
            />
            <EventCard
              dot="#97650a"
              dayLabel={`Day ${inventoryDays}`}
              title="Stock converts to sale"
              desc={
                inventoryDays > 0
                  ? `After ${inventoryDays} days your stock has been sold, but the money has not arrived yet.`
                  : "Your inventory turns over immediately — very fast!"
              }
            />
            <EventCard
              dot="#147052"
              dayLabel={`Day ${cycleDays}`}
              title="Cash finally arrives"
              desc={
                cycleDays > 0
                  ? `On day ${cycleDays} the sale payment reaches you and the cycle closes.`
                  : "You collect cash on the spot — zero cycle gap."
              }
              highlight={gapCost != null && gapCost > 0}
              highlightText={gapCost != null && gapCost > 0 ? `${formatINR(gapCost)} bridged` : null}
            />
          </div>
        </div>

        {cycleDays > 0 && workingCapital && (
          <div className="mx-5 mb-5 rounded-xl border border-line-strong bg-paper-dim px-4 py-3.5 flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-[15px] font-semibold text-ink leading-snug">
                Working capital bridges a{" "}
                <span style={{ color: "#b83d0b" }}>{cycleDays}-day gap</span> every month
              </p>
              <p className="text-[13px] text-ink-soft mt-0.5 leading-snug">
                From when you spend to when you are paid — that is the stretch these funds cover.
              </p>
            </div>
            {gapCost != null && gapCost > 0 && (
              <div className="shrink-0 text-right">
                <p className="figure text-[22px] font-bold leading-none" style={{ color: "#b83d0b" }}>
                  {formatINR(gapCost)}
                </p>
                <p className="text-[12px] text-ink-soft mt-0.5">one-time cycle buffer</p>
              </div>
            )}
          </div>
        )}

        {cycleDays === 0 && (
          <div className="mx-5 mb-5 rounded-xl border border-good/30 bg-good-tint px-4 py-3">
            <p className="text-[15px] font-semibold text-good-dim">No cash-cycle gap</p>
            <p className="text-[14px] mt-0.5 leading-snug" style={{ color: "rgba(13,85,64,0.8)" }}>
              With 0 inventory days and 0 receivable days you collect cash instantly — no bridging needed.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function TimelinePin({ left, color }) {
  return (
    <div
      className="absolute top-0 bottom-0 w-px z-10"
      style={{ left, background: color, boxShadow: `0 0 0 1.5px white, 0 0 0 2.5px ${color}` }}
    />
  );
}

function DayAxis({ totalDays, inventoryDays, cycleDays }) {
  const ticks = Array.from(
    new Set([0, inventoryDays, cycleDays, totalDays].filter((d) => d >= 0 && d <= totalDays)),
  ).sort((a, b) => a - b);

  return (
    <div className="relative h-6 mt-1 select-none">
      {ticks.map((d) => {
        const pos = (d / totalDays) * 100;
        const isCollection = d === cycleDays && d > 0;
        const isInventory = d === inventoryDays && d > 0 && d !== cycleDays;
        const color = isCollection ? "#147052" : isInventory ? "#97650a" : "var(--color-ink-faint)";
        const align = pos > 88 ? "translateX(-100%)" : pos > 8 ? "translateX(-50%)" : "translateX(0)";
        return (
          <span
            key={d}
            className="absolute top-0 text-[12px] font-semibold whitespace-nowrap"
            style={{ left: `${pos}%`, transform: align, color }}
          >
            Day {d}
          </span>
        );
      })}
    </div>
  );
}

function EventCard({ dot, dayLabel, title, desc, highlight, highlightText }) {
  return (
    <div
      className={`rounded-xl border p-3.5 transition-colors ${
        highlight ? "border-good/40 bg-good-tint" : "border-line bg-paper"
      }`}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="h-2.5 w-2.5 rounded-full shrink-0 ring-2 ring-white" style={{ background: dot }} />
        <span className="text-[12px] font-bold text-ink-faint uppercase tracking-widest">{dayLabel}</span>
      </div>
      <p className="text-[15px] font-semibold text-ink leading-snug">{title}</p>
      <p className="text-[13px] text-ink-soft mt-1 leading-snug">{desc}</p>
      {highlightText && (
        <p className="mt-2 text-[13px] font-bold text-good-dim">
          {highlightText}
        </p>
      )}
    </div>
  );
}

function LegendDot({ color, label, hatched }) {
  return (
    <div className="flex items-center gap-1.5 shrink-0">
      <span
        className="h-3 w-4 rounded-sm shrink-0"
        style={{
          background: hatched
            ? "repeating-linear-gradient(-45deg, rgba(184,61,11,0.10) 0 3px, rgba(184,61,11,0.22) 3px 6px)"
            : color,
          border: hatched ? "1.5px dashed rgba(184,61,11,0.4)" : undefined,
        }}
      />
      <span className="text-[13px] text-ink-soft">{label}</span>
    </div>
  );
}
