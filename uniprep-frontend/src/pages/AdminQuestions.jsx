import { useEffect, useState } from "react";
import api from "../api/api";

const AdminQuestions = () => {
  const [questions, setQuestions] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState({
    topic: "",
    text: "",
    bloom_level: "knowledge",
    difficulty: "medium",
    explanation: "",
    is_active: true,
    choice_a: "",
    choice_b: "",
    choice_c: "",
    choice_d: "",
    correct_answer: "A",
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [questionRes, topicRes] = await Promise.all([
        api.get("/exit-exams/questions/"),
        api.get("/exit-exams/topics/"),
      ]);

      setQuestions(questionRes.data);
      setTopics(topicRes.data);

      if (topicRes.data.length > 0) {
        setForm((prev) => ({
          ...prev,
          topic: topicRes.data[0].id,
        }));
      }
    } catch (err) {
      setError("Failed to load question bank.");
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;

    setForm({
      ...form,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  const createQuestion = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const questionResponse = await api.post("/exit-exams/questions/", {
        topic: Number(form.topic),
        text: form.text,
        bloom_level: form.bloom_level,
        difficulty: form.difficulty,
        explanation: form.explanation,
        is_active: form.is_active,
      });

      const questionId = questionResponse.data.id;

      const choices = [
        {
          letter: "A",
          text: form.choice_a,
        },
        {
          letter: "B",
          text: form.choice_b,
        },
        {
          letter: "C",
          text: form.choice_c,
        },
        {
          letter: "D",
          text: form.choice_d,
        },
      ];

      for (const choice of choices) {
        await api.post("/exit-exams/choices/", {
          question: questionId,
          text: choice.text,
          is_correct: form.correct_answer === choice.letter,
        });
      }

      setSuccess("Question and choices created successfully.");

      setForm({
        ...form,
        text: "",
        explanation: "",
        choice_a: "",
        choice_b: "",
        choice_c: "",
        choice_d: "",
        correct_answer: "A",
      });

      await fetchData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to create question. Check all fields."
      );
    }
  };

  const deleteQuestion = async (questionId) => {
    const confirmed = window.confirm(
      "Delete this question? This will also remove its choices."
    );

    if (!confirmed) return;

    try {
      await api.delete(`/exit-exams/questions/${questionId}/`);
      setSuccess("Question deleted successfully.");
      await fetchData();
    } catch (err) {
      setError("Failed to delete question.");
    }
  };

  const getCorrectChoice = (question) => {
    const correct = question.choices?.find((choice) => choice.is_correct);
    return correct ? correct.text : "Not set";
  };

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-2">Question Bank</h2>
      <p className="text-muted">
        Manage official Exit Exam questions and choices.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="row g-4">
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Create Question</h5>

              <form onSubmit={createQuestion}>
                <div className="mb-3">
                  <label className="form-label">Topic</label>
                  <select
                    name="topic"
                    className="form-select"
                    value={form.topic}
                    onChange={handleChange}
                    required
                  >
                    {topics.map((topic) => (
                      <option key={topic.id} value={topic.id}>
                        {topic.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Question Text</label>
                  <textarea
                    name="text"
                    className="form-control"
                    rows="4"
                    value={form.text}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Bloom Level</label>
                    <select
                      name="bloom_level"
                      className="form-select"
                      value={form.bloom_level}
                      onChange={handleChange}
                    >
                      <option value="knowledge">Knowledge</option>
                      <option value="comprehension">Comprehension</option>
                      <option value="application">Application</option>
                      <option value="analysis">Analysis</option>
                    </select>
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Difficulty</label>
                    <select
                      name="difficulty"
                      className="form-select"
                      value={form.difficulty}
                      onChange={handleChange}
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                </div>

                <div className="mb-3">
                  <label className="form-label">Choice A</label>
                  <input
                    name="choice_a"
                    className="form-control"
                    value={form.choice_a}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Choice B</label>
                  <input
                    name="choice_b"
                    className="form-control"
                    value={form.choice_b}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Choice C</label>
                  <input
                    name="choice_c"
                    className="form-control"
                    value={form.choice_c}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Choice D</label>
                  <input
                    name="choice_d"
                    className="form-control"
                    value={form.choice_d}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Correct Answer</label>
                  <select
                    name="correct_answer"
                    className="form-select"
                    value={form.correct_answer}
                    onChange={handleChange}
                  >
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Explanation</label>
                  <textarea
                    name="explanation"
                    className="form-control"
                    rows="3"
                    value={form.explanation}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-check mb-3">
                  <input
                    type="checkbox"
                    name="is_active"
                    className="form-check-input"
                    checked={form.is_active}
                    onChange={handleChange}
                    id="isActive"
                  />
                  <label className="form-check-label" htmlFor="isActive">
                    Active question
                  </label>
                </div>

                <button className="btn btn-primary w-100">
                  Save Question
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">All Questions</h5>

              {questions.length === 0 ? (
                <p className="text-muted">No questions found.</p>
              ) : (
                <div className="d-grid gap-3">
                  {questions.map((question) => (
                    <div key={question.id} className="question-bank-card">
                      <div className="d-flex justify-content-between gap-3">
                        <div>
                          <div className="mb-2">
                            <span className="badge bg-secondary me-2">
                              {question.difficulty}
                            </span>

                            <span className="badge bg-info text-dark me-2">
                              {question.bloom_level}
                            </span>

                            {question.is_active ? (
                              <span className="badge bg-success">Active</span>
                            ) : (
                              <span className="badge bg-danger">Inactive</span>
                            )}
                          </div>

                          <h6 className="fw-bold">{question.text}</h6>

                          <p className="small text-muted mb-2">
                            Topic: {question.topic_name || question.topic}
                          </p>

                          <div className="small">
                            {question.choices?.map((choice, index) => (
                              <div
                                key={choice.id}
                                className={
                                  choice.is_correct
                                    ? "text-success fw-bold"
                                    : "text-muted"
                                }
                              >
                                {String.fromCharCode(65 + index)}. {choice.text}
                                {choice.is_correct && " (correct)"}
                              </div>
                            ))}
                          </div>

                          <p className="small mt-2 mb-0">
                            <strong>Correct:</strong>{" "}
                            {getCorrectChoice(question)}
                          </p>
                        </div>

                        <button
                          className="btn btn-sm btn-outline-danger align-self-start"
                          onClick={() => deleteQuestion(question.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminQuestions;
