import { useNavigate } from "react-router-dom";
import { UsersThree } from "@phosphor-icons/react";
import { useAppState } from "../../context/AppContext";

/**
 * "Ask others like you" - the bridge from a report page into Chaupal.
 * Carries only trade, district and a suggested topic/title into the
 * compose dialog. Never the person's financial inputs: those stay in
 * their own plan, and the forum shows trade + place + stage only.
 */
export default function AskChaupal({ topic, title }) {
  const { profile, t } = useAppState();
  const navigate = useNavigate();
  const params = new URLSearchParams({
    compose: "question",
    topic: topic || "",
    title: title || "",
    trade: profile.businessType || "",
    district: profile.district || "",
  });
  return (
    <div className="no-print mt-8 flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 border-gold/40 bg-gold-tint px-5 py-4">
      <div className="flex items-start gap-3">
        <UsersThree size={26} weight="fill" className="text-gold shrink-0 mt-0.5" />
        <div>
          <p className="text-[16px] font-semibold text-ink">{t("chaupal.askOthers")}</p>
          <p className="text-[14.5px] text-ink-soft leading-snug">People in your trade who have already applied, waited, and repaid - and the officers who answer them.</p>
        </div>
      </div>
      <button
        type="button"
        onClick={() => navigate(`/chaupal?${params.toString()}`)}
        className="inline-flex items-center gap-2 rounded-xl bg-white border-2 border-gold/40 px-4 py-2.5 text-[15px] font-bold text-gold hover:border-gold transition"
      >
        Open Chaupal →
      </button>
    </div>
  );
}
