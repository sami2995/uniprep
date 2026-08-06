import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api/api";

const ResultDetail = () => {
  const { attemptId } = useParams();

  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchResult();
  }, [attemptId]);

  const fetchResult = async () => {
    try {
      const response = await api.get(`/exit-exams/my-results/${attemptId}/`);
      setResult(response.data);
    } catch (err) {
      setError("Failed to load result detail.");
    }
  };

  if (error) {
    return <div className="container py-5 alert alert-danger">{error}</div>;
  }

  if (!result) {
    return <div className="container py-5">Loading result...</div>;
  }

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-1">{result.exam_title}</h2>
      <p className="text-muted">
        {result.course} - Submitted {new Date(result.submitted_at).toLocaleString()}
      </p>

      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body">
              <h6 className="text-muted">Score</h6>
              <h2 className="fw-bold">{result.score}%</h2>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body">
              <h6 className="text-muted">Question Source</h6>
              {result.source_breakdown?.official === result.questions.length ? (
                <h5 className="fw-bold mb-0">
                  {result.source_breakdown.official} Official MOE Questions
                </h5>
              ) : (
                <div className="small">
                  <div>✓ Official MOE: {result.source_breakdown?.official || 0}</div>
                  <div>✓ Instructor-authored: {result.source_breakdown?.instructor || 0}</div>
                  <div className="fw-bold">Total: {result.questions.length}</div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body">
              <h6 className="text-muted">Questions</h6>
              <h2 className="fw-bold">{result.questions.length}</h2>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body">
              <h6 className="text-muted">Duration</h6>
              <h2 className="fw-bold">{result.duration_seconds}s</h2>
            </div>
          </div>
        </div>
      </div>

      <div className="d-grid gap-3">
        {result.questions.map((item, index) => (
          <div key={item.question_id} className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <div className="d-flex justify-content-between mb-2">
                <span className="badge bg-secondary">
                  Q{index + 1} - {item.domain} / {item.topic}
                </span>

                {item.is_correct ? (
                  <span className="badge bg-success">Correct</span>
                ) : (
                  <span className="badge bg-danger">Wrong</span>
                )}
              </div>

              <h5 className="fw-bold">{item.question}</h5>

              <p className="mb-1">
                <strong>Your answer:</strong>{" "}
                {item.selected_answer || "Not answered"}
              </p>

              <p className="mb-1">
                <strong>Correct answer:</strong> {item.correct_answer}
              </p>

              {item.explanation && (
                <div className="alert alert-info mt-3 mb-0">
                  <strong>Explanation:</strong> {item.explanation}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultDetail;
