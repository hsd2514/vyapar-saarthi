import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { formatINR } from "../data/constants";
import { Card, PageHeader, Section, TileGrid, FigureTile, Badge, Spinner } from "../components/ui";
import FinancingSplitBar from "../components/FinancingSplitBar";
import GovSchemeMatches from "../components/GovSchemeMatches";
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
        <p className="text-[17px] text-ink-soft mb-5">Please answer the first few questions before we can work out your loan.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go back to the first step
        </button>
      </Card>
    );
  }

  const scheme = structuring?.scheme;

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Step 3 of 5"
        title="How much money you can get"
        description="For every ₹10 the business needs, you put in ₹1 and the government scheme lends the other ₹9. How big your business is decides which scheme you get."
      />

      {loading && (
        <Card className="flex items-center gap-3 py-10 justify-center text-ink-soft">
          <Spinner className="text-pine" /> Working out your loan...
        </Card>
      )}

      {error && <Card className="border-clay/30 bg-clay-tint text-clay text-[17px] mb-6">Sorry, we could not load this right now. Please check your internet and try again.</Card>}

      {structuring && (
        <div className="space-y-8">
          {/* The one result this screen exists to deliver. */}
          <Card className="rise-in">
            <FinancingSplitBar
              marginCapital={structuring.margin_capital}
              loanAmount={structuring.max_loan_amount || 0}
              projectCost={structuring.project_cost}
            />
            <p className="mt-5 pt-5 border-t border-line text-[15px] text-ink-soft leading-relaxed">
              How this is worked out: your savings are one tenth of the total. The loan is the other nine tenths, up to the scheme's limit.
            </p>
          </Card>

          <Section
            title="The scheme you qualify for"
            aside={scheme ? <Badge tone="good">You qualify</Badge> : <Badge tone="clay">Nothing matches</Badge>}
            className="rise-in"
            style={{ "--rise-delay": "80ms" }}
          >
            {scheme ? (
              <>
                <h3 className="font-display text-2xl font-bold mb-2">{scheme.name}</h3>
                <p className="text-[17px] text-ink-soft mb-5 leading-relaxed">{structuring.rule_text}</p>
                <TileGrid min="200px">
                  <FigureTile label="Interest charged" value={`${scheme.annual_rate_pct}%`} note="a year, lower than a normal bank loan" />
                  <FigureTile label="Time to pay it back" value={`${scheme.tenure_months / 12} years`} note={`${scheme.tenure_months} months in total`} />
                  <FigureTile label="Free period at the start" value={`${scheme.moratorium_months} months`} note="you pay nothing during this time" tone="gold" />
                </TileGrid>
                {structuring.loan_capped && (
                  <p className="mt-5 rounded-xl border-2 border-gold/35 bg-gold-tint px-4 py-3.5 text-[16px] text-ink leading-relaxed">
                    This scheme will not lend more than {formatINR(scheme.loan_cap)}. So you would need to arrange the rest yourself, shown in grey above.
                  </p>
                )}
              </>
            ) : (
              <div className="rounded-xl border-2 border-clay/30 bg-clay-tint p-5 text-[17px] text-ink leading-relaxed">
                <p className="mb-2">{structuring.rule_text}</p>
                <p>Try starting with a smaller business, or ask your bank about other loans.</p>
              </div>
            )}
          </Section>

          <Section
            title="All the government schemes that could fund this"
            className="rise-in"
            style={{ "--rise-delay": "140ms" }}
          >
            <GovSchemeMatches projectCost={structuring.project_cost} businessType={profile.businessType} />
          </Section>
        </div>
      )}

      <StepFooter backTo="/feasibility" nextTo="/repayment-plan" nextDisabled={!scheme} onNext={() => markStepReached(3)} />
    </div>
  );
}
