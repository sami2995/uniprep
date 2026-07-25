import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import api from "../api/api";

const TakeExam = () => {
  const { examId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const mockExam = location.state?.mockExam;

  const [answers, setAnswers] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [startTime] = useState(Date.now());
  const [timeLeft, setTimeLeft] = useState(
    mockExam ? mockExam.duration_minutes * 60 : 0
  );

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  const questions = useMemo(() => {
    return mockExam?.mock_questions || [];
  }, [mockExam]);

  const answeredCount = Object.keys(answers).length;
  const totalQuestions = questions.length;
  const unansweredCount = totalQuestions - answeredCount;
  const progressPercent =
    totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const isTimeLow = timeLeft <= 5 * 60;

  useEffect(() => {
    if (!mockExam) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          executeSubmit(true);
          return 0;
        }

        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [mockExam, answers]);

  useEffect(() => {
    const preventLeaving = (e) => {
      if (!submitting && answeredCount > 0) {
        e.preventDefault();
        e.returnValue = "";
      }
    };

    window.addEventListener("beforeunload", preventLeaving);

    return () => {
      window.removeEventListener("beforeunload", preventLeaving);
    };
  }, [answeredCount, submitting]);

  if (!mockExam) {
    return (
      <div className="container py-5">
        <div className="alert alert-warning">
          Exam data was not found. Please start a new exam.
        </div>

        <button
          className="btn btn-primary"
          onClick={() => navigate("/student/exams")}
        >
          Back to Exams
        </button>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="container py-5">
        <div className="alert alert-warning">
          This exam has no questions.
        </div>

        <button
          className="btn btn-primary"
          onClick={() => navigate("/student/exams")}
        >
          Back to Exams
        </button>
      </div>
    );
  }

  const currentItem = questions[currentIndex];
  const currentQuestion = currentItem.question;

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;

    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const selectAnswer = (questionId, choiceId) => {
    setAnswers({
      ...answers,
      [questionId]: choiceId,
    });
  };

  const goToNextUnanswered = () => {
    const nextUnansweredIndex = questions.findIndex(
      (item, index) => index > currentIndex && !answers[item.question.id]
    );

    if (nextUnansweredIndex !== -1) {
      setCurrentIndex(nextUnansweredIndex);
      return;
    }

    const firstUnansweredIndex = questions.findIndex(
      (item) => !answers[item.question.id]
    );

    if (firstUnansweredIndex !== -1) {
      setCurrentIndex(firstUnansweredIndex);
    }
  };

  const handlePrepareSubmit = () => {
    if (unansweredCount > 0) {
      setShowSubmitModal(true);
    } else {
      executeSubmit(false);
    }
  };

  const handleReviewUnanswered = () => {
    setShowSubmitModal(false);
    const firstUnansweredIndex = questions.findIndex(
      (item) => !answers[item.question.id]
    );
    if (firstUnansweredIndex !== -1) {
      setCurrentIndex(firstUnansweredIndex);
    }
  };

  const executeSubmit = async (isTimeExpired = false) => {
    if (unansweredCount > 0 && !isTimeExpired) {
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const durationSeconds = Math.floor((Date.now() - startTime) / 1000);

      const formattedAnswers = Object.entries(answers).map(
        ([questionId, selectedChoiceId]) => ({
          question_id: Number(questionId),
          selected_choice_id: Number(selectedChoiceId),
        })
      );

      const response = await api.post("/exit-exams/submit-mock-exam/", {
        mock_exam_id: Number(examId),
        duration_seconds: durationSeconds,
        answers: formattedAnswers,
      });

      navigate(`/student/results/${response.data.attempt_id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit exam.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container-fluid py-4">
      <div className="exam-top-bar mb-3">
        <div>
          <h2 className="fw-bold mb-1">{mockExam.title}</h2>
          <p className="text-muted mb-0">
            Question {currentIndex + 1} of {totalQuestions}
          </p>
        </div>

        <div className={`timer-box ${isTimeLow ? "danger" : ""}`}>
          {formatTime(timeLeft)}
        </div>
      </div>

      <div className="exam-progress-card mb-4">
        <div className="d-flex justify-content-between flex-wrap gap-2 mb-2">
          <strong>{answeredCount}/{totalQuestions} answered</strong>
          <span className="text-muted">{unansweredCount} unanswered</span>
        </div>

        <div className="progress exam-progress">
          <div
            className="progress-bar"
            style={{ width: `${progressPercent}%` }}
          >
            {progressPercent}%
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row">
        <div className="col-lg-8">
          <div
            className={`card shadow-sm rounded-4 ${
              !answers[currentQuestion.id] ? "unanswered-card" : "border-0"
            }`}
          >
            <div className="card-body p-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <span className="badge bg-primary">
                  Q{currentIndex + 1}
                </span>

                {answers[currentQuestion.id] ? (
                  <span className="badge bg-success">Answered</span>
                ) : (
                  <span className="badge bg-danger">
                    Not answered
                  </span>
                )}
              </div>

              <h5 className="fw-bold mb-4">{currentQuestion.text}</h5>

              <div className="d-grid gap-3">
                {currentQuestion.choices.map((choice, index) => (
                  <button
                    key={choice.id}
                    className={`choice-btn ${
                      answers[currentQuestion.id] === choice.id
                        ? "selected"
                        : ""
                    }`}
                    onClick={() => selectAnswer(currentQuestion.id, choice.id)}
                  >
                    <span className="choice-letter">
                      {String.fromCharCode(65 + index)}
                    </span>
                    <span>{choice.text}</span>
                  </button>
                ))}
              </div>

              <div className="d-flex justify-content-between flex-wrap gap-2 mt-4">
                <button
                  className="btn btn-outline-secondary"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex(currentIndex - 1)}
                >
                  Previous
                </button>

                <div className="d-flex gap-2 flex-wrap">
                  {unansweredCount > 0 && (
                    <button
                      className="btn btn-outline-primary"
                      onClick={goToNextUnanswered}
                    >
                      Next Unanswered
                    </button>
                  )}

                  {currentIndex < totalQuestions - 1 ? (
                    <button
                      className="btn btn-primary"
                      onClick={() => setCurrentIndex(currentIndex + 1)}
                    >
                      Next
                    </button>
                  ) : (
                    <button
                      className="btn btn-success"
                      disabled={submitting}
                      onClick={handlePrepareSubmit}
                    >
                      {submitting ? "Submitting..." : "Submit Exam"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-lg-4 mt-4 mt-lg-0">
          <div className="card border-0 shadow-sm rounded-4 sticky-exam-panel">
            <div className="card-body p-4">
              <h5 className="fw-bold">Question Navigator</h5>

              <div className="exam-summary-mini mt-3">
                <div>
                  <strong>{answeredCount}</strong>
                  <span>Answered</span>
                </div>

                <div>
                  <strong>{unansweredCount}</strong>
                  <span>Unanswered</span>
                </div>
              </div>

              <div className="question-grid mt-4">
                {questions.map((item, index) => {
                  const isAnswered = Boolean(answers[item.question.id]);
                  const isActive = currentIndex === index;

                  return (
                    <button
                      key={item.id}
                      className={`question-number ${
                        isActive ? "active" : ""
                      } ${isAnswered ? "answered" : "unanswered"}`}
                      onClick={() => setCurrentIndex(index)}
                    >
                      {index + 1}
                    </button>
                  );
                })}
              </div>

              <button
                className="btn btn-success w-100 mt-4"
                disabled={submitting}
                onClick={handlePrepareSubmit}
              >
                Submit Exam
              </button>

              {unansweredCount > 0 && (
                <p className="small text-muted mt-2 mb-0 text-center">
                  You still have {unansweredCount} unanswered question(s).
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {showSubmitModal && (
        <div
          className="modal d-block"
          tabIndex="-1"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.5)" }}
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content rounded-4 border-0 shadow">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold text-danger">
                  Unanswered Questions
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowSubmitModal(false)}
                />
              </div>
              <div className="modal-body py-3">
                <p className="mb-0 fs-5">
                  You have <strong>{unansweredCount}</strong> unanswered question{unansweredCount > 1 ? "s" : ""}.
                </p>
              </div>
              <div className="modal-footer border-0 pt-0">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={handleReviewUnanswered}
                >
                  Go to First Unanswered
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setShowSubmitModal(false)}
                >
                  Continue Exam
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TakeExam;