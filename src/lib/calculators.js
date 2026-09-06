// Pure, deterministic financial calculators, mirrored 1:1 with
// backend/deterministic.py so the instant client-side preview always
// matches what the Python backend would return for the same inputs.

export function calcBreakEven({ fixedCosts, variableCostPerUnit, pricePerUnit }) {
  const fc = Number(fixedCosts) || 0;
  const vc = Number(variableCostPerUnit) || 0;
  const price = Number(pricePerUnit) || 0;

  const contributionMargin = price - vc;
  const contributionMarginPct = price > 0 ? (contributionMargin / price) * 100 : 0;
  const isViable = contributionMargin > 0;
  const breakEvenUnits = isViable ? fc / contributionMargin : null;
  const breakEvenRevenue = isViable ? breakEvenUnits * price : null;

  return { fixedCosts: fc, variableCostPerUnit: vc, pricePerUnit: price, contributionMargin, contributionMarginPct, isViable, breakEvenUnits, breakEvenRevenue };
}

export function calcPricingCheck({ unitCost, desiredMarginPct, marketPrice }) {
  const cost = Number(unitCost) || 0;
  const marginPct = Number(desiredMarginPct) || 0;
  const market = Number(marketPrice) || 0;

  const costPlusPrice = cost * (1 + marginPct / 100);
  const gapVsMarket = market - costPlusPrice;
  const gapVsMarketPct = costPlusPrice > 0 ? (gapVsMarket / costPlusPrice) * 100 : 0;

  let verdict = "insufficient_data";
  if (cost > 0 && market > 0) verdict = costPlusPrice <= market ? "room_to_compete" : "needs_adjustment";
  const marginAtMarketPrice = cost > 0 ? ((market - cost) / cost) * 100 : 0;

  return { unitCost: cost, desiredMarginPct: marginPct, marketPrice: market, costPlusPrice, gapVsMarket, gapVsMarketPct, marginAtMarketPrice, verdict };
}

export function calcWorkingCapital({ monthlyExpenses, inventoryDays, receivableDays }) {
  const expenses = Number(monthlyExpenses) || 0;
  const invDays = Number(inventoryDays) || 0;
  const recDays = Number(receivableDays) || 0;

  const dailyExpense = expenses / 30;
  const cashCycleDays = invDays + recDays;
  const workingCapitalNeeded = dailyExpense * cashCycleDays;

  return { monthlyExpenses: expenses, inventoryDays: invDays, receivableDays: recDays, dailyExpense, cashCycleDays, workingCapitalNeeded };
}
