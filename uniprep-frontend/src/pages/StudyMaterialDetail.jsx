import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import {
  FileText, MessageSquare, CreditCard, HelpCircle,
  Volume2, ChevronLeft, ChevronRight, RotateCcw,
  Play, Pause, StopCircle, Zap, Loader, Sparkles,
  MoreVertical, ArrowUp, SkipBack, SkipForward
} from "lucide-react";
import api from "../api/api";

/* ── Tab definitions ── */
const TABS = [
  { key: "summary",    label: "Summary",    icon: FileText      },
  { key: "ask",        label: "Chat",       icon: MessageSquare },
  { key: "flashcards", label: "Flashcards", icon: CreditCard    },
  { key: "quiz",       label: "Quiz",       icon: HelpCircle    },
  { key: "audio",      label: "Audio",      icon: Volume2       },
];

/* ────────────────────────────────────────────
   Main component
──────────────────────────────────────────── */
const StudyMaterialDetail = () => {
  const { materialId } = useParams();

  const [material,      setMaterial]      = useState(null);
  const [summary,       setSummary]       = useState(null);
  const [flashcards,    setFlashcards]    = useState([]);
  const [quiz,          setQuiz]          = useState(null);
  const [quizCount,     setQuizCount]     = useState(5);
  const [quizAnswers,   setQuizAnswers]   = useState({});
  const [confidence,    setConfidence]    = useState({});   // question id → "guess"|"unsure"|"sure"
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizResult,    setQuizResult]    = useState(null);  // server-scored attempt (answers keyed by question id)
  const [quizSubmitting,setQuizSubmitting]= useState(false);
  const [activeTab,     setActiveTab]     = useState("summary");
  const [loadingAction, setLoadingAction] = useState("");
  const [error,         setError]         = useState("");

  /* Chat state */
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput,    setChatInput]    = useState("");
  const [isSending,    setIsSending]    = useState(false);
  const chatEndRef = useRef(null);

  /* Audio state */
  const [isSpeaking,    setIsSpeaking]    = useState(false);
  const [isPaused,      setIsPaused]      = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const [progressDeterminate, setProgressDeterminate] = useState(false);
  const [audioError,    setAudioError]    = useState("");
  const [speechRate,    setSpeechRate]    = useState(1);
  // utterGenRef: every new utterance (play/skip/rate-restart) bumps this.
  // Callbacks from superseded utterances see a stale generation and no-op,
  // so an async onerror from our own cancel() can't clobber live state.
  const utterGenRef       = useRef(0);
  const boundaryCharRef   = useRef(0);   // last onboundary charIndex, absolute in full text
  const baseCharRef       = useRef(0);   // start offset of the currently-spoken slice
  const boundarySeenRef   = useRef(false);
  const pausedRef         = useRef(false);
  const resumeTickRef     = useRef(null);
  const wordOffsetsRef    = useRef([]);

  useEffect(() => { fetchMaterial(); }, [materialId]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

  const fetchMaterial = async () => {
    try {
      const res = await api.get(`/rag/materials/${materialId}/`);
      setMaterial(res.data);
    } catch { setError("Failed to load material."); }
  };

  const isCompleted = material?.processing_status === "completed";

  /* ── Load existing artifacts on first open ── */
  const loadArtifacts = async () => {
    if (!isCompleted) return;
    try {
      const [sumRes, flashRes, quizRes, chatRes] = await Promise.all([
        api.get(`/rag/materials/${materialId}/summary/`),
        api.get(`/rag/materials/${materialId}/flashcards/`),
        api.get(`/rag/materials/${materialId}/quiz/`),
        api.get(`/rag/materials/${materialId}/chat/`),
      ]);
      setSummary(sumRes.data.summary);
      setFlashcards(flashRes.data.flashcards || []);
      setQuiz(quizRes.data);
      setChatMessages(chatRes.data.messages || []);

      // If the server returned the student's most recent completed attempt
      // for this quiz, restore it so a reopen shows previous results
      // instead of a blank quiz (consistent with the persisted-artifact pattern).
      const latest = quizRes.data?.latest_attempt;
      if (latest) {
        const { result, selections, confidences } = hydrateAttempt(latest);
        setQuizAnswers(selections);
        setConfidence(confidences);
        setQuizResult(result);
        setQuizSubmitted(true);
      } else {
        setQuizAnswers({}); setConfidence({}); setQuizSubmitted(false); setQuizResult(null);
      }
    } catch (e) {
      // Silently ignore individual failures; user can still regenerate.
    }
  };

  useEffect(() => {
    if (material && isCompleted) {
      loadArtifacts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [materialId, material?.processing_status]);

  /* ── Generate summary ── */
  const generateSummary = async () => {
    setError(""); setLoadingAction("summary");
    try {
      const res = await api.post(`/rag/materials/${materialId}/summary/`);
      setSummary(res.data.summary);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to generate summary.");
    } finally { setLoadingAction(""); }
  };

  /* ── Chat / ask ── */
  const sendChatMessage = async (e) => {
    e.preventDefault();
    const q = chatInput.trim();
    if (!q) return;
    setChatInput("");
    setChatMessages((m) => [...m, { role: "user", text: q }]);
    setChatMessages((m) => [...m, { role: "ai", text: "…", thinking: true }]);
    setIsSending(true);
    try {
      const res = await api.post(`/rag/materials/${materialId}/ask/`, { question: q });
      const answer  = res.data.answer || "No answer returned.";
      const sources = res.data.sources || [];
      setChatMessages((m) => {
        const updated = [...m];
        updated[updated.length - 1] = { role: "ai", text: answer, sources };
        return updated;
      });
    } catch (e) {
      setChatMessages((m) => {
        const updated = [...m];
        updated[updated.length - 1] = { role: "ai", text: "Sorry, I couldn't get an answer. Please try again.", error: true };
        return updated;
      });
    } finally {
      setIsSending(false);
    }
  };

  /* ── Flashcards ── */
  const generateFlashcards = async () => {
    setError(""); setLoadingAction("flashcards");
    try {
      const res = await api.post(`/rag/materials/${materialId}/flashcards/`);
      setFlashcards(res.data.flashcards || []);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to generate flashcards.");
    } finally { setLoadingAction(""); }
  };

  /* ── Quiz ── */
  const QUIZ_COUNT_PRESETS = [5, 10, 15, 20];
  const MAX_QUIZ_COUNT = 30;

  const effectiveQuizCount = () => {
    const parsed = parseInt(quizCount, 10);
    if (isNaN(parsed)) return 5;
    return Math.min(MAX_QUIZ_COUNT, Math.max(1, parsed));
  };

  const generateQuiz = async () => {
    setError(""); setLoadingAction("quiz");
    setQuizAnswers({}); setConfidence({}); setQuizSubmitted(false); setQuizResult(null);
    try {
      const res = await api.post(`/rag/materials/${materialId}/generate-quiz/`, {
        question_count: effectiveQuizCount(),
      });
      setQuiz(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to generate quiz.");
    } finally { setLoadingAction(""); }
  };

  const selectAnswer   = (qId, choice) => !quizSubmitted && setQuizAnswers((a) => ({ ...a, [qId]: choice }));
  const setConf        = (qId, level)  => !quizSubmitted && setConfidence((c) => ({ ...c, [qId]: level }));

  // Transforms a server attempt payload (with an `answers` array) into the
  // shape used by the render: answers keyed by question_id. Also rebuilds the
  // local quizAnswers/confidence maps so the student's selected choices and
  // confidence highlights are restored when viewing a past attempt.
  const hydrateAttempt = (payload) => {
    const answersMap = {};
    const selMap = {};
    const confMap = {};
    (payload?.answers || []).forEach((a) => {
      const qid = a.question_id;
      answersMap[qid] = a;
      if (a.selected_answer) selMap[qid] = a.selected_answer;
      if (a.confidence) confMap[qid] = a.confidence;
    });
    return {
      result: { ...payload, answers: answersMap },
      selections: selMap,
      confidences: confMap,
    };
  };

  const checkAnswers = async () => {
    if (!quiz) return;
    const quizId = quiz.quiz_id || quiz.id;
    if (!quizId) return;

    const answered = Object.entries(quizAnswers).map(([qId, selected_answer]) => ({
      question_id: parseInt(qId, 10),
      selected_answer,
      confidence: confidence[qId] || "",
    }));

    if (answered.length === 0) {
      setError("Please answer at least one question before checking answers.");
      return;
    }

    setError(""); setQuizSubmitting(true);
    try {
    const res = await api.post(
        `/rag/materials/${materialId}/quiz/submit/`,
        { quiz_id: quizId, answers: answered }
      );
      const { result } = hydrateAttempt(res.data);
      setQuizResult(result);
    setQuizSubmitted(true);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to submit quiz.");
    } finally { setQuizSubmitting(false); }
  };

  const resetQuiz = () => {
    setQuizAnswers({}); setConfidence({}); setQuizSubmitted(false); setQuizResult(null);
  };

  /* ── Audio ── */
  const SKIP_WORDS = 15; // skip buttons jump ±15 words (≈ ±10 s at reading speed)

  const computeWordOffsets = (text) => {
    const offsets = [];
    const re = /\S+/g;
    let m;
    while ((m = re.exec(text)) !== null) offsets.push(m.index);
    return offsets;
  };

  const clearResumeTick = () => {
    if (resumeTickRef.current) {
      clearInterval(resumeTickRef.current);
      resumeTickRef.current = null;
    }
  };

  const startSpeech = (fromChar, rate) => {
    const fullText = summary?.summary_text || "";
    if (!fullText) return;
    const sliceStart = Math.max(0, Math.min(fromChar, fullText.length - 1));
    const gen = ++utterGenRef.current;
    baseCharRef.current = sliceStart;
    boundaryCharRef.current = sliceStart;
    boundarySeenRef.current = false;
    setProgressDeterminate(false);

    const utter = new SpeechSynthesisUtterance(fullText.slice(sliceStart));
    utter.rate = rate;

    utter.onstart = () => {
      if (gen !== utterGenRef.current) return;
      setIsSpeaking(true);
      setIsPaused(false);
      pausedRef.current = false;
      // Chrome can silently stall synthesis after ~15 s of continuous speech
      // with some voices; periodic resume() is the standard workaround.
      // Verified: resume() while not paused fires no events/errors.
      clearResumeTick();
      resumeTickRef.current = setInterval(() => {
        if (!pausedRef.current) window.speechSynthesis.resume();
      }, 10000);
    };

    // Word-boundary events give a real position: charIndex is word-aligned.
    // Verified to fire in Edge/Chrome. If an engine never fires them, the UI
    // stays in the indeterminate state rather than faking numbers.
    utter.onboundary = (ev) => {
      if (gen !== utterGenRef.current) return;
      if (typeof ev.charIndex !== "number") return;
      boundarySeenRef.current = true;
      setProgressDeterminate(true);
      const abs = sliceStart + ev.charIndex;
      boundaryCharRef.current = abs;
      setAudioProgress(Math.min(100, Math.round((abs / fullText.length) * 100)));
    };

    utter.onend = () => {
      if (gen !== utterGenRef.current) return;
      console.log("[TTS] onend — playback completed normally");
      clearResumeTick();
      setIsSpeaking(false);
      setIsPaused(false);
      pausedRef.current = false;
      setAudioProgress(100);
    };

    utter.onerror = (ev) => {
      // Log every code for debugging; only genuine failures show the banner.
      console.error("[TTS] onerror SpeechSynthesisErrorEvent:", ev);
      console.error("[TTS] ev.error:", ev && ev.error);
      if (gen !== utterGenRef.current) return; // superseded (stop/skip/restart)
      clearResumeTick();
      setIsSpeaking(false);
      setIsPaused(false);
      pausedRef.current = false;
      setAudioProgress(0);
      // cancel()-driven interruptions are EXPECTED, not failures. Verified in
      // Edge/Chrome: mid-speech cancel -> "interrupted"; queued cancel may
      // surface as "canceled" in some engines. Silent cleanup, no banner.
      const expected = ev && (ev.error === "interrupted" || ev.error === "canceled");
      if (!expected) {
        setAudioError("Audio playback failed. See console for details.");
      }
    };

    window.speechSynthesis.speak(utter);
  };

  const speakSummary = () => {
    if (!summary?.summary_text) return;
    window.speechSynthesis.cancel();
    utterGenRef.current++;
    clearResumeTick();
    setAudioError("");
    setAudioProgress(0);
    wordOffsetsRef.current = computeWordOffsets(summary.summary_text);

    // Observability: log the exact text being read so we can confirm
    // whether a clean AI summary or a fallback chunk dump is spoken.
    console.log("[TTS] speakSummary text:", summary.summary_text);

    // Voices can be empty on first call in some browsers until the
    // voiceschanged event fires. Wait for them before speaking.
    const voices = window.speechSynthesis.getVoices();
    let spoken = false;
    const doSpeak = () => {
      if (spoken) return;
      spoken = true;
      startSpeech(0, speechRate);
    };
    if (voices && voices.length > 0) {
      doSpeak();
    } else {
      // No voices yet; attach a one-shot listener and speak when ready.
      const onVoicesReady = () => {
        console.log("[TTS] voiceschanged fired:", window.speechSynthesis.getVoices().length, "voices");
        window.speechSynthesis.removeEventListener("voiceschanged", onVoicesReady);
        doSpeak();
      };
      window.speechSynthesis.addEventListener("voiceschanged", onVoicesReady);
      // Safety fallback: if voiceschanged never fires, speak anyway after
      // a short delay (the engine may still accept the utterance).
      setTimeout(() => {
        window.speechSynthesis.removeEventListener("voiceschanged", onVoicesReady);
        doSpeak();
      }, 500);
    }
  };

  // Genuine pause/resume via speechSynthesis.pause()/.resume(). Verified in
  // Edge/Chrome: pause() fires no onerror, paused flag flips, resume()
  // continues from the pause point (boundary charIndex keeps advancing).
  const pauseSpeaking = () => {
    if (!isSpeaking || isPaused) return;
    window.speechSynthesis.pause();
    pausedRef.current = true;
    setIsPaused(true);
    // Some engines (notably older Safari) silently ignore pause(). Detect
    // that and report honestly instead of pretending playback paused.
    setTimeout(() => {
      if (pausedRef.current && !window.speechSynthesis.paused) {
        pausedRef.current = false;
        setIsPaused(false);
        setAudioError("Pause isn't supported by this browser's speech engine. Use Stop instead.");
      }
    }, 500);
  };

  const resumeSpeaking = () => {
    if (!isSpeaking || !isPaused) return;
    window.speechSynthesis.resume();
    pausedRef.current = false;
    setIsPaused(false);
  };

  // Full stop — a separate, explicit action from pause.
  const stopSpeaking = () => {
    utterGenRef.current++; // makes the pending "interrupted" callback stale
    clearResumeTick();
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setIsPaused(false);
    pausedRef.current = false;
    setAudioProgress(0);
    setAudioError("");
  };

  const skipBy = (wordDelta) => {
    if (!isSpeaking || isPaused) return;
    const offsets = wordOffsetsRef.current;
    if (!offsets.length || !boundarySeenRef.current) return; // no position info
    let idx = 0;
    for (let i = 0; i < offsets.length; i++) {
      if (offsets[i] <= boundaryCharRef.current) idx = i;
      else break;
    }
    const target = Math.max(0, Math.min(offsets.length - 1, idx + wordDelta));
    const fromChar = offsets[target];
    console.log(`[TTS] skip ${wordDelta > 0 ? "+" : ""}${wordDelta} words → char ${fromChar}`);
    window.speechSynthesis.cancel(); // old utterance's error callback goes stale
    startSpeech(fromChar, speechRate);
  };

  // Rate cannot change mid-utterance in any browser — restart from the last
  // known word boundary (start of the current slice if none seen yet).
  const changeSpeed = (rate) => {
    if (rate === speechRate) return;
    setSpeechRate(rate);
    if (isSpeaking) {
      const fromChar = boundarySeenRef.current ? boundaryCharRef.current : baseCharRef.current;
      console.log(`[TTS] rate ${speechRate}→${rate}, restarting from char ${fromChar}`);
      setIsPaused(false);
      pausedRef.current = false;
      window.speechSynthesis.cancel();
      startSpeech(fromChar, rate);
    }
  };

  if (!material) return (
    <div className="container py-5 d-flex align-items-center gap-3 text-muted">
      <div className="spinner-border spinner-border-sm text-primary" /> Loading material…
    </div>
  );

  return (
    <div className="container py-4">
      {/* ── Header ── */}
      <div className="d-flex align-items-center gap-3 mb-4 flex-wrap">
        <div style={{ width: 46, height: 46, borderRadius: 12, background: "#eff6ff", display: "grid", placeItems: "center", flexShrink: 0 }}>
          <FileText size={22} color="#2563eb" />
        </div>
        <div className="flex-fill">
          <h2 className="fw-bold mb-0">{material.title}</h2>
          <div className="d-flex gap-2 mt-1 align-items-center">
            <span className="badge bg-light text-dark">{(material.file_type || "file").toUpperCase()}</span>
            <span className={`badge ${material.processing_status === "completed" ? "bg-success" : material.processing_status === "processing" ? "bg-warning text-dark" : "bg-secondary"}`}>
              {material.processing_status}
            </span>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {!isCompleted && (
        <div className="alert alert-warning mb-4">
          This material hasn't been processed yet. Go to <strong>Materials</strong> and click <strong>Process</strong> to enable AI features.
        </div>
      )}

      {/* ── Tab bar ── */}
      <div className="rag-tabs mb-4">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            className={activeTab === key ? "active" : ""}
            onClick={() => setActiveTab(key)}
          >
            <Icon size={14} style={{ marginRight: 6, verticalAlign: "middle" }} />
            {label}
          </button>
        ))}
      </div>

      {/* ══ Summary tab ══ */}
      {activeTab === "summary" && (
        <div>
          {!summary ? (
            <div className="text-center py-5">
              <Zap size={40} color="#cbd5e1" className="mb-3" />
              <p className="text-muted mb-3">No summary yet. Generate one from your uploaded material.</p>
              <button className="btn btn-primary px-4" onClick={generateSummary} disabled={!isCompleted || loadingAction === "summary"}>
                {loadingAction === "summary" ? <><Loader size={14} className="me-2 spin-icon" />Generating…</> : "✨ Generate Summary"}
              </button>
            </div>
          ) : (
            <div>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="fw-bold mb-0">AI Summary</h5>
                <button className="btn btn-sm btn-outline-secondary" onClick={generateSummary} disabled={loadingAction === "summary"}>
                  <RotateCcw size={13} className="me-1" />Regenerate
                </button>
              </div>
              <div className="card border-0 shadow-sm rounded-4 mb-4">
                <div className="card-body p-4" style={{ lineHeight: 1.8, color: "#1e293b" }}>
                  {summary.summary_text}
                </div>
              </div>
              {summary.key_points?.length > 0 && (
                <div>
                  <h6 className="fw-bold mb-3">Key Points</h6>
                  <div className="d-grid gap-2">
                    {summary.key_points.map((pt, i) => (
                      <div key={i} style={{ display: "flex", gap: 10, padding: "10px 14px", background: "#f8fafc", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: "0.9rem" }}>
                        <span style={{ color: "#2563eb", fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
                        {pt}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ══ Chat tab ══ */}
      {activeTab === "ask" && (
        <div className="chat-panel">
          <div className="chat-card">
            {/* Header */}
            <div className="chat-header d-flex align-items-center gap-3 px-3 py-3 border-bottom bg-white">
              <div className="chat-header-avatar">
                <Sparkles size={16} />
              </div>
              <div className="flex-fill" style={{ minWidth: 0 }}>
                <div className="chat-header-title">AI study chat</div>
                <div className="chat-header-subtitle">Grounded in: {material.title}</div>
              </div>
              <button className="chat-header-menu" type="button" aria-label="Chat options">
                <MoreVertical size={16} />
              </button>
            </div>

            {/* Messages */}
            <div className="chat-messages d-flex flex-column gap-3 p-3 overflow-auto">
              {chatMessages.length === 0 && (
                <div className="chat-empty text-center text-muted m-auto px-3">
                  <MessageSquare size={32} className="mb-2 d-block mx-auto" style={{ color: "#cbd5e1" }} />
                  <p className="mb-0 small">Ask a question about this material to get started.</p>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`chat-row d-flex align-items-end ${msg.role === "user" ? "justify-content-end" : "justify-content-start"}`}
                >
                  {msg.role === "ai" && (
                    <div className="chat-avatar flex-shrink-0">
                      <Sparkles size={14} />
                    </div>
                  )}
                  <div className={`chat-bubble ${msg.role} ${msg.thinking ? "thinking" : ""}`}>
                    {msg.thinking ? (
                      <span className="typing-dots d-flex align-items-center gap-1">
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                      </span>
                    ) : (
                      msg.text
                    )}
                    {/* Source chips */}
                    {msg.sources?.length > 0 && (
                      <div className="mt-2 d-flex gap-1 flex-wrap">
                        {msg.sources.slice(0, 3).map((s, si) => (
                          <span key={si} className="chat-source-chip">
                            📄 Chunk {s.chunk_index}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="chat-input-bar p-3 border-top bg-white">
              <form onSubmit={sendChatMessage} className="chat-form d-flex align-items-center gap-2">
                <input
                  className="form-control chat-input"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about this material"
                  disabled={!isCompleted || isSending}
                />
                <button
                  className="chat-send-btn"
                  type="submit"
                  disabled={!isCompleted || !chatInput.trim() || isSending}
                  aria-label="Send"
                >
                  <ArrowUp size={18} />
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* ══ Flashcards tab ══ */}
      {activeTab === "flashcards" && (
        <div>
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div>
              <h5 className="fw-bold mb-0">Flashcards</h5>
              <p className="text-muted small mb-0">Click a card to flip it and reveal the answer.</p>
            </div>
            <button className="btn btn-primary" onClick={generateFlashcards} disabled={!isCompleted || loadingAction === "flashcards"}>
              {loadingAction === "flashcards" ? <><Loader size={14} className="me-2 spin-icon" />Generating…</> : "✨ Generate Flashcards"}
            </button>
          </div>

          {flashcards.length === 0 && loadingAction !== "flashcards" && (
            <div className="text-center py-5 text-muted">
              <CreditCard size={40} color="#cbd5e1" className="mb-3" />
              <p>Click "Generate Flashcards" to create study cards from this material.</p>
            </div>
          )}

          <div className="row g-3">
            {flashcards.map((card, i) => (
              <div key={card.id || i} className="col-md-6">
                <FlashCard front={card.front} back={card.back} index={i} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ══ Quiz tab ══ */}
      {activeTab === "quiz" && (
        <div>
          <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
            <div>
              <h5 className="fw-bold mb-0">Practice Quiz</h5>
              <p className="text-muted small mb-0">AI-generated MCQ questions from your material.</p>
            </div>
            <div className="d-flex align-items-center gap-2 flex-wrap">
              <div className="d-flex align-items-center gap-1">
                <span className="text-muted small me-1">Questions:</span>
                {QUIZ_COUNT_PRESETS.map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={`btn btn-sm ${effectiveQuizCount() === n ? "btn-primary" : "btn-outline-secondary"}`}
                    onClick={() => setQuizCount(n)}
                    disabled={loadingAction === "quiz"}
                  >
                    {n}
                  </button>
                ))}
                <input
                  type="number"
                  className="form-control form-control-sm"
                  style={{ width: 72 }}
                  min={1}
                  max={MAX_QUIZ_COUNT}
                  title={`Custom (1–${MAX_QUIZ_COUNT})`}
                  value={quizCount}
                  onChange={(e) => setQuizCount(e.target.value)}
                  onBlur={() => setQuizCount(effectiveQuizCount())}
                  disabled={loadingAction === "quiz"}
                />
              </div>
              <button className="btn btn-primary" onClick={generateQuiz} disabled={!isCompleted || loadingAction === "quiz"}>
                {loadingAction === "quiz" ? <><Loader size={14} className="me-2 spin-icon" />Generating…</> : "✨ Generate Quiz"}
              </button>
            </div>
          </div>

          {quiz?.ai_status === "fallback_generated" && (
            <div className="alert alert-warning small">AI quiz generation unavailable — showing fallback questions.</div>
          )}

          {quiz?.questions?.length > 0 && (
            <div className="d-grid gap-3 mb-3">
              {quiz.questions.map((item, idx) => {
                const selected   = quizAnswers[item.id];
                const resItem    = quizResult?.answers?.[item.id];
                const answered   = quizSubmitted ? !!resItem : selected !== undefined;
                const isCorrect  = quizSubmitted ? !!resItem?.is_correct : false;
                const correctAnswer = resItem?.correct_answer ?? item.correct_answer;
                const explanation    = resItem?.explanation ?? item.explanation;
                return (
                  <div key={item.id} className="card border-0 shadow-sm rounded-4">
                    <div className="card-body p-4">
                      <p className="fw-bold mb-3">{idx + 1}. {item.question_text}</p>

                      <div className="d-grid gap-2">
                        {item.choices.map((choice, ci) => {
                          const isSelected  = selected === choice;
                          const isCorrectC  = quizSubmitted && answered && choice === correctAnswer;
                          const isWrongSel  = quizSubmitted && answered && isSelected && choice !== correctAnswer;
                          let cls = "choice-btn";
                          if (isSelected && !quizSubmitted) cls += " selected";
                          if (isCorrectC)  cls += " choice-correct";
                          if (isWrongSel)  cls += " choice-wrong";
                          return (
                            <button key={ci} className={cls} onClick={() => selectAnswer(item.id, choice)} disabled={quizSubmitted}>
                              <span className="choice-letter">{["A","B","C","D"][ci]}</span>
                              {choice}
                            </button>
                          );
                        })}
                      </div>

                      {/* Confidence rating */}
                      {!quizSubmitted && selected && (
                        <div className="mt-3">
                          <p className="text-muted small mb-2">How confident are you?</p>
                          <div className="confidence-row">
                            {[
                              { key: "guess",  label: "🎲 Guessing" },
                              { key: "unsure", label: "🤔 Unsure"   },
                              { key: "sure",   label: "✅ Confident" },
                            ].map(({ key, label }) => (
                              <button
                                key={key}
                                className={`conf-btn ${key} ${confidence[item.id] === key ? "active" : ""}`}
                                onClick={() => setConf(item.id, key)}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {quizSubmitted && (
                        <div className="mt-3 p-3 rounded-3" style={{ background: answered ? (isCorrect ? "#f0fdf4" : "#fef2f2") : "#f8fafc" }}>
                          {answered ? (
                            <>
                              <span className={`badge ${isCorrect ? "bg-success" : "bg-danger"} mb-2`}>
                                {isCorrect ? "✓ Correct" : "✗ Wrong"}
                              </span>
                              {!isCorrect && correctAnswer && (
                                <p className="small mb-1"><strong>Correct:</strong> {correctAnswer}</p>
                              )}
                              {explanation && (
                                <p className="small text-muted mb-0"><strong>Explanation:</strong> {explanation}</p>
                              )}
                            </>
                          ) : (
                            <span className="badge bg-secondary mb-0">Not answered</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {quiz?.questions?.length > 0 && quizSubmitted && quizResult && (
            <div className="card border-0 shadow-sm rounded-4 mb-3">
              <div className="card-body p-3 d-flex flex-wrap gap-3 align-items-center">
                <span className="badge bg-success fs-6">{quizResult.correct_count} correct</span>
                <span className="badge bg-danger fs-6">{quizResult.wrong_count} wrong</span>
                <span className="badge bg-secondary fs-6">{quizResult.unanswered_count} not answered</span>
                <span className="text-muted small ms-auto">{quizResult.total_questions} questions total · {quizResult.total_score}%</span>
              </div>
            </div>
          )}

          {quiz?.questions?.length > 0 && (
            <div className="d-flex gap-2">
              {!quizSubmitted
                ? <button className="btn btn-success px-4" onClick={checkAnswers} disabled={quizSubmitting}>
                    {quizSubmitting ? <><Loader size={14} className="me-2 spin-icon" />Scoring…</> : "Check Answers"}
                  </button>
                : <button className="btn btn-outline-primary" onClick={resetQuiz}><RotateCcw size={14} className="me-1" />Try Again</button>
              }
            </div>
          )}
        </div>
      )}

      {/* ══ Audio tab ══ */}
      {activeTab === "audio" && (
        <div>
          <h5 className="fw-bold mb-1">Audio Summary</h5>
          <p className="text-muted mb-4">Listen to your AI-generated summary using browser text-to-speech.</p>

          {!summary ? (
            <div className="alert alert-info">
              Generate a summary from the <strong>Summary</strong> tab first, then return here to listen.
            </div>
          ) : (
            <>
            {audioError && (
              <div className="alert alert-danger py-2 mb-3" role="alert">
                {audioError}
              </div>
            )}
            <div className={`audio-player ${isSpeaking ? "playing" : ""} ${isPaused ? "paused" : ""}`}>

              {/* 1 · Header */}
              <div className="audio-header">
                <span className="audio-header-icon"><Volume2 size={16} /></span>
                <div className="audio-header-text">
                  <span className="audio-header-title">Audio summary</span>
                  <span className="audio-header-sub">{material.title}</span>
                </div>
                <span className="audio-header-meta">
                  {summary.summary_text?.split(" ").length || 0} words
                </span>
              </div>

              {/* Waveform */}
              <div className="audio-waveform">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div key={i} className="audio-bar" style={{ height: isSpeaking ? undefined : 4 + (i % 5) * 3 }} />
                ))}
              </div>

              {/* 2 · Progress — word-boundary driven when the engine supports
                    it, otherwise an honest indeterminate pulse (no fake times) */}
              <div className={`audio-track ${isSpeaking && !progressDeterminate ? "indeterminate" : ""}`}>
                <div className="audio-track-fill" style={{ width: `${audioProgress}%` }} />
              </div>
              <div className="audio-status">
                {isSpeaking
                  ? isPaused
                    ? `Paused${progressDeterminate ? ` · ${audioProgress}%` : ""}`
                    : progressDeterminate
                      ? `Playing · ${audioProgress}%`
                      : "Playing…"
                  : audioProgress === 100
                    ? "Finished"
                    : "Ready"}
              </div>

              {/* 3 · Primary controls — real pause/resume toggle, word-offset skip */}
              <div className="audio-controls">
                <button
                  className="audio-btn"
                  onClick={() => skipBy(-SKIP_WORDS)}
                  disabled={!isSpeaking || isPaused || !progressDeterminate}
                  title={`Back ~${SKIP_WORDS} words`}
                >
                  <SkipBack size={18} />
                </button>
                <button
                  className="audio-btn play-btn"
                  onClick={isSpeaking ? (isPaused ? resumeSpeaking : pauseSpeaking) : speakSummary}
                  title={isSpeaking ? (isPaused ? "Resume" : "Pause") : "Play"}
                >
                  {isSpeaking && !isPaused ? <Pause size={22} /> : <Play size={22} />}
                </button>
                <button
                  className="audio-btn"
                  onClick={() => skipBy(SKIP_WORDS)}
                  disabled={!isSpeaking || isPaused || !progressDeterminate}
                  title={`Forward ~${SKIP_WORDS} words`}
                >
                  <SkipForward size={18} />
                </button>
              </div>

              {/* 4 · Secondary row — speed + explicit Stop */}
              <div className="audio-secondary">
                <div className="audio-speed-group">
                  {[0.75, 1, 1.25, 1.5].map((r) => (
                    <button
                      key={r}
                      className={`audio-speed-chip ${speechRate === r ? "active" : ""}`}
                      onClick={() => changeSpeed(r)}
                      title={isSpeaking ? "Applies from the current position" : "Set playback speed"}
                    >
                      {r}×
                    </button>
                  ))}
                </div>
                <button
                  className="audio-btn stop-btn"
                  onClick={stopSpeaking}
                  disabled={!isSpeaking}
                  title="Stop"
                >
                  <StopCircle size={18} />
                </button>
              </div>
            </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

/* ── 3D Flip Flashcard ── */
const FlashCard = ({ front, back, index }) => {
  const [flipped, setFlipped] = useState(false);
  return (
    <div className="flashcard-scene" style={{ height: 160 }} onClick={() => setFlipped((f) => !f)}>
      <div className={`flashcard-inner ${flipped ? "flipped" : ""}`} style={{ height: 160 }}>
        <div className="flashcard-front">
          <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Card {index + 1} · Question
          </span>
          <p className="fw-semibold mt-2 mb-0" style={{ fontSize: "0.92rem", color: "#1e293b" }}>{front}</p>
          <span className="flashcard-hint">👆 Click to flip</span>
        </div>
        <div className="flashcard-back">
          <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#1d4ed8", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Answer
          </span>
          <p className="mt-2 mb-0" style={{ fontSize: "0.92rem", color: "#1e3a8a" }}>{back}</p>
          <span className="flashcard-hint" style={{ color: "#3b82f6" }}>👆 Click to flip back</span>
        </div>
      </div>
    </div>
  );
};

export default StudyMaterialDetail;