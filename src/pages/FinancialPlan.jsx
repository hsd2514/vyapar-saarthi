import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { formatINR } from "../data/constants";
import { Card, PageHeader, SectionLabel, StatRow, Badge, Spinner } from "../components/ui";
import StepFooter from "../components/StepFooter";

export default function FinancialPlan() {
  const { profile, markStepReached } = useAppState();
  const navigate = useNavigate();
  const [structuring, setStructuring] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profile.availableMarginCapital) return;
    setLoading(true);
    api
      .financialStructuring(Number(profile.availableMarginCapital))
      .then(setStructuring)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profile.availableMarginCapital]);

  if (!profile.availableMarginCapital) {
    return (
      <Card className="max-w-3xl text-center py-14">
        <p className="text-ink-soft mb-4">Complete voice intake first to work out your financial structuring.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go to Voice Intake
        </button>
      </Card>
    );
  }

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Step 3 of 5"
        title="Financial structuring & scheme router"
        description="Your margin capital determines your project cost, your maximum loan, and which of the two scheme tiers you qualify for - all plain arithmetic, no guessing."
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Working out your project cost and eligible scheme...
        </Card>
      )}

      {error && <Card className="border-clay/30 bg-clay-tint text-[#7a1f28] text-sm mb-6">Could not reach the backend: {error}</Card>}

      {structuring && (
        <div className="space-y-6">
          <Card>
            <SectionLabel>Financial structuring</SectionLabel>
            <p className="font-mono text-xs text-ink-faint mb-3">Project cost = Margin capital / 10%. Max loan = Project cost x 90% (capped per scheme).</p>
            <StatRow label="Available margin capital (your 10%)" value={formatINR(structuring.margin_capital)} />
            <StatRow label="Implied project cost" value={formatINR(structuring.project_cost)} />
            <StatRow label="Maximum loan eligibility (90%)" value={structuring.max_loan_amount !== null ? formatINR(structuring.max_loan_amount) : "-"} />
          </Card>

          <Card>
            <SectionLabel>Scheme auto-selection</SectionLabel>
            <div className="rounded-lg border border-line bg-paper-dim/50 p-3.5 mb-4">
              <p className="text-xs font-mono uppercase tracking-wide text-ink-faint mb-1">Routing rule applied</p>
              <p className="text-sm leading-relaxed">{structuring.rule_text}</p>
            </div>

            {structuring.scheme ? (
              <div className="rounded-xl border border-pine/30 bg-pine-tint/30 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-display text-lg font-semibold">{structuring.scheme.name}</h3>
                  <Badge tone="pine">Selected</Badge>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <StatRow label="Interest rate" value={`${structuring.scheme.annual_rate_pct}% p.a.`} mono={false} />
                  <StatRow label="Tenure" value={`${structuring.scheme.tenure_months} months`} />
                  <StatRow label="Moratorium" value={`${structuring.scheme.moratorium_months} months`} />
                  <StatRow label="Loan cap for this tier" value={formatINR(structuring.scheme.loan_cap)} />
                </div>
                {structuring.loan_capped && (
                  <p className="mt-3 text-sm text-gold">
                    Your 90% loan share exceeds this tier's cap of {formatINR(structuring.scheme.loan_cap)} - your loan eligibility has been capped accordingly.
                  </p>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-clay/30 bg-clay-tint/40 p-4 text-sm text-[#7a1f28]">
                No scheme tier matches this project cost. Consider a smaller initial project scope, or a different funding route outside this tool's scope.
              </div>
            )}
          </Card>
        </div>
      )}

      <StepFooter backTo="/feasibility" nextTo="/repayment-plan" nextDisabled={!structuring?.scheme} onNext={() => markStepReached(3)} />
    </div>
  );
}
