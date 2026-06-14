import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";

const StudentExams = () => {
  const navigate = useNavigate();

  const [courses, setCourses] = useState([]);
  const [blueprints, setBlueprints] = useState([]);

  const [mode, setMode] = useState("course");
  const [courseId, setCourseId] = useState("");
  const [blueprintId, setBlueprintId] = useState("");
  const [totalQuestions, setTotalQuestions] = useState(1);
  const [durationMinutes, setDurationMinutes] = useState(30);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [courseRes, blueprintRes] = await Promise.all([
        api.get("/exit-exams/courses/"),
        api.get("/exit-exams/exam-blueprints/"),
      ]);

      setCourses(courseRes.data);
      setBlueprints(blueprintRes.data);

      if (courseRes.data.length > 0) {
        setCourseId(courseRes.data[0].id);
      }

      if (blueprintRes.data.length > 0) {
        setBlueprintId(blueprintRes.data[0].id);
      }
    } catch (err) {
      setError("Failed to load exam setup data.");
    }
  };

  const startExam = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let payload = {};

      if (mode === "blueprint") {
        payload = {
          blueprint_id: Number(blueprintId),
        };
      } else {
        payload = {
          course_id: Number(courseId),
          total_questions: Number(totalQuestions),
          duration_minutes: Number(durationMinutes),
        };
      }

      const response = await api.post("/exit-exams/generate-mock-exam/", payload);

      navigate(`/student/exam/${response.data.mock_exam.id}`, {
        state: {
          mockExam: response.data.mock_exam,
        },
      });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to generate exam. Check if enough questions exist."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-2">Start Exam</h2>
      <p className="text-muted">
        Generate a normal mock exam or an official-style blueprint exam.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row">
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <form onSubmit={startExam}>
                <div className="mb-3">
                  <label className="form-label fw-semibold">Exam Mode</label>
                  <select
                    className="form-select"
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                  >
                    <option value="course">Normal Mock Exam</option>
                    <option value="blueprint">Blueprint Exit Exam Simulation</option>
                  </select>
                </div>

                {mode === "course" && (
                  <>
                    <div className="mb-3">
                      <label className="form-label fw-semibold">Course</label>
                      <select
                        className="form-select"
                        value={courseId}
                        onChange={(e) => setCourseId(e.target.value)}
                      >
                        {courses.map((course) => (
                          <option key={course.id} value={course.id}>
                            {course.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="row">
                      <div className="col-md-6 mb-3">
                        <label className="form-label fw-semibold">
                          Total Questions
                        </label>
                        <input
                          type="number"
                          className="form-control"
                          value={totalQuestions}
                          onChange={(e) => setTotalQuestions(e.target.value)}
                          min="1"
                        />
                      </div>

                      <div className="col-md-6 mb-3">
                        <label className="form-label fw-semibold">
                          Duration Minutes
                        </label>
                        <input
                          type="number"
                          className="form-control"
                          value={durationMinutes}
                          onChange={(e) => setDurationMinutes(e.target.value)}
                          min="1"
                        />
                      </div>
                    </div>
                  </>
                )}

                {mode === "blueprint" && (
                  <div className="mb-3">
                    <label className="form-label fw-semibold">Blueprint</label>
                    <select
                      className="form-select"
                      value={blueprintId}
                      onChange={(e) => setBlueprintId(e.target.value)}
                    >
                      {blueprints.map((blueprint) => (
                        <option key={blueprint.id} value={blueprint.id}>
                          {blueprint.title} - {blueprint.total_questions} questions
                        </option>
                      ))}
                    </select>

                    <div className="form-text">
                      Blueprint exams follow admin-defined domain distribution.
                    </div>
                  </div>
                )}

                <button className="btn btn-primary w-100" disabled={loading}>
                  {loading ? "Generating Exam..." : "Start Exam"}
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-5 mt-4 mt-lg-0">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold">Exam Rules</h5>
              <ul className="text-muted mt-3">
                <li>Questions are selected from approved question bank.</li>
                <li>Correct answers are hidden during the exam.</li>
                <li>Score and explanation appear after submission.</li>
                <li>Your weak topics and readiness score update automatically.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentExams;
