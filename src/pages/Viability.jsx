import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS } from "../data/constants";
import { Card, PageHeader, SectionLabel, Spinner } from "../components/ui";
import StepFooter from "../components/StepFooter";

function scoreBand(score) {
  if (score >= 75) return { label: "Strong", color: "#0fa968" };
  if (score >= 50) return { label: "Moderate", color: "#c2760a" };
  return { label: "Needs Improvement", color: "#d6402a" };
}

export default function Viability() {
  const { profile, markStepReached } = useAppState();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profile.businessType || !profile.district) return;
    setLoading(true);
    api
      .viability(profile.district, profile.businessType)
      .then((res) => setResult(res))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profile.businessType, profile.district]);

  if (!profile.businessType || !profile.district) {
    return (
      <Card className="text-center py-14">
        <p className="text-ink-soft mb-4">Complete voice intake first to generate a viability score.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go to Voice Intake
        </button>
      </Card>
    );
  }

  const typeLabel = BUSINESS_TYPE_LABELS[profile.businessType];

  return (
    <div>
      <PageHeader
        eyebrow="Step 3 of 5"
        title="Viability score"
        description="Computed server-side in Python from three lookup-table signals, weighted by business type. Nothing here is a black box - every contribution below is shown."
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Scoring against {profile.district} district data...
        </Card>
      )}

      {error && (
        <Card className="border-clay/30 bg-clay-tint text-[#7a2f14] text-sm">Could not reach the backend: {error}. Is `uv run fastapi dev main.py` running in /backend?</Card>
      )}

      {result && (
        <>
          <Card className="mb-6">
            <div className="flex flex-col sm:flex-row sm:items-center gap-6 sm:gap-10">
              <ScoreDial score={result.final_score} band={scoreBand(result.final_score)} />
              <div className="flex-1">
                <SectionLabel>{typeLabel} · {result.district}</SectionLabel>
                <p className="font-display text-2xl font-semibold">{scoreBand(result.final_score).label} viability</p>
                <p className="mt-1.5 text-sm text-ink-soft max-w-md">
                  Weighted from commodity price position, local competition density, and seasonal demand proximity for this district.
                </p>
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="font-display text-lg font-semibold mb-1">Score breakdown</h2>
            <p className="text-sm text-ink-soft mb-5">
              Final score = sum(signal score x weight). Weights: price {(result.weights.price * 100).toFixed(0)}%, competition {(result.weights.competition * 100).toFixed(0)}%, season {(result.weights.season * 100).toFixed(0)}%.
            </p>
            <div className="space-y-4">
              {result.breakdown.map((row) => (
                <div key={row.key} className="rounded-xl border border-line p-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
                    <p className="font-medium text-[15px]">{row.label}</p>
                    <span className="font-mono text-sm text-ink-soft">
                      {row.raw_value.toFixed(1)} x {row.weight.toFixed(2)} = <b className="text-ink">{row.contribution.toFixed(1)} pts</b>
                    </span>
                  </div>
                  <p className="text-sm text-ink-soft mb-3">{row.detail}</p>
                  <div className="h-2 rounded-full bg-paper-dim overflow-hidden">
                    <div className="h-full bg-pine rounded-full" style={{ width: `${row.raw_value}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-5 rounded-xl bg-pine-tint/50 border border-pine/20 p-4 flex items-center justify-between">
              <span className="text-sm font-medium text-pine-dim">Final weighted score</span>
              <span className="font-display text-2xl font-semibold text-pine-dim">{result.final_score} / 100</span>
            </div>
          </Card>
        </>
      )}

      <StepFooter backTo="/calculators" nextTo="/schemes" onNext={() => markStepReached(3)} />
    </div>
  );
}

function ScoreDial({ score, band }) {
  const circumference = 2 * Math.PI * 42;
  const offset = circumference * (1 - score / 100);
  return (
    <div className="relative h-32 w-32 shrink-0 mx-auto sm:mx-0">
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
        <circle cx="50" cy="50" r="42" fill="none" stroke="#e2e6eb" strokeWidth="9" />
        <circle cx="50" cy="50" r="42" fill="none" stroke={band.color} strokeWidth="9" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} style={{ transition: "stroke-dashoffset 0.6s ease" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-bold num">{score}</span>
        <span className="text-[10px] font-mono text-ink-faint">/ 100</span>
      </div>
    </div>
  );
}
