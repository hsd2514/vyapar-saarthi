/**
 * Client for Vyapar Chaupal (the forum) - /api/forum/*.
 *
 * Kept separate from api.js because this is the one part of the app that
 * carries a sign-in: every call sends the member's bearer token when there
 * is one. The token lives in localStorage under its own key so clearing
 * the wizard's saved plan never signs someone out of the forum, and vice
 * versa.
 */

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8003";
const TOKEN_KEY = "vyapar-chaupal-token-v1";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode etc. - forum still works for this tab */
  }
}

async function request(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const err = new Error(detail.detail || `Request to ${path} failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

const qs = (params) => {
  const s = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
  return s ? `?${s}` : "";
};

export const forumApi = {
  labels: () => request("/api/forum/labels"),

  requestOtp: (phone) => request("/api/forum/auth/otp", { method: "POST", body: JSON.stringify({ phone }) }),
  verifyOtp: (phone, code, profile) =>
    request("/api/forum/auth/verify", { method: "POST", body: JSON.stringify({ phone, code, profile: profile || null }) }),
  me: () => request("/api/forum/me"),

  listThreads: (filters) => request(`/api/forum/threads${qs(filters)}`),
  getThread: (id) => request(`/api/forum/threads/${encodeURIComponent(id)}`),
  checkBeforePost: (body, trade) => request("/api/forum/threads/check", { method: "POST", body: JSON.stringify({ body, trade }) }),
  createThread: (payload) => request("/api/forum/threads", { method: "POST", body: JSON.stringify(payload) }),
  addReply: (threadId, payload) =>
    request(`/api/forum/threads/${encodeURIComponent(threadId)}/replies`, { method: "POST", body: JSON.stringify(payload) }),
  connect: (threadId, message) =>
    request(`/api/forum/threads/${encodeURIComponent(threadId)}/connect`, { method: "POST", body: JSON.stringify({ message }) }),
  report: (targetType, targetId, reason) =>
    request("/api/forum/report", { method: "POST", body: JSON.stringify({ target_type: targetType, target_id: targetId, reason }) }),

  priceSummary: (filters) => request(`/api/forum/price-summary${qs(filters)}`),
  waitSummary: (filters) => request(`/api/forum/wait-summary${qs(filters)}`),

  modQueue: () => request("/api/forum/mod/queue"),
  modThread: (id, action) => request(`/api/forum/mod/threads/${encodeURIComponent(id)}`, { method: "POST", body: JSON.stringify({ action }) }),
  modReply: (id, action) => request(`/api/forum/mod/replies/${encodeURIComponent(id)}`, { method: "POST", body: JSON.stringify({ action }) }),
  modConnect: (id, action) => request(`/api/forum/mod/connects/${encodeURIComponent(id)}`, { method: "POST", body: JSON.stringify({ action }) }),
};
