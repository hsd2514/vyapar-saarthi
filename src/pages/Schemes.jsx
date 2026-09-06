import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { formatINR } from "../data/constants";
import { Card, PageHeader, SectionLabel, Badge, Spinner } from "../components/ui";
import StepFooter from "../components/StepFooter";

export default function Schemes() {
  const { profile, markStepReached } = useAppState();
  const navigate = useNavigate();
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!profile.businessType) return;
    setLoading(true);
    api
      .schemes(Number(profile.monthlyRevenue) || 0, Number(profile.yearsInOperation) || 0, profile.businessType)
      .then((res) => setSchemes(res.schemes))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profile.businessType, profile.monthlyRevenue, profile.yearsInOperation]);

  if (!profile.businessType) {
    return (
      <Card className="text-center py-14">
        <p className="text-ink-soft mb-4">Complete voice intake first to check scheme eligibility.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go to Voice Intake
        </button>
      </Card>
    );
  }

  const eligible = schemes.filter((s) => s.eligible);
  const ineligible = schemes.filter((s) => !s.eligible);

  return (
    <div>
      <PageHeader
        eyebrow="Step 4 of 5"
        title="Scheme matching"
        description="Your profile is checked server-side against explicit eligibility rules for each scheme. Every match cites the exact clause that qualifies you."
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Checking eligibility rules...
        </Card>
      )}

      {error && <Card className="border-clay/30 bg-clay-tint text-[#7a2f14] text-sm mb-6">Could not reach the backend: {error}</Card>}

      {!loading && !error && (
        <>
          {eligible.length > 0 ? (
            <div className="mb-8">
              <SectionLabel>{eligible.length} scheme{eligible.length > 1 ? "s" : ""} matched</SectionLabel>
              <div className="space-y-4">
                {eligible.map((s) => (
                  <SchemeCard key={s.id} scheme={s} eligible />
                ))}
              </div>
            </div>
          ) : (
            <Card className="mb-8 text-center py-10">
              <p className="text-ink-soft">No schemes matched this profile's current figures. Adjust revenue or years in operation to re-check.</p>
            </Card>
          )}

          {ineligible.length > 0 && (
            <details>
              <summary className="cursor-pointer text-sm font-medium text-ink-soft hover:text-ink no-print list-none flex items-center gap-2">
                <span>▸</span> Show {ineligible.length} non-matching scheme{ineligible.length > 1 ? "s" : ""}
              </summary>
              <div className="mt-4 space-y-4">
                {ineligible.map((s) => (
                  <SchemeCard key={s.id} scheme={s} eligible={false} />
                ))}
              </div>
            </details>
          )}
        </>
      )}

      <StepFooter backTo="/viability" nextTo="/summary" nextLabel="View Summary" onNext={() => markStepReached(4)} />
    </div>
  );
}

function SchemeCard({ scheme, eligible }) {
  return (
    <Card className={eligible ? "border-pine/30" : "opacity-80"}>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
        <div>
          <h3 className="font-display text-lg font-semibold">{scheme.name}</h3>
          <p className="text-xs text-ink-faint font-mono mt-0.5">{scheme.agency}</p>
        </div>
        {eligible ? <Badge tone="pine">Eligible - up to {formatINR(scheme.max_loan)}</Badge> : <Badge tone="neutral">Not eligible</Badge>}
      </div>
      <div className={`rounded-lg p-3.5 mt-3 ${eligible ? "border border-pine/25 bg-pine-tint/40" : "border border-line bg-paper-dim/50"}`}>
        <p className="text-xs font-mono uppercase tracking-wide text-ink-faint mb-1">{eligible ? "Qualifying rule clause" : "Rule not met"}</p>
        <p className="text-sm leading-relaxed">{scheme.rule_text}</p>
      </div>
      {eligible && (
        <div className="mt-4">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-faint mb-2">Auto-generated document checklist</p>
          <ul className="grid sm:grid-cols-2 gap-x-4 gap-y-1.5">
            {scheme.documents.map((doc, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink-soft">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-gold shrink-0" />
                {doc}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
