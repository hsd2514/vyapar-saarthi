/**
 * SharedSummaryView — /view/:id
 *
 * A read-only rendering of a shared business plan snapshot.
 * Data is fetched from GET /api/summary/share/:id and rendered using the
 * same layout as Summary.jsx, but:
 *  - No AppContext dependency
 *  - No editing or navigation buttons (Back / Start over)
 *  - No "Copy shareable link" button (would create infinite share chains)
 *  - Shows an expiry / read-only banner at the top
 *
 * Known limitations (by design for demo):
 *  - Links expire when the backend server restarts (in-memory store).
 *  - No authentication; anyone with the URL can view the plan.
 */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS, formatINR } from "../data/constants";
import { Card, Section, TileGrid, FigureTile, Badge, StatRow, Button, Spinner } from "../components/ui";
import FinancingSplitBar from "../components/FinancingSplitBar";

export default function SharedSummaryView() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [networkError, setNetworkError] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api
      .shareGet(id)
      .then((res) => {
        setData(res);
      })
      .catch((e) => {
        if (e.message && (e.message.includes("404") || e.message.toLowerCase().includes("not found") || e.message.toLowerCase().includes("expired"))) {
          setNotFound(true);
        } else {
          setNetworkError(true);
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

  const exportPDF = async () => {
    try {
      const { default: html2canvas } = await import("html2canvas");
      const { jsPDF } = await import("jspdf");
      const element = document.getElementById("shared-pdf-content");
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

  /* ── Loading ── */
  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-paper">
        <div className="flex flex-col items-center gap-4 text-ink-soft">
          <Spinner className="text-pine h-8 w-8" />
          <p className="text-[17px]">Loading shared plan…</p>
        </div>
      </div>
    );
  }

  /* ── 404 / Expired ── */
  if (notFound) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-paper px-5">
        <Card className="max-w-md w-full text-center py-14">
          <div className="text-5xl mb-5">🔗</div>
          <h1 className="font-display text-2xl font-bold text-ink mb-3">Link not found</h1>
          <p className="text-[17px] text-ink-soft leading-relaxed mb-6">
            This shared plan link has expired or never existed. Links are valid for 24 hours and are cleared when the server restarts.
          </p>
          <a href="/" className="inline-flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-[17px] font-bold tracking-tight transition bg-pine text-white hover:bg-pine-dim">
            Create your own plan
          </a>
        </Card>
      </div>
    );
  }

  /* ── Network error ── */
  if (networkError) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-paper px-5">
        <Card className="max-w-md w-full text-center py-14">
          <div className="text-5xl mb-5">⚠️</div>
          <h1 className="font-display text-2xl font-bold text-ink mb-3">Could not load plan</h1>
          <p className="text-[17px] text-ink-soft leading-relaxed mb-6">
            Something went wrong while fetching this shared plan. Please check your internet and try again.
          </p>
          <button onClick={() => window.location.reload()} className="inline-flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-[17px] font-bold tracking-tight transition bg-pine text-white hover:bg-pine-dim">
            Retry
          </button>
        </Card>
      </div>
    );
  }

  /* ── Render shared plan ── */
  const { profile, structuring, schedule, working_capital: workingCapital, feasibility, advisory, contacts = [], expires_at } = data;
  const typeLabel = BUSINESS_TYPE_LABELS[profile?.businessType] || profile?.businessType || "Business";
  const createdDate = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" });
  const expiryDate = expires_at
    ? new Date(expires_at * 1000).toLocaleString("en-IN", { day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className="min-h-dvh bg-paper">
      {/* Top banner */}
      <div className="bg-pine-tint border-b border-pine/20 px-5 py-3 flex flex-wrap items-center justify-between gap-3 no-print">
        <div className="flex items-center gap-2.5 text-[15px] text-pine-dim font-semibold">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          Read-only shared plan
          {expiryDate && <span className="font-normal text-pine/70">· expires {expiryDate}</span>}
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => window.print()}>Print</Button>
          <Button onClick={exportPDF}>Save as PDF</Button>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-3xl mx-auto px-5 sm:px-8 py-8 sm:py-12">
        {/* Read-only notice */}
        <div className="mb-6 rounded-xl border border-gold/40 bg-gold-tint px-5 py-4 flex gap-3 items-start no-print">
          <span className="text-gold text-xl shrink-0 mt-0.5">ℹ</span>
          <div>
            <p className="text-[16px] font-semibold text-ink mb-0.5">This is a shared read-only plan</p>
            <p className="text-[15px] text-ink-soft leading-relaxed">
              You are viewing a snapshot shared by the plan&apos;s owner. You cannot edit it. Links are valid for 24&nbsp;hours from when they were created.
            </p>
          </div>
        </div>

        <Card id="shared-pdf-content" className="p-6 sm:p-8">
          <header className="flex flex-wrap items-baseline justify-between gap-2 pb-5 border-b border-line">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight">My Business Plan</h1>
              <p className="text-[17px] text-ink-soft mt-1">
                {typeLabel} in {profile?.block}
                {profile?.village ? `, ${profile.village}` : ""}, {profile?.district}
              </p>
            </div>
            <span className="text-[15px] text-ink-soft">{createdDate}</span>
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
              {structuring?.scheme && (
                <FigureTile
                  label="Your scheme"
                  value={structuring.scheme.name.replace(" Scheme", "")}
                  note={`${structuring.scheme.annual_rate_pct}% interest, ${structuring.scheme.tenure_months / 12} years to repay`}
                  tone="good"
                />
              )}
              {schedule && (
                <FigureTile
                  label="You pay each month"
                  value={formatINR(schedule.monthly_emi)}
                  note={`starting after ${schedule.moratorium_months} months`}
                  emphasis
                />
              )}
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
              {advisory.caution && (
                <div className="rounded-lg border border-clay/30 bg-clay-tint px-4 py-3 text-[17px] text-clay">
                  {advisory.caution}
                </div>
              )}
              <p className="mt-3 text-[15px] text-ink-soft">
                Written by an AI from the figures on this page. It explains them; it does not compute them.
              </p>
            </Section>
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
                  {workingCapital && (
                    <StatRow label="Cost to run it monthly" value={formatINR(workingCapital.monthly_operational_cost)} />
                  )}
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
                    <StatRow
                      label="Price to charge"
                      value={`Rs ${feasibility.product_market_value.suggested_entry_price.toFixed(0)} / ${feasibility.product_market_value.unit}`}
                      mono={false}
                    />
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

        {/* Footer notice */}
        <p className="mt-6 text-center text-[14px] text-ink-soft">
          Generated by{" "}
          <a href="/" className="underline underline-offset-2 text-pine-dim">Vyapar Saarthi</a>{" "}
          · Every financial figure is a deterministic calculation, never an LLM guess.
        </p>
      </div>
    </div>
  );
}
