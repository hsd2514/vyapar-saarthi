const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

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

  viability: (district, businessType) =>
    request("/api/viability", {
      method: "POST",
      body: JSON.stringify({ district, business_type: businessType }),
    }),

  schemes: (monthlyRevenue, yearsInOperation, businessType) =>
    request("/api/schemes", {
      method: "POST",
      body: JSON.stringify({
        monthly_revenue: monthlyRevenue,
        years_in_operation: yearsInOperation,
        business_type: businessType,
      }),
    }),

  advisory: (payload) =>
    request("/api/advisory", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  weatherAdvisory: (district, businessType) =>
    request(`/api/weather-advisory?district=${encodeURIComponent(district)}&business_type=${encodeURIComponent(businessType)}`),
};
