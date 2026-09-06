export const BUSINESS_TYPE_LABELS = {
  vendor: "Vegetable / Fruit Vendor",
  dairy: "Dairy (Milk & Products)",
  textiles: "Textiles & Tailoring",
  retail: "Retail / Kirana Shop",
  handicrafts: "Handicrafts",
  food_stall: "Food Stall / Snacks",
};

// Typical operational cost benchmarks per business type, used to
// auto-suggest the working-capital-by-phase inputs - a lookup table,
// never a guess, always editable.
export const OPERATIONS_BENCHMARKS = {
  vendor: { monthlyOperationalCost: 8000, inventoryDays: 3, receivableDays: 1 },
  dairy: { monthlyOperationalCost: 14000, inventoryDays: 2, receivableDays: 7 },
  textiles: { monthlyOperationalCost: 11000, inventoryDays: 15, receivableDays: 10 },
  retail: { monthlyOperationalCost: 16000, inventoryDays: 20, receivableDays: 5 },
  handicrafts: { monthlyOperationalCost: 7000, inventoryDays: 25, receivableDays: 15 },
  food_stall: { monthlyOperationalCost: 9000, inventoryDays: 2, receivableDays: 1 },
};

export function formatINR(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return "Rs " + Math.round(n).toLocaleString("en-IN");
}
