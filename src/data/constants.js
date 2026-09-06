export const BUSINESS_TYPE_LABELS = {
  vendor: "Vegetable / Fruit Vendor",
  dairy: "Dairy (Milk & Products)",
  tailoring: "Tailoring & Stitching",
  retail: "Retail / Kirana Shop",
  handicrafts: "Handicrafts",
  food_stall: "Food Stall / Snacks",
};

export const CHALLENGE_LABELS = {
  pricing: "Pricing my product/service correctly",
  stock: "Stock / inventory planning",
  credit: "Access to credit or loans",
  seasonal: "Seasonal swings in demand",
  records: "Record keeping / bookkeeping",
};

// Typical per-unit economics used to auto-suggest calculator inputs once a
// business type is known - the same idea as the deterministic viability
// lookup: a starting point from a table, never a guess, always editable.
export const CALCULATOR_BENCHMARKS = {
  vendor: { unitLabel: "kg of produce sold", breakEven: { fixedCosts: 3500, variableCostPerUnit: 18, pricePerUnit: 25 }, pricing: { unitCost: 18, desiredMarginPct: 20, marketPrice: 24 }, workingCapital: { inventoryDays: 3, receivableDays: 1 } },
  dairy: { unitLabel: "litre of milk sold", breakEven: { fixedCosts: 6000, variableCostPerUnit: 34, pricePerUnit: 48 }, pricing: { unitCost: 34, desiredMarginPct: 18, marketPrice: 47 }, workingCapital: { inventoryDays: 2, receivableDays: 7 } },
  tailoring: { unitLabel: "garment stitched", breakEven: { fixedCosts: 5500, variableCostPerUnit: 180, pricePerUnit: 400 }, pricing: { unitCost: 180, desiredMarginPct: 35, marketPrice: 380 }, workingCapital: { inventoryDays: 15, receivableDays: 10 } },
  retail: { unitLabel: "basket sold", breakEven: { fixedCosts: 8000, variableCostPerUnit: 100, pricePerUnit: 118 }, pricing: { unitCost: 100, desiredMarginPct: 15, marketPrice: 115 }, workingCapital: { inventoryDays: 20, receivableDays: 5 } },
  handicrafts: { unitLabel: "piece sold", breakEven: { fixedCosts: 4000, variableCostPerUnit: 90, pricePerUnit: 220 }, pricing: { unitCost: 90, desiredMarginPct: 40, marketPrice: 200 }, workingCapital: { inventoryDays: 25, receivableDays: 15 } },
  food_stall: { unitLabel: "plate/snack sold", breakEven: { fixedCosts: 4500, variableCostPerUnit: 22, pricePerUnit: 40 }, pricing: { unitCost: 22, desiredMarginPct: 30, marketPrice: 38 }, workingCapital: { inventoryDays: 2, receivableDays: 1 } },
};

export function formatINR(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return "Rs " + Math.round(n).toLocaleString("en-IN");
}
