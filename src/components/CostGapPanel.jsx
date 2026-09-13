import { useEffect, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { formatINR, formatINRExact } from "../data/constants";
import { Badge, Checkbox, Field, FigureTile, NumberInput, Section, Select, Spinner, TileGrid } from "./ui";

/**
 * Required cost vs eligible cost.
 *
 * The scheme sizes the project from the applicant's savings (margin / 10%).
 * The bank sizes it from NABARD's unit-cost sheet for the activity. This
 * panel shows both numbers side by side, the gap, and the three honest ways
 * to close it - then asks the one question no calculator asks: where the
 * 10% is coming from, and what it really costs if it is a moneylender's.
 *
 * Every figure comes from POST /api/cost-gap (cost_gap.py). The panel only
 * collects choices and renders.
 */

const MARGIN_SOURCES = [
  { value: "savings", label: "My own savings" },
  { value: "family", label: "Family or friends, no interest" },
  { value: "moneylender", label: "A moneylender or private lender" },
  { value: "not_arranged", label: "Not arranged yet" },
];

export default function CostGapPanel() {
  const { profile, operations, updateOperations } = useAppState();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const margin = Number(profile.availableMarginCapital);
  const {
    unitCostVariant,
    unitCostScale,
    unitCostIncludeOptional,
    marginSource,
    moneylenderMonthlyRatePct,
    moneylenderTenureMonths,
  } = operations;

  useEffect(() => {
    if (!profile.businessType || !(margin > 0)) return;
    setLoading(true);
    setError("");
    api
      .costGap({
        business_type: profile.businessType,
        available_margin_capital: margin,
        variant_key: unitCostVariant || null,
        scale_count: unitCostScale === "" ? null : Number(unitCostScale),
        include_optional: unitCostIncludeOptional !== false,
        margin_source: marginSource || "savings",
        moneylender_monthly_rate_pct: Number(moneylenderMonthlyRatePct) || 0,
        moneylender_tenure_months: Math.max(1, Number(moneylenderTenureMonths) || 12),
      })
      .then(setResult)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profile.businessType, margin, unitCostVariant, unitCostScale, unitCostIncludeOptional, marginSource, moneylenderMonthlyRatePct, moneylenderTenureMonths]);

  if (loading && !result) {
    return (
      <Section title="Is that enough for the business?">
        <div className="flex items-center gap-3 py-6 text-ink-soft"><Spinner className="text-pine" /> Checking the bank's cost sheet...</div>
      </Section>
    );
  }
  if (error) {
    return (
      <Section title="Is that enough for the business?">
        <p className="rounded-xl border-2 border-clay/30 bg-clay-tint px-4 py-3 text-[16px] text-clay">Could not load the cost sheet right now.</p>
      </Section>
    );
  }
  if (!result) return null;

  if (result.status === "UNAVAILABLE") {
    return (
      <Section title="Is that enough for the business?">
        <p className="text-[16px] text-ink-soft leading-relaxed">{result.note}</p>
      </Section>
    );
  }

  const { eligible, required, gap, closers, profile: unit } = result;
  const verified = unit.provenance === "VERIFIED_EXTERNAL";
  const optionalItem = required.items.find((i) => i.kind === "optional");
  const closer = Object.fromEntries(closers.map((c) => [c.id, c]));

  return (
    <Section
      title="Is that enough for the business?"
      aside={verified ? <Badge tone="good">Bank's own cost sheet</Badge> : <Badge tone="gold">Estimate - no official sheet yet</Badge>}
    >
      <p className="text-[16px] text-ink-soft leading-relaxed mb-5 max-w-2xl">
        Your savings decide how much you are <em>eligible</em> for. The bank checks that against what a {unit.label.toLowerCase()} unit
        actually costs - the same list its officer has on the desk. Here are both numbers.
      </p>

      {/* The comparison this panel exists for. */}
      <TileGrid min="190px">
        <FigureTile label="You are eligible for" value={formatINR(eligible.project_cost)} note={`from your ${formatINR(eligible.margin_capital)} margin`} />
        <FigureTile label="This business actually costs" value={formatINR(required.project_cost)} note={`${unit.label}, ${required.scale_count} ${unit.scale?.label || unit.unit_label}`} tone="accent" />
        {gap.covered ? (
          <FigureTile label="Covered" value={formatINR(gap.surplus)} note="to spare after the unit cost" tone="good" />
        ) : (
          <FigureTile label="You are short by" value={formatINR(gap.amount)} note={`${gap.pct_of_required}% of what it costs`} tone="clay" emphasis />
        )}
      </TileGrid>

      {/* Choices that change the required side. */}
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {unit.available_variants.length > 1 && (
          <Field label={`Which ${unit.scale?.label === "animals" ? "animal" : "option"}?`}>
            <Select id="unit-cost-variant" value={unit.key} onChange={(e) => updateOperations({ unitCostVariant: e.target.value, unitCostScale: "" })}>
              {unit.available_variants.map((v) => (
                <option key={v.key} value={v.key}>{v.label} - {formatINR(v.project_cost)}</option>
              ))}
            </Select>
          </Field>
        )}
        {unit.scale && (
          <Field label={`How many ${unit.scale.label}?`} hint={`The sheet prices ${unit.scale.count}; you can plan for ${unit.scale.min}-${unit.scale.max}.`}>
            <NumberInput
              id="unit-cost-scale"
              min={unit.scale.min}
              max={unit.scale.max}
              step={1}
              value={unitCostScale === "" ? required.scale_count : unitCostScale}
              onChange={(e) => updateOperations({ unitCostScale: e.target.value })}
            />
          </Field>
        )}
        {optionalItem && (
          <div className="sm:col-span-2">
            <Checkbox
              id="unit-cost-optional"
              checked={unitCostIncludeOptional !== false}
              onChange={(e) => updateOperations({ unitCostIncludeOptional: e.target.checked })}
              label={`Include: ${optionalItem.name} - ${formatINR(optionalItem.amount)}`}
            />
          </div>
        )}
      </div>

      {/* The line items - what the number is made of. */}
      <details className="mt-5 rounded-xl border-2 border-line bg-white open:bg-paper-dim/40">
        <summary className="cursor-pointer px-4 py-3 text-[16px] font-semibold text-ink">See what goes into {formatINR(required.project_cost)}</summary>
        <div className="px-4 pb-4">
          <ItemGroup title="To buy once" items={required.items.filter((i) => i.kind === "capital")} total={required.capital_total} />
          <ItemGroup title="To run it until money comes in" items={required.items.filter((i) => i.kind === "working_capital")} total={required.working_capital_total} />
          {required.optional_included && required.optional_total > 0 && (
            <ItemGroup title="If you do not already have it" items={required.items.filter((i) => i.kind === "optional")} total={required.optional_total} />
          )}
          <p className="mt-3 text-[14px] text-ink-soft leading-relaxed">
            Source: {unit.source}. Figures are indicative (banks allow about 20% either way).{unit.note ? ` ${unit.note}` : ""}
          </p>
        </div>
      </details>

      {/* Three ways to close it. */}
      {!gap.covered && (
        <div className="mt-6">
          <h3 className="font-display text-xl font-bold text-ink tracking-tight mb-3">Three ways to close the {formatINR(gap.amount)} gap</h3>
          <ol className="space-y-3">
            <Closer n={1} title="Bring a little more margin">
              You need {formatINR(closer.raise_margin.margin_needed)} as your 10% instead of {formatINR(eligible.margin_capital)} - that is{" "}
              <strong>{formatINR(closer.raise_margin.extra_margin)} more</strong>. Then the loan covers the full {formatINR(required.project_cost)}.
            </Closer>
            {closer.scale_down && (
              <Closer n={2} title={closer.scale_down.fits ? `Start with ${closer.scale_down.scale_count} ${closer.scale_down.unit}` : "Start smaller"}>
                {closer.scale_down.fits ? (
                  <>
                    {closer.scale_down.scale_count} {closer.scale_down.unit} costs {formatINR(closer.scale_down.required_project_cost)}, which fits inside what you are eligible for.
                    Add the rest once the first is earning.
                  </>
                ) : (
                  <>
                    Even {closer.scale_down.scale_count} {closer.scale_down.unit} costs {formatINR(closer.scale_down.required_project_cost)} - still{" "}
                    {formatINR(closer.scale_down.gap_at_smallest)} more than you are eligible for. Look at options 1 and 3.
                  </>
                )}
              </Closer>
            )}
            <Closer n={closer.scale_down ? 3 : 2} title="Stack a subsidy scheme">
              {closer.stack_subsidy.schemes.length === 0 ? (
                <>No subsidy scheme in our list covers this category at this size. Ask the DIC office about state margin-money schemes.</>
              ) : (
                <ul className="mt-1 space-y-2">
                  {closer.stack_subsidy.schemes.map((s) => (
                    <li key={s.id} className="text-[15.5px] leading-snug">
                      <a href={s.portal_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-pine-dim underline underline-offset-4">{s.name}</a>{" "}
                      - about <strong>{formatINR(s.estimated_subsidy)}</strong> ({s.subsidy_pct}% of the cost)
                      {s.covers_gap ? <Badge tone="good">covers the gap</Badge> : null}
                      <span className="block text-[14px] text-ink-soft">{s.note}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Closer>
          </ol>
        </div>
      )}

      {/* Where the 10% comes from. */}
      <div className="mt-7 pt-6 border-t border-line">
        <h3 className="font-display text-xl font-bold text-ink tracking-tight mb-1">Where is your {formatINR(eligible.margin_capital)} coming from?</h3>
        <p className="text-[15px] text-ink-soft mb-3 max-w-2xl">Be honest here - it changes what you can afford every month.</p>
        <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Source of margin money">
          {MARGIN_SOURCES.map((s) => (
            <button
              key={s.value}
              type="button"
              role="radio"
              aria-checked={(marginSource || "savings") === s.value}
              onClick={() => updateOperations({ marginSource: s.value })}
              className={`rounded-xl border-2 px-4 py-3 text-left text-[16px] font-semibold transition ${
                (marginSource || "savings") === s.value ? "border-pine bg-pine-tint text-pine-dim" : "border-line text-ink hover:border-pine/50"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {marginSource === "moneylender" && result.margin_source.moneylender && (
          <MoneylenderCost
            ml={result.margin_source.moneylender}
            margin={eligible.margin_capital}
            ratePct={moneylenderMonthlyRatePct}
            tenure={moneylenderTenureMonths}
            onChange={updateOperations}
          />
        )}

        {marginSource === "not_arranged" && (
          <p className="mt-4 rounded-xl border-2 border-gold/35 bg-gold-tint px-4 py-3.5 text-[16px] text-ink leading-relaxed">
            Do not borrow it from a moneylender to get started - see option 3 above for schemes that can put up part of it, and ask the DIC or your SCA office
            about a margin-money grant before you apply.
          </p>
        )}
      </div>
    </Section>
  );
}

function ItemGroup({ title, items, total }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-[14px] font-semibold text-ink-soft mb-1">{title}</p>
      <ul>
        {items.map((i) => (
          <li key={i.name} className="flex items-baseline justify-between gap-4 py-1.5 border-b border-line last:border-b-0 text-[15.5px]">
            <span className="text-ink leading-snug">{i.name}</span>
            <span className="figure font-semibold text-ink whitespace-nowrap">{formatINRExact(i.amount)}</span>
          </li>
        ))}
      </ul>
      <p className="flex justify-between text-[15px] font-semibold text-ink pt-1.5"><span>Subtotal</span><span className="figure">{formatINRExact(total)}</span></p>
    </div>
  );
}

function Closer({ n, title, children }) {
  return (
    <li className="flex gap-3 rounded-xl border-2 border-line bg-white p-4">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-pine text-white font-bold">{n}</span>
      <div className="min-w-0">
        <p className="text-[17px] font-semibold text-ink mb-1">{title}</p>
        <div className="text-[16px] text-ink-soft leading-relaxed">{children}</div>
      </div>
    </li>
  );
}

function MoneylenderCost({ ml, margin, ratePct, tenure, onChange }) {
  return (
    <div className="mt-4 rounded-xl border-2 border-clay/30 bg-clay-tint p-4 sm:p-5">
      <div className="grid gap-3 sm:grid-cols-2 mb-4">
        <Field label="Interest per month">
          <NumberInput id="ml-rate" suffix="% / month" min={0} max={20} step={0.5} value={ratePct} onChange={(e) => onChange({ moneylenderMonthlyRatePct: e.target.value })} />
        </Field>
        <Field label="Months to repay them">
          <NumberInput id="ml-tenure" suffix="months" min={1} max={60} step={1} value={tenure} onChange={(e) => onChange({ moneylenderTenureMonths: e.target.value })} />
        </Field>
      </div>
      <TileGrid min="170px">
        <FigureTile label="Interest every month" value={formatINR(ml.monthly_interest)} note={`${ml.monthly_rate_pct}% of ${formatINR(margin)}, from month one`} tone="clay" />
        <FigureTile label="Total interest you will pay" value={formatINR(ml.total_interest)} note={`${ml.interest_as_pct_of_margin}% of your margin, over ${ml.tenure_months} months`} tone="clay" />
        <FigureTile label="Their instalment + scheme EMI" value={formatINR(ml.combined_monthly_after_moratorium)} note="every month once the free period ends" tone="clay" />
      </TileGrid>
      <p className="mt-4 text-[16px] text-ink leading-relaxed">
        The moneylender's {formatINR(ml.monthly_outgo)} a month starts <strong>before the business earns anything</strong> and before the scheme loan's free period is over.
        Most people in this position end up paying the moneylender first and the scheme late - which is how a good loan turns into a default.
        If you can, use option 3 above or a margin-money grant instead.
      </p>
      <p className="mt-2 text-[13.5px] text-ink-soft">Worked out as {ml.assumption}.</p>
    </div>
  );
}
