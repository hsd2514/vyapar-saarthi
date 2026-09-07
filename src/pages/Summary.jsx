import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS, formatINR } from "../data/constants";
import { Card, PageHeader, Section, TileGrid, FigureTile, Badge, StatRow, Button, Spinner } from "../components/ui";
import FinancingSplitBar from "../components/FinancingSplitBar";

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
  const [contacts, setContacts] = useState([]);

  useEffect(() => {
    if (!profile.availableMarginCapital || !profile.district || !profile.block || !profile.businessType) return;
    
    api.getContacts(profile.district, profile.block)
      .then((res) => setContacts(res.contacts || []))
      .catch((e) => console.warn("Failed to fetch contacts", e));

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
        <p className="text-[17px] text-ink-soft mb-5">Please finish the earlier steps first.</p>
        <button onClick={() => navigate("/intake")} className="text-pine-dim font-semibold underline underline-offset-4">
          Go back to the first step
        </button>
      </Card>
    );
  }

  const typeLabel = BUSINESS_TYPE_LABELS[profile.businessType];
  const today = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" });

  const exportPDF = async () => {
    try {
      const { default: html2canvas } = await import("html2canvas");
      const { jsPDF } = await import("jspdf");

      const element = document.getElementById("pdf-content");
      if (!element) return;

      const canvas = await html2canvas(element, { scale: 2, useCORS: true });
      const imgData = canvas.toDataURL("image/png");

      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "px",
        format: [canvas.width, canvas.height],
      });

      pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height);
      pdf.save("business-plan.pdf");
    } catch (e) {
      console.error("PDF generation failed:", e);
      alert("Could not generate PDF. Please try printing instead.");
    }
  };

  return (
    <div className="max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8 sm:mb-10 no-print">
        <PageHeader
          eyebrow="Step 5 of 5"
          title="Your full plan"
          description="Everything on one page. Print this and take it with you to the bank, the CSC centre, or your SHG group."
        />
        <div className="flex gap-2 mt-1">
          <Button variant="secondary" onClick={() => window.print()}>
            Print
          </Button>
          <Button onClick={exportPDF}>
            Save as PDF
          </Button>
        </div>
      </div>

      {error && <Card className="mb-6 border-clay/30 bg-clay-tint text-clay text-[17px]">Sorry, we could not load this right now. Please check your internet and try again.</Card>}

      {/* The printed document itself: one continuous sheet, sections
          separated by rules rather than floating cards, which is how a
          real financial report reads on paper. */}
      <Card id="pdf-content" className="p-6 sm:p-8">
        <header className="flex flex-wrap items-baseline justify-between gap-2 pb-5 border-b border-line">
          <div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight">My Business Plan</h1>
            <p className="text-[17px] text-ink-soft mt-1">
              {typeLabel} in {profile.block}
              {profile.village ? `, ${profile.village}` : ""}, {profile.district}
            </p>
          </div>
          <span className="text-[15px] text-ink-soft">{today}</span>
        </header>

        {structuring && (
          <div className="py-6 border-b border-line">
            <FinancingSplitBar
              marginCapital={structuring.margin_capital}
              loanAmount={structuring.max_loan_amount || 0}
              projectCost={structuring.project_cost}
            />
          </div>
        )}

        <div className="py-6 border-b border-line">
          <TileGrid min="150px">
            {structuring?.scheme && <FigureTile label="Your scheme" value={structuring.scheme.name.replace(" Scheme", "")} note={`${structuring.scheme.annual_rate_pct}% interest, ${structuring.scheme.tenure_months / 12} years to repay`} tone="good" />}
            {schedule && <FigureTile label="You pay each month" value={formatINR(schedule.monthly_emi)} note={`starting after ${schedule.moratorium_months} months`} emphasis />}
            {feasibility && (
              <FigureTile
                label="Your area"
                value={feasibility.opportunity_analysis.is_underserved ? "Good place" : "Crowded"}
                note={`${feasibility.competitor_mapping.competitor_count} shops like yours in ${feasibility.block}`}
                tone={feasibility.opportunity_analysis.is_underserved ? "good" : "gold"}
              />
            )}
          </TileGrid>
        </div>

        {advisory && (
          <Section title="What this means" className="py-6 border-t-0" aside={<Badge tone="neutral">Written by AI</Badge>}>
            <p className="font-display text-xl sm:text-2xl font-bold mb-4 text-balance leading-snug">{advisory.headline}</p>
            <ul className="space-y-1.5 mb-3">
              {advisory.talking_points.map((point, i) => (
                <li key={i} className="text-[17px] text-ink-soft flex gap-2.5 leading-relaxed">
                  <span className="text-pine shrink-0">&bull;</span> {point}
                </li>
              ))}
            </ul>
            {advisory.caution && <div className="rounded-lg border border-clay/30 bg-clay-tint px-4 py-3 text-[17px] text-clay">{advisory.caution}</div>}
            <p className="mt-3 text-[15px] text-ink-soft">Written by an AI from the figures on this page. It explains them; it does not compute them.</p>
          </Section>
        )}
        {advisoryLoading && (
          <div className="py-6 flex items-center gap-3 text-ink-soft text-sm">
            <Spinner className="text-pine" /> Writing your summary...
          </div>
        )}

        {schedule && (
          <Section title="What you pay back" className="py-6">
            <div className="grid sm:grid-cols-2 gap-x-8">
              <div>
                <StatRow label="Loan amount" value={formatINR(schedule.principal)} />
                <StatRow label="Extra you pay (interest)" value={formatINR(schedule.total_interest)} />
                <StatRow label="Total you give back" value={formatINR(schedule.total_repayment)} />
              </div>
              <div>
                <StatRow label="Free period at start" value={`${schedule.moratorium_months} months`} />
                <StatRow label="Then you pay for" value={`${schedule.repayment_months} months`} />
                {workingCapital && <StatRow label="Cost to run it monthly" value={formatINR(workingCapital.monthly_operational_cost)} />}
              </div>
            </div>
            {workingCapital && (
              <p className="mt-4 text-sm text-ink-soft leading-relaxed">
                Plan for <b className="text-ink num">{formatINR(workingCapital.monthly_cash_needed_during_moratorium)}</b> a month during the moratorium, rising to{" "}
                <b className="text-ink num">{formatINR(workingCapital.monthly_cash_needed_after_moratorium)}</b> once instalments begin.
              </p>
            )}
          </Section>
        )}

        {feasibility && (
          <Section title="Your area and customers" className="py-6">
            <div className="grid sm:grid-cols-2 gap-x-8">
              <div>
                <StatRow label="People who might buy" value={feasibility.market_reach.addressable_consumers.toLocaleString("en-IN")} />
                <StatRow label="People living nearby" value={feasibility.market_reach.block_population.toLocaleString("en-IN")} />
              </div>
              <div>
                <StatRow label="Shops like yours" value={feasibility.competitor_mapping.competitor_count} />
                {feasibility.product_market_value && (
                  <StatRow label="Price to charge" value={`Rs ${feasibility.product_market_value.suggested_entry_price.toFixed(0)} / ${feasibility.product_market_value.unit}`} mono={false} />
                )}
              </div>
            </div>
            <p className="mt-4 text-[17px] font-semibold text-ink mb-3">Things to watch out for</p>
            <ul className="grid sm:grid-cols-3 gap-2">
              {feasibility.threats.items.map((t, i) => (
                <li key={i} className="text-[16px] text-ink-soft leading-snug rounded-xl border border-line px-4 py-3">
                  {t}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {contacts.length > 0 && (
          <Section title="Where to take this" className="py-6">
            <p className="text-sm text-ink-soft mb-4">
              * Note: These are illustrative sample institutions for your block to give you an idea of where to apply. They are not a real live directory.
            </p>
            <div className="grid sm:grid-cols-3 gap-4">
              {contacts.map((c, i) => (
                <div key={i} className="rounded-xl border border-line p-4 bg-paper-dim">
                  <div className="mb-2">
                    <Badge tone="neutral">{c.type}</Badge>
                  </div>
                  <p className="font-semibold text-[16px] text-ink mb-1">{c.name}</p>
                  <p className="text-[14px] text-ink-soft leading-snug">{c.note}</p>
                </div>
              ))}
            </div>
          </Section>
        )}
      </Card>

      <div className="mt-10 flex items-center justify-between no-print">
        <Button variant="secondary" onClick={() => navigate("/repayment-plan")}>
          ← Back
        </Button>
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
