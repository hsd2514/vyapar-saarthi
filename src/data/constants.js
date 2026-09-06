export const BUSINESS_TYPE_LABELS = {
  vendor: "Vegetables & fruit",
  dairy: "Milk & dairy",
  textiles: "Tailoring & cloth",
  retail: "Kirana shop",
  handicrafts: "Handicrafts",
  food_stall: "Food stall",
};

// Typical monthly running costs per business category, used to pre-fill the
// planning estimate. A lookup table, never a guess, always editable.
export const OPERATIONS_BENCHMARKS = {
  vendor: { monthlyOperationalCost: 8000, inventoryDays: 3, receivableDays: 1 },
  dairy: { monthlyOperationalCost: 14000, inventoryDays: 2, receivableDays: 7 },
  textiles: { monthlyOperationalCost: 11000, inventoryDays: 15, receivableDays: 10 },
  retail: { monthlyOperationalCost: 16000, inventoryDays: 20, receivableDays: 5 },
  handicrafts: { monthlyOperationalCost: 7000, inventoryDays: 25, receivableDays: 15 },
  food_stall: { monthlyOperationalCost: 9000, inventoryDays: 2, receivableDays: 1 },
};

/**
 * Rupees the way people here actually say them: "₹9 lakh", "₹1.4 lakh",
 * "₹12,000". Reading "Rs 9,00,000" digit by digit is real friction for
 * someone who isn't comfortable with numbers on a screen.
 */
export function formatINR(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
  const v = Math.round(Number(n));
  if (Math.abs(v) >= 10000000) return `₹${trim(v / 10000000)} crore`;
  if (Math.abs(v) >= 100000) return `₹${trim(v / 100000)} lakh`;
  return `₹${v.toLocaleString("en-IN")}`;
}

/** Exact rupees, for the printed record where precision matters. */
export function formatINRExact(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
  return "₹" + Math.round(Number(n)).toLocaleString("en-IN");
}

function trim(x) {
  const r = Math.round(x * 100) / 100;
  return Number.isInteger(r) ? String(r) : r.toFixed(r < 10 ? 2 : 1).replace(/\.?0+$/, "");
}

/** Large counts, said plainly: "1.7 lakh people" rather than "168,700". */
export function formatCount(n) {
  const v = Math.round(Number(n) || 0);
  if (v >= 100000) return `${trim(v / 100000)} lakh`;
  return v.toLocaleString("en-IN");
}
