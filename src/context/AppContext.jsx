import { createContext, useContext, useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "vyapar-saarthi-margin-v1";

const defaultProfile = {
  businessType: "",
  district: "",
  block: "",
  village: "",
  availableMarginCapital: "",
};

// Optional operational inputs - not part of the PS's 3 core intake inputs,
// kept separate and always editable/defaultable. monthlyOperationalCost
// already feeds the Repayment Plan screen's working-capital-by-phase
// calculation and is reused as-is by the Viability Engine's Financial Fit
// dimension (operating_expenses) - no duplicate field. The other three are
// used only by the Financial Fit dimension on the Feasibility page.
const defaultOperations = {
  monthlyOperationalCost: "",
  inventoryDays: "",
  receivableDays: "",
  capitaliseMoratoriumInterest: false,
  monthlyHouseholdIncome: "",
  monthlyHouseholdExpenses: "",
  existingLoanEmi: "",
  expectedBusinessRevenue: "",
};

const initialState = {
  profile: defaultProfile,
  operations: defaultOperations,
  conversation: [], // [{ role: "agent" | "user", text: string }] - voice intake transcript
  agentHistory: [], // raw pydantic-ai message history for the intake agent - its memory
  intakeDone: false,
  furthestStep: 0,
  feasibilityChat: [], // [{ role: "agent" | "user", text: string }] - feasibility advisor transcript
  feasibilityChatHistory: [], // raw pydantic-ai message history for the feasibility advisor - its memory
  voiceLanguage: "en-IN", // BCP-47 tag for SpeechRecognition - persisted so it survives a refresh/navigation
};

function loadInitial() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialState;
    const parsed = JSON.parse(raw);
    return {
      profile: { ...defaultProfile, ...parsed.profile },
      operations: { ...defaultOperations, ...parsed.operations },
      conversation: parsed.conversation || [],
      agentHistory: parsed.agentHistory || [],
      intakeDone: parsed.intakeDone || false,
      furthestStep: parsed.furthestStep || 0,
      feasibilityChat: parsed.feasibilityChat || [],
      feasibilityChatHistory: parsed.feasibilityChatHistory || [],
      voiceLanguage: parsed.voiceLanguage || "en-IN",
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

  const updateOperations = useCallback((patch) => {
    setState((s) => ({ ...s, operations: { ...s.operations, ...patch } }));
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
        ...(patch.village ? { village: patch.village } : {}),
        ...(patch.available_margin_capital !== undefined && patch.available_margin_capital !== null
          ? { availableMarginCapital: String(patch.available_margin_capital) }
          : {}),
      },
    }));
  }, []);

  const setIntakeDone = useCallback((done) => {
    setState((s) => ({ ...s, intakeDone: done }));
  }, []);

  const markStepReached = useCallback((step) => {
    setState((s) => ({ ...s, furthestStep: Math.max(s.furthestStep, step) }));
  }, []);

  const pushFeasibilityChat = useCallback((entry) => {
    setState((s) => ({ ...s, feasibilityChat: [...s.feasibilityChat, entry] }));
  }, []);

  const setFeasibilityChatHistory = useCallback((history) => {
    setState((s) => ({ ...s, feasibilityChatHistory: history }));
  }, []);

  const resetFeasibilityChat = useCallback(() => {
    setState((s) => ({ ...s, feasibilityChat: [], feasibilityChatHistory: [] }));
  }, []);

  const setVoiceLanguage = useCallback((lang) => {
    setState((s) => ({ ...s, voiceLanguage: lang }));
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
        updateOperations,
        pushConversation,
        setAgentHistory,
        applyProfilePatch,
        setIntakeDone,
        markStepReached,
        pushFeasibilityChat,
        setFeasibilityChatHistory,
        resetFeasibilityChat,
        setVoiceLanguage,
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
