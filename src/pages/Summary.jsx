import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS, formatINR } from "../data/constants";
import { Card, PageHeader, SectionLabel, Badge, StatRow, Button, Spinner } from "../components/ui";

export default function Summary() {
  const { profile, operations, resetAll } = useAppState();
  const navigate = useNavigate();
  const [structuring, setStructuring] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [workingCapital, setWorkingCapital] = useState(null);
  const [feasibility, setFeasibility] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [advisoryLoading, setAdvisoryLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!profile.availableMarginCapital || !profile.district || !profile.block || !profile.businessType) return;
    Promise.all([
      api.financialStructuring(Number(profile.availableMarginCapital)),
      api.feasibilityReport(profile.district, profile.block, profile.businessType),
    ])
      .then(([s, f]) => {
        setStructuring(s);
        setFeasibility(f);
        if (s.scheme) {
          return api.repaymentSchedule(s.max_loan_amount, s.scheme.annual_rate_pct, s.scheme.tenure_months, s.scheme.moratorium_months);
        }
        return null;
      })
      .then((sched) => setSchedule(sched))
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.availableMarginCapital, profile.district, profile.block, profile.businessType]);

  useEffect(() => {
    if (!schedule || !operations.monthlyOperationalCost) return;
    api
      .workingCapital(Number(operations.monthlyOperationalCost), Number(operations.inventoryDays) || 0, Number(operations.receivableDays) || 0, schedule.monthly_emi)
      .then(setWorkingCapital)
      .catch((e) => setError(e.message));
  }, [schedule, operations.monthlyOperationalCost, operations.inventoryDays, operations.receivableDays]);

  useEffect(() => {
    if (!structuring || !feasibility) return;
    setAdvisoryLoading(true);
    api
      .advisory({
        profile: { business_type: profile.businessType, district: profile.district, block: profile.block, available_margin_capital: Number(profile.availableMarginCapital) },
        financial_structuring: structuring,
        repayment_schedule: schedule || {},
        working_capital: workingCapital || {},
        feasibility,
      })
      .then(setAdvisory)
      .catch((e) => setError(e.message))
      .finally(() => setAdvisoryLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [structuring, feasibility, schedule, workingCapital]);

  if (!profile.businessType) {
    return (
      <Card className="max-w-3xl text-center py-14">
        <p className="text-ink-soft mb-4">Complete the earlier steps first to generate your summary.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Start at Voice Intake
        </button>
      </Card>
    );
  }

  const typeLabel = BUSINESS_TYPE_LABELS[profile.businessType];
  const today = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" });

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8 sm:mb-10 no-print max-w-3xl">
        <PageHeader eyebrow="Step 5 of 5" title="Feasibility & credit-readiness summary" description="Deterministic figures, plus a plain-language AI advisory layer that only explains the numbers below - it never computes them." />
        <Button onClick={() => window.print()} className="mt-1">Print / Save as PDF</Button>
      </div>

      {error && <Card className="max-w-3xl mb-6 border-clay/30 bg-clay-tint text-[#7a1f28] text-sm">Could not reach the backend: {error}</Card>}

      <div className="max-w-3xl space-y-6">
        <Card>
          <div className="flex items-center justify-between mb-1">
            <h1 className="font-display text-2xl font-bold">Vyapar Saarthi - Feasibility & Credit Report</h1>
            <span className="text-xs font-mono text-ink-faint">{today}</span>
          </div>
        </Card>

        {advisory && (
          <Card className="border-pine/30 bg-pine-tint/20">
            <div className="flex items-center justify-between mb-2">
              <SectionLabel>AI advisory (commentary only, not a calculation)</SectionLabel>
              <Badge tone="pine">LLM-phrased</Badge>
            </div>
            <p className="font-display text-lg font-semibold mb-3">{advisory.headline}</p>
            <ul className="space-y-1.5 mb-3">
              {advisory.talking_points.map((point, i) => (
                <li key={i} className="text-sm text-ink-soft flex gap-2">
                  <span className="text-pine">-</span> {point}
                </li>
              ))}
            </ul>
            {advisory.caution && <div className="rounded-lg border border-clay/30 bg-clay-tint px-3.5 py-2.5 text-sm text-[#7a1f28]">{advisory.caution}</div>}
          </Card>
        )}
        {advisoryLoading && (
          <Card className="flex items-center gap-3 text-ink-soft py-6 justify-center">
            <Spinner className="text-pine" /> Generating advisory commentary...
          </Card>
        )}

        <Card>
          <SectionLabel>Business Profile</SectionLabel>
          <div className="grid sm:grid-cols-2 gap-x-8">
            <div>
              <StatRow label="Business category" value={typeLabel} mono={false} />
              <StatRow label="Location" value={`${profile.block}${profile.village ? `, ${profile.village}` : ""}, ${profile.district}`} mono={false} />
            </div>
            <div>
              <StatRow label="Available margin capital" value={formatINR(Number(profile.availableMarginCapital))} />
            </div>
          </div>
        </Card>

        {structuring && (
          <Card>
            <SectionLabel>Financial Structuring & Scheme</SectionLabel>
            <StatRow label="Project cost" value={formatINR(structuring.project_cost)} />
            <StatRow label="Maximum loan eligibility" value={structuring.max_loan_amount !== null ? formatINR(structuring.max_loan_amount) : "-"} />
            {structuring.scheme ? (
              <>
                <StatRow label="Scheme" value={structuring.scheme.name} mono={false} />
                <StatRow label="Terms" value={`${structuring.scheme.annual_rate_pct}% p.a., ${structuring.scheme.tenure_months} months, ${structuring.scheme.moratorium_months}-month moratorium`} mono={false} />
              </>
            ) : (
              <p className="text-sm text-clay mt-2">No scheme tier matched this project cost.</p>
            )}
          </Card>
        )}

        {schedule && (
          <Card>
            <SectionLabel>Repayment Plan</SectionLabel>
            <StatRow label="Monthly EMI (after moratorium)" value={formatINR(schedule.monthly_emi)} />
            <StatRow label="Total repayment over tenure" value={formatINR(schedule.total_repayment)} />
            <StatRow label="Total interest" value={formatINR(schedule.total_interest)} />
            {workingCapital && (
              <>
                <StatRow label="Monthly cash needed (moratorium)" value={formatINR(workingCapital.monthly_cash_needed_during_moratorium)} />
                <StatRow label="Monthly cash needed (post-moratorium)" value={formatINR(workingCapital.monthly_cash_needed_after_moratorium)} />
              </>
            )}
          </Card>
        )}

        {feasibility && (
          <Card>
            <SectionLabel>Feasibility Highlights</SectionLabel>
            <StatRow label="Addressable consumers" value={feasibility.market_reach.addressable_consumers.toLocaleString("en-IN")} />
            <StatRow label="Competitor density" value={`${feasibility.competitor_mapping.competitor_count} / ${feasibility.competitor_mapping.scale_ceiling}`} mono={false} />
            <StatRow label="Market read" value={feasibility.opportunity_analysis.is_underserved ? "Under-served niche" : "Competitive market"} mono={false} />
            {feasibility.product_market_value && (
              <StatRow label="Suggested entry price" value={`Rs ${feasibility.product_market_value.suggested_entry_price.toFixed(0)} / ${feasibility.product_market_value.unit}`} mono={false} />
            )}
          </Card>
        )}
      </div>

      <div className="max-w-3xl mt-10 flex items-center justify-between no-print">
        <Button variant="secondary" onClick={() => navigate("/repayment-plan")}>← Back</Button>
        <Button
          variant="ghost"
          onClick={() => {
            if (confirm("Clear all entered data and start over?")) {
              resetAll();
              navigate("/intake");
            }
          }}
        >
          Start over
        </Button>
      </div>
    </div>
  );
}
