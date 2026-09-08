import { useEffect, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { formatINR } from "../data/constants";
import { Badge, FigureTile, NumberInput, Section, Spinner, TileGrid } from "./ui";

const DIMENSION_LABELS = {
  market_demand: "Market Demand",
  financial_fit: "Financial Fit",
  competition: "Competition",
  location_infrastructure: "Location & Infrastructure",
  resource_availability: "Resource Availability",
  risk_seasonality: "Risk & Seasonality",
};

const RECOMMENDATION_TONE = {
  PROCEED: "good",
  PROCEED_WITH_CAUTION: "gold",
  VALIDATE_FIRST: "neutral",
  REDUCE_SCALE: "gold",
  HIGH_RISK: "clay",
  INSUFFICIENT_EVIDENCE: "neutral",
};

const RECOMMENDATION_LABELS = {
  PROCEED: "Proceed",
  PROCEED_WITH_CAUTION: "Proceed with caution",
  VALIDATE_FIRST: "Validate first",
  REDUCE_SCALE: "Reduce scale",
  HIGH_RISK: "High risk",
  INSUFFICIENT_EVIDENCE: "Insufficient evidence",
};

const PROVENANCE_TONE = {
  VERIFIED_EXTERNAL: "good",
  USER_PROVIDED: "good",
  ESTIMATED: "gold",
  ASSUMPTION: "gold",
  DEMO: "neutral",
  UNAVAILABLE: "clay",
};

const PROVENANCE_LABELS = {
  VERIFIED_EXTERNAL: "Verified external data",
  USER_PROVIDED: "You provided this",
  ESTIMATED: "Estimated",
  ASSUMPTION: "Assumption",
  DEMO: "Demo data",
  UNAVAILABLE: "Unavailable",
};

const SEVERITY_TONE = {
  VERY_LOW: "good",
  LOW: "good",
  MODERATE: "gold",
  HIGH: "clay",
  VERY_HIGH: "clay",
  UNSCORED: "neutral",
};

function toBackendPayload(district, block, businessType, availableMarginCapital, operations) {
  const num = (v) => (v === "" || v === undefined || v === null ? null : Number(v));
  return {
    district,
    block,
    business_type: businessType,
    available_margin_capital: Number(availableMarginCapital) || 0,
    monthly_household_income: num(operations.monthlyHouseholdIncome),
    monthly_household_expenses: num(operations.monthlyHouseholdExpenses),
    existing_loan_emi: num(operations.existingLoanEmi),
    expected_business_revenue: num(operations.expectedBusinessRevenue),
    operating_expenses: num(operations.monthlyOperationalCost),
  };
}

export default function ViabilityDashboard({ district, block, businessType }) {
  const { profile, operations, updateOperations } = useAppState();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showExplain, setShowExplain] = useState(false);
  const [showFinancialForm, setShowFinancialForm] = useState(false);

  function runAnalysis() {
    setLoading(true);
    setError("");
    api
      .viabilityAnalyze(toBackendPayload(district, block, businessType, profile.availableMarginCapital, operations))
      .then(setResult)
      .catch((e) => setError(e.message || "Could not reach the viability engine."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    runAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [district, block, businessType]);

  return (
    <Section title="Business viability" className="rise-in" style={{ "--rise-delay": "300ms" }}>
      {loading && (
        <div className="paper-card rounded-2xl p-8 flex items-center gap-3 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Analysing your local market...
        </div>
      )}

      {!loading && error && (
        <div className="paper-card rounded-2xl p-6 border-clay/30 bg-clay-tint text-[16px] text-[#7a1f28]">
          We couldn't complete the analysis. Please try again.
          <button onClick={runAnalysis} className="ml-2 underline underline-offset-4 font-semibold">
            Retry
          </button>
        </div>
      )}

      {!loading && !error && result && (
        <div className="paper-card rounded-2xl p-5 sm:p-7 space-y-6">
          {/* Overall score + recommendation - understandable in under 10 seconds */}
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[15px] text-ink-soft mb-1">Viability score</p>
              <p className="font-display text-[44px] sm:text-[52px] font-bold text-ink tracking-tight leading-none">
                {Math.round(result.overall_score)}<span className="text-[22px] text-ink-faint font-semibold"> / 100</span>
              </p>
            </div>
            <div className="text-right">
              <Badge tone={RECOMMENDATION_TONE[result.recommendation] || "neutral"}>{RECOMMENDATION_LABELS[result.recommendation] || result.recommendation}</Badge>
              <p className="mt-2 text-[15px] text-ink-soft">Confidence: {Math.round(result.confidence * 100)}%</p>
            </div>
          </div>
          <p className="text-[16px] text-ink-soft leading-relaxed border-t border-line pt-4">{result.recommendation_summary}</p>
          {result.ai_narrative?.plain_language_summary && (
            <p className="text-[16px] text-ink leading-relaxed">{result.ai_narrative.plain_language_summary}</p>
          )}

          {/* Hard warnings - never hidden behind the weighted average */}
          {result.hard_constraints.length > 0 && (
            <div className="rounded-xl border-2 border-clay/30 bg-clay-tint px-4 py-3.5 space-y-1.5">
              <p className="text-[15px] font-bold text-[#7a1f28]">Before you proceed</p>
              {result.hard_constraints.map((c) => (
                <p key={c.flag} className="text-[15px] text-[#7a1f28] leading-snug">{c.explanation}</p>
              ))}
            </div>
          )}

          {/* Six dimensions */}
          <TileGrid min="170px">
            {Object.entries(result.dimensions).map(([key, dim]) => (
              <FigureTile
                key={key}
                label={DIMENSION_LABELS[key]}
                value={Math.round(dim.score)}
                note={`Confidence ${Math.round(dim.confidence * 100)}%`}
                tone={dim.score >= 65 ? "good" : dim.score >= 45 ? "neutral" : "clay"}
              />
            ))}
          </TileGrid>

          {/* Explainability */}
          <div>
            <button
              type="button"
              onClick={() => setShowExplain((s) => !s)}
              className="text-[15px] font-semibold text-pine-dim underline underline-offset-4"
            >
              {showExplain ? "Hide" : "Why is my score " + Math.round(result.overall_score) + "?"}
            </button>
            {showExplain && (
              <div className="mt-3 rounded-xl border border-line bg-white p-4 space-y-1.5">
                {result.explainability.contributions.map((c) => (
                  <div key={c.dimension} className="flex items-center justify-between text-[15px] text-ink-soft">
                    <span>{DIMENSION_LABELS[c.dimension]} ({Math.round(c.score)} &times; {Math.round(c.weight * 100)}%)</span>
                    <span className="figure font-semibold text-ink">+{c.contribution.toFixed(1)}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between text-[15px] font-bold text-ink border-t border-line pt-1.5 mt-1.5">
                  <span>Total</span>
                  <span className="figure">{result.explainability.total.toFixed(1)} &asymp; {Math.round(result.overall_score)}</span>
                </div>
              </div>
            )}
          </div>

          {/* Opportunity gaps */}
          {result.opportunity_gaps.length > 0 && (
            <div>
              <p className="text-[15px] font-bold text-ink mb-2">Opportunity</p>
              {result.opportunity_gaps.map((g, i) => (
                <p key={i} className="text-[15px] text-ink-soft leading-snug">{g.opportunity}</p>
              ))}
            </div>
          )}

          {/* Named risks */}
          {result.risks.length > 0 && (
            <div>
              <p className="text-[15px] font-bold text-ink mb-2">Key risks</p>
              <ul className="space-y-2">
                {result.risks.map((r, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-[15px] text-ink-soft leading-snug">
                    <Badge tone={SEVERITY_TONE[r.severity] || "neutral"}>{r.severity.replace("_", " ")}</Badge>
                    <span>{r.explanation}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Hyper-local radius schematic */}
          <RadiusSchematic competitorCount={result.dimension_details.competition.competitor_count} />

          {/* Financial fit + optional details */}
          <div className="border-t border-line pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <p className="text-[15px] font-bold text-ink">Financial fit</p>
              <button
                type="button"
                onClick={() => setShowFinancialForm((s) => !s)}
                className="text-[14px] font-semibold text-pine-dim underline underline-offset-4"
              >
                {showFinancialForm ? "Hide financial details" : "Add financial details (optional)"}
              </button>
            </div>

            {showFinancialForm && (
              <FinancialDetailsForm operations={operations} updateOperations={updateOperations} onSave={runAnalysis} />
            )}

            <FinancialSummary summary={result.financial_summary} />
          </div>

          {/* Data quality / provenance */}
          <div className="border-t border-line pt-5">
            <p className="text-[15px] font-bold text-ink mb-2">Data sources</p>
            <div className="space-y-1.5">
              {Object.entries(result.data_quality).map(([key, dq]) => (
                <div key={key} className="flex flex-wrap items-center gap-2 text-[14px] text-ink-soft">
                  <span className="font-semibold text-ink">{DIMENSION_LABELS[key] || key}:</span>
                  <Badge tone={PROVENANCE_TONE[dq.provenance] || "neutral"}>{PROVENANCE_LABELS[dq.provenance] || dq.provenance}</Badge>
                  <span>Level: {dq.geographic_level}</span>
                  <span>Confidence: {Math.round(dq.confidence * 100)}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Missing information */}
          {result.missing_information.length > 0 && (
            <div className="border-t border-line pt-5">
              <p className="text-[15px] font-bold text-ink mb-2">Not yet available</p>
              <p className="text-[14px] text-ink-soft leading-relaxed">
                {result.missing_information.join(", ").replace(/_/g, " ")} - these were left out of the score above rather than guessed at.
              </p>
            </div>
          )}

          <div className="border-t border-line pt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-[13px] text-ink-faint leading-relaxed max-w-xl">
              This is decision support based on available information. It does not guarantee business success, loan
              approval, or scheme eligibility. Final decisions remain with you and the relevant lenders/authorities.
            </p>
            <button type="button" onClick={runAnalysis} className="text-[14px] font-semibold text-pine-dim underline underline-offset-4 shrink-0">
              Re-run analysis
            </button>
          </div>
        </div>
      )}
    </Section>
  );
}

function FinancialSummary({ summary }) {
  return (
    <TileGrid min="150px">
      <FigureTile label="Project cost" value={formatINR(summary.project_cost)} tone="accent" />
      <FigureTile label="Indicative loan" value={summary.max_loan_amount ? formatINR(summary.max_loan_amount) : "Not available"} />
      <FigureTile
        label="DSCR"
        value={summary.dscr !== null ? summary.dscr.toFixed(2) : "Insufficient evidence"}
        note={summary.dscr !== null ? "Repayment capacity vs. EMI" : "Add income/expense details"}
        tone={summary.insufficient_repayment_capacity ? "clay" : "neutral"}
      />
      <FigureTile
        label="Post-loan monthly surplus"
        value={summary.post_loan_surplus !== null ? formatINR(summary.post_loan_surplus) : "Insufficient evidence"}
      />
    </TileGrid>
  );
}

function FinancialDetailsForm({ operations, updateOperations, onSave }) {
  return (
    <div className="rounded-xl border border-line bg-white p-4 mb-4 space-y-3">
      <div className="grid sm:grid-cols-2 gap-3">
        <LabeledInput
          label="Monthly household income"
          value={operations.monthlyHouseholdIncome}
          onChange={(v) => updateOperations({ monthlyHouseholdIncome: v })}
        />
        <LabeledInput
          label="Monthly household expenses"
          value={operations.monthlyHouseholdExpenses}
          onChange={(v) => updateOperations({ monthlyHouseholdExpenses: v })}
        />
        <LabeledInput label="Existing loan EMI" value={operations.existingLoanEmi} onChange={(v) => updateOperations({ existingLoanEmi: v })} />
        <LabeledInput
          label="Expected monthly business revenue"
          value={operations.expectedBusinessRevenue}
          onChange={(v) => updateOperations({ expectedBusinessRevenue: v })}
        />
        <LabeledInput
          label="Expected monthly operating expenses"
          value={operations.monthlyOperationalCost}
          onChange={(v) => updateOperations({ monthlyOperationalCost: v })}
        />
      </div>
      <button type="button" onClick={onSave} className="text-[14px] font-bold text-white bg-pine hover:bg-pine-dim rounded-lg px-4 py-2 transition">
        Update financial fit
      </button>
    </div>
  );
}

function LabeledInput({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="block text-[14px] font-semibold text-ink-soft mb-1">{label}</span>
      <NumberInput prefix="Rs" min="0" value={value} onChange={(e) => onChange(e.target.value)} placeholder="Leave blank if unknown" />
    </label>
  );
}

/* A labelled schematic, not a live GIS map - this app has no mapping
   library and no per-competitor coordinates, only an aggregate count, so a
   real map would either need a new dependency or fabricate pins. Two
   concentric rings plus the real observed competitor count communicate the
   same "hyper-local" framing honestly. */
function RadiusSchematic({ competitorCount }) {
  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <p className="text-[14px] font-semibold text-ink-soft mb-3">Hyper-local reach (schematic)</p>
      <div className="flex items-center gap-5">
        <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden="true">
          <circle cx="60" cy="60" r="55" fill="none" stroke="var(--color-line-strong)" strokeWidth="1.5" strokeDasharray="4 3" />
          <circle cx="60" cy="60" r="32" fill="var(--color-pine-tint)" stroke="var(--color-pine)" strokeWidth="1.5" />
          <circle cx="60" cy="60" r="4" fill="var(--color-pine)" />
        </svg>
        <div className="text-[14px] text-ink-soft space-y-1">
          <p><span className="inline-block h-2.5 w-2.5 rounded-full bg-pine-tint border border-pine mr-1.5" /> 5 km reach</p>
          <p><span className="inline-block h-2.5 w-2.5 rounded-full border border-line-strong mr-1.5" /> 10 km reach</p>
          <p className="pt-1 text-ink">
            {competitorCount !== null && competitorCount !== undefined
              ? `${competitorCount} similar business(es) observed at block level (exact locations not available).`
              : "Competitor data unavailable for this area."}
          </p>
        </div>
      </div>
    </div>
  );
}
