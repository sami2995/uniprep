import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import {
  FileText, MessageSquare, CreditCard, HelpCircle,
  Volume2, ChevronLeft, ChevronRight, RotateCcw,
  Play, Pause, StopCircle, Zap, Loader
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
  const [quizAnswers,   setQuizAnswers]   = useState({});
  const [confidence,    setConfidence]    = useState({});   // question id → "guess"|"unsure"|"sure"
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [activeTab,     setActiveTab]     = useState("summary");
  const [loadingAction, setLoadingAction] = useState("");
  const [error,         setError]         = useState("");

  /* Chat state */
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput,    setChatInput]    = useState("");
  const chatEndRef = useRef(null);

  /* Audio state */
  const [isSpeaking,    setIsSpeaking]    = useState(false);
  const [audioProgress, setAudioProgress] = useState(0);
  const [speechRate,    setSpeechRate]    = useState(1);
  const audioInterval = useRef(null);

  useEffect(() => { fetchMaterial(); }, [materialId]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

  const fetchMaterial = async () => {
    try {
      const res = await api.get(`/rag/materials/${materialId}/`);
      setMaterial(res.data);
    } catch { setError("Failed to load material."); }
  };

  const isCompleted = material?.processing_status === "completed";

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
  const generateQuiz = async () => {
    setError(""); setLoadingAction("quiz");
    setQuizAnswers({}); setConfidence({}); setQuizSubmitted(false);
    try {
      const res = await api.post(`/rag/materials/${materialId}/generate-quiz/`);
      setQuiz(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to generate quiz.");
    } finally { setLoadingAction(""); }
  };

  const selectAnswer   = (qId, choice) => !quizSubmitted && setQuizAnswers((a) => ({ ...a, [qId]: choice }));
  const setConf        = (qId, level)  => !quizSubmitted && setConfidence((c) => ({ ...c, [qId]: level }));
  const checkAnswers   = () => setQuizSubmitted(true);
  const resetQuiz      = () => { setQuizAnswers({}); setConfidence({}); setQuizSubmitted(false); };

  /* ── Audio ── */
  const speakSummary = () => {
    if (!summary?.summary_text) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(summary.summary_text);
    utter.rate = speechRate;
    utter.onstart = () => {
      setIsSpeaking(true);
      setAudioProgress(0);
      let p = 0;
      audioInterval.current = setInterval(() => {
        p = Math.min(100, p + 0.4);
        setAudioProgress(p);
      }, 200);
    };
    utter.onend = utter.onerror = () => {
      setIsSpeaking(false);
      setAudioProgress(100);
      clearInterval(audioInterval.current);
    };
    window.speechSynthesis.speak(utter);
  };

  const stopSpeaking = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setAudioProgress(0);
    clearInterval(audioInterval.current);
  };

  const cycleSpeed = () => {
    const speeds = [0.75, 1, 1.25, 1.5, 2];
    const next = speeds[(speeds.indexOf(speechRate) + 1) % speeds.length];
    setSpeechRate(next);
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
        <div>
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold mb-0">Chat with your Material</h5>
            <span className="badge bg-light text-muted" style={{ fontSize: "0.75rem" }}>RAG — answers from your document only</span>
          </div>

          <div className="card border-0 shadow-sm rounded-4" style={{ overflow: "hidden" }}>
            {/* Messages */}
            <div className="chat-messages p-4" style={{ minHeight: 280, maxHeight: 420, overflowY: "auto" }}>
              {chatMessages.length === 0 && (
                <div className="text-center py-4 text-muted" style={{ fontSize: "0.9rem" }}>
                  <MessageSquare size={32} color="#cbd5e1" className="mb-2" />
                  <p className="mb-0">Ask anything about <strong>{material.title}</strong></p>
                  <p className="small">e.g. "What are the main topics?" or "Explain the first concept."</p>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start", marginBottom: 10 }}>
                  <div className={`chat-bubble ${msg.role} ${msg.thinking ? "thinking" : ""}`}>
                    {msg.thinking ? (
                      <span className="d-flex align-items-center gap-2">
                        <Loader size={13} className="spin-icon" /> Searching your material…
                      </span>
                    ) : msg.text}
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
            <div style={{ borderTop: "1px solid #e2e8f0", padding: "14px 16px", background: "#fafbfc" }}>
              <form onSubmit={sendChatMessage} className="d-flex gap-2">
                <input
                  className="form-control"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask a question about this material…"
                  disabled={!isCompleted}
                />
                <button className="btn btn-primary px-3" disabled={!isCompleted || !chatInput.trim()}>
                  Send
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
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div>
              <h5 className="fw-bold mb-0">Practice Quiz</h5>
              <p className="text-muted small mb-0">AI-generated MCQ questions from your material.</p>
            </div>
            <button className="btn btn-primary" onClick={generateQuiz} disabled={!isCompleted || loadingAction === "quiz"}>
              {loadingAction === "quiz" ? <><Loader size={14} className="me-2 spin-icon" />Generating…</> : "✨ Generate Quiz"}
            </button>
          </div>

          {quiz?.ai_status !== "ai_generated" && quiz && (
            <div className="alert alert-warning small">AI quiz generation unavailable — showing fallback questions.</div>
          )}

          {quiz?.questions?.length > 0 && (
            <div className="d-grid gap-3 mb-3">
              {quiz.questions.map((item, idx) => {
                const selected   = quizAnswers[item.id];
                const isCorrect  = selected === item.correct_answer;
                return (
                  <div key={item.id} className="card border-0 shadow-sm rounded-4">
                    <div className="card-body p-4">
                      <p className="fw-bold mb-3">{idx + 1}. {item.question_text}</p>

                      <div className="d-grid gap-2">
                        {item.choices.map((choice, ci) => {
                          const isSelected  = selected === choice;
                          const isCorrectC  = quizSubmitted && choice === item.correct_answer;
                          const isWrongSel  = quizSubmitted && isSelected && choice !== item.correct_answer;
                          let cls = "choice-btn";
                          if (isSelected && !quizSubmitted) cls += " selected";
                          if (isCorrectC)  cls += " choice-correct";
                          if (isWrongSel)  cls += " choice-wrong";
                          return (
                            <button key={ci} className={cls} onClick={() => selectAnswer(item.id, choice)}>
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
                        <div className="mt-3 p-3 rounded-3" style={{ background: isCorrect ? "#f0fdf4" : "#fef2f2" }}>
                          <span className={`badge ${isCorrect ? "bg-success" : "bg-danger"} mb-2`}>
                            {isCorrect ? "✓ Correct" : "✗ Wrong"}
                          </span>
                          {!isCorrect && (
                            <p className="small mb-1"><strong>Correct:</strong> {item.correct_answer}</p>
                          )}
                          {item.explanation && (
                            <p className="small text-muted mb-0"><strong>Explanation:</strong> {item.explanation}</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {quiz?.questions?.length > 0 && (
            <div className="d-flex gap-2">
              {!quizSubmitted
                ? <button className="btn btn-success px-4" onClick={checkAnswers}>Check Answers</button>
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
            <div className={`audio-player ${isSpeaking ? "playing" : ""}`}>
              <p className="mb-0 fw-semibold" style={{ opacity: 0.9, fontSize: "0.88rem" }}>
                {material.title}
              </p>
              <p style={{ opacity: 0.55, fontSize: "0.78rem", marginTop: 2 }}>
                {summary.summary_text?.split(" ").length || 0} words · speed {speechRate}×
              </p>

              {/* Waveform */}
              <div className="audio-waveform">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div key={i} className="audio-bar" style={{ height: isSpeaking ? undefined : 4 + (i % 5) * 3 }} />
                ))}
              </div>

              {/* Progress track */}
              <div className="audio-track">
                <div className="audio-track-fill" style={{ width: `${audioProgress}%` }} />
              </div>

              {/* Controls */}
              <div className="audio-controls">
                <button className="audio-speed-badge" onClick={cycleSpeed} title="Change speed">
                  {speechRate}×
                </button>
                <button className="audio-btn play-btn" onClick={isSpeaking ? stopSpeaking : speakSummary}>
                  {isSpeaking ? <StopCircle size={22} /> : <Play size={22} />}
                </button>
                <button className="audio-btn" onClick={() => setAudioProgress(0)} disabled={isSpeaking} title="Reset">
                  <RotateCcw size={16} />
                </button>
              </div>
            </div>
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