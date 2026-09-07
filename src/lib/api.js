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

  repaymentSchedule: (principal, annualRatePct, tenureMonths, moratoriumMonths, capitalizeInterest = false) =>
    request("/api/repayment-schedule", {
      method: "POST",
      body: JSON.stringify({
        principal,
        annual_rate_pct: annualRatePct,
        tenure_months: tenureMonths,
        moratorium_months: moratoriumMonths,
        capitalize_interest: capitalizeInterest,
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

  feasibilityCompare: (district, block) =>
    request(`/api/feasibility-report/compare?district=${encodeURIComponent(district)}&block=${encodeURIComponent(block)}`),

  feasibilityCompareBlocks: (district, businessType) =>
    request(`/api/feasibility-report/compare-blocks?district=${encodeURIComponent(district)}&business_type=${encodeURIComponent(businessType)}`),

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

  getContacts: (district, block) =>
    request(`/api/contacts?district=${encodeURIComponent(district)}&block=${encodeURIComponent(block)}`),

  /**
   * Store a compiled summary snapshot on the backend and receive a shareable
   * link (valid for 24 hours, cleared on server restart).
   * @param {object} payload - Full summary data to persist.
   * @param {string} [origin] - Frontend origin used to build the share URL.
   */
  shareCreate: (payload, origin = window.location.origin) =>
    request(`/api/summary/share?frontend_origin=${encodeURIComponent(origin)}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /**
   * Retrieve a stored summary snapshot by its share ID.
   * Throws if the ID is unknown or expired (server returns 404).
   */
  shareGet: (shareId) => request(`/api/summary/share/${encodeURIComponent(shareId)}`),
};
