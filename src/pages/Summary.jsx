import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { calcBreakEven, calcPricingCheck, calcWorkingCapital } from "../lib/calculators";
import { BUSINESS_TYPE_LABELS, CHALLENGE_LABELS, formatINR } from "../data/constants";
import { Card, PageHeader, SectionLabel, Badge, StatRow, Button, Spinner } from "../components/ui";

function scoreBand(score) {
  if (score >= 75) return "Strong";
  if (score >= 50) return "Moderate";
  return "Needs Improvement";
}

export default function Summary() {
  const { profile, calculators, resetAll } = useAppState();
  const navigate = useNavigate();
  const [viability, setViability] = useState(null);
  const [schemes, setSchemes] = useState([]);
  const [advisory, setAdvisory] = useState(null);
  const [advisoryLoading, setAdvisoryLoading] = useState(false);
  const [weatherAdvisory, setWeatherAdvisory] = useState(null);
  const [error, setError] = useState("");

  const be = calcBreakEven(calculators.breakEven);
  const pc = calcPricingCheck(calculators.pricing);
  const wc = calcWorkingCapital(calculators.workingCapital);

  useEffect(() => {
    if (!profile.businessType || !profile.district) return;
    Promise.all([
      api.viability(profile.district, profile.businessType),
      api.schemes(Number(profile.monthlyRevenue) || 0, Number(profile.yearsInOperation) || 0, profile.businessType),
      api.weatherAdvisory(profile.district, profile.businessType).catch(() => null),
    ])
      .then(([v, s, w]) => {
        setViability(v);
        setSchemes(s.schemes.filter((x) => x.eligible));
        setWeatherAdvisory(w);
      })
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.businessType, profile.district]);

  useEffect(() => {
    if (!viability) return;
    setAdvisoryLoading(true);
    api
      .advisory({
        profile: { business_type: profile.businessType, district: profile.district, monthly_revenue: Number(profile.monthlyRevenue) || 0 },
        break_even: { contribution_margin: be.contributionMargin, break_even_units: be.breakEvenUnits, is_viable: be.isViable },
        pricing: { verdict: pc.verdict, cost_plus_price: pc.costPlusPrice, market_price: pc.marketPrice },
        working_capital: { working_capital_needed: wc.workingCapitalNeeded, cash_cycle_days: wc.cashCycleDays },
        viability: { final_score: viability.final_score, breakdown: viability.breakdown },
        matched_schemes: schemes.map((s) => ({ name: s.name, max_loan: s.max_loan })),
      })
      .then(setAdvisory)
      .catch((e) => setError(e.message))
      .finally(() => setAdvisoryLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viability]);

  if (!profile.businessType) {
    return (
      <Card className="text-center py-14">
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
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8 sm:mb-10 no-print">
        <PageHeader eyebrow="Step 5 of 5" title="Credit-readiness summary" description="Deterministic figures, plus a plain-language AI advisory layer that only explains the numbers below - it never computes them." />
        <Button onClick={() => window.print()} className="mt-1">Print / Save as PDF</Button>
      </div>

      {error && <Card className="mb-6 border-clay/30 bg-clay-tint text-[#7a2f14] text-sm">Could not reach the backend: {error}</Card>}

      <div className="space-y-6">
        <Card>
          <div className="flex items-center justify-between mb-1">
            <h1 className="font-display text-2xl font-bold">Vyapar Saarthi - Credit Readiness Report</h1>
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
            {advisory.caution && (
              <div className="rounded-lg border border-clay/30 bg-clay-tint px-3.5 py-2.5 text-sm text-[#7a2f14]">{advisory.caution}</div>
            )}
          </Card>
        )}
        {advisoryLoading && (
          <Card className="flex items-center gap-3 text-ink-soft py-6 justify-center">
            <Spinner className="text-pine" /> Generating advisory commentary...
          </Card>
        )}

        <WeatherAdvisoryCard data={weatherAdvisory} />

        <Card>
          <SectionLabel>Business Profile</SectionLabel>
          <div className="grid sm:grid-cols-2 gap-x-8">
            <div>
              <StatRow label="Business type" value={typeLabel} mono={false} />
              <StatRow label="Location" value={`${profile.block}, ${profile.district}`} mono={false} />
            </div>
            <div>
              <StatRow label="Monthly revenue (est.)" value={formatINR(Number(profile.monthlyRevenue))} />
              <StatRow label="Years in operation" value={profile.yearsInOperation} />
            </div>
          </div>
          {profile.challenges.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {profile.challenges.map((c) => (
                <Badge tone="neutral" key={c}>
                  {CHALLENGE_LABELS[c]}
                </Badge>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <SectionLabel>Financial Calculators</SectionLabel>
          <div className="grid sm:grid-cols-3 gap-4">
            <MiniCalc title="Break-even">
              <StatRow label="Contribution margin" value={formatINR(be.contributionMargin)} />
              <StatRow label="Break-even units" value={be.isViable ? Math.ceil(be.breakEvenUnits) : "N/A"} />
              <StatRow label="Break-even revenue" value={be.isViable ? formatINR(be.breakEvenRevenue) : "N/A"} />
            </MiniCalc>
            <MiniCalc title="Pricing check">
              <StatRow label="Cost-plus price" value={formatINR(pc.costPlusPrice)} />
              <StatRow label="Market price" value={formatINR(pc.marketPrice)} />
              <StatRow label="Verdict" value={pc.verdict === "room_to_compete" ? "Competitive" : pc.verdict === "needs_adjustment" ? "Adjust cost/margin" : "N/A"} mono={false} />
            </MiniCalc>
            <MiniCalc title="Working capital">
              <StatRow label="Cash cycle" value={`${wc.cashCycleDays} days`} />
              <StatRow label="Daily expense" value={formatINR(wc.dailyExpense)} />
              <StatRow label="Capital needed" value={formatINR(wc.workingCapitalNeeded)} />
            </MiniCalc>
          </div>
        </Card>

        {viability && (
          <Card>
            <div className="flex items-center justify-between mb-3">
              <SectionLabel>Viability Score</SectionLabel>
              <span className="font-display text-xl font-bold">{viability.final_score}/100 - {scoreBand(viability.final_score)}</span>
            </div>
            <div className="space-y-2">
              {viability.breakdown.map((row) => (
                <div key={row.key} className="flex items-center justify-between text-sm border-b border-line py-1.5 last:border-0">
                  <span className="text-ink-soft">
                    {row.label} <span className="font-mono text-xs text-ink-faint">(w={row.weight.toFixed(2)})</span>
                  </span>
                  <span className="font-mono font-medium">{row.contribution.toFixed(1)} pts</span>
                </div>
              ))}
            </div>
          </Card>
        )}

        <Card>
          <SectionLabel>Matched Government Schemes</SectionLabel>
          {schemes.length === 0 ? (
            <p className="text-sm text-ink-soft">No schemes matched current profile figures.</p>
          ) : (
            <div className="space-y-4">
              {schemes.map((s) => (
                <div key={s.id} className="border-b border-line pb-4 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="font-semibold">{s.name}</p>
                    <span className="text-sm font-mono text-pine-dim">up to {formatINR(s.max_loan)}</span>
                  </div>
                  <p className="text-sm text-ink-soft mb-2">{s.rule_text}</p>
                  <p className="text-xs font-mono uppercase tracking-wide text-ink-faint mb-1">Checklist</p>
                  <ul className="text-sm text-ink-soft grid sm:grid-cols-2 gap-x-4 gap-y-0.5 list-disc list-inside">
                    {s.documents.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="mt-10 flex items-center justify-between no-print">
        <Button variant="secondary" onClick={() => navigate("/schemes")}>← Back</Button>
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

function MiniCalc({ title, children }) {
  return (
    <div className="rounded-lg border border-line p-3.5">
      <p className="font-medium text-sm mb-2">{title}</p>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// WeatherAdvisoryCard
// ---------------------------------------------------------------------------

function ForecastPill({ day }) {
  const date = new Date(day.date + "T00:00:00");
  const dayName = date.toLocaleDateString("en-IN", { weekday: "short" });
  const dateStr = date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  const rainPct = day.precip_prob_pct ?? "—";
  const tempC = day.temp_max_c != null ? `${day.temp_max_c}°C` : "—";
  const isRainy = (day.precip_prob_pct ?? 0) > 60;
  const isHot = (day.temp_max_c ?? 0) > 38;

  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border border-line bg-paper-dim/50 px-4 py-3 min-w-[90px]">
      <span className="text-xs font-mono uppercase tracking-wide text-ink-faint">{dayName}</span>
      <span className="text-[11px] text-ink-faint">{dateStr}</span>
      <span className={`text-sm font-semibold num mt-1 ${isRainy ? "text-[#1a6fa8]" : "text-ink-soft"}`}>
        🌧 {rainPct}%
      </span>
      <span className={`text-sm font-semibold num ${isHot ? "text-clay" : "text-ink-soft"}`}>
        🌡 {tempC}
      </span>
    </div>
  );
}

function WeatherAdvisoryCard({ data }) {
  // Not yet fetched (still loading — parallel fetch hasn't resolved)
  if (data === null || data === undefined) return null;

  // Unavailable state — network blocked or open-meteo unreachable
  if (!data.available) {
    return (
      <Card className="border-line">
        <div className="flex items-center justify-between mb-2">
          <SectionLabel>Weather stocking advisory</SectionLabel>
          <Badge tone="neutral">Unavailable</Badge>
        </div>
        <p className="text-sm text-ink-soft">
          ⚠ Weather data could not be fetched — {data.reason || "check network connectivity."}  Other sections of this report are unaffected.
        </p>
      </Card>
    );
  }

  const fetchedTime = new Date(data.fetched_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <SectionLabel>Weather stocking advisory</SectionLabel>
          <p className="text-xs text-ink-faint font-mono mt-0.5">
            Live 3-day forecast · {data.district} · fetched at {fetchedTime} ·{" "}
            <a
              href="https://open-meteo.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-ink"
            >
              Open-Meteo
            </a>
          </p>
        </div>
        <Badge tone="neutral">Live forecast · no API key</Badge>
      </div>

      {/* 3-day strip */}
      <div className="flex gap-2 flex-wrap mb-5">
        {data.forecast_days.map((day) => (
          <ForecastPill key={day.date} day={day} />
        ))}
        <div className="flex flex-col justify-center gap-1 text-[11px] text-ink-faint font-mono ml-1">
          <span>🌧 Rain prob.</span>
          <span>🌡 Max temp</span>
        </div>
      </div>

      {/* Rules section */}
      {!data.weather_affected ? (
        <div className="rounded-lg border border-line bg-paper-dim/40 px-4 py-3 text-sm text-ink-soft">
          {data.note || "Weather has minimal stocking impact for this business type."}
        </div>
      ) : data.triggered_rules.length === 0 ? (
        <div className="rounded-lg border border-pine/25 bg-pine-tint/30 px-4 py-3 text-sm text-ink-soft">
          ✓ No adverse weather signals in the next 3 days. Normal stocking levels advised.
        </div>
      ) : (
        <div className="space-y-3">
          {data.triggered_rules.map((rule, i) => (
            <div
              key={i}
              className={`rounded-lg border px-4 py-3 ${
                rule.severity === "warning"
                  ? "border-clay/30 bg-clay-tint"
                  : "border-gold/30 bg-gold-tint/30"
              }`}
            >
              <p
                className={`text-xs font-mono uppercase tracking-wide mb-1 ${
                  rule.severity === "warning" ? "text-[#7a2f14]" : "text-[#7a5a12]"
                }`}
              >
                {rule.severity === "warning" ? "⚠ Stocking warning" : "ℹ Stocking note"}
              </p>
              <p className="text-xs font-mono text-ink-faint mb-1.5">
                Triggered by: {rule.trigger_description}
              </p>
              <p className="text-sm leading-snug">{rule.advice}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
