import { useEffect, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS, CHALLENGE_LABELS } from "../data/constants";
import { Card, PageHeader, SectionLabel, Field, TextInput, Select, NumberInput, Checkbox, Badge } from "../components/ui";
import StepFooter from "../components/StepFooter";
import VoiceAgent from "../components/VoiceAgent";

const REQUIRED_FIELDS = ["businessType", "district", "block", "monthlyRevenue", "yearsInOperation"];

export default function Intake() {
  const { profile, fieldConfidence, updateProfile, intakeDone, markStepReached } = useAppState();
  const [districts, setDistricts] = useState([]);

  useEffect(() => {
    api.getCities().then((res) => setDistricts(res.districts)).catch(() => setDistricts([]));
  }, []);

  const toggleChallenge = (value) => {
    const has = profile.challenges.includes(value);
    updateProfile({ challenges: has ? profile.challenges.filter((c) => c !== value) : [...profile.challenges, value] });
  };

  const isValid = REQUIRED_FIELDS.every((f) => profile[f] !== "" && profile[f] !== undefined && profile[f] !== null);
  const currentDistrict = districts.find((d) => d.key === profile.district);

  // Map backend snake_case field names to frontend camelCase keys used in fieldConfidence.
  const FIELD_KEY_MAP = {
    businessType: "business_type",
    district: "district",
    block: "block",
    monthlyRevenue: "monthly_revenue",
    yearsInOperation: "years_in_operation",
  };

  /** Amber dot shown when the agent flagged this field as low-confidence. */
  function ConfidenceDot({ fieldKey }) {
    const backendKey = FIELD_KEY_MAP[fieldKey];
    if (!backendKey || fieldConfidence[backendKey] !== "low") return null;
    return (
      <span
        title="Saarthi marked this value as approximate or uncertain — please double-check before continuing"
        className="ml-1.5 inline-flex items-center"
      >
        <span className="h-2 w-2 rounded-full bg-[#d4860a] inline-block" aria-label="Low confidence — verify this value" />
        <span className="ml-1 text-[10px] font-mono text-[#7a5a12] leading-none">approx.</span>
      </span>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Step 1 of 5"
        title="Tell Saarthi about your business, out loud"
        description="Speak naturally - Saarthi asks one question at a time and fills the profile below as you go. You can correct anything by hand afterward."
      />

      <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6 items-start">
        <VoiceAgent onDone={() => markStepReached(1)} />

        <Card>
          <div className="flex items-center justify-between mb-4">
            <SectionLabel>Extracted profile</SectionLabel>
            {intakeDone ? <Badge tone="pine">Intake complete</Badge> : <Badge tone="gold">In progress</Badge>}
          </div>

          <div className="space-y-4">
            <Field label={<span className="flex items-center">Business type<ConfidenceDot fieldKey="businessType" /></span>}>
              <Select value={profile.businessType} onChange={(e) => updateProfile({ businessType: e.target.value })}>
                <option value="">Not yet mentioned</option>
                {Object.entries(BUSINESS_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label={<span className="flex items-center">District<ConfidenceDot fieldKey="district" /></span>}>
                <Select value={profile.district} onChange={(e) => updateProfile({ district: e.target.value, block: "" })}>
                  <option value="">Not yet mentioned</option>
                  {districts.map((d) => (
                    <option key={d.key} value={d.key}>
                      {d.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={<span className="flex items-center">Block<ConfidenceDot fieldKey="block" /></span>}>
                <Select value={profile.block} onChange={(e) => updateProfile({ block: e.target.value })} disabled={!currentDistrict}>
                  <option value="">Not yet mentioned</option>
                  {(currentDistrict?.blocks || []).map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label={<span className="flex items-center">Monthly revenue<ConfidenceDot fieldKey="monthlyRevenue" /></span>}>
                <NumberInput prefix="Rs" value={profile.monthlyRevenue} onChange={(e) => updateProfile({ monthlyRevenue: e.target.value })} placeholder="e.g. 18000" />
              </Field>
              <Field label={<span className="flex items-center">Years running<ConfidenceDot fieldKey="yearsInOperation" /></span>}>
                <NumberInput suffix="yrs" value={profile.yearsInOperation} onChange={(e) => updateProfile({ yearsInOperation: e.target.value })} placeholder="e.g. 2" />
              </Field>
            </div>

            <Field label="Challenges mentioned">
              <div className="grid grid-cols-1 gap-2 mt-1">
                {Object.entries(CHALLENGE_LABELS).map(([value, label]) => (
                  <Checkbox key={value} label={label} checked={profile.challenges.includes(value)} onChange={() => toggleChallenge(value)} />
                ))}
              </div>
            </Field>
          </div>

          {currentDistrict && (
            <p className="mt-4 text-xs text-ink-faint border-t border-line pt-3">{currentDistrict.note}</p>
          )}
        </Card>
      </div>

      <StepFooter nextTo="/calculators" nextDisabled={!isValid} nextLabel="Continue to calculators" />
    </div>
  );
}
