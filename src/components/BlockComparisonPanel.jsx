/**
 * BlockComparisonPanel - "What if I picked a different block?"
 *
 * The other half of issue #8: BusinessComparisonPanel already lets someone
 * compare business categories for their chosen block; this compares their
 * chosen business category across every other block in the same district.
 *
 * Same constraints as BusinessComparisonPanel:
 *   - Does NOT mutate profile state, purely informational.
 *   - Collapsed by default, only fetches on first expand.
 */

import { useState, useRef } from "react";
import { api } from "../lib/api";
import { formatCount } from "../data/constants";

export default function BlockComparisonPanel({ district, block, businessType }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fetchedRef = useRef(false);

  const handleToggle = () => {
    const next = !open;
    setOpen(next);
    if (next && !fetchedRef.current) {
      fetchedRef.current = true;
      setLoading(true);
      api
        .feasibilityCompareBlocks(district, businessType)
        .then(setData)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }
  };

  const rows = data
    ? Object.entries(data.by_block)
        .filter(([, r]) => r !== null)
        .map(([key, r]) => ({
          key,
          consumers: r.market_reach.addressable_consumers,
          competitors: r.competitor_mapping.competitor_count,
          consumersPerComp: r.competitor_mapping.addressable_consumers_per_competitor,
          isUnderserved: r.opportunity_analysis.is_underserved,
        }))
        .sort((a, b) => b.consumersPerComp - a.consumersPerComp)
    : [];

  const topKey = rows[0]?.key;

  return (
    <div className="mt-8 border-t border-line pt-6">
      <button
        onClick={handleToggle}
        aria-expanded={open}
        className="group flex w-full items-center justify-between gap-3 rounded-2xl border-2 border-line bg-white px-5 py-4 text-left transition hover:border-pine/50 hover:bg-pine-tint focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-pine/20"
      >
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-pine-tint text-[22px]">📍</span>
          <div>
            <p className="text-[17px] font-bold text-ink leading-tight">Compare other blocks in {district}</p>
            <p className="text-[14px] text-ink-soft mt-0.5">See how this business would do in a different block nearby.</p>
          </div>
        </div>
        <ChevronIcon open={open} />
      </button>

      {open && (
        <div className="mt-4 rise-in">
          {loading && <SkeletonTable />}

          {error && (
            <div className="rounded-xl border border-clay/30 bg-clay-tint px-5 py-4 text-[16px] text-clay">
              Sorry, we could not load this right now. Please check your internet and try again.
            </div>
          )}

          {!loading && !error && rows.length > 0 && (
            <>
              <div className="mb-3 flex flex-wrap gap-3 text-[14px]">
                <LegendPill color="good" label="Good news" />
                <LegendPill color="gold" label="Be careful" />
                <LegendPill color="pine" label="Your block" />
              </div>

              <div className="overflow-x-auto rounded-2xl border border-line bg-white shadow-sm scrollbar-thin">
                <table className="w-full min-w-[520px] border-collapse text-[15px]">
                  <thead>
                    <tr className="bg-paper-dim border-b border-line">
                      <th className="px-4 py-3 text-left font-semibold text-ink-soft w-40">Block</th>
                      <th className="px-4 py-3 text-right font-semibold text-ink-soft">People who might buy</th>
                      <th className="px-4 py-3 text-right font-semibold text-ink-soft">Shops already there</th>
                      <th className="px-4 py-3 text-right font-semibold text-ink-soft">Customers per shop</th>
                      <th className="px-4 py-3 text-center font-semibold text-ink-soft">Signal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, idx) => (
                      <ComparisonRow key={row.key} row={row} isChosen={row.key === block} isTop={row.key === topKey} isLast={idx === rows.length - 1} />
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="mt-3 text-[13px] text-ink-faint leading-snug">
                Sorted by customers per existing shop (highest opportunity first). This is a hypothetical comparison,
                not your real filing - your actual profile stays {block}.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ComparisonRow({ row, isChosen, isTop, isLast }) {
  const rowBase = isChosen ? "bg-pine-tint border-l-4 border-l-pine" : row.isUnderserved ? "bg-good-tint/30 hover:bg-good-tint/50" : "bg-gold-tint/20 hover:bg-gold-tint/40";
  const borderBottom = isLast ? "" : "border-b border-line";

  return (
    <tr className={`${rowBase} ${borderBottom} transition`}>
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-ink leading-snug">{row.key}</span>
          {isChosen && <span className="inline-flex items-center rounded-full bg-pine px-2 py-0.5 text-[11px] font-bold text-white">Your block</span>}
          {isTop && !isChosen && <span className="inline-flex items-center rounded-full bg-good px-2 py-0.5 text-[11px] font-bold text-white">⭐ Top pick</span>}
        </div>
      </td>
      <td className="px-4 py-3.5 text-right">
        <span className="figure font-semibold text-ink">{formatCount(row.consumers)}</span>
      </td>
      <td className="px-4 py-3.5 text-right">
        <span className={`figure font-semibold ${row.competitors <= 5 ? "text-good-dim" : row.competitors >= 12 ? "text-clay" : "text-ink"}`}>{row.competitors}</span>
      </td>
      <td className="px-4 py-3.5 text-right">
        <span className="figure font-bold text-ink text-[16px]">{formatCount(row.consumersPerComp)}</span>
      </td>
      <td className="px-4 py-3.5 text-center">
        <MarketSignalChip underserved={row.isUnderserved} />
      </td>
    </tr>
  );
}

function MarketSignalChip({ underserved }) {
  return underserved ? (
    <span className="inline-flex items-center gap-1 rounded-full border border-good/40 bg-good-tint px-2.5 py-1 text-[12px] font-semibold text-good-dim whitespace-nowrap">
      <span className="h-1.5 w-1.5 rounded-full bg-good-dim" /> Good news
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full border border-gold/40 bg-gold-tint px-2.5 py-1 text-[12px] font-semibold text-gold whitespace-nowrap">
      <span className="h-1.5 w-1.5 rounded-full bg-gold" /> Be careful
    </span>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg className={`h-5 w-5 shrink-0 text-ink-faint transition-transform duration-300 ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
    </svg>
  );
}

function LegendPill({ color, label }) {
  const styles = { good: "bg-good-tint border-good/30 text-good-dim", gold: "bg-gold-tint border-gold/40 text-gold", pine: "bg-pine-tint border-pine/30 text-pine-dim" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 ${styles[color]}`}>
      <span className={`h-2 w-2 rounded-full ${color === "good" ? "bg-good-dim" : color === "gold" ? "bg-gold" : "bg-pine"}`} />
      {label}
    </span>
  );
}

function SkeletonTable() {
  return (
    <div className="rounded-2xl border border-line bg-white overflow-hidden shadow-sm animate-pulse">
      <div className="bg-paper-dim border-b border-line px-4 py-3 flex gap-4">
        {[30, 20, 20, 20].map((w, i) => (
          <div key={i} className="h-3 rounded bg-line-strong" style={{ width: `${w}%` }} />
        ))}
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="border-b border-line last:border-b-0 px-4 py-4 flex gap-4 items-center">
          <div className="h-3 rounded bg-line" style={{ width: "28%" }} />
          <div className="ml-auto h-3 rounded bg-line" style={{ width: "14%" }} />
          <div className="h-3 rounded bg-line" style={{ width: "14%" }} />
          <div className="h-5 rounded-full bg-line" style={{ width: "18%" }} />
        </div>
      ))}
    </div>
  );
}
