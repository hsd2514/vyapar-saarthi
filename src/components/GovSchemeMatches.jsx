/**
 * GovSchemeMatches — ranks real government MSME credit schemes (PMEGP, Mudra
 * tiers, Stand-Up India) plus this tool's own margin-money scheme against
 * the entrepreneur's computed project cost, using the weighted rules engine
 * in backend/schemes.py. Each row shows the visible weight breakdown that
 * produced its score and a link to the scheme's real official portal.
 */
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { formatINR } from "../data/constants";
import { Spinner } from "./ui";

const FACTOR_LABELS = {
  cost_band_fit: "Fits your project size",
  collateral_free: "No collateral needed",
  subsidy: "Subsidy on offer",
  category_match: "Matches your business stage",
};

export default function GovSchemeMatches({ projectCost, businessType }) {
  const [matches, setMatches] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!projectCost) return;
    api
      .schemeMatch(projectCost, businessType)
      .then((res) => setMatches(res.matches))
      .catch((e) => setError(e.message));
  }, [projectCost, businessType]);

  if (error) return null; // non-critical panel - fail quietly rather than block the page
  if (!matches) {
    return (
      <div className="flex items-center gap-2 text-ink-soft text-[15px] py-4">
        <Spinner className="text-pine" /> Checking which government schemes match...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[15px] text-ink-soft leading-relaxed">
        Ranked by fit for your project cost of {formatINR(projectCost)} - each score is a plain, visible sum of the factors below it, not a guess.
      </p>
      {matches.map((m, i) => (
        <div
          key={m.id}
          className={`rounded-xl border-2 p-4 ${
            i === 0 ? "border-pine bg-pine-tint" : "border-line bg-white"
          }`}
        >
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <p className="font-display font-bold text-[16px] text-ink leading-tight">{m.name}</p>
                {businessType && m.business_types?.includes(businessType) && (
                  <span className="inline-flex items-center rounded-full bg-good px-2 py-0.5 text-[11px] font-bold text-white whitespace-nowrap">
                    Built for your business
                  </span>
                )}
              </div>
              <p className="text-[13px] text-ink-faint mt-0.5">{m.operator}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className={`figure font-bold text-[20px] ${i === 0 ? "text-pine-dim" : "text-ink"}`}>
                {m.match_score}
              </span>
              <span className="text-[12px] text-ink-faint">/ 100 match</span>
            </div>
          </div>

          <p className="text-[14px] text-ink-soft mt-2 leading-relaxed">{m.note}</p>

          <div className="flex flex-wrap gap-1.5 mt-3">
            {Object.entries(m.score_breakdown).map(([factor, points]) => (
              <span
                key={factor}
                className="inline-flex items-center gap-1 rounded-full border border-line bg-paper-dim px-2.5 py-1 text-[12px] text-ink-soft"
              >
                {FACTOR_LABELS[factor] || factor}: <span className="font-semibold text-ink">{points}</span>
              </span>
            ))}
          </div>

          <a
            href={m.portal_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-3 text-[14px] font-semibold text-pine-dim underline underline-offset-2"
          >
            Apply / verify on the official portal ↗
          </a>
        </div>
      ))}
    </div>
  );
}
