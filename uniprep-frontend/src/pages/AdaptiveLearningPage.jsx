import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import {
  BookOpen,
  Layers,
  HelpCircle,
  Award,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Check,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Loader2,
} from "lucide-react";

// ─── Helpers ────────────────────────────────────────────────────────────────
const getPriorityBadge = (priority) => {
  if (priority === "high") return <span className="badge bg-danger">High Priority</span>;
  if (priority === "medium") return <span className="badge bg-warning text-dark">Medium Priority</span>;
  return <span className="badge bg-secondary">Low Priority</span>;
};

// ─── Sub-components ──────────────────────────────────────────────────────────

/**
 * STEP 1 — AI SUMMARY (sourced from exam bank questions via adaptive AI service)
 */
const SummaryStep = ({ path, onComplete, actionLoading }) => {
  const [summaryData, setSummaryData] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const loadSummary = useCallback(async () => {
    if (!path?.topic) return;
    setSummaryLoading(true);
    setSummaryError("");
    try {
      const res = await api.get("/adaptive-learning/summary/", {
        params: { topic: path.topic },
      });
      setSummaryData(res.data);
    } catch (err) {
      setSummaryError(
        err.response?.data?.detail ||
        "Failed to generate summary. Please try again."
      );
    } finally {
      setSummaryLoading(false);
    }
  }, [path?.topic]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  return (
    <div>
      <div className="d-flex align-items-center gap-2 text-primary fw-bold mb-3">
        <BookOpen size={24} />
        <h4 className="fw-bold mb-0">Step 1: AI Topic Summary</h4>
      </div>
      <p className="text-muted mb-4">
        An AI-generated study summary for <strong>{path.topic}</strong>, synthesised directly
        from the approved exam bank questions — covering key concepts, rules, and definitions
        you need to master.
      </p>

      {summaryLoading && (
        <div className="d-flex align-items-center gap-3 p-4 bg-light rounded-4 border mb-4 text-muted">
          <Loader2 size={22} className="text-primary" style={{ animation: "spin 1s linear infinite" }} />
          <span>Generating your personalised topic summary from the exam bank…</span>
        </div>
      )}

      {summaryError && (
        <div className="alert alert-warning d-flex align-items-center gap-2 mb-4">
          <AlertCircle size={18} />
          <div>
            {summaryError}
            <button className="btn btn-sm btn-outline-secondary ms-3" onClick={loadSummary}>
              Retry
            </button>
          </div>
        </div>
      )}

      {summaryData && !summaryLoading && (
        <div className="mb-4">
          {/* Narrative summary */}
          <div className="p-4 bg-light rounded-4 border mb-3">
            <h5 className="fw-bold text-dark mb-3">
              Summary — {summaryData.topic}
              <span className="badge bg-info text-dark ms-2 fs-6 fw-normal">
                {summaryData.domain}
              </span>
            </h5>
            {summaryData.summary_text ? (
              summaryData.summary_text.split("\n").map((para, i) =>
                para.trim() ? (
                  <p key={i} className="text-secondary mb-2">
                    {para}
                  </p>
                ) : null
              )
            ) : (
              <p className="text-muted">No summary text generated.</p>
            )}
          </div>

          {/* Key points */}
          {summaryData.key_points?.length > 0 && (
            <div className="p-4 bg-white rounded-4 border mb-3">
              <h6 className="fw-bold text-dark mb-3">📌 Key Points to Remember</h6>
              <ul className="mb-0 text-secondary">
                {summaryData.key_points.map((pt, i) => (
                  <li key={i} className="mb-1">{pt}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Important terms */}
          {summaryData.important_terms?.length > 0 && (
            <div className="p-4 bg-white rounded-4 border mb-3">
              <h6 className="fw-bold text-dark mb-3">📖 Important Terms</h6>
              <div className="row g-2">
                {summaryData.important_terms.map((term, i) => {
                  const [termName, ...defParts] = term.split(":");
                  const definition = defParts.join(":").trim();
                  return (
                    <div key={i} className="col-md-6">
                      <div className="p-2 border rounded-3 bg-light">
                        <strong className="text-primary">{termName.trim()}</strong>
                        {definition && <span className="text-muted"> — {definition}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
        <button
          className="btn btn-outline-secondary rounded-3 d-flex align-items-center gap-1"
          onClick={loadSummary}
          disabled={summaryLoading}
        >
          <RefreshCw size={14} /> Regenerate Summary
        </button>
        <button
          className="btn btn-primary btn-lg rounded-3 px-4 d-flex align-items-center gap-2"
          onClick={() => onComplete("summary")}
          disabled={actionLoading || summaryLoading || !summaryData}
        >
          {actionLoading ? "Saving…" : "Mark Complete & Proceed to Flashcards"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
};

/**
 * STEP 2 — FLASHCARDS (AI-generated, gap-weighted toward student's unseen/wrong questions)
 */
const FlashcardsStep = ({ path, onComplete, actionLoading }) => {
  const [cards, setCards] = useState([]);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [cardsError, setCardsError] = useState("");
  const [cardIndex, setCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const loadFlashcards = useCallback(async () => {
    if (!path?.topic) return;
    setCardsLoading(true);
    setCardsError("");
    setCardIndex(0);
    setIsFlipped(false);
    try {
      const res = await api.get("/adaptive-learning/flashcards/", {
        params: { topic: path.topic, count: 10 },
      });
      setCards(res.data.flashcards || []);
    } catch (err) {
      setCardsError(
        err.response?.data?.detail ||
        "Failed to generate flashcards. Please try again."
      );
    } finally {
      setCardsLoading(false);
    }
  }, [path?.topic]);

  useEffect(() => {
    loadFlashcards();
  }, [loadFlashcards]);

  const currentCard = cards[cardIndex];
  const difficultyColor = {
    easy: "bg-success",
    medium: "bg-warning text-dark",
    hard: "bg-danger",
  };

  return (
    <div>
      <div className="d-flex align-items-center gap-2 text-primary fw-bold mb-3">
        <Layers size={24} />
        <h4 className="fw-bold mb-0">Step 2: Personalised Flashcard Practice</h4>
      </div>
      <p className="text-muted mb-4">
        Flashcards for <strong>{path.topic}</strong> — prioritised toward questions you've
        missed or never attempted yet. Click a card to reveal the answer.
      </p>

      {cardsLoading && (
        <div className="d-flex align-items-center gap-3 p-4 bg-light rounded-4 border mb-4 text-muted">
          <Loader2 size={22} className="text-primary" style={{ animation: "spin 1s linear infinite" }} />
          <span>Generating personalised flashcards from your question gaps…</span>
        </div>
      )}

      {cardsError && (
        <div className="alert alert-warning d-flex align-items-center gap-2 mb-4">
          <AlertCircle size={18} />
          <div>
            {cardsError}
            <button className="btn btn-sm btn-outline-secondary ms-3" onClick={loadFlashcards}>
              Retry
            </button>
          </div>
        </div>
      )}

      {cards.length > 0 && !cardsLoading && (
        <div className="mb-4">
          {/* Card counter */}
          <div className="d-flex justify-content-between align-items-center mb-3">
            <span className="fw-semibold text-muted small">
              Card {cardIndex + 1} of {cards.length}
            </span>
            {currentCard?.difficulty && (
              <span className={`badge ${difficultyColor[currentCard.difficulty] || "bg-secondary"}`}>
                {currentCard.difficulty}
              </span>
            )}
          </div>

          {/* Flip card */}
          <div
            className="card border-0 shadow-sm rounded-4 text-center p-5 mb-3"
            style={{
              minHeight: "200px",
              cursor: "pointer",
              background: isFlipped
                ? "linear-gradient(135deg, #e8f5e9, #f0fdf4)"
                : "linear-gradient(135deg, #eff6ff, #f0f9ff)",
              transition: "background 0.3s ease",
            }}
            onClick={() => setIsFlipped(!isFlipped)}
          >
            <span className="small fw-semibold text-muted mb-3 d-block">
              {isFlipped ? "ANSWER" : "QUESTION — tap to reveal"}
            </span>
            <h5 className="fw-bold text-dark mb-0">
              {isFlipped ? currentCard.back : currentCard.front}
            </h5>
          </div>

          {/* Navigation */}
          <div className="d-flex justify-content-between align-items-center">
            <button
              className="btn btn-outline-secondary rounded-3 d-flex align-items-center gap-1"
              disabled={cardIndex === 0}
              onClick={() => { setCardIndex(cardIndex - 1); setIsFlipped(false); }}
            >
              <ChevronLeft size={16} /> Previous
            </button>

            <button
              className="btn btn-outline-secondary rounded-3 d-flex align-items-center gap-1"
              onClick={loadFlashcards}
            >
              <RefreshCw size={14} /> Regenerate
            </button>

            <button
              className="btn btn-outline-secondary rounded-3 d-flex align-items-center gap-1"
              disabled={cardIndex === cards.length - 1}
              onClick={() => { setCardIndex(cardIndex + 1); setIsFlipped(false); }}
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      <div className="d-flex justify-content-end mt-4">
        <button
          className="btn btn-primary btn-lg rounded-3 px-4 d-flex align-items-center gap-2"
          onClick={() => onComplete("flashcards")}
          disabled={actionLoading || cardsLoading || cards.length === 0}
        >
          {actionLoading ? "Saving…" : "Mark Complete & Proceed to Quiz"}
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
};

/**
 * STEP 3 — REAL QUIZ (AI-free, direct exam bank questions)
 */
const QuizStep = ({ path, onComplete, actionLoading }) => {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizError, setQuizError] = useState("");
  const [quizResult, setQuizResult] = useState(null);

  const loadQuiz = useCallback(async () => {
    if (!path?.topic) return;
    setQuizLoading(true);
    setQuizError("");
    setQuizResult(null);
    setAnswers({});
    try {
      const res = await api.get("/adaptive-learning/quiz/");
      setQuestions(res.data.questions || []);
    } catch (err) {
      setQuizError(
        err.response?.data?.detail ||
        "Failed to load quiz questions. Please try again."
      );
    } finally {
      setQuizLoading(false);
    }
  }, [path?.topic]);

  useEffect(() => {
    loadQuiz();
  }, [loadQuiz]);

  const selectAnswer = (questionId, choiceId) => {
    setAnswers((prev) => ({ ...prev, [questionId]: choiceId }));
  };

  const submitQuiz = async () => {
    if (Object.keys(answers).length < questions.length) {
      setQuizError("Please answer all questions before submitting.");
      return;
    }
    setQuizLoading(true);
    setQuizError("");
    try {
      const formattedAnswers = Object.entries(answers).map(
        ([questionId, selectedChoiceId]) => ({
          question_id: Number(questionId),
          selected_choice_id: Number(selectedChoiceId),
        })
      );
      const res = await api.post("/adaptive-learning/quiz/submit/", {
        answers: formattedAnswers,
      });
      setQuizResult(res.data);
    } catch (err) {
      setQuizError(
        err.response?.data?.detail ||
        "Failed to submit quiz. Please try again."
      );
    } finally {
      setQuizLoading(false);
    }
  };

  return (
    <div>
      <div className="d-flex align-items-center gap-2 text-primary fw-bold mb-3">
        <HelpCircle size={24} />
        <h4 className="fw-bold mb-0">Step 3: Practice Quiz Gate</h4>
      </div>
      <p className="text-muted mb-4">
        Complete the quiz for <strong>{path.topic}</strong>. You must achieve the system
        unlock threshold score to unlock the Mini Mock step.
      </p>

      <div className="alert alert-info d-flex align-items-start gap-2 mb-4">
        <AlertCircle size={18} className="mt-1 flex-shrink-0" />
        <div>
          <strong>Exam Bank Quiz</strong> — questions are selected directly from approved exit
          exam questions for this topic (unseen and wrong-answer priority). This step is entirely
          AI-free for reliability.
        </div>
      </div>

      {quizLoading && !quizResult && (
        <div className="d-flex align-items-center gap-3 p-4 bg-light rounded-4 border mb-4 text-muted">
          <Loader2 size={22} className="text-primary" style={{ animation: "spin 1s linear infinite" }} />
          <span>Loading quiz questions…</span>
        </div>
      )}

      {quizError && (
        <div className="alert alert-warning d-flex align-items-center gap-2 mb-4">
          <AlertCircle size={18} />
          <div>
            {quizError}
            <button className="btn btn-sm btn-outline-secondary ms-3" onClick={loadQuiz}>
              Retry
            </button>
          </div>
        </div>
      )}

      {!quizResult && questions.length > 0 && !quizLoading && (
        <div className="mb-4">
          {questions.map((question, index) => (
            <div key={question.id} className="card border-0 shadow-sm rounded-4 mb-3">
              <div className="card-body p-4">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <span className="badge bg-primary">Q{index + 1}</span>
                  <span className="badge bg-secondary text-capitalize">{question.difficulty}</span>
                </div>
                <h5 className="fw-bold mb-3">{question.text}</h5>
                <div className="d-grid gap-2">
                  {question.choices.map((choice) => (
                    <button
                      key={choice.id}
                      className={`btn text-start ${
                        answers[question.id] === choice.id
                          ? "btn-primary"
                          : "btn-outline-secondary"
                      }`}
                      onClick={() => selectAnswer(question.id, choice.id)}
                    >
                      {choice.text}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}

          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <button
              className="btn btn-outline-secondary rounded-3 d-flex align-items-center gap-1"
              onClick={loadQuiz}
              disabled={quizLoading}
            >
              <RefreshCw size={14} /> Regenerate Quiz
            </button>
            <button
              className="btn btn-primary btn-lg rounded-3 px-4 d-flex align-items-center gap-2"
              onClick={submitQuiz}
              disabled={quizLoading || Object.keys(answers).length < questions.length}
            >
              {quizLoading ? "Submitting…" : "Submit Quiz Answers"}
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {quizResult && (
        <div className="mb-4">
          <div className={`alert ${quizResult.score >= (quizResult.quiz_unlock_score || 70) ? "alert-success" : "alert-warning"} mb-4`}>
            <h5 className="fw-bold mb-1">
              Quiz Score: {quizResult.score}% ({quizResult.correct_count}/{quizResult.total_questions})
            </h5>
            <p className="mb-0">
              {quizResult.score >= (quizResult.quiz_unlock_score || 70)
                ? "Great job! You unlocked the Mini Mock step."
                : `Score below the unlock threshold (${quizResult.quiz_unlock_score || 70}%). Review the explanations and try again.`}
            </p>
          </div>

          <div className="mb-4">
            {quizResult.details.map((detail, index) => (
              <div key={detail.question_id} className="card border-0 shadow-sm rounded-4 mb-3">
                <div className="card-body p-4">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="badge bg-primary">Q{index + 1}</span>
                    <span className={`badge ${detail.is_correct ? "bg-success" : "bg-danger"}`}>
                      {detail.is_correct ? "Correct" : "Incorrect"}
                    </span>
                  </div>
                  <p className="fw-semibold mb-2">{detail.question}</p>
                  <p className="text-muted mb-1">
                    <strong>Your answer:</strong> {detail.selected_answer || "Not answered"}
                  </p>
                  <p className="text-muted mb-1">
                    <strong>Correct answer:</strong> {detail.correct_answer}
                  </p>
                  {detail.explanation && (
                    <p className="text-muted mb-0">
                      <strong>Explanation:</strong> {detail.explanation}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <button
              className="btn btn-outline-secondary rounded-3 d-flex align-items-center gap-1"
              onClick={loadQuiz}
              disabled={actionLoading}
            >
              <RefreshCw size={14} /> Retry Quiz
            </button>
            <button
              className="btn btn-primary btn-lg rounded-3 px-4 d-flex align-items-center gap-2"
              onClick={() => onComplete("quiz", quizResult.score)}
              disabled={actionLoading || quizResult.score < (quizResult.quiz_unlock_score || 70)}
            >
              {actionLoading ? "Unlocking…" : "Proceed to Mini Mock"}
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * STEP 4 — REAL MINI MOCK (AI-free, 5 exam bank questions)
 */
const MiniMockStep = ({ path, onComplete, onFinish, actionLoading, stepObj }) => {
  const navigate = useNavigate();
  const [miniMockLoading, setMiniMockLoading] = useState(false);
  const [miniMockError, setMiniMockError] = useState("");

  useEffect(() => {
    // Auto-complete the mini mock step if the student has already submitted a real attempt.
    if (stepObj?.completed) return;
    const autoComplete = async () => {
      try {
        const res = await api.post("/adaptive-learning/mini-mock/complete/");
        if (res.data?.unlocked) {
          onComplete("mini_mock");
        }
      } catch {
        // No submitted attempt yet; show the Start button.
      }
    };
    autoComplete();
  }, [stepObj?.completed, onComplete]);

  const startMiniMock = async () => {
    if (!path?.topic) return;
    setMiniMockLoading(true);
    setMiniMockError("");
    try {
      const res = await api.post("/exit-exams/generate-mock-exam/", {
        topic: path.topic,
        total_questions: 5,
        duration_minutes: 15,
      });
      navigate(`/student/exam/${res.data.mock_exam.id}`, {
        state: {
          mockExam: res.data.mock_exam,
          returnTo: "/student/learning",
        },
      });
    } catch (err) {
      setMiniMockError(
        err.response?.data?.detail ||
        "Failed to generate mini mock. Please try again."
      );
    } finally {
      setMiniMockLoading(false);
    }
  };

  return (
    <div>
      <div className="d-flex align-items-center gap-2 text-primary fw-bold mb-3">
        <Award size={24} />
        <h4 className="fw-bold mb-0">Step 4: 5-Question Topic Mini Mock</h4>
      </div>
      <p className="text-muted mb-4">
        Final assessment step for <strong>{path.topic}</strong>. Questions are selected from
        the exam bank with anti-redundancy priority (unseen and previously-wrong questions first).
      </p>

      {miniMockError && (
        <div className="alert alert-warning d-flex align-items-center gap-2 mb-4">
          <AlertCircle size={18} />
          <div>{miniMockError}</div>
        </div>
      )}

      {!stepObj?.completed && (
        <div className="p-4 bg-light rounded-4 border mb-4">
          <h6 className="fw-bold mb-3">Start Real Mini Mock</h6>
          <p className="text-muted mb-3">
            Take a timed 5-question mock exam for this topic. Your answers are scored on the
            backend and the result updates your topic performance and readiness score.
          </p>
          <button
            className="btn btn-primary btn-lg rounded-3 px-4 d-flex align-items-center gap-2"
            onClick={startMiniMock}
            disabled={miniMockLoading || actionLoading}
          >
            {miniMockLoading ? "Generating Mini Mock…" : "Start Mini Mock Exam"}
            <ArrowRight size={18} />
          </button>
        </div>
      )}

      {stepObj?.completed && (
        <div className="alert alert-success d-flex align-items-center gap-2 mb-4">
          <Check size={18} />
          <div className="fw-semibold">Mini Mock completed. You can now finish the learning path.</div>
        </div>
      )}

      <div className="d-flex justify-content-end">
        <button
          className="btn btn-success btn-lg rounded-3 px-5 fw-bold d-flex align-items-center gap-2"
          onClick={onFinish}
          disabled={actionLoading || !stepObj?.completed}
        >
          {actionLoading
            ? "Recalculating Readiness…"
            : "Finish Learning Path & Update Readiness Score ★"}
        </button>
      </div>
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const AdaptiveLearningPage = () => {
  const navigate = useNavigate();
  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [activeStepTab, setActiveStepTab] = useState("summary");
  const [completionResult, setCompletionResult] = useState(null);

  useEffect(() => {
    fetchCurrentPath();
  }, []);

  const fetchCurrentPath = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/adaptive-learning/current/");
      setPath(res.data);
      if (res.data?.current_step) setActiveStepTab(res.data.current_step);
    } catch (err) {
      if (err.response?.status === 404) setPath(null);
      else setError("Failed to load current learning path.");
    } finally {
      setLoading(false);
    }
  };

  const handleStartPath = async () => {
    setActionLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await api.post("/adaptive-learning/start/");
      setPath(res.data);
      setActiveStepTab(res.data.current_step || "summary");
      setMessage("New learning path initiated!");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start learning path.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteStep = async (stepType, score = null) => {
    if (!path) return;
    setActionLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await api.post("/adaptive-learning/step-complete/", {
        learning_path_id: path.id,
        step_type: stepType,
        score: score !== null ? Number(score) : null,
      });
      const updatedPath = res.data.learning_path;
      setPath(updatedPath);
      if (res.data.unlocked) {
        setMessage(res.data.message || "Step completed!");
        if (updatedPath.current_step) setActiveStepTab(updatedPath.current_step);
      } else {
        setError(res.data.message || "Score did not meet the unlock threshold. Please retry.");
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to complete step."
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleFinishPath = async () => {
    if (!path) return;
    setActionLoading(true);
    setError("");
    try {
      const res = await api.post("/adaptive-learning/finish/", {
        learning_path_id: path.id,
      });
      setCompletionResult(res.data);
      setPath(null);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to finish learning path.");
    } finally {
      setActionLoading(false);
    }
  };

  // ── Loading ──
  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading…</span>
        </div>
        <p className="small text-muted mt-2">Loading your adaptive learning path…</p>
      </div>
    );
  }

  // ── Completion Celebration ──
  if (completionResult) {
    return (
      <div className="container py-5">
        <div className="row justify-content-center">
          <div className="col-lg-8 text-center">
            <div className="card border-0 shadow-lg rounded-4 p-5 bg-white">
              <div className="mb-3 d-inline-flex p-3 bg-success-subtle text-success rounded-circle mx-auto">
                <Sparkles size={48} />
              </div>
              <h2 className="fw-bold mb-2">Learning Path Completed!</h2>
              <p className="text-muted fs-5 mb-4">
                Topic: <strong>{completionResult.topic}</strong>
              </p>

              <div className="row g-3 justify-content-center mb-4">
                <div className="col-md-4">
                  <div className="p-3 border rounded-4 bg-light">
                    <span className="small text-muted d-block">Before Readiness</span>
                    <strong className="fs-3 text-secondary">{completionResult.before_readiness}%</strong>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="p-3 border rounded-4 bg-light">
                    <span className="small text-muted d-block">After Readiness</span>
                    <strong className="fs-3 text-primary">{completionResult.after_readiness}%</strong>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="p-3 border rounded-4 bg-success text-white">
                    <span className="small opacity-75 d-block">Readiness Gain</span>
                    <strong className="fs-3">
                      {completionResult.readiness_delta >= 0
                        ? `+${completionResult.readiness_delta}%`
                        : `${completionResult.readiness_delta}%`}
                    </strong>
                  </div>
                </div>
              </div>

              <div className="d-flex justify-content-center gap-3 flex-wrap">
                <button
                  className="btn btn-primary btn-lg rounded-3 px-4"
                  onClick={() => { setCompletionResult(null); handleStartPath(); }}
                >
                  Start Next Topic Path →
                </button>
                <button
                  className="btn btn-outline-secondary btn-lg rounded-3"
                  onClick={() => navigate("/student/dashboard")}
                >
                  Back to Dashboard
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── No active path — prompt to start ──
  if (!path) {
    return (
      <div className="container py-5">
        <div className="row justify-content-center">
          <div className="col-lg-8 text-center">
            <div className="card border-0 shadow-sm rounded-4 p-5 bg-white">
              <div className="mb-3 d-inline-flex p-3 bg-primary-subtle text-primary rounded-circle mx-auto">
                <Sparkles size={40} />
              </div>
              <h2 className="fw-bold mb-2">Adaptive Learning Engine</h2>
              <p className="text-muted mb-4">
                Connect AI Summaries, Flashcards, Quizzes, and Mini Mocks into a single guided
                learning journey — automatically tailored to your weakest exam topics.
              </p>

              {error && <div className="alert alert-danger mb-4">{error}</div>}

              <button
                className="btn btn-primary btn-lg rounded-3 px-5 py-3 fw-bold d-inline-flex align-items-center gap-2 mx-auto"
                onClick={handleStartPath}
                disabled={actionLoading}
              >
                {actionLoading ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" />
                    Selecting optimal topic…
                  </>
                ) : (
                  <>
                    Start Personalised Learning Path
                    <ArrowRight size={20} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Active path ──
  const steps = path.steps || [];
  const getStepObj = (st) => steps.find((s) => s.step_type === st);

  const STEP_CONFIG = [
    { id: "summary",    label: "1. AI Summary",    icon: BookOpen },
    { id: "flashcards", label: "2. Flashcards",     icon: Layers },
    { id: "quiz",       label: "3. Practice Quiz",  icon: HelpCircle },
    { id: "mini_mock",  label: "4. Mini Mock",      icon: Award },
  ];

  return (
    <div className="container-fluid py-4">
      {/* Hero */}
      <div className="dashboard-hero mb-4">
        <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 w-100">
          <div>
            <span className="dashboard-badge">Guided Student Journey</span>
            <h2 className="fw-bold mt-2 mb-1">Topic: {path.topic}</h2>
            <p className="text-muted mb-0">
              Complete each sequential step to unlock the Mini Mock and update your readiness score.
            </p>
          </div>
          <div className="d-flex gap-2 align-items-center">
            {getPriorityBadge(path.priority)}
            <button
              className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
              onClick={fetchCurrentPath}
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger mb-4">{error}</div>}
      {message && <div className="alert alert-success mb-4">{message}</div>}

      {/* Stepper Timeline */}
      <div className="card border-0 shadow-sm rounded-4 mb-4 bg-white">
        <div className="card-body p-4">
          <div className="row g-3 text-center">
            {STEP_CONFIG.map((st) => {
              const stepObj = getStepObj(st.id);
              const isDone = stepObj?.completed;
              const isCurrent = path.current_step === st.id;
              const Icon = st.icon;

              let badgeStyle = "bg-light text-muted border";
              if (isDone) badgeStyle = "bg-success text-white";
              else if (isCurrent) badgeStyle = "bg-primary text-white";

              return (
                <div key={st.id} className="col-md-3">
                  <div
                    className={`p-3 rounded-4 ${
                      activeStepTab === st.id
                        ? "border border-2 border-primary bg-primary-subtle"
                        : "border"
                    }`}
                    onClick={() => setActiveStepTab(st.id)}
                    style={{ cursor: "pointer" }}
                  >
                    <div className="d-flex align-items-center justify-content-center gap-2 mb-2">
                      <div className={`p-2 rounded-circle ${badgeStyle}`}>
                        {isDone ? <Check size={18} /> : <Icon size={18} />}
                      </div>
                      <span className="fw-bold small">{st.label}</span>
                    </div>
                    <div className="small">
                      {isDone ? (
                        <span className="badge bg-success">Completed</span>
                      ) : isCurrent ? (
                        <span className="badge bg-primary">In Progress</span>
                      ) : (
                        <span className="badge bg-secondary">Locked</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Active Step Content */}
      <div className="card border-0 shadow-sm rounded-4 bg-white">
        <div className="card-body p-4">
          {activeStepTab === "summary" && (
            <SummaryStep
              path={path}
              onComplete={handleCompleteStep}
              actionLoading={actionLoading}
            />
          )}
          {activeStepTab === "flashcards" && (
            <FlashcardsStep
              path={path}
              onComplete={handleCompleteStep}
              actionLoading={actionLoading}
            />
          )}
          {activeStepTab === "quiz" && (
            <QuizStep
              path={path}
              onComplete={handleCompleteStep}
              actionLoading={actionLoading}
            />
          )}
          {activeStepTab === "mini_mock" && (
            <MiniMockStep
              path={path}
              onComplete={handleCompleteStep}
              onFinish={handleFinishPath}
              actionLoading={actionLoading}
              stepObj={getStepObj("mini_mock")}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default AdaptiveLearningPage;
