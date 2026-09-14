import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { forumApi, getToken, setToken } from "../lib/forumApi";

/**
 * Who is signed in to Chaupal, plus the label taxonomy every forum screen
 * needs (trades, stages, topics, post types, districts). Loaded once.
 *
 * Reading is open to everyone; posting needs a member. `openSignIn()`
 * raises the OTP dialog from anywhere, and `pendingAction` lets a screen
 * resume what the user was doing once they are in.
 */
const ForumContext = createContext(null);

export function ForumProvider({ children }) {
  const [member, setMember] = useState(null);
  const [labels, setLabels] = useState(null);
  const [labelsError, setLabelsError] = useState("");
  const [signInOpen, setSignInOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  useEffect(() => {
    forumApi.labels().then(setLabels).catch((e) => setLabelsError(e.message));
    if (getToken()) {
      forumApi
        .me()
        .then(setMember)
        .catch(() => setToken(""));
    }
  }, []);

  const signIn = useCallback((token, m) => {
    setToken(token);
    setMember(m);
    setSignInOpen(false);
  }, []);

  const signOut = useCallback(() => {
    setToken("");
    setMember(null);
  }, []);

  const openSignIn = useCallback((action) => {
    setPendingAction(() => action || null);
    setSignInOpen(true);
  }, []);

  const closeSignIn = useCallback(() => {
    setSignInOpen(false);
    setPendingAction(null);
  }, []);

  // Fast lookups for rendering chips: value -> label, per axis.
  const lookup = useMemo(() => {
    const mk = (arr) => Object.fromEntries((arr || []).map((x) => [x.value, x.label]));
    const districts = Object.fromEntries((labels?.districts || []).map((d) => [d.key, d.label]));
    return {
      trade: mk(labels?.trades),
      stage: mk(labels?.stages),
      topic: mk(labels?.topics),
      postType: mk(labels?.post_types),
      expertRole: mk(labels?.expert_roles),
      district: districts,
    };
  }, [labels]);

  const value = useMemo(
    () => ({ member, labels, labelsError, lookup, signIn, signOut, signInOpen, openSignIn, closeSignIn, pendingAction, setPendingAction }),
    [member, labels, labelsError, lookup, signIn, signOut, signInOpen, openSignIn, closeSignIn, pendingAction]
  );

  return <ForumContext.Provider value={value}>{children}</ForumContext.Provider>;
}

export function useForum() {
  const ctx = useContext(ForumContext);
  if (!ctx) throw new Error("useForum must be used inside <ForumProvider>");
  return ctx;
}
