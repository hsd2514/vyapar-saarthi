import { useNavigate } from "react-router-dom";
import { Button } from "./ui";
import { useAppState } from "../context/AppContext";

export default function StepFooter({ backTo, nextTo, nextLabel, onNext, nextDisabled }) {
  const navigate = useNavigate();
  const { t } = useAppState();
  return (
    <div className="mt-10 flex items-center justify-between gap-3 no-print">
      {backTo ? (
        <Button variant="secondary" onClick={() => navigate(backTo)}>
          ← {t("common.back")}
        </Button>
      ) : (
        <span />
      )}
      {nextTo && (
        <Button
          disabled={nextDisabled}
          onClick={() => {
            onNext?.();
            navigate(nextTo);
          }}
        >
          {nextLabel || t("common.next")} →
        </Button>
      )}
    </div>
  );
}
