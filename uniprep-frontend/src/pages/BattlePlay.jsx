import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/api";

const BattlePlay = () => {
  const { roomCode } = useParams();
  const navigate = useNavigate();

  const [room, setRoom] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [startTime] = useState(Date.now());
  const [timeLeft, setTimeLeft] = useState(0);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchQuestions();
  }, [roomCode]);

  useEffect(() => {
    if (!room) return;

    setTimeLeft(room.duration_minutes * 60);
  }, [room]);

  useEffect(() => {
    if (!room || timeLeft <= 0) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          submitBattle(true);
          return 0;
        }

        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [room, answers, timeLeft]);

  const fetchQuestions = async () => {
    try {
      const response = await api.get(
        `/collaboration/challenges/${roomCode}/questions/`
      );

      setRoom(response.data.room);
      setQuestions(response.data.questions || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load battle questions.");
    }
  };

  const answeredCount = Object.keys(answers).length;
  const totalQuestions = questions.length;
  const progressPercent =
    totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const currentQuestion = useMemo(() => {
    return questions[currentIndex];
  }, [questions, currentIndex]);

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

  const submitBattle = async (autoSubmit = false) => {
    if (!autoSubmit) {
      const confirmed = window.confirm("Submit your battle attempt?");
      if (!confirmed) return;
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

      await api.post(`/collaboration/challenges/${roomCode}/submit/`, {
        duration_seconds: durationSeconds,
        answers: formattedAnswers,
      });

      navigate(`/student/battle/${roomCode}/results`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit battle.");
    } finally {
      setSubmitting(false);
    }
  };

  if (error) {
    return <div className="container py-5 alert alert-danger">{error}</div>;
  }

  if (!room || !currentQuestion) {
    return <div className="container py-5">Loading battle...</div>;
  }

  return (
    <div className="container-fluid py-4">
      <div className="exam-top-bar mb-3">
        <div>
          <span className="dashboard-badge">Battle Mode</span>
          <h2 className="fw-bold mt-2 mb-1">{room.title}</h2>
          <p className="text-muted mb-0">
            Question {currentIndex + 1} of {questions.length}
          </p>
        </div>

        <div className={`timer-box ${timeLeft <= 120 ? "danger" : ""}`}>
          {formatTime(timeLeft)}
        </div>
      </div>

      <div className="exam-progress-card mb-4">
        <div className="d-flex justify-content-between mb-2">
          <strong>
            {answeredCount}/{totalQuestions} answered
          </strong>
          <span className="text-muted">
            {totalQuestions - answeredCount} unanswered
          </span>
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

      <div className="row">
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-4">{currentQuestion.text}</h5>

              <div className="d-grid gap-3">
                {currentQuestion.choices.map((choice, index) => (
                  <button
                    key={choice.id}
                    className={`choice-btn ${
                      answers[currentQuestion.question_id] === choice.id
                        ? "selected"
                        : ""
                    }`}
                    onClick={() =>
                      selectAnswer(currentQuestion.question_id, choice.id)
                    }
                  >
                    <span className="choice-letter">
                      {String.fromCharCode(65 + index)}
                    </span>
                    <span>{choice.text}</span>
                  </button>
                ))}
              </div>

              <div className="d-flex justify-content-between mt-4">
                <button
                  className="btn btn-outline-secondary"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex(currentIndex - 1)}
                >
                  Previous
                </button>

                {currentIndex < questions.length - 1 ? (
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
                    onClick={() => submitBattle(false)}
                  >
                    {submitting ? "Submitting..." : "Submit Battle"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="col-lg-4 mt-4 mt-lg-0">
          <div className="card border-0 shadow-sm rounded-4 sticky-exam-panel">
            <div className="card-body p-4">
              <h5 className="fw-bold">Navigator</h5>

              <div className="question-grid mt-3">
                {questions.map((item, index) => (
                  <button
                    key={item.id}
                    className={`question-number ${
                      currentIndex === index ? "active" : ""
                    } ${answers[item.question_id] ? "answered" : ""}`}
                    onClick={() => setCurrentIndex(index)}
                  >
                    {index + 1}
                  </button>
                ))}
              </div>

              <button
                className="btn btn-success w-100 mt-4"
                disabled={submitting}
                onClick={() => submitBattle(false)}
              >
                Submit Battle
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BattlePlay;