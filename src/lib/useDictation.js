import { useCallback, useEffect, useRef, useState } from "react";

const SpeechRecognitionCtor = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

/**
 * Speak-to-fill for a text field. Same browser Web Speech API the intake
 * voice agent uses (VoiceAgent.jsx), minus the conversation: it just
 * appends what the person says to whatever they already have in the box,
 * and stops on its own after a short silence. `supported` is false on
 * browsers without the API (Firefox) - callers hide the mic button then.
 */
export function useDictation({ lang = "hi-IN", onText }) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState("");
  const recRef = useRef(null);
  const onTextRef = useRef(onText);
  useEffect(() => {
    onTextRef.current = onText;
  }, [onText]);

  useEffect(() => () => recRef.current?.stop(), []);

  const stop = useCallback(() => recRef.current?.stop(), []);

  const start = useCallback(() => {
    if (!SpeechRecognitionCtor || listening) return;
    setError("");
    const rec = new SpeechRecognitionCtor();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    let silenceTimer = null;
    rec.onstart = () => setListening(true);
    rec.onend = () => {
      setListening(false);
      setInterim("");
      clearTimeout(silenceTimer);
    };
    rec.onerror = (e) => {
      if (e.error !== "no-speech") setError(e.error);
      rec.stop();
    };
    rec.onresult = (event) => {
      let live = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const r = event.results[i];
        if (r.isFinal) onTextRef.current?.(r[0].transcript.trim());
        else live += r[0].transcript;
      }
      setInterim(live);
      clearTimeout(silenceTimer);
      silenceTimer = setTimeout(() => rec.stop(), 2500);
    };
    recRef.current = rec;
    rec.start();
  }, [lang, listening]);

  return { supported: Boolean(SpeechRecognitionCtor), listening, interim, error, start, stop };
}
