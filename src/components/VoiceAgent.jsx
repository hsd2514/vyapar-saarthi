import { useEffect, useRef, useState } from "react";
import { useAppState } from "../context/AppContext";
import { api } from "../lib/api";
import { Button, Badge, Spinner } from "./ui";
import Markdown from "./Markdown";

const SpeechRecognitionCtor = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

// BCP-47 tags SpeechRecognition needs to transcribe each language well.
// The agent itself already understands code-mixed speech regardless of
// this setting (its system prompt handles "whatever language they use") -
// this only tunes what the browser's speech recognizer listens for.
const LANGUAGES = [
  { code: "en-IN", label: "English" },
  { code: "hi-IN", label: "हिंदी" },
  { code: "mr-IN", label: "मराठी" },
];

// All of this component's own UI copy (not the agent's replies, which the
// backend already writes in the chosen language) - translated so the whole
// chatbox matches whichever language button the entrepreneur picked, not
// just what the agent says back.
const UI_TEXT = {
  "en-IN": {
    title: "Talk to Saarthi",
    startOver: "Start over",
    confirmStartOver: "Start a new conversation? This clears everything you've told Saarthi so far and asks all the questions again from the start.",
    alreadyDone: "You already finished this. Review your conversation below, or start over if you want to change everything.",
    greetingWait: "Saarthi will say hello in a moment.",
    thinking: "Saarthi is thinking...",
    noSpeechSupport: "Speech recognition isn't supported in this browser - use the text box below instead.",
    micError: "Mic error: ",
    backendError: "Could not reach the agent backend. Is the FastAPI server running on :8000?",
    languageQuestion: "What language will you speak?",
    speakingLanguageAria: "Speaking language",
    stopListening: "Stop listening",
    startSpeaking: "Start speaking",
    listeningPlaceholder: "Listening to you...",
    typePlaceholder: "Or type your answer",
    send: "Send",
    listeningHint: "Listening... take your time, it waits for you to pause.",
    helpText: "Press the button and speak. Saarthi asks one thing at a time, and only writes down what you actually say - press the button again if you want to stop early.",
  },
  "hi-IN": {
    title: "सारथी से बात करें",
    startOver: "फिर से शुरू करें",
    confirmStartOver: "नई बातचीत शुरू करें? इससे अब तक की सारी जानकारी मिट जाएगी और सारे सवाल फिर से पूछे जाएंगे।",
    alreadyDone: "आपने यह पूरा कर लिया है। नीचे अपनी बातचीत देखें, या सब कुछ बदलने के लिए फिर से शुरू करें।",
    greetingWait: "सारथी अभी नमस्ते कहेगा।",
    thinking: "सारथी सोच रहा है...",
    noSpeechSupport: "इस ब्राउज़र में आवाज़ पहचानने की सुविधा नहीं है - नीचे टेक्स्ट बॉक्स का उपयोग करें।",
    micError: "माइक में समस्या: ",
    backendError: "एजेंट से संपर्क नहीं हो पाया। कृपया जांचें कि सर्वर चालू है।",
    languageQuestion: "आप कौन सी भाषा में बोलेंगे?",
    speakingLanguageAria: "बोलने की भाषा",
    stopListening: "सुनना बंद करें",
    startSpeaking: "बोलना शुरू करें",
    listeningPlaceholder: "आपकी बात सुन रहे हैं...",
    typePlaceholder: "या अपना जवाब टाइप करें",
    send: "भेजें",
    listeningHint: "सुन रहे हैं... अपना समय लें, यह आपके रुकने का इंतज़ार करेगा।",
    helpText: "बटन दबाएं और बोलें। सारथी एक बार में एक सवाल पूछता है, और सिर्फ वही लिखता है जो आप कहते हैं - जल्दी रोकने के लिए बटन फिर से दबाएं।",
  },
  "mr-IN": {
    title: "सारथीशी बोला",
    startOver: "पुन्हा सुरू करा",
    confirmStartOver: "नवीन संभाषण सुरू करायचे? यामुळे आतापर्यंतची सर्व माहिती पुसली जाईल आणि सर्व प्रश्न पुन्हा विचारले जातील.",
    alreadyDone: "तुम्ही हे आधीच पूर्ण केले आहे. खाली तुमचे संभाषण पहा, किंवा सर्व काही बदलण्यासाठी पुन्हा सुरू करा.",
    greetingWait: "सारथी लवकरच नमस्कार करेल.",
    thinking: "सारथी विचार करत आहे...",
    noSpeechSupport: "या ब्राउझरमध्ये आवाज ओळखण्याची सुविधा नाही - खालील टेक्स्ट बॉक्स वापरा.",
    micError: "मायक्रोफोनमध्ये अडचण: ",
    backendError: "एजंटशी संपर्क होऊ शकला नाही. कृपया सर्व्हर सुरू आहे का ते तपासा.",
    languageQuestion: "तुम्ही कोणत्या भाषेत बोलणार?",
    speakingLanguageAria: "बोलण्याची भाषा",
    stopListening: "ऐकणे थांबवा",
    startSpeaking: "बोलणे सुरू करा",
    listeningPlaceholder: "तुमचे बोलणे ऐकत आहोत...",
    typePlaceholder: "किंवा तुमचे उत्तर टाइप करा",
    send: "पाठवा",
    listeningHint: "ऐकत आहोत... तुमचा वेळ घ्या, हे तुम्ही थांबण्याची वाट पाहील.",
    helpText: "बटण दाबा आणि बोला. सारथी एका वेळी एक प्रश्न विचारतो, आणि तुम्ही जे बोलता तेच लिहितो - लवकर थांबण्यासाठी बटण पुन्हा दाबा.",
  },
};

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
  const { profile, conversation, agentHistory, pushConversation, setAgentHistory, applyProfilePatch, setIntakeDone, intakeDone, resetAll, voiceLanguage, setVoiceLanguage } = useAppState();
  const [listening, setListening] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [typedFallback, setTypedFallback] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState("");
  const recognitionRef = useRef(null);
  const scrollRef = useRef(null);
  const hasStarted = useRef(false);
  const t = UI_TEXT[voiceLanguage] || UI_TEXT["en-IN"];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [conversation, thinking]);

  // Kick off the conversation with an opening question if nothing said yet.
  useEffect(() => {
    if (conversation.length === 0 && !hasStarted.current && !intakeDone) {
      hasStarted.current = true;
      sendTurn("(start of conversation - greet me and ask your first question)");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation.length, intakeDone]);

  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    // Strip markdown syntax before speaking it aloud - otherwise "**one lakh**"
    // gets read out as "asterisk asterisk one lakh asterisk asterisk".
    const spoken = text.replace(/[*_`#]+/g, "").replace(/^-\s+/gm, "");
    const utter = new SpeechSynthesisUtterance(spoken);
    utter.lang = voiceLanguage;
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
      const res = await api.agentTurn(message, agentHistory, toBackendProfile(profile), voiceLanguage);
      applyProfilePatch(res.profile);
      setAgentHistory(res.history);
      pushConversation({ role: "agent", text: res.reply_text });
      speak(res.reply_text);
      if (res.done) {
        setIntakeDone(true);
        onDone?.();
      }
    } catch (e) {
      setError(e.message || t.backendError);
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
      setError(t.noSpeechSupport);
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
    recognition.lang = voiceLanguage;
    // continuous + interimResults so a mid-sentence pause to think doesn't
    // trip the browser's own (very quick) silence detector and cut the
    // user off. We decide when they're actually done ourselves, via
    // SILENCE_TIMEOUT_MS below, resetting the timer on every new result.
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let finalTranscript = "";
    let silenceTimer = null;
    const SILENCE_TIMEOUT_MS = 1800;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => {
      setListening(false);
      stopVisualizer();
      setInterimTranscript("");
      clearTimeout(silenceTimer);
      const transcript = finalTranscript.trim();
      if (transcript) sendTurn(transcript);
    };
    recognition.onerror = (e) => {
      // "no-speech" fires whenever the mic is open but hasn't picked up
      // anything yet - not worth alarming the user over.
      if (e.error !== "no-speech") setError(`${t.micError}${e.error}`);
      recognition.stop();
    };
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript + " ";
        } else {
          interim += result[0].transcript;
        }
      }
      setInterimTranscript(interim);
      clearTimeout(silenceTimer);
      silenceTimer = setTimeout(() => recognition.stop(), SILENCE_TIMEOUT_MS);
    };
    recognitionRef.current = recognition;
    recognition.start();
  }

  function submitTyped() {
    if (!typedFallback.trim()) return;
    sendTurn(typedFallback.trim());
    setTypedFallback("");
  }

  function startOver() {
    const hasProgress = conversation.length > 0 || intakeDone;
    if (hasProgress && !window.confirm(t.confirmStartOver)) {
      return;
    }
    recognitionRef.current?.stop();
    stopVisualizer();
    window.speechSynthesis?.cancel();
    setError("");
    setTypedFallback("");
    hasStarted.current = false;
    resetAll();
  }

  return (
    <div className="paper-card rounded-2xl p-5 sm:p-7 flex flex-col h-full min-h-105 max-h-[85vh] relative">
      <div className="flex items-center justify-between gap-3 mb-3">
        <p className="font-display text-base font-semibold">{t.title}</p>
        {(conversation.length > 0 || intakeDone) && (
          <button
            type="button"
            onClick={startOver}
            className="text-sm font-medium text-ink-soft underline underline-offset-4 hover:text-clay transition-colors"
          >
            {t.startOver}
          </button>
        )}
      </div>

      {intakeDone && (
        <div className="mb-4 flex flex-col sm:flex-row items-center justify-between gap-3 p-4 rounded-xl bg-good-tint border-2 border-good/20">
          <p className="text-[16px] text-ink font-medium">{t.alreadyDone}</p>
        </div>
      )}

      <div ref={scrollRef} className="flex-1 min-h-60 overflow-y-auto scrollbar-thin space-y-3 pr-1 mb-5">
        {conversation.length === 0 && !thinking && !intakeDone && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-2 text-ink-faint py-10">
            <MicIcon className="opacity-40 h-8 w-8" />
            <p className="text-[17px]">{t.greetingWait}</p>
          </div>
        )}
        {conversation.map((entry, i) => (
          <div key={i} className={`flex ${entry.role === "agent" ? "justify-start" : "justify-end"}`}>
            <div
              className={`max-w-[88%] rounded-2xl px-4 py-3 text-[17px] leading-relaxed ${
                entry.role === "agent" ? "bg-pine-tint text-ink border border-pine/20" : "bg-paper-dim text-ink border border-line"
              }`}
            >
              {entry.role === "agent" ? <Markdown>{entry.text}</Markdown> : entry.text}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="flex justify-start">
            <div className="rounded-2xl px-4 py-3 text-[17px] bg-pine-tint border border-pine/20 flex items-center gap-2 text-ink-soft">
              <Spinner className="text-pine" /> {t.thinking}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-clay/30 bg-clay-tint px-3.5 py-2.5 text-sm text-[#7a2f14]">{error}</div>
      )}

      {!intakeDone && (
        <>
          <div className="flex items-center justify-between gap-3 mb-3">
            <p className="text-[15px] font-semibold text-ink-soft">{t.languageQuestion}</p>
            <div className="flex rounded-xl border-2 border-line-strong bg-white p-1" role="group" aria-label={t.speakingLanguageAria}>
              {LANGUAGES.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  onClick={() => setVoiceLanguage(l.code)}
                  className={`rounded-lg px-3.5 py-1.5 text-[15px] font-semibold transition ${
                    voiceLanguage === l.code ? "bg-pine text-white" : "text-ink-soft hover:text-ink"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleListening}
              disabled={thinking}
              className={`relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 transition ${
                listening ? "border-clay bg-clay-tint text-clay" : "border-pine bg-pine-tint text-pine-dim hover:bg-pine/10"
              } disabled:opacity-50`}
              aria-label={listening ? t.stopListening : t.startSpeaking}
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
                placeholder={listening ? t.listeningPlaceholder : t.typePlaceholder}
                className="flex-1 rounded-xl border-2 border-line-strong bg-white px-4 py-3 text-[17px] outline-none focus:border-pine focus:ring-4 focus:ring-pine/15"
              />
              <Button variant="secondary" onClick={submitTyped} disabled={thinking}>
                {t.send}
              </Button>
            </div>
          </div>
          {listening && (
            <p className="mt-3 text-[16px] text-ink-soft italic min-h-6">
              {interimTranscript ? `"${interimTranscript.trim()}"` : t.listeningHint}
            </p>
          )}
          <p className="mt-3 text-[15px] text-ink-soft">{t.helpText}</p>
        </>
      )}
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
