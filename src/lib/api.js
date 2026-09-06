const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8003";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request to ${path} failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  getCities: () => request("/api/cities"),

  agentTurn: (message, history, profileSoFar) =>
    request("/api/agent/turn", {
      method: "POST",
      body: JSON.stringify({ message, history, profile_so_far: profileSoFar }),
    }),

  financialStructuring: (availableMarginCapital) =>
    request("/api/financial-structuring", {
      method: "POST",
      body: JSON.stringify({ available_margin_capital: availableMarginCapital }),
    }),

  repaymentSchedule: (principal, annualRatePct, tenureMonths, moratoriumMonths) =>
    request("/api/repayment-schedule", {
      method: "POST",
      body: JSON.stringify({
        principal,
        annual_rate_pct: annualRatePct,
        tenure_months: tenureMonths,
        moratorium_months: moratoriumMonths,
      }),
    }),

  workingCapital: (monthlyOperationalCost, inventoryDays, receivableDays, monthlyEmi) =>
    request("/api/working-capital", {
      method: "POST",
      body: JSON.stringify({
        monthly_operational_cost: monthlyOperationalCost,
        inventory_days: inventoryDays,
        receivable_days: receivableDays,
        monthly_emi: monthlyEmi,
      }),
    }),

  feasibilityReport: (district, block, businessType) =>
    request("/api/feasibility-report", {
      method: "POST",
      body: JSON.stringify({ district, block, business_type: businessType }),
    }),

  feasibilityChat: (message, history, district, block, businessType) =>
    request("/api/feasibility-agent/chat", {
      method: "POST",
      body: JSON.stringify({ message, history, district, block, business_type: businessType }),
    }),

  advisory: (payload) =>
    request("/api/advisory", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
