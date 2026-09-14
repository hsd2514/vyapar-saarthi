import { useEffect, useState } from "react";
import { Tag, HourglassMedium } from "@phosphor-icons/react";
import { forumApi } from "../../lib/forumApi";
import { formatINR } from "../../data/constants";
import { useForum } from "../../context/ForumContext";

/**
 * What members report they actually paid, and how long their loans
 * actually took - aggregated per district. This is the forum acting as a
 * sensor, not just a chat: the numbers are tagged USER_REPORTED and are
 * meant to sit beside the official figures, never replace them.
 */
export default function CrowdPanel({ trade, district }) {
  const { lookup } = useForum();
  const [prices, setPrices] = useState([]);
  const [waits, setWaits] = useState([]);

  useEffect(() => {
    forumApi.priceSummary({ trade, district }).then((r) => setPrices(r.summary.slice(0, 4))).catch(() => setPrices([]));
    forumApi.waitSummary({ district }).then((r) => setWaits(r.summary.slice(0, 2))).catch(() => setWaits([]));
  }, [trade, district]);

  if (prices.length === 0 && waits.length === 0) return null;
  const place = lookup.district[district] || "all districts";

  return (
    <div className="grid gap-3 sm:grid-cols-2 mb-5">
      {prices.length > 0 && (
        <div className="rounded-xl border-2 border-line bg-white p-4">
          <p className="flex items-center gap-2 text-[14px] font-semibold text-ink-soft mb-2"><Tag size={16} weight="fill" className="text-pine" /> What members paid · {place}</p>
          <ul className="space-y-1.5">
            {prices.map((p) => (
              <li key={`${p.item}-${p.district}`} className="flex items-baseline justify-between gap-3 text-[15px]">
                <span className="text-ink">{p.item} <span className="text-ink-faint">/ {p.unit}</span></span>
                <span className="figure font-semibold text-ink whitespace-nowrap">{formatINR(p.median)} <span className="text-[13px] font-normal text-ink-soft">({p.n})</span></span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[12.5px] text-ink-faint">Median of member reports, last 6 months. Not the official unit cost.</p>
        </div>
      )}
      {waits.length > 0 && (
        <div className="rounded-xl border-2 border-line bg-white p-4">
          <p className="flex items-center gap-2 text-[14px] font-semibold text-ink-soft mb-2"><HourglassMedium size={16} weight="fill" className="text-pine" /> How long loans took · {place}</p>
          <ul className="space-y-1.5">
            {waits.map((w) => (
              <li key={`${w.agency}-${w.district}`} className="text-[15px] text-ink">
                <span className="font-semibold">{w.agency}</span> <span className="text-ink-soft">({w.n} reports)</span>
                <div className="text-[14px] text-ink-soft">
                  {w.median_months_to_sanction != null && <>apply → sanction ~{w.median_months_to_sanction} mo</>}
                  {w.median_months_sanction_to_money != null && <> · sanction → money ~{w.median_months_sanction_to_money} mo</>}
                  {w.still_waiting > 0 && <> · {w.still_waiting} still waiting</>}
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[12.5px] text-ink-faint">Reported by members. Plan for this wait; do not borrow your margin to bridge it.</p>
        </div>
      )}
    </div>
  );
}
