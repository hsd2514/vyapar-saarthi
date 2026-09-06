import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { calcBreakEven, calcPricingCheck, calcWorkingCapital } from "../lib/calculators";
import { BUSINESS_TYPE_LABELS, CHALLENGE_LABELS, formatINR } from "../data/constants";
import { Card, PageHeader, SectionLabel, Badge, StatRow, Button, Spinner, Select } from "../components/ui";

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
  const [error, setError] = useState("");

  // What-If Explorer state
  const [cities, setCities] = useState(null);
  const [whatIfBlock, setWhatIfBlock] = useState("");
  const [whatIfType, setWhatIfType] = useState("");
  const [whatIfResult, setWhatIfResult] = useState(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfError, setWhatIfError] = useState("");
  const explorerRef = useRef(null);

  const be = calcBreakEven(calculators.breakEven);
  const pc = calcPricingCheck(calculators.pricing);
  const wc = calcWorkingCapital(calculators.workingCapital);

  useEffect(() => {
    if (!profile.businessType || !profile.district) return;
    Promise.all([
      api.viability(profile.district, profile.businessType),
      api.schemes(Number(profile.monthlyRevenue) || 0, Number(profile.yearsInOperation) || 0, profile.businessType),
      api.getCities(),
    ])
      .then(([v, s, c]) => {
        setViability(v);
        setSchemes(s.schemes.filter((x) => x.eligible));
        setCities(c);
        // Pre-populate what-if selectors to current profile
        setWhatIfBlock(profile.block || "");
        setWhatIfType(profile.businessType || "");
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

  function handleCompare() {
    if (!whatIfType) return;
    setWhatIfLoading(true);
    setWhatIfError("");
    setWhatIfResult(null);
    api
      .viability(profile.district, whatIfType)
      .then((res) => {
        setWhatIfResult(res);
        setTimeout(() => explorerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
      })
      .catch((e) => setWhatIfError(e.message))
      .finally(() => setWhatIfLoading(false));
  }

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

        {/* ── What-If Scenario Explorer ─────────────────────────────── */}
        {viability && cities && (
          <WhatIfExplorer
            profile={profile}
            cities={cities}
            realViability={viability}
            whatIfBlock={whatIfBlock}
            setWhatIfBlock={setWhatIfBlock}
            whatIfType={whatIfType}
            setWhatIfType={setWhatIfType}
            whatIfResult={whatIfResult}
            whatIfLoading={whatIfLoading}
            whatIfError={whatIfError}
            onCompare={handleCompare}
            explorerRef={explorerRef}
          />
        )}
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
// What-If Explorer
// ---------------------------------------------------------------------------

function scoreColor(score) {
  if (score >= 75) return "#0fa968";
  if (score >= 50) return "#c2760a";
  return "#d6402a";
}

function scoreBandLabel(score) {
  if (score >= 75) return "Strong";
  if (score >= 50) return "Moderate";
  return "Needs Improvement";
}

function WhatIfExplorer({
  profile, cities, realViability,
  whatIfBlock, setWhatIfBlock,
  whatIfType, setWhatIfType,
  whatIfResult, whatIfLoading, whatIfError,
  onCompare, explorerRef,
}) {
  const currentDistrict = cities.districts.find((d) => d.key === profile.district);
  const blocks = currentDistrict?.blocks || [];
  const isSameAsReal =
    whatIfType === profile.businessType && (whatIfBlock === profile.block || !whatIfBlock);
  const delta = whatIfResult ? whatIfResult.final_score - realViability.final_score : null;

  return (
    <Card className="no-print border-2 border-dashed border-line-strong bg-paper-dim/40">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <SectionLabel>What-If Scenario Explorer</SectionLabel>
          <p className="font-display text-lg font-semibold text-ink">
            How would the viability score change?
          </p>
          <p className="text-sm text-ink-soft mt-0.5 max-w-xl">
            Pick an alternate block or business category to see a side-by-side comparison.
            Your real report above is never affected.
          </p>
        </div>
        <Badge tone="gold">Hypothetical only</Badge>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3 mb-5">
        <label className="flex-1 min-w-[160px]">
          <span className="block text-xs font-medium text-ink-soft mb-1">
            Alternate block <span className="font-normal text-ink-faint">(same district)</span>
          </span>
          <Select
            id="whatif-block"
            value={whatIfBlock}
            onChange={(e) => setWhatIfBlock(e.target.value)}
          >
            {blocks.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </Select>
        </label>

        <label className="flex-1 min-w-[200px]">
          <span className="block text-xs font-medium text-ink-soft mb-1">Alternate business type</span>
          <Select
            id="whatif-type"
            value={whatIfType}
            onChange={(e) => setWhatIfType(e.target.value)}
          >
            {cities.business_types.map((bt) => (
              <option key={bt.value} value={bt.value}>{bt.label}</option>
            ))}
          </Select>
        </label>

        <Button
          id="whatif-compare-btn"
          onClick={onCompare}
          disabled={whatIfLoading || isSameAsReal}
          className="self-end"
        >
          {whatIfLoading ? <><Spinner /> Comparing…</> : "Compare →"}
        </Button>
      </div>

      {/* Note on block granularity */}
      <p className="text-xs text-ink-faint mb-5 italic">
        ℹ️ Competition density data is district-level — the block picker sets context for your analysis, but
        the viability score changes only when you select a different business type.
      </p>

      {whatIfError && (
        <p className="text-sm text-[#7a2f14] bg-clay-tint border border-clay/30 rounded-lg px-4 py-2.5 mb-4">
          {whatIfError}
        </p>
      )}

      {/* Side-by-side comparison */}
      {(whatIfResult || whatIfLoading) && (
        <div ref={explorerRef} className="mt-2">
          <div className="grid sm:grid-cols-2 gap-4">
            {/* Real */}
            <ViabilityCompareSide
              label="Your profile"
              tone="pine"
              badgeLabel="Real"
              block={profile.block}
              businessType={BUSINESS_TYPE_LABELS[profile.businessType] || profile.businessType}
              district={realViability.district}
              result={realViability}
            />
            {/* Hypothetical */}
            {whatIfLoading ? (
              <div className="rounded-xl border-2 border-dashed border-line p-5 flex items-center justify-center text-ink-soft gap-3">
                <Spinner className="text-pine" /> Fetching hypothetical score…
              </div>
            ) : whatIfResult ? (
              <ViabilityCompareSide
                label="What-if scenario"
                tone="gold"
                badgeLabel="Hypothetical"
                block={whatIfBlock || profile.block}
                businessType={BUSINESS_TYPE_LABELS[whatIfType] || whatIfType}
                district={whatIfResult.district}
                result={whatIfResult}
              />
            ) : null}
          </div>

          {/* Delta row */}
          {whatIfResult && delta !== null && (
            <div className={`mt-4 rounded-xl px-5 py-3.5 flex flex-wrap items-center justify-between gap-2 border ${
              delta > 0
                ? "bg-pine-tint/30 border-pine/20"
                : delta < 0
                ? "bg-clay-tint border-clay/20"
                : "bg-paper-dim border-line"
            }`}>
              <span className="text-sm font-medium text-ink">
                {delta === 0
                  ? "Same viability score as your actual profile."
                  : delta > 0
                  ? `What-if scores ${Math.abs(delta)} pts higher than your real profile`
                  : `Your real profile scores ${Math.abs(delta)} pts higher than the what-if scenario`}
              </span>
              <span className={`font-display text-xl font-bold num ${
                delta > 0 ? "text-pine-dim" : delta < 0 ? "text-[#d6402a]" : "text-ink-soft"
              }`}>
                {delta > 0 ? "+" : ""}{delta} pts
              </span>
            </div>
          )}
        </div>
      )}

      {isSameAsReal && !whatIfResult && (
        <p className="text-sm text-ink-faint text-center py-4">
          Change the block or business type above to explore a different scenario.
        </p>
      )}
    </Card>
  );
}

function ViabilityCompareSide({ label, tone, badgeLabel, block, businessType, district, result }) {
  const color = scoreColor(result.final_score);
  return (
    <div className={`rounded-xl border-2 p-5 ${
      tone === "pine" ? "border-pine/30 bg-pine-tint/10" : "border-[#c2760a]/30 bg-[#fff9e6]/50"
    }`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-mono uppercase tracking-widest text-ink-faint">{label}</span>
        <Badge tone={tone === "pine" ? "pine" : "gold"}>{badgeLabel}</Badge>
      </div>
      <p className="text-sm text-ink-soft mb-0.5">{businessType}</p>
      <p className="text-xs text-ink-faint mb-3">{block} · {district}</p>

      {/* Score pill */}
      <div className="flex items-baseline gap-2 mb-4">
        <span className="font-display text-4xl font-bold num" style={{ color }}>{result.final_score}</span>
        <span className="text-sm text-ink-faint">/100</span>
        <span className="ml-1 text-sm font-medium" style={{ color }}>{scoreBandLabel(result.final_score)}</span>
      </div>

      {/* Breakdown bars */}
      <div className="space-y-3">
        {result.breakdown.map((row) => (
          <div key={row.key}>
            <div className="flex items-baseline justify-between mb-1">
              <span className="text-xs text-ink-soft">{row.label}</span>
              <span className="text-xs font-mono text-ink num">{row.contribution.toFixed(1)} pts</span>
            </div>
            <div className="h-1.5 rounded-full bg-paper-dim overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${row.raw_value}%`, background: color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
