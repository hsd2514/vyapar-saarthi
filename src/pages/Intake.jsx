import { useEffect, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { BUSINESS_TYPE_LABELS } from "../data/constants";
import { Card, PageHeader, SectionLabel, Field, TextInput, Select, NumberInput, Badge } from "../components/ui";
import StepFooter from "../components/StepFooter";
import VoiceAgent from "../components/VoiceAgent";

const REQUIRED_FIELDS = ["businessType", "district", "block", "availableMarginCapital"];

export default function Intake() {
  const { profile, updateProfile, intakeDone, markStepReached } = useAppState();
  const [districts, setDistricts] = useState([]);

  useEffect(() => {
    api.getCities().then((res) => setDistricts(res.districts)).catch(() => setDistricts([]));
  }, []);

  const isValid = REQUIRED_FIELDS.every((f) => profile[f] !== "" && profile[f] !== undefined && profile[f] !== null);
  const currentDistrict = districts.find((d) => d.key === profile.district);
  const projectCostPreview = profile.availableMarginCapital ? Number(profile.availableMarginCapital) / 0.1 : null;

  return (
    <div>
      <PageHeader
        eyebrow="Step 1 of 5"
        title="Tell Saarthi about your business, out loud"
        description="Speak naturally - Saarthi asks one question at a time and fills the profile below as you go. You can correct anything by hand afterward."
      />

      <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6 items-stretch">
        <VoiceAgent onDone={() => markStepReached(1)} />

        <Card>
          <div className="flex items-center justify-between mb-4">
            <SectionLabel>Extracted profile</SectionLabel>
            {intakeDone ? <Badge tone="pine">Intake complete</Badge> : <Badge tone="gold">In progress</Badge>}
          </div>

          <div className="space-y-4">
            <Field label="Business category">
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
              <Field label="District">
                <Select value={profile.district} onChange={(e) => updateProfile({ district: e.target.value, block: "" })}>
                  <option value="">Not yet mentioned</option>
                  {districts.map((d) => (
                    <option key={d.key} value={d.key}>
                      {d.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Block">
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

            <Field label="Village" hint="Optional">
              <TextInput value={profile.village} onChange={(e) => updateProfile({ village: e.target.value })} placeholder="e.g. Ambulga" />
            </Field>

            <Field label="Available margin capital" hint="The cash you already have saved to contribute as your own 10% share">
              <NumberInput prefix="Rs" value={profile.availableMarginCapital} onChange={(e) => updateProfile({ availableMarginCapital: e.target.value })} placeholder="e.g. 100000" />
            </Field>
          </div>

          {projectCostPreview && (
            <div className="mt-4 rounded-lg border border-pine/25 bg-pine-tint/40 px-3.5 py-2.5 text-sm text-ink-soft">
              At 10% margin, this implies a project cost of roughly <b className="text-ink num">Rs {Math.round(projectCostPreview).toLocaleString("en-IN")}</b> - the next step works out the exact loan and scheme.
            </div>
          )}

          {currentDistrict && (
            <p className="mt-4 text-xs text-ink-faint border-t border-line pt-3">{currentDistrict.note}</p>
          )}
        </Card>
      </div>

      <StepFooter nextTo="/feasibility" nextDisabled={!isValid} nextLabel="Continue to feasibility report" />
    </div>
  );
}
