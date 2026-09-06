import { useEffect, useRef } from "react";
import { useAppState } from "../context/AppContext";
import { calcBreakEven, calcPricingCheck, calcWorkingCapital } from "../lib/calculators";
import { BUSINESS_TYPE_LABELS, CALCULATOR_BENCHMARKS, formatINR } from "../data/constants";
import { Card, Field, NumberInput, PageHeader, SectionLabel, StatRow, Badge } from "../components/ui";
import StepFooter from "../components/StepFooter";
import BreakEvenChart from "../components/BreakEvenChart";

export default function Calculators() {
  const { profile, calculators, updateCalculator, markStepReached } = useAppState();
  const autoFilledFor = useRef(null);

  useEffect(() => {
    const benchmark = CALCULATOR_BENCHMARKS[profile.businessType];
    if (!benchmark || autoFilledFor.current === profile.businessType) return;
    autoFilledFor.current = profile.businessType;

    const fillEmpty = (name, values) => {
      const current = calculators[name];
      const patch = {};
      Object.keys(values).forEach((key) => {
        if (current[key] === "" || current[key] === undefined) patch[key] = String(values[key]);
      });
      if (Object.keys(patch).length) updateCalculator(name, patch);
    };

    fillEmpty("breakEven", benchmark.breakEven);
    fillEmpty("pricing", benchmark.pricing);
    const estimatedExpenses = Math.round((Number(profile.monthlyRevenue) || 0) * 0.65) || benchmark.breakEven.fixedCosts * 2;
    fillEmpty("workingCapital", { ...benchmark.workingCapital, monthlyExpenses: estimatedExpenses });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.businessType]);

  const be = calcBreakEven(calculators.breakEven);
  const pc = calcPricingCheck(calculators.pricing);
  const wc = calcWorkingCapital(calculators.workingCapital);
  const typeLabel = BUSINESS_TYPE_LABELS[profile.businessType];
  const benchmark = CALCULATOR_BENCHMARKS[profile.businessType];

  return (
    <div>
      <PageHeader
        eyebrow="Step 2 of 5"
        title="Financial calculators"
        description="Deterministic arithmetic, not guesswork. Every result below shows the formula and intermediate values used, so a bank officer can re-derive it by hand."
      />

      {benchmark && (
        <div className="mb-6 rounded-xl border border-gold/40 bg-gold-tint/30 px-4 py-3 flex items-start gap-3">
          <span className="mt-0.5 text-gold text-base leading-none">●</span>
          <p className="text-sm text-ink-soft">
            Fields below are pre-filled with typical figures for a <b className="text-ink">{typeLabel?.toLowerCase()}</b> (per {benchmark.unitLabel}), not your actual numbers. Edit anything you know for certain.
          </p>
        </div>
      )}

      <div className="space-y-6">
        <Card>
          <SectionLabel>Calculator 1</SectionLabel>
          <h2 className="font-display text-xl font-semibold text-ink mb-1">Break-even analysis</h2>
          <p className="text-sm text-ink-soft mb-5">How many units must you sell before fixed costs are covered?</p>

          <div className="grid sm:grid-cols-3 gap-4 mb-6">
            <Field label="Fixed costs / month">
              <NumberInput prefix="Rs" value={calculators.breakEven.fixedCosts} onChange={(e) => updateCalculator("breakEven", { fixedCosts: e.target.value })} />
            </Field>
            <Field label="Variable cost / unit">
              <NumberInput prefix="Rs" value={calculators.breakEven.variableCostPerUnit} onChange={(e) => updateCalculator("breakEven", { variableCostPerUnit: e.target.value })} />
            </Field>
            <Field label="Price / unit">
              <NumberInput prefix="Rs" value={calculators.breakEven.pricePerUnit} onChange={(e) => updateCalculator("breakEven", { pricePerUnit: e.target.value })} />
            </Field>
          </div>

          <div className="rounded-xl bg-paper-dim/60 border border-line p-4">
            <p className="font-mono text-xs text-ink-faint mb-3">Contribution margin = Price - Variable cost. Break-even units = Fixed costs / Contribution margin</p>
            <StatRow label="Contribution margin" value={`${formatINR(be.contributionMargin)} (${be.contributionMarginPct.toFixed(1)}% of price)`} />
            <StatRow label="Break-even point" value={be.isViable ? `${Math.ceil(be.breakEvenUnits).toLocaleString("en-IN")} units` : "Not viable at this price"} />
            <StatRow label="Break-even revenue" value={be.isViable ? formatINR(be.breakEvenRevenue) : "-"} />
            {!be.isViable && (calculators.breakEven.pricePerUnit || calculators.breakEven.variableCostPerUnit) && (
              <p className="mt-3 text-sm text-clay">Your price per unit does not exceed your variable cost - no volume of sales will cover fixed costs at this pricing.</p>
            )}
          </div>

          <BreakEvenChart be={be} />
        </Card>

        <Card>
          <SectionLabel>Calculator 2</SectionLabel>
          <h2 className="font-display text-xl font-semibold text-ink mb-1">Pricing check</h2>
          <p className="text-sm text-ink-soft mb-5">Compares your cost-plus price against what the market is actually paying.</p>

          <div className="grid sm:grid-cols-3 gap-4 mb-6">
            <Field label="Unit cost">
              <NumberInput prefix="Rs" value={calculators.pricing.unitCost} onChange={(e) => updateCalculator("pricing", { unitCost: e.target.value })} />
            </Field>
            <Field label="Desired margin">
              <NumberInput suffix="%" value={calculators.pricing.desiredMarginPct} onChange={(e) => updateCalculator("pricing", { desiredMarginPct: e.target.value })} />
            </Field>
            <Field label="Market price">
              <NumberInput prefix="Rs" value={calculators.pricing.marketPrice} onChange={(e) => updateCalculator("pricing", { marketPrice: e.target.value })} />
            </Field>
          </div>

          <div className="rounded-xl bg-paper-dim/60 border border-line p-4">
            <p className="font-mono text-xs text-ink-faint mb-3">Cost-plus price = Unit cost x (1 + Desired margin)</p>
            <StatRow label="Your cost-plus price" value={formatINR(pc.costPlusPrice)} />
            <StatRow label="Market price" value={formatINR(pc.marketPrice)} />
            <StatRow label="Gap vs. market" value={`${pc.gapVsMarket >= 0 ? "+" : ""}${formatINR(pc.gapVsMarket)} (${pc.gapVsMarketPct.toFixed(1)}%)`} />
            {pc.verdict !== "insufficient_data" && (
              <div className="mt-3">
                {pc.verdict === "room_to_compete" ? <Badge tone="pine">You have room to price competitively</Badge> : <Badge tone="clay">Cost-plus exceeds market - reduce cost or margin</Badge>}
                <p className="mt-2 text-sm text-ink-soft">At the current market price, your effective margin would be {pc.marginAtMarketPrice.toFixed(1)}%.</p>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <SectionLabel>Calculator 3</SectionLabel>
          <h2 className="font-display text-xl font-semibold text-ink mb-1">Working capital requirement</h2>
          <p className="text-sm text-ink-soft mb-5">Cash needed to bridge the gap between paying expenses and collecting revenue.</p>

          <div className="grid sm:grid-cols-3 gap-4 mb-6">
            <Field label="Monthly expenses">
              <NumberInput prefix="Rs" value={calculators.workingCapital.monthlyExpenses} onChange={(e) => updateCalculator("workingCapital", { monthlyExpenses: e.target.value })} />
            </Field>
            <Field label="Inventory cycle" hint="Days stock sits before sale">
              <NumberInput suffix="days" value={calculators.workingCapital.inventoryDays} onChange={(e) => updateCalculator("workingCapital", { inventoryDays: e.target.value })} />
            </Field>
            <Field label="Receivable days" hint="Days to collect payment">
              <NumberInput suffix="days" value={calculators.workingCapital.receivableDays} onChange={(e) => updateCalculator("workingCapital", { receivableDays: e.target.value })} />
            </Field>
          </div>

          <div className="rounded-xl bg-paper-dim/60 border border-line p-4">
            <p className="font-mono text-xs text-ink-faint mb-3">Daily expense = Monthly expenses / 30. Working capital = Daily expense x (Inventory days + Receivable days)</p>
            <StatRow label="Daily expense" value={formatINR(wc.dailyExpense)} />
            <StatRow label="Total cash cycle" value={`${wc.cashCycleDays} days`} />
            <StatRow label="Working capital needed" value={formatINR(wc.workingCapitalNeeded)} />
          </div>
        </Card>
      </div>

      <StepFooter backTo="/intake" nextTo="/viability" onNext={() => markStepReached(2)} />
    </div>
  );
}
