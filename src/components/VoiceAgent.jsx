import { useEffect, useRef, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { Button, Badge, Spinner } from "./ui";

const SpeechRecognitionCtor = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

function toBackendProfile(profile) {
  return {
    business_type: profile.businessType || null,
    district: profile.district || null,
    block: profile.block || null,
    village: profile.village || null,
    available_margin_capital: profile.availableMarginCapital ? Number(profile.availableMarginCapital) : null,
  };
}

export default function VoiceAgent({ onDone }) {
  const { profile, conversation, agentHistory, pushConversation, setAgentHistory, applyProfilePatch, setIntakeDone } = useAppState();
  const [listening, setListening] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [typedFallback, setTypedFallback] = useState("");
  const [error, setError] = useState("");
  const recognitionRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [conversation, thinking]);

  // Kick off the conversation with an opening question if nothing said yet.
  useEffect(() => {
    if (conversation.length === 0) {
      sendTurn("(start of conversation - greet me and ask your first question)");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1;
    utter.pitch = 1;
    window.speechSynthesis.speak(utter);
  }

  async function sendTurn(message) {
    setThinking(true);
    setError("");
    if (message !== "(start of conversation - greet me and ask your first question)") {
      pushConversation({ role: "user", text: message });
    }
    try {
      const res = await api.agentTurn(message, agentHistory, toBackendProfile(profile));
      applyProfilePatch(res.profile);
      setAgentHistory(res.history);
      pushConversation({ role: "agent", text: res.reply_text });
      speak(res.reply_text);
      if (res.done) {
        setIntakeDone(true);
        onDone?.();
      }
    } catch (e) {
      setError(e.message || "Could not reach the agent backend. Is the FastAPI server running on :8000?");
    } finally {
      setThinking(false);
    }
  }

  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const rafRef = useRef(null);
  const [frequencies, setFrequencies] = useState([0, 0, 0, 0, 0]);

  function stopVisualizer() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
    }
    setFrequencies([0, 0, 0, 0, 0]);
  }

  async function toggleListening() {
    if (!SpeechRecognitionCtor) {
      setError("Speech recognition isn't supported in this browser - use the text box below instead.");
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      stopVisualizer();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioCtxRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateVolume = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        // sample 5 frequency bands
        setFrequencies([dataArray[5], dataArray[15], dataArray[25], dataArray[35], dataArray[45]]);
        rafRef.current = requestAnimationFrame(updateVolume);
      };
      updateVolume();
    } catch (err) {
      console.warn("Could not start audio visualizer", err);
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => {
      setListening(false);
      stopVisualizer();
    };
    recognition.onerror = (e) => {
      setListening(false);
      stopVisualizer();
      setError(`Mic error: ${e.error}`);
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendTurn(transcript);
    };
    recognitionRef.current = recognition;
    recognition.start();
  }

  function submitTyped() {
    if (!typedFallback.trim()) return;
    sendTurn(typedFallback.trim());
    setTypedFallback("");
  }

  return (
    <div className="paper-card rounded-2xl p-5 sm:p-7 flex flex-col h-full min-h-105">
      <div ref={scrollRef} className="flex-1 min-h-60 overflow-y-auto scrollbar-thin space-y-3 pr-1 mb-5">
        {conversation.length === 0 && !thinking && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-2 text-ink-faint py-10">
            <MicIcon className="opacity-40 h-8 w-8" />
            <p className="text-[17px]">Saarthi will say hello in a moment.</p>
          </div>
        )}
        {conversation.map((entry, i) => (
          <div key={i} className={`flex ${entry.role === "agent" ? "justify-start" : "justify-end"}`}>
            <div
              className={`max-w-[88%] rounded-2xl px-4 py-3 text-[17px] leading-relaxed ${
                entry.role === "agent" ? "bg-pine-tint text-ink border border-pine/20" : "bg-paper-dim text-ink border border-line"
              }`}
            >
              {entry.text}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="flex justify-start">
            <div className="rounded-2xl px-4 py-3 text-[17px] bg-pine-tint border border-pine/20 flex items-center gap-2 text-ink-soft">
              <Spinner className="text-pine" /> Saarthi is thinking...
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-clay/30 bg-clay-tint px-3.5 py-2.5 text-sm text-[#7a2f14]">{error}</div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggleListening}
          disabled={thinking}
          className={`relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 transition ${
            listening ? "border-clay bg-clay-tint text-clay" : "border-pine bg-pine-tint text-pine-dim hover:bg-pine/10"
          } disabled:opacity-50`}
          aria-label={listening ? "Stop listening" : "Start speaking"}
        >
          {listening ? (
            <div className="flex gap-1 items-end h-6 justify-center w-full">
              {frequencies.map((f, i) => (
                <div
                  key={i}
                  className="w-1 bg-clay rounded-full transition-all duration-75"
                  style={{ height: `${Math.max(4, (f / 255) * 24)}px` }}
                />
              ))}
            </div>
          ) : (
            <MicIcon />
          )}
        </button>
        <div className="flex-1 flex items-center gap-2">
          <input
            type="text"
            value={typedFallback}
            onChange={(e) => setTypedFallback(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitTyped()}
            placeholder={listening ? "Listening to you..." : "Or type your answer"}
            className="flex-1 rounded-xl border-2 border-line-strong bg-white px-4 py-3 text-[17px] outline-none focus:border-pine focus:ring-4 focus:ring-pine/15"
          />
          <Button variant="secondary" onClick={submitTyped} disabled={thinking}>
            Send
          </Button>
        </div>
      </div>
      <p className="mt-3 text-[15px] text-ink-soft">
        Press the button and speak. Saarthi asks one thing at a time, and only writes down what you actually say.
      </p>
    </div>
  );
}

function MicIcon({ className = "" }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}
