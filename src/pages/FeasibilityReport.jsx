import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS, formatCount } from "../data/constants";
import { Card, PageHeader, Section, TileGrid, FigureTile, Badge, Spinner } from "../components/ui";
import StepFooter from "../components/StepFooter";
import FeasibilityAdvisorChat from "../components/FeasibilityAdvisorChat";

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
        <p className="text-[17px] text-ink-soft mb-5">Please answer the first few questions before we can check your area.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go back to the first step
        </button>
      </Card>
    );
  }

  const typeLabel = BUSINESS_TYPE_LABELS[profile.businessType];
  const underserved = report?.opportunity_analysis?.is_underserved;

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Step 2 of 5"
        title={`Will a ${typeLabel?.toLowerCase()} business work in ${profile.block}?`}
        description="We looked at how many people live near you, how many shops like yours are already there, and what prices are like in your area."
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Checking your area...
        </Card>
      )}

      {error && <Card className="border-clay/30 bg-clay-tint text-clay text-[17px]">Sorry, we could not load this right now. Please check your internet and try again.</Card>}

      {report && (
        <div className="space-y-8">
          {/* The verdict, before any of the supporting detail. */}
          <Card className="rise-in">
            <Badge tone={underserved ? "good" : "gold"}>{underserved ? "Good news" : "Be careful"}</Badge>
            <p className="mt-4 font-display text-[26px] sm:text-3xl font-bold text-ink tracking-tight text-balance leading-tight">
              {underserved
                ? "There are enough customers here for a new shop."
                : "There are already many shops like this here."}
            </p>
            <p className="mt-3 text-[17px] text-ink-soft leading-relaxed">
              {underserved
                ? `About ${formatCount(report.competitor_mapping.addressable_consumers_per_competitor)} people for every shop like yours. That is more than most areas can support, so there is room for you.`
                : `Only about ${formatCount(report.competitor_mapping.addressable_consumers_per_competitor)} people for every shop like yours. You will need to do something different to win customers.`}
            </p>

            <TileGrid min="210px" className="mt-6">
              <FigureTile
                label="People near you who might buy"
                value={formatCount(report.market_reach.addressable_consumers)}
                note={`out of ${formatCount(report.market_reach.block_population)} people living within 5-10 km`}
                emphasis
              />
              <FigureTile
                label="Shops like yours already here"
                value={report.competitor_mapping.competitor_count}
                note={`about ${formatCount(report.competitor_mapping.addressable_consumers_per_competitor)} customers each`}
                emphasis
              />
              {report.product_market_value && (
                <FigureTile
                  label="What you should charge"
                  value={`₹${report.product_market_value.suggested_entry_price.toFixed(0)}`}
                  note={`per ${report.product_market_value.unit}. Others charge ₹${report.product_market_value.current} today.`}
                  emphasis
                  tone="accent"
                />
              )}
            </TileGrid>
          </Card>

          <Section title="How you can reach these customers" className="rise-in" style={{ "--rise-delay": "60ms" }}>
            <p className="text-[17px] text-ink-soft leading-relaxed mb-4">{report.market_reach.detail}</p>
            <ul className="grid sm:grid-cols-3 gap-3">
              {report.market_reach.distribution_channels.map((c, i) => (
                <li key={i} className="rounded-lg border border-line bg-white px-4 py-3 text-[16px] text-ink-soft leading-snug">
                  {c}
                </li>
              ))}
            </ul>
          </Section>

          <Section title="What is good and what is hard about this" className="rise-in" style={{ "--rise-delay": "120ms" }}>
            <div className="grid sm:grid-cols-2 gap-3">
              <SwotBlock title="What helps you" tone="good" items={report.swot.strengths} />
              <SwotBlock title="What is hard" tone="clay" items={report.swot.weaknesses} />
              <SwotBlock title="Your chance" tone="good" items={report.swot.opportunities} />
              <SwotBlock title="Watch out for" tone="clay" items={report.swot.threats} />
            </div>
          </Section>

          <Section
            title="Things that could go wrong"
            aside={<span className="text-[16px] text-ink-soft">Busiest time: <b className="text-ink">{report.threats.seasonal_peak}</b></span>}
            className="rise-in"
            style={{ "--rise-delay": "180ms" }}
          >
            <ul className="space-y-2">
              {report.threats.items.map((t, i) => (
                <li key={i} className="flex items-start gap-3 rounded-lg border border-line bg-white px-4 py-3 text-[16px] text-ink-soft leading-snug">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-clay shrink-0" />
                  {t}
                </li>
              ))}
            </ul>
          </Section>

          {report.product_market_value && (
            <Section title="What price to charge" className="rise-in" style={{ "--rise-delay": "240ms" }}>
              <p className="text-[17px] text-ink-soft leading-relaxed mb-4">{report.product_market_value.detail}</p>
              <PriceScale pricing={report.product_market_value} />
            </Section>
          )}

          <FeasibilityAdvisorChat district={profile.district} block={profile.block} businessType={profile.businessType} />
        </div>
      )}

      <StepFooter backTo="/intake" nextTo="/financial-plan" onNext={() => markStepReached(2)} />
    </div>
  );
}

/* The local price band drawn to scale, with today's rate and the suggested
   entry point marked on it - a range is far easier to judge as a line than
   as three separate numbers in boxes. */
function PriceScale({ pricing }) {
  const { range_low: low, range_high: high, current, suggested_entry_price: suggested } = pricing;
  const span = high - low || 1;
  const pos = (v) => ((v - low) / span) * 100;

  return (
    <div className="rounded-xl border border-line bg-white p-4 pt-8">
      <div className="relative h-2 rounded-full bg-paper-dim">
        <div className="absolute inset-y-0 left-0 rounded-full bg-pine/25" style={{ width: `${pos(current)}%` }} />
        <Marker at={pos(suggested)} label={`Rs ${suggested.toFixed(0)}`} sub="suggested" tone="pine" />
        <Marker at={pos(current)} label={`Rs ${current}`} sub="today" tone="ink" />
      </div>
      <div className="mt-3 flex justify-between text-[15px] text-ink-soft">
        <span>Rs {low}</span>
        <span>per {pricing.unit}</span>
        <span>Rs {high}</span>
      </div>
    </div>
  );
}

function Marker({ at, label, sub, tone }) {
  const color = tone === "pine" ? "bg-pine" : "bg-ink";
  const text = tone === "pine" ? "text-pine-dim" : "text-ink";
  return (
    <div className="absolute -top-7 -translate-x-1/2 flex flex-col items-center" style={{ left: `${at}%` }}>
      <span className={`text-[15px] font-bold ${text} whitespace-nowrap`}>{label}</span>
      <span className="text-[9px] text-ink-faint whitespace-nowrap">{sub}</span>
      <span className={`mt-1 h-3.5 w-0.5 ${color}`} />
    </div>
  );
}

function SwotBlock({ title, tone, items }) {
  return (
    <div className={`rounded-lg border p-3.5 ${tone === "good" ? "border-good/25 bg-good-tint" : "border-clay/25 bg-clay-tint"}`}>
      <p className="text-[15px] font-bold text-ink mb-2">{title}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-ink-soft leading-snug">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
