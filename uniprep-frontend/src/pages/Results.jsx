import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/api";

const Results = () => {
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      const response = await api.get("/exit-exams/my-results/");
      setResults(response.data.results || []);
    } catch (err) {
      setError("Failed to load results.");
    }
  };

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-3">Exam Results</h2>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="card border-0 shadow-sm rounded-4">
        <div className="card-body p-4">
          {results.length === 0 ? (
            <p className="text-muted mb-0">No exam results yet.</p>
          ) : (
            <div className="table-responsive">
              <table className="table align-middle">
                <thead>
                  <tr>
                    <th>Exam</th>
                    <th>Course</th>
                    <th>Score</th>
                    <th>Correct</th>
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  {results.map((result) => (
                    <tr key={result.attempt_id}>
                      <td>{result.exam_title}</td>
                      <td>{result.course}</td>
                      <td>
                        <span className="badge bg-primary">
                          {result.score}%
                        </span>
                      </td>
                      <td>
                        {result.correct_count}/{result.total_questions}
                      </td>
                      <td>
                        {new Date(result.submitted_at).toLocaleString()}
                      </td>
                      <td>
                        <Link
                          className="btn btn-sm btn-outline-primary"
                          to={`/student/results/${result.attempt_id}`}
                        >
                          Review
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Results;