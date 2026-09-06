import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS } from "../data/constants";
import { Card, PageHeader, SectionLabel, Badge, Spinner } from "../components/ui";
import StepFooter from "../components/StepFooter";

export default function FeasibilityReport() {
  const { profile, markStepReached } = useAppState();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profile.businessType || !profile.district || !profile.block) return;
    setLoading(true);
    api
      .feasibilityReport(profile.district, profile.block, profile.businessType)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profile.businessType, profile.district, profile.block]);

  if (!profile.businessType || !profile.district || !profile.block) {
    return (
      <Card className="max-w-3xl text-center py-14">
        <p className="text-ink-soft mb-4">Complete voice intake first to generate a feasibility report.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go to Voice Intake
        </button>
      </Card>
    );
  }

  const typeLabel = BUSINESS_TYPE_LABELS[profile.businessType];

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Step 2 of 5"
        title="Hyper-local business feasibility report"
        description={`A district/block-level read for ${typeLabel?.toLowerCase()} in ${profile.block}, computed from lookup-table data - every figure below is traceable, none of it is guessed.`}
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Building the report for {profile.block}...
        </Card>
      )}

      {error && <Card className="border-clay/30 bg-clay-tint text-[#7a1f28] text-sm">Could not reach the backend: {error}</Card>}

      {report && (
        <div className="space-y-6">
          <Card>
            <SectionLabel>1. Market reach</SectionLabel>
            <p className="text-sm text-ink-soft leading-relaxed mb-4">{report.market_reach.detail}</p>
            <div className="grid sm:grid-cols-2 gap-4">
              <Stat label="Block population" value={report.market_reach.block_population.toLocaleString("en-IN")} />
              <Stat label="Addressable consumers (5-10km)" value={report.market_reach.addressable_consumers.toLocaleString("en-IN")} />
            </div>
            <p className="text-xs font-mono uppercase tracking-wide text-ink-faint mt-4 mb-2">Primary distribution channels</p>
            <ul className="grid sm:grid-cols-2 gap-x-4 gap-y-1.5">
              {report.market_reach.distribution_channels.map((c, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-ink-soft">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-pine shrink-0" />
                  {c}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionLabel>2. Opportunity analysis</SectionLabel>
            <div className="flex items-start gap-3">
              <Badge tone={report.opportunity_analysis.is_underserved ? "pine" : "gold"}>
                {report.opportunity_analysis.is_underserved ? "Under-served niche" : "Competitive market"}
              </Badge>
            </div>
            <p className="text-sm text-ink-soft leading-relaxed mt-3">{report.opportunity_analysis.detail}</p>
          </Card>

          <Card>
            <SectionLabel>3. SWOT analysis</SectionLabel>
            <div className="grid sm:grid-cols-2 gap-4">
              <SwotBlock title="Strengths" tone="pine" items={report.swot.strengths} />
              <SwotBlock title="Weaknesses" tone="clay" items={report.swot.weaknesses} />
              <SwotBlock title="Opportunities" tone="pine" items={report.swot.opportunities} />
              <SwotBlock title="Threats" tone="clay" items={report.swot.threats} />
            </div>
          </Card>

          <Card>
            <SectionLabel>4. Threats identification</SectionLabel>
            <p className="text-sm text-ink-soft mb-3">Nearest seasonal demand peak: <b className="text-ink">{report.threats.seasonal_peak}</b></p>
            <ul className="space-y-1.5">
              {report.threats.items.map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-ink-soft">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-clay shrink-0" />
                  {t}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <SectionLabel>5. Competitor mapping</SectionLabel>
            <p className="text-sm text-ink-soft leading-relaxed mb-4">{report.competitor_mapping.detail}</p>
            <div className="grid sm:grid-cols-2 gap-4">
              <Stat label="Similar businesses in block" value={`${report.competitor_mapping.competitor_count} / ${report.competitor_mapping.scale_ceiling} scale`} mono={false} />
              <Stat label="Consumers per competitor" value={report.competitor_mapping.addressable_consumers_per_competitor.toLocaleString("en-IN")} />
            </div>
          </Card>

          {report.product_market_value && (
            <Card>
              <SectionLabel>6. Product market value</SectionLabel>
              <p className="text-sm text-ink-soft leading-relaxed mb-4">{report.product_market_value.detail}</p>
              <div className="grid sm:grid-cols-3 gap-4">
                <Stat label="Local price range" value={`Rs ${report.product_market_value.range_low}-Rs ${report.product_market_value.range_high}`} mono={false} />
                <Stat label="Current price" value={`Rs ${report.product_market_value.current}`} mono={false} />
                <Stat label="Suggested entry price" value={`Rs ${report.product_market_value.suggested_entry_price.toFixed(0)}`} mono={false} />
              </div>
            </Card>
          )}
        </div>
      )}

      <StepFooter backTo="/intake" nextTo="/financial-plan" onNext={() => markStepReached(2)} />
    </div>
  );
}

function Stat({ label, value, mono = true }) {
  return (
    <div className="rounded-lg border border-line p-3.5">
      <p className="text-xs text-ink-faint mb-1">{label}</p>
      <p className={`text-lg font-semibold text-ink ${mono ? "num" : ""}`}>{value}</p>
    </div>
  );
}

function SwotBlock({ title, tone, items }) {
  return (
    <div className={`rounded-lg border p-3.5 ${tone === "pine" ? "border-pine/25 bg-pine-tint/30" : "border-clay/25 bg-clay-tint/30"}`}>
      <p className="text-xs font-mono uppercase tracking-wide text-ink-faint mb-2">{title}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-ink-soft leading-snug">{item}</li>
        ))}
      </ul>
    </div>
  );
}
