import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api/api";

const STATUS_LABELS = {
  draft: { label: "Draft", cls: "secondary" },
  submitted: { label: "Pending Approval", cls: "warning" },
  approved: { label: "Approved", cls: "success" },
  rejected: { label: "Rejected", cls: "danger" },
};

const BLOOM_LEVELS = ["knowledge", "comprehension", "application", "analysis"];
const DIFFICULTIES = ["easy", "medium", "hard"];
const CORRECT_OPTIONS = ["A", "B", "C", "D"];

const EMPTY_FORM = {
  topic: "",
  text: "",
  bloom_level: "knowledge",
  difficulty: "medium",
  explanation: "",
  choice_a: "",
  choice_b: "",
  choice_c: "",
  choice_d: "",
  correct_answer: "A",
};

const TeacherQuestionBank = () => {
  const [searchParams] = useSearchParams();
  const [questions, setQuestions] = useState([]);
  const [topics, setTopics] = useState([]);
  const [teachingTopics, setTeachingTopics] = useState([]);
  const [domains, setDomains] = useState([]);

  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);

  // Filters
  const [filters, setFilters] = useState({
    status: "",
    domain: "",
    difficulty: "",
    keyword: "",
  });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Duplicate detection
  const [duplicateModal, setDuplicateModal] = useState(null); // null | { duplicates, pendingSubmit }
  const [checkingDupes, setCheckingDupes] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(
    searchParams.get("filter") || "all"
  );

  useEffect(() => {
    loadMetadata();
  }, []);

  useEffect(() => {
    searchQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page, activeTab]);

  const loadMetadata = async () => {
    try {
      const [topicsRes, assignedRes, domainsRes] = await Promise.all([
        api.get("/exit-exams/topics/"),
        api.get("/exit-exams/my-assigned-topics/"),
        api.get("/exit-exams/domains/"),
      ]);
      // Topics the teacher may create questions for come from the canonical
      // TeacherTopicAssignment endpoint. The autocomplete listing ("topics")
      // is filtered server-side to the same set, so intersect to be safe.
      const assignedTopicIds = new Set(assignedRes.data.map((a) => a.topic));
      const allowedTopics = topicsRes.data.filter((t) =>
        assignedTopicIds.has(t.id)
      );
      setTopics(allowedTopics);
      setTeachingTopics(assignedRes.data);
      setDomains(domainsRes.data);

      if (allowedTopics.length > 0) {
        setForm((f) => ({ ...f, topic: allowedTopics[0].id }));
      }
    } catch {
      setError("Failed to load form data.");
    } finally {
      setLoading(false);
    }
  };

  const buildSearchParams = useCallback(() => {
    const params = new URLSearchParams();
    if (activeTab !== "all") params.set("status", activeTab);
    if (filters.status) params.set("status", filters.status);
    if (filters.domain) params.set("domain", filters.domain);
    if (filters.difficulty) params.set("difficulty", filters.difficulty);
    if (filters.keyword) params.set("keyword", filters.keyword);
    params.set("page", page);
    params.set("page_size", 10);
    return params.toString();
  }, [filters, page, activeTab]);

  const searchQuestions = useCallback(async () => {
    try {
      const res = await api.get(`/exit-exams/questions/search/?${buildSearchParams()}`);
      setQuestions(res.data.results || []);
      setTotalPages(res.data.total_pages || 1);
      setTotalCount(res.data.count || 0);
    } catch {
      /* silent */
    }
  }, [buildSearchParams]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
    setPage(1);
  };

  // ── Duplicate check then submit ──────────────────────────────────────────
  const checkAndSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    // Find course_id from selected topic
    const selectedTopic = topics.find((t) => t.id === Number(form.topic));
    const courseId = selectedTopic?.domain_course_id || null;

    setCheckingDupes(true);
    try {
      const res = await api.post("/exit-exams/questions/check-duplicate/", {
        text: form.text,
        course_id: courseId,
        exclude_question_id: editingId || null,
        threshold: 0.85,
      });

      if (res.data.has_duplicates) {
        setDuplicateModal({
          duplicates: res.data.duplicates,
          pendingSubmit: true,
        });
        setCheckingDupes(false);
        return;
      }
    } catch {
      /* ignore duplicate-check errors — proceed anyway */
    }

    setCheckingDupes(false);
    await saveQuestion();
  };

  // ── Save (create/update) ─────────────────────────────────────────────────
  const saveQuestion = async () => {
    try {
      let questionId = editingId;

      const questionPayload = {
        topic: Number(form.topic),
        text: form.text,
        bloom_level: form.bloom_level,
        difficulty: form.difficulty,
        explanation: form.explanation,
      };

      if (editingId) {
        await api.patch(`/exit-exams/questions/${editingId}/`, questionPayload);
        // Replace choices
        const qRes = await api.get(`/exit-exams/questions/${editingId}/`);
        const existingChoices = qRes.data.choices || [];
        await Promise.all(existingChoices.map((c) => api.delete(`/exit-exams/choices/${c.id}/`)));
      } else {
        const qRes = await api.post("/exit-exams/questions/", questionPayload);
        questionId = qRes.data.id;
      }

      // Save choices
      const choiceKeys = { A: "choice_a", B: "choice_b", C: "choice_c", D: "choice_d" };
      await Promise.all(
        CORRECT_OPTIONS.map((letter) =>
          api.post("/exit-exams/choices/", {
            question: questionId,
            text: form[choiceKeys[letter]],
            is_correct: form.correct_answer === letter,
          })
        )
      );

      setSuccess(editingId ? "Question updated successfully." : "Draft question saved.");
      resetForm();
      await searchQuestions();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save question.");
    }
  };

  const resetForm = () => {
    setForm({ ...EMPTY_FORM, topic: topics[0]?.id || "" });
    setEditingId(null);
  };

  // ── Submit for Approval ──────────────────────────────────────────────────
  const submitForApproval = async (questionId) => {
    setError("");
    setSuccess("");
    try {
      await api.post(`/exit-exams/questions/${questionId}/submit/`);
      setSuccess("Question submitted for approval.");
      await searchQuestions();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit question.");
    }
  };

  // ── Edit ─────────────────────────────────────────────────────────────────
  const startEdit = (question) => {
    const choices = question.choices || [];
    const getChoice = (index) => choices[index]?.text || "";
    const correctIndex = choices.findIndex((c) => c.is_correct);
    const correctLetter = correctIndex >= 0 ? CORRECT_OPTIONS[correctIndex] : "A";

    setForm({
      topic: question.topic,
      text: question.text,
      bloom_level: question.bloom_level,
      difficulty: question.difficulty,
      explanation: question.explanation || "",
      choice_a: getChoice(0),
      choice_b: getChoice(1),
      choice_c: getChoice(2),
      choice_d: getChoice(3),
      correct_answer: correctLetter,
    });
    setEditingId(question.id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // ── Delete ───────────────────────────────────────────────────────────────
  const deleteQuestion = async (id) => {
    if (!window.confirm("Delete this draft question?")) return;
    try {
      await api.delete(`/exit-exams/questions/${id}/`);
      setSuccess("Question deleted.");
      await searchQuestions();
    } catch {
      setError("Failed to delete question.");
    }
  };

  const tabCounts = {
    all: totalCount,
  };

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  return (
    <div className="container-fluid py-4">
      {/* Header */}
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Teacher Portal</span>
          <h2 className="fw-bold mt-2 mb-1">Question Bank</h2>
          <p className="text-muted mb-0">
            Create, edit, and submit questions for department head approval.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger alert-dismissible" role="alert">
          {error}
          <button className="btn-close" onClick={() => setError("")} />
        </div>
      )}
      {success && (
        <div className="alert alert-success alert-dismissible" role="alert">
          {success}
          <button className="btn-close" onClick={() => setSuccess("")} />
        </div>
      )}

      {/* Duplicate Warning Modal */}
      {duplicateModal && (
        <DuplicateWarningModal
          duplicates={duplicateModal.duplicates}
          onContinue={async () => {
            setDuplicateModal(null);
            await saveQuestion();
          }}
          onCancel={() => setDuplicateModal(null)}
        />
      )}

      <div className="row g-4">
        {/* ── Form ── */}
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">
                {editingId ? "✏️ Edit Question" : "➕ New Question"}
              </h5>

              <form onSubmit={checkAndSubmit}>
                {/* Topic */}
                <div className="mb-3">
                  <label className="form-label fw-semibold">Topic</label>
                  <select
                    name="topic"
                    className="form-select"
                    value={form.topic}
                    onChange={handleChange}
                    required
                  >
                    {topics.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Question Text */}
                <div className="mb-3">
                  <label className="form-label fw-semibold">Question Text</label>
                  <textarea
                    name="text"
                    className="form-control"
                    rows="4"
                    value={form.text}
                    onChange={handleChange}
                    placeholder="Enter the question text…"
                    required
                  />
                </div>

                {/* Bloom + Difficulty */}
                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label fw-semibold">Bloom Level</label>
                    <select
                      name="bloom_level"
                      className="form-select"
                      value={form.bloom_level}
                      onChange={handleChange}
                    >
                      {BLOOM_LEVELS.map((l) => (
                        <option key={l} value={l} className="text-capitalize">
                          {l.charAt(0).toUpperCase() + l.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-md-6 mb-3">
                    <label className="form-label fw-semibold">Difficulty</label>
                    <select
                      name="difficulty"
                      className="form-select"
                      value={form.difficulty}
                      onChange={handleChange}
                    >
                      {DIFFICULTIES.map((d) => (
                        <option key={d} value={d} className="text-capitalize">
                          {d.charAt(0).toUpperCase() + d.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Choices */}
                {CORRECT_OPTIONS.map((letter) => {
                  const fieldName = `choice_${letter.toLowerCase()}`;
                  return (
                    <div className="mb-3" key={letter}>
                      <label className="form-label fw-semibold">Choice {letter}</label>
                      <input
                        name={fieldName}
                        className="form-control"
                        value={form[fieldName]}
                        onChange={handleChange}
                        placeholder={`Option ${letter}…`}
                        required
                      />
                    </div>
                  );
                })}

                {/* Correct Answer */}
                <div className="mb-3">
                  <label className="form-label fw-semibold">Correct Answer</label>
                  <select
                    name="correct_answer"
                    className="form-select"
                    value={form.correct_answer}
                    onChange={handleChange}
                  >
                    {CORRECT_OPTIONS.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Explanation */}
                <div className="mb-4">
                  <label className="form-label fw-semibold">
                    Explanation <span className="text-muted fw-normal">(optional)</span>
                  </label>
                  <textarea
                    name="explanation"
                    className="form-control"
                    rows="3"
                    value={form.explanation}
                    onChange={handleChange}
                    placeholder="Explain why this answer is correct…"
                  />
                </div>

                <div className="d-flex gap-2">
                  <button
                    type="submit"
                    className="btn btn-primary flex-grow-1"
                    disabled={checkingDupes}
                  >
                    {checkingDupes
                      ? "Checking for duplicates…"
                      : editingId
                      ? "Update Question"
                      : "Save as Draft"}
                  </button>
                  {editingId && (
                    <button
                      type="button"
                      className="btn btn-outline-secondary"
                      onClick={resetForm}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* ── Question List ── */}
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              {/* Tabs */}
              <ul className="nav nav-tabs mb-3">
                {["all", "draft", "submitted", "approved", "rejected"].map((tab) => (
                  <li className="nav-item" key={tab}>
                    <button
                      className={`nav-link text-capitalize${activeTab === tab ? " active fw-semibold" : ""}`}
                      onClick={() => {
                        setActiveTab(tab);
                        setPage(1);
                      }}
                    >
                      {tab === "submitted" ? "Pending" : tab}
                    </button>
                  </li>
                ))}
              </ul>

              {/* Filters */}
              <div className="row g-2 mb-3">
                <div className="col-md-4">
                  <input
                    name="keyword"
                    className="form-control form-control-sm"
                    placeholder="Search keyword…"
                    value={filters.keyword}
                    onChange={handleFilterChange}
                  />
                </div>
                <div className="col-md-4">
                  <select
                    name="domain"
                    className="form-select form-select-sm"
                    value={filters.domain}
                    onChange={handleFilterChange}
                  >
                    <option value="">All Domains</option>
                    {domains.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-4">
                  <select
                    name="difficulty"
                    className="form-select form-select-sm"
                    value={filters.difficulty}
                    onChange={handleFilterChange}
                  >
                    <option value="">All Difficulties</option>
                    {DIFFICULTIES.map((d) => (
                      <option key={d} value={d} className="text-capitalize">
                        {d.charAt(0).toUpperCase() + d.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <p className="text-muted small mb-3">{totalCount} question(s) found</p>

              {/* List */}
              {questions.length === 0 ? (
                <p className="text-muted text-center py-4">No questions found.</p>
              ) : (
                <div className="d-grid gap-3">
                  {questions.map((q) => {
                    const s = STATUS_LABELS[q.status] || { label: q.status, cls: "secondary" };
                    const canEdit =
                      q.status === "draft" || q.status === "rejected";
                    const canSubmit =
                      q.status === "draft" || q.status === "rejected";
                    const canDelete = q.status === "draft";

                    return (
                      <div key={q.id} className="question-bank-card">
                        <div className="d-flex justify-content-between gap-3">
                          <div className="flex-grow-1" style={{ minWidth: 0 }}>
                            <div className="d-flex gap-2 flex-wrap mb-2">
                              <span className={`badge bg-${s.cls}`}>{s.label}</span>
                              <span className="badge bg-light text-dark border">
                                {q.difficulty}
                              </span>
                              <span className="badge bg-light text-dark border">
                                {q.bloom_level}
                              </span>
                            </div>
                            <p className="fw-semibold mb-1 small">{q.text}</p>
                            <p className="text-muted small mb-0">
                              Topic: {q.topic_name || q.topic}
                            </p>
                            {q.status === "rejected" && q.rejection_reason && (
                              <div className="alert alert-danger py-1 px-2 mt-2 mb-0 small">
                                <strong>Reason:</strong> {q.rejection_reason}
                              </div>
                            )}
                          </div>

                          <div className="d-flex flex-column gap-1 flex-shrink-0">
                            {canSubmit && (
                              <button
                                className="btn btn-sm btn-success"
                                onClick={() => submitForApproval(q.id)}
                              >
                                Submit
                              </button>
                            )}
                            {canEdit && (
                              <button
                                className="btn btn-sm btn-outline-primary"
                                onClick={() => startEdit(q)}
                              >
                                Edit
                              </button>
                            )}
                            {canDelete && (
                              <button
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => deleteQuestion(q.id)}
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="d-flex justify-content-center gap-2 mt-4">
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    ← Prev
                  </button>
                  <span className="btn btn-sm btn-light disabled">
                    {page} / {totalPages}
                  </span>
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    disabled={page === totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next →
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Duplicate Warning Modal ────────────────────────────────────────────────
const DuplicateWarningModal = ({ duplicates, onContinue, onCancel }) => (
  <div
    className="modal show d-block"
    style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
    tabIndex="-1"
  >
    <div className="modal-dialog modal-lg modal-dialog-centered">
      <div className="modal-content border-0 shadow rounded-4">
        <div className="modal-header border-0 pb-0">
          <h5 className="modal-title fw-bold">
            ⚠️ Possible Duplicate Questions Found
          </h5>
          <button className="btn-close" onClick={onCancel} />
        </div>
        <div className="modal-body pt-2">
          <p className="text-muted">
            The following existing questions are similar to yours (≥85% match).
            You can continue saving or cancel to revise.
          </p>
          <div className="d-grid gap-3">
            {duplicates.map((d) => (
              <div key={d.question_id} className="alert alert-warning mb-0 rounded-3">
                <div className="d-flex justify-content-between align-items-start">
                  <div>
                    <p className="fw-semibold mb-1 small">{d.text}</p>
                    <span className="badge bg-light text-dark border me-2">
                      {d.topic_name}
                    </span>
                    <span className="badge bg-light text-dark border">
                      {d.status}
                    </span>
                  </div>
                  <span className="badge bg-danger ms-2 flex-shrink-0">
                    {d.similarity}% match
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="modal-footer border-0 pt-0">
          <button className="btn btn-outline-secondary" onClick={onCancel}>
            Cancel — I'll revise
          </button>
          <button className="btn btn-warning" onClick={onContinue}>
            Save Anyway
          </button>
        </div>
      </div>
    </div>
  </div>
);

export default TeacherQuestionBank;
