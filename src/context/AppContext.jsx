import { createContext, useContext, useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "vyapar-saarthi-voice-v1";

const defaultProfile = {
  businessType: "",
  district: "",
  block: "",
  monthlyRevenue: "",
  yearsInOperation: "",
  challenges: [],
};

const defaultCalculators = {
  breakEven: { fixedCosts: "", variableCostPerUnit: "", pricePerUnit: "" },
  pricing: { unitCost: "", desiredMarginPct: "", marketPrice: "" },
  workingCapital: { monthlyExpenses: "", inventoryDays: "", receivableDays: "" },
};

const initialState = {
  profile: defaultProfile,
  calculators: defaultCalculators,
  conversation: [], // [{ role: "agent" | "user", text: string }]
  agentHistory: [], // raw pydantic-ai message history, round-tripped to the backend
  intakeDone: false,
  furthestStep: 0,
};

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialState;
    const parsed = JSON.parse(raw);
    return {
      profile: { ...defaultProfile, ...parsed.profile },
      calculators: {
        breakEven: { ...defaultCalculators.breakEven, ...parsed.calculators?.breakEven },
        pricing: { ...defaultCalculators.pricing, ...parsed.calculators?.pricing },
        workingCapital: { ...defaultCalculators.workingCapital, ...parsed.calculators?.workingCapital },
      },
      conversation: parsed.conversation || [],
      agentHistory: parsed.agentHistory || [],
      intakeDone: parsed.intakeDone || false,
      furthestStep: parsed.furthestStep || 0,
    };
  } catch {
    return initialState;
  }
}

const AppStateContext = createContext(null);

export function AppProvider({ children }) {
  const [state, setState] = useState(loadInitial);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  const updateProfile = useCallback((patch) => {
    setState((s) => ({ ...s, profile: { ...s.profile, ...patch } }));
  }, []);

  const updateCalculator = useCallback((name, patch) => {
    setState((s) => ({ ...s, calculators: { ...s.calculators, [name]: { ...s.calculators[name], ...patch } } }));
  }, []);

  const pushConversation = useCallback((entry) => {
    setState((s) => ({ ...s, conversation: [...s.conversation, entry] }));
  }, []);

  const setAgentHistory = useCallback((history) => {
    setState((s) => ({ ...s, agentHistory: history }));
  }, []);

  const applyProfilePatch = useCallback((patch) => {
    setState((s) => ({
      ...s,
      profile: {
        ...s.profile,
        ...(patch.business_type ? { businessType: patch.business_type } : {}),
        ...(patch.district ? { district: patch.district } : {}),
        ...(patch.block ? { block: patch.block } : {}),
        ...(patch.monthly_revenue !== undefined && patch.monthly_revenue !== null ? { monthlyRevenue: String(patch.monthly_revenue) } : {}),
        ...(patch.years_in_operation !== undefined && patch.years_in_operation !== null ? { yearsInOperation: String(patch.years_in_operation) } : {}),
        ...(patch.challenges?.length ? { challenges: Array.from(new Set([...s.profile.challenges, ...patch.challenges])) } : {}),
      },
    }));
  }, []);

  const setIntakeDone = useCallback((done) => {
    setState((s) => ({ ...s, intakeDone: done }));
  }, []);

  const markStepReached = useCallback((step) => {
    setState((s) => ({ ...s, furthestStep: Math.max(s.furthestStep, step) }));
  }, []);

  const resetAll = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setState(initialState);
  }, []);

  return (
    <AppStateContext.Provider
      value={{
        ...state,
        updateProfile,
        updateCalculator,
        pushConversation,
        setAgentHistory,
        applyProfilePatch,
        setIntakeDone,
        markStepReached,
        resetAll,
      }}
    >
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppProvider");
  return ctx;
}
