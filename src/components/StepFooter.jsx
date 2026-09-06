import { useNavigate } from "react-router-dom";
import { Button } from "./ui";

export default function StepFooter({ backTo, nextTo, nextLabel = "Continue", onNext, nextDisabled }) {
  const navigate = useNavigate();
  return (
    <div className="mt-10 flex items-center justify-between gap-3 no-print">
      {backTo ? (
        <Button variant="secondary" onClick={() => navigate(backTo)}>
          ← Back
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
          {nextLabel} →
        </Button>
      )}
    </div>
  );
}
