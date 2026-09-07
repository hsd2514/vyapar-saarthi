import { useEffect, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS, formatINR } from "../data/constants";
import { Card, PageHeader, Field, TextInput, Select, NumberInput, Badge } from "../components/ui";
import StepFooter from "../components/StepFooter";
import VoiceAgent from "../components/VoiceAgent";

const REQUIRED_FIELDS = ["businessType", "district", "block", "availableMarginCapital"];

export default function Intake() {
  const { profile, updateProfile, intakeDone, markStepReached } = useAppState();
  const [districts, setDistricts] = useState([]);
  const [useTypedMode, setUseTypedMode] = useState(false);


  useEffect(() => {
    api.getCities().then((res) => setDistricts(res.districts)).catch(() => setDistricts([]));
  }, []);

  const isValid =
    REQUIRED_FIELDS.every((f) => profile[f] !== "" && profile[f] !== undefined && profile[f] !== null) &&
    Number(profile.availableMarginCapital) > 0;
  const currentDistrict = districts.find((d) => d.key === profile.district);
  const projectCostPreview = profile.availableMarginCapital ? Number(profile.availableMarginCapital) / 0.1 : null;

  return (
    <div>
      <PageHeader
        eyebrow="Step 1 of 5"
        title="Tell us about the business you want to start"
        description="Talk to Saarthi like you would to a person. It will ask one thing at a time and fill in the answers here. You can also type or change anything yourself."
      />

      <div className={`grid gap-6 items-stretch ${useTypedMode ? "max-w-2xl mx-auto" : "lg:grid-cols-[1.1fr_0.9fr]"}`}>
        {!useTypedMode && (
          <div className="flex flex-col gap-3">
            <VoiceAgent onDone={() => markStepReached(1)} />
            <button onClick={() => setUseTypedMode(true)} className="text-sm font-medium text-pine underline text-center hover:text-pine-dim transition-colors">
              Type instead (Skip voice agent)
            </button>
          </div>
        )}

        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2 mb-5">
            <h2 className="font-display text-xl font-bold text-ink">{useTypedMode ? "Fill your business details" : "Your answers"}</h2>
            {useTypedMode ? (
              <button onClick={() => setUseTypedMode(false)} className="text-sm font-medium text-pine underline hover:text-pine-dim transition-colors">
                Use voice instead
              </button>
            ) : (
              intakeDone ? <Badge tone="good">All done</Badge> : <Badge tone="gold">Still asking</Badge>
            )}
          </div>

          <div className="space-y-5">
            <Field label="What kind of business?">
              <Select value={profile.businessType} onChange={(e) => updateProfile({ businessType: e.target.value })}>
                <option value="">Not answered yet</option>
                {Object.entries(BUSINESS_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>

            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="District">
                <Select value={profile.district} onChange={(e) => updateProfile({ district: e.target.value, block: "" })}>
                  <option value="">Not answered yet</option>
                  {districts.map((d) => (
                    <option key={d.key} value={d.key}>
                      {d.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Block (taluka)">
                <Select value={profile.block} onChange={(e) => updateProfile({ block: e.target.value })} disabled={!currentDistrict}>
                  <option value="">Not answered yet</option>
                  {(currentDistrict?.blocks || []).map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>

            <Field label="Village name" hint="You can leave this empty">
              <TextInput value={profile.village} onChange={(e) => updateProfile({ village: e.target.value })} placeholder="e.g. Ambulga" />
            </Field>

            <Field label="Money you already have saved" hint="Your own money that you can put into the business. The scheme lends the rest.">
              <NumberInput prefix="₹" min="1" value={profile.availableMarginCapital} onChange={(e) => updateProfile({ availableMarginCapital: e.target.value })} placeholder="1,00,000" />
            </Field>
          </div>

          {projectCostPreview > 0 && (
            <div className="mt-5 rounded-xl border-2 border-pine/25 bg-pine-tint px-4 py-3.5 text-[16px] text-ink-soft leading-relaxed">
              With this much of your own money, you could start a business worth about{" "}
              <b className="figure text-ink text-[19px]">{formatINR(projectCostPreview)}</b>. We work out the exact loan next.
            </div>
          )}

          {currentDistrict && (
            <p className="mt-5 text-[15px] text-ink-soft border-t border-line pt-4 leading-relaxed">{currentDistrict.note}</p>
          )}
        </Card>
      </div>

      <StepFooter nextTo="/feasibility" nextDisabled={!isValid} nextLabel="See if it will work here" onNext={() => markStepReached(1)} />
    </div>
  );
}
