import { useEffect, useMemo, useState } from "react";
import api from "../api/api";

const getRelationId = (value) => {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "object") return value.id ?? "";
  return value;
};

const AdminPdfImports = () => {
  const [imports, setImports] = useState([]);
  const [extractedQuestions, setExtractedQuestions] = useState([]);
  const [courses, setCourses] = useState([]);
  const [domains, setDomains] = useState([]);
  const [topics, setTopics] = useState([]);

  const [selectedIds, setSelectedIds] = useState([]);
  const [skippedReasons, setSkippedReasons] = useState([]);

  const [statusFilter, setStatusFilter] = useState("draft");
  const [searchTerm, setSearchTerm] = useState("");

  const [form, setForm] = useState({
    course: "",
    title: "",
    source_type: "mock_exam",
    year: new Date().getFullYear(),
    file: null,
  });

  const [editing, setEditing] = useState({});

  const [bulkForm, setBulkForm] = useState({
    domain: "",
    topic: "",
    difficulty: "medium",
    bloom_level: "knowledge",
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState(null);
  const [classifyingId, setClassifyingId] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [importsRes, extractedRes, coursesRes, domainsRes, topicsRes] =
        await Promise.all([
          api.get("/exit-exams/exam-pdf-imports/"),
          api.get("/exit-exams/extracted-questions/"),
          api.get("/exit-exams/courses/"),
          api.get("/exit-exams/domains/"),
          api.get("/exit-exams/topics/"),
        ]);

      setImports(importsRes.data);
      setExtractedQuestions(extractedRes.data);
      setCourses(coursesRes.data);
      setDomains(domainsRes.data);
      setTopics(topicsRes.data);

      setBulkForm((prev) => ({
        ...prev,
        domain: domainsRes.data[0]?.id || "",
        topic: topicsRes.data[0]?.id || "",
      }));

      const editState = {};

      extractedRes.data.forEach((item) => {
        editState[item.id] = {
          question_text: item.question_text || "",
          option_a: item.option_a || "",
          option_b: item.option_b || "",
          option_c: item.option_c || "",
          option_d: item.option_d || "",
          domain: getRelationId(item.domain),
          topic: getRelationId(item.topic),
          correct_answer: item.correct_answer || "A",
          difficulty: item.difficulty || "medium",
          bloom_level: item.bloom_level || "knowledge",
          explanation: item.explanation || "",
        };
      });

      setEditing(editState);
    } catch (err) {
      setError("Failed to load PDF import data.");
    }
  };

  const counts = useMemo(() => {
    return {
      all: extractedQuestions.length,
      draft: extractedQuestions.filter((q) => q.status === "draft").length,
      approved: extractedQuestions.filter((q) => q.status === "approved").length,
      rejected: extractedQuestions.filter((q) => q.status === "rejected").length,
    };
  }, [extractedQuestions]);

  const filteredQuestions = useMemo(() => {
    let items = [...extractedQuestions];

    if (statusFilter !== "all") {
      items = items.filter((item) => item.status === statusFilter);
    }

    if (searchTerm.trim()) {
      const search = searchTerm.toLowerCase();

      items = items.filter((item) => {
        const combinedText = `
          ${item.question_number}
          ${item.question_text}
          ${item.option_a}
          ${item.option_b}
          ${item.option_c}
          ${item.option_d}
        `.toLowerCase();

        return combinedText.includes(search);
      });
    }

    return items;
  }, [extractedQuestions, statusFilter, searchTerm]);

  const draftQuestions = extractedQuestions.filter(
    (item) => item.status === "draft"
  );

  const handleUploadChange = (e) => {
    const { name, value, files } = e.target;

    setForm({
      ...form,
      [name]: files ? files[0] : value,
    });
  };

  const uploadPdf = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSkippedReasons([]);

    if (!form.file) {
      setError("Please choose a PDF file.");
      return;
    }

    setUploading(true);

    try {
      const data = new FormData();

      data.append("course", form.course);
      data.append("title", form.title);
      data.append("source_type", form.source_type);
      data.append("year", form.year);
      data.append("file", form.file);

      await api.post("/exit-exams/exam-pdf-imports/", data, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setSuccess("PDF uploaded successfully.");

      setForm({
        ...form,
        title: "",
        file: null,
      });

      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "PDF upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const processImport = async (importId) => {
    setError("");
    setSuccess("");
    setSkippedReasons([]);
    setProcessingId(importId);

    try {
      const response = await api.post(
        `/exit-exams/exam-pdf-imports/${importId}/process/`
      );

      setSuccess(
        `PDF processed successfully. Detected ${response.data.detected_questions} questions.`
      );

      setStatusFilter("draft");
      await fetchData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.error ||
          "PDF processing failed."
      );
    } finally {
      setProcessingId(null);
    }
  };

  const autoClassifyImport = async (importId) => {
    setError("");
    setSuccess("");
    setSkippedReasons([]);
    setClassifyingId(importId);

    try {
      const response = await api.post(
        "/exit-exams/extracted-questions/auto-classify/",
        { import_id: importId }
      );

      setSuccess(
        `Auto-classification completed. Updated: ${response.data.updated}, ` +
          `Needs manual review: ${response.data.not_matched}.`
      );

      setStatusFilter("draft");
      await fetchData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.error ||
          "Auto-classification failed."
      );
    } finally {
      setClassifyingId(null);
    }
  };

  const updateEditField = (id, field, value) => {
    setEditing({
      ...editing,
      [id]: {
        ...editing[id],
        [field]: value,
      },
    });
  };

  const saveExtractedQuestion = async (id) => {
    setError("");
    setSuccess("");
    setSkippedReasons([]);

    try {
      const payload = editing[id];

      await api.patch(`/exit-exams/extracted-questions/${id}/`, {
        question_text: payload.question_text,
        option_a: payload.option_a,
        option_b: payload.option_b,
        option_c: payload.option_c,
        option_d: payload.option_d,
        domain: payload.domain ? Number(payload.domain) : null,
        topic: payload.topic ? Number(payload.topic) : null,
        correct_answer: payload.correct_answer,
        difficulty: payload.difficulty,
        bloom_level: payload.bloom_level,
        explanation: payload.explanation,
      });

      setSuccess("Extracted question updated successfully.");
      await fetchData();
    } catch (err) {
      setError("Failed to update extracted question.");
    }
  };

  const approveQuestion = async (id) => {
    setError("");
    setSuccess("");
    setSkippedReasons([]);

    try {
      await saveExtractedQuestion(id);
      await api.post(`/exit-exams/extracted-questions/${id}/approve/`);

      setSuccess("Question approved and added to question bank.");
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Approval failed.");
    }
  };

  const rejectQuestion = async (id) => {
    const confirmed = window.confirm("Reject this extracted question?");
    if (!confirmed) return;

    setError("");
    setSuccess("");
    setSkippedReasons([]);

    try {
      await api.post(`/exit-exams/extracted-questions/${id}/reject/`);
      setSuccess("Question rejected.");
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Reject failed.");
    }
  };

  const toggleSelectQuestion = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const selectAllVisibleDrafts = () => {
    const ids = filteredQuestions
      .filter((item) => item.status === "draft")
      .map((item) => item.id);

    setSelectedIds(ids);
  };

  const selectAllDrafts = () => {
    const ids = draftQuestions.map((item) => item.id);
    setSelectedIds(ids);
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  const bulkUpdateSelected = async () => {
    setError("");
    setSuccess("");
    setSkippedReasons([]);

    if (selectedIds.length === 0) {
      setError("Please select at least one draft question.");
      return;
    }

    try {
      for (const id of selectedIds) {
        await api.patch(`/exit-exams/extracted-questions/${id}/`, {
          domain: Number(bulkForm.domain),
          topic: Number(bulkForm.topic),
          difficulty: bulkForm.difficulty,
          bloom_level: bulkForm.bloom_level,
        });
      }

      setSuccess(`Updated ${selectedIds.length} selected questions.`);
      await fetchData();
    } catch (err) {
      setError("Bulk update failed.");
    }
  };

  const bulkApproveSelected = async () => {
    setError("");
    setSuccess("");
    setSkippedReasons([]);

    if (selectedIds.length === 0) {
      setError("Please select at least one draft question.");
      return;
    }

    const confirmed = window.confirm(
      `Approve ${selectedIds.length} selected questions?`
    );

    if (!confirmed) return;

    try {
      const response = await api.post(
        "/exit-exams/extracted-questions/bulk-approve/",
        {
          ids: selectedIds,
        }
      );

      setSuccess(
        `Bulk approval completed. Approved: ${response.data.approved_count}, Skipped: ${response.data.skipped_count}`
      );

      setSkippedReasons(response.data.skipped || []);
      setSelectedIds([]);
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Bulk approval failed.");
    }
  };

  const statusBadge = (status) => {
    if (status === "approved") return "bg-success";
    if (status === "rejected") return "bg-danger";
    if (status === "needs_review") return "bg-warning text-dark";
    if (status === "failed") return "bg-danger";
    return "bg-secondary";
  };

  const getSkippedReasonText = (reason) => {
    const labels = {
      missing_topic: "Missing topic",
      missing_or_invalid_correct_answer: "Missing or invalid correct answer",
      missing_options: "Missing options",
      missing_question_text: "Missing question text",
    };

    return labels[reason] || reason;
  };

  return (
    <div className="container-fluid py-4">
      <h2 className="fw-bold mb-2">PDF Import & Question Review</h2>
      <p className="text-muted">
        Upload mock/Exit Exam PDFs, extract MCQs, review them, and approve valid
        questions into the official question bank.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {skippedReasons.length > 0 && (
        <div className="alert alert-warning">
          <h6 className="fw-bold">Skipped Questions</h6>
          <p className="mb-2">
            These questions were not approved because they are incomplete.
          </p>

          <div className="d-grid gap-2">
            {skippedReasons.map((item) => (
              <div key={item.id}>
                <strong>Q{item.question_number}</strong>:{" "}
                {item.reasons?.map(getSkippedReasonText).join(", ")}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="row g-4">
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Upload Exam PDF</h5>

              <form onSubmit={uploadPdf}>
                <div className="mb-3">
                  <label className="form-label">Course</label>
                  <select
                    name="course"
                    className="form-select"
                    value={form.course}
                    onChange={handleUploadChange}
                    required
                  >
                    <option value="">Select exit-exam program</option>
                    {courses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">PDF Title</label>
                  <input
                    name="title"
                    className="form-control"
                    value={form.title}
                    onChange={handleUploadChange}
                    placeholder="Computer Science Exit Exam 2018"
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Source Type</label>
                  <select
                    name="source_type"
                    className="form-select"
                    value={form.source_type}
                    onChange={handleUploadChange}
                  >
                    <option value="mock_exam">Mock Exam</option>
                    <option value="past_exam">Past Exam</option>
                    <option value="practice">Practice</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Year</label>
                  <input
                    type="number"
                    name="year"
                    className="form-control"
                    value={form.year}
                    onChange={handleUploadChange}
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">PDF File</label>
                  <input
                    type="file"
                    name="file"
                    className="form-control"
                    accept=".pdf"
                    onChange={handleUploadChange}
                    required
                  />
                </div>

                <button className="btn btn-primary w-100" disabled={uploading}>
                  {uploading ? "Uploading..." : "Upload PDF"}
                </button>
              </form>
            </div>
          </div>

          <div className="card border-0 shadow-sm rounded-4 mt-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Uploaded PDFs</h5>

              {imports.length === 0 ? (
                <p className="text-muted">No PDF imports yet.</p>
              ) : (
                <div className="d-grid gap-3">
                  {imports.map((item) => (
                    <div key={item.id} className="admin-list-item">
                      <div>
                        <strong>{item.title}</strong>
                        <p className="small text-muted mb-1">
                          {item.source_type} • {item.year || "No year"}
                        </p>
                        <span className={`badge ${statusBadge(item.status)}`}>
                          {item.status}
                        </span>
                      </div>

                      <div className="d-flex gap-2 flex-wrap">
                        <button
                          className="btn btn-sm btn-outline-primary"
                          onClick={() => processImport(item.id)}
                          disabled={
                            processingId === item.id ||
                            item.status === "approved"
                          }
                          title={
                            item.status === "approved"
                              ? "Approved imports cannot be processed again."
                              : ""
                          }
                        >
                          {processingId === item.id
                            ? "Processing..."
                            : "Process"}
                        </button>

                        <button
                          className="btn btn-sm btn-outline-success"
                          onClick={() => autoClassifyImport(item.id)}
                          disabled={
                            classifyingId === item.id ||
                            item.status !== "needs_review"
                          }
                        >
                          {classifyingId === item.id
                            ? "Classifying..."
                            : "Auto Classify"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap mb-3">
                <div>
                  <h5 className="fw-bold mb-1">Extracted Questions</h5>
                  <p className="text-muted small mb-0">
                    Search, filter, edit, and approve extracted questions.
                  </p>
                </div>

                <span className="badge bg-primary">
                  {selectedIds.length} selected
                </span>
              </div>

              <div className="row g-2 mb-3">
                <div className="col-md-6">
                  <input
                    className="form-control"
                    placeholder="Search question number, text, or options..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                <div className="col-md-6">
                  <select
                    className="form-select"
                    value={statusFilter}
                    onChange={(e) => {
                      setStatusFilter(e.target.value);
                      setSelectedIds([]);
                    }}
                  >
                    <option value="draft">Draft ({counts.draft})</option>
                    <option value="approved">Approved ({counts.approved})</option>
                    <option value="rejected">Rejected ({counts.rejected})</option>
                    <option value="all">All ({counts.all})</option>
                  </select>
                </div>
              </div>

              <div className="status-counts mb-4">
                <span className="badge bg-secondary">All: {counts.all}</span>
                <span className="badge bg-warning text-dark">
                  Draft: {counts.draft}
                </span>
                <span className="badge bg-success">
                  Approved: {counts.approved}
                </span>
                <span className="badge bg-danger">
                  Rejected: {counts.rejected}
                </span>
              </div>

              <div className="bulk-review-box mb-4">
                <h6 className="fw-bold mb-2">Bulk Review Actions</h6>

                <div className="row">
                  <div className="col-md-6 mb-2">
                    <label className="form-label small">Domain</label>
                    <select
                      className="form-select form-select-sm"
                      value={bulkForm.domain}
                      onChange={(e) =>
                        setBulkForm({
                          ...bulkForm,
                          domain: e.target.value,
                        })
                      }
                    >
                      {domains.map((domain) => (
                        <option key={domain.id} value={domain.id}>
                          {domain.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-md-6 mb-2">
                    <label className="form-label small">Topic</label>
                    <select
                      className="form-select form-select-sm"
                      value={bulkForm.topic}
                      onChange={(e) =>
                        setBulkForm({
                          ...bulkForm,
                          topic: e.target.value,
                        })
                      }
                    >
                      {topics.map((topic) => (
                        <option key={topic.id} value={topic.id}>
                          {topic.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="col-md-6 mb-2">
                    <label className="form-label small">Difficulty</label>
                    <select
                      className="form-select form-select-sm"
                      value={bulkForm.difficulty}
                      onChange={(e) =>
                        setBulkForm({
                          ...bulkForm,
                          difficulty: e.target.value,
                        })
                      }
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>

                  <div className="col-md-6 mb-2">
                    <label className="form-label small">Bloom Level</label>
                    <select
                      className="form-select form-select-sm"
                      value={bulkForm.bloom_level}
                      onChange={(e) =>
                        setBulkForm({
                          ...bulkForm,
                          bloom_level: e.target.value,
                        })
                      }
                    >
                      <option value="knowledge">Knowledge</option>
                      <option value="comprehension">Comprehension</option>
                      <option value="application">Application</option>
                      <option value="analysis">Analysis</option>
                    </select>
                  </div>
                </div>

                <div className="d-flex gap-2 flex-wrap mt-3">
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={selectAllVisibleDrafts}
                  >
                    Select Visible Drafts
                  </button>

                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={selectAllDrafts}
                  >
                    Select All Drafts
                  </button>

                  <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={clearSelection}
                  >
                    Clear
                  </button>

                  <button
                    className="btn btn-sm btn-primary"
                    onClick={bulkUpdateSelected}
                  >
                    Apply Domain/Topic
                  </button>

                  <button
                    className="btn btn-sm btn-success"
                    onClick={bulkApproveSelected}
                  >
                    Bulk Approve Selected
                  </button>
                </div>
              </div>

              {filteredQuestions.length === 0 ? (
                <p className="text-muted">
                  No extracted questions match this filter.
                </p>
              ) : (
                <div className="d-grid gap-4">
                  {filteredQuestions.map((item) => (
                    <div key={item.id} className="extracted-question-card">
                      <div className="d-flex justify-content-between mb-2">
                        <div className="d-flex align-items-center gap-2">
                          {item.status === "draft" && (
                            <input
                              type="checkbox"
                              className="form-check-input"
                              checked={selectedIds.includes(item.id)}
                              onChange={() => toggleSelectQuestion(item.id)}
                            />
                          )}

                          <span className="badge bg-secondary">
                            Q{item.question_number}
                          </span>
                        </div>

                        <span className={`badge ${statusBadge(item.status)}`}>
                          {item.status}
                        </span>
                      </div>

                      {item.status === "draft" ? (
                        <>
                          <div className="mb-2">
                            <label className="form-label small">
                              Question Text
                            </label>
                            <textarea
                              className="form-control form-control-sm"
                              rows="3"
                              value={editing[item.id]?.question_text || ""}
                              onChange={(e) =>
                                updateEditField(
                                  item.id,
                                  "question_text",
                                  e.target.value
                                )
                              }
                            />
                          </div>

                          <div className="row">
                            <div className="col-md-6 mb-2">
                              <label className="form-label small">Option A</label>
                              <input
                                className="form-control form-control-sm"
                                value={editing[item.id]?.option_a || ""}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "option_a",
                                    e.target.value
                                  )
                                }
                              />
                            </div>

                            <div className="col-md-6 mb-2">
                              <label className="form-label small">Option B</label>
                              <input
                                className="form-control form-control-sm"
                                value={editing[item.id]?.option_b || ""}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "option_b",
                                    e.target.value
                                  )
                                }
                              />
                            </div>

                            <div className="col-md-6 mb-2">
                              <label className="form-label small">Option C</label>
                              <input
                                className="form-control form-control-sm"
                                value={editing[item.id]?.option_c || ""}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "option_c",
                                    e.target.value
                                  )
                                }
                              />
                            </div>

                            <div className="col-md-6 mb-2">
                              <label className="form-label small">Option D</label>
                              <input
                                className="form-control form-control-sm"
                                value={editing[item.id]?.option_d || ""}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "option_d",
                                    e.target.value
                                  )
                                }
                              />
                            </div>
                          </div>

                          <div className="row mt-2">
                            <div className="col-md-6 mb-2">
                              <label className="form-label small">Domain</label>
                              <select
                                className="form-select form-select-sm"
                                value={editing[item.id]?.domain || ""}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "domain",
                                    e.target.value
                                  )
                                }
                              >
                                <option value="">Select domain</option>
                                {domains.map((domain) => (
                                  <option key={domain.id} value={domain.id}>
                                    {domain.name}
                                  </option>
                                ))}
                              </select>
                            </div>

                            <div className="col-md-6 mb-2">
                              <label className="form-label small">Topic</label>
                              <select
                                className="form-select form-select-sm"
                                value={editing[item.id]?.topic || ""}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "topic",
                                    e.target.value
                                  )
                                }
                              >
                                <option value="">Select topic</option>
                                {topics.map((topic) => (
                                  <option key={topic.id} value={topic.id}>
                                    {topic.name}
                                  </option>
                                ))}
                              </select>
                            </div>

                            <div className="col-md-4 mb-2">
                              <label className="form-label small">Correct</label>
                              <select
                                className="form-select form-select-sm"
                                value={editing[item.id]?.correct_answer || "A"}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "correct_answer",
                                    e.target.value
                                  )
                                }
                              >
                                <option value="A">A</option>
                                <option value="B">B</option>
                                <option value="C">C</option>
                                <option value="D">D</option>
                              </select>
                            </div>

                            <div className="col-md-4 mb-2">
                              <label className="form-label small">
                                Difficulty
                              </label>
                              <select
                                className="form-select form-select-sm"
                                value={editing[item.id]?.difficulty || "medium"}
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "difficulty",
                                    e.target.value
                                  )
                                }
                              >
                                <option value="easy">Easy</option>
                                <option value="medium">Medium</option>
                                <option value="hard">Hard</option>
                              </select>
                            </div>

                            <div className="col-md-4 mb-2">
                              <label className="form-label small">Bloom</label>
                              <select
                                className="form-select form-select-sm"
                                value={
                                  editing[item.id]?.bloom_level || "knowledge"
                                }
                                onChange={(e) =>
                                  updateEditField(
                                    item.id,
                                    "bloom_level",
                                    e.target.value
                                  )
                                }
                              >
                                <option value="knowledge">Knowledge</option>
                                <option value="comprehension">
                                  Comprehension
                                </option>
                                <option value="application">Application</option>
                                <option value="analysis">Analysis</option>
                              </select>
                            </div>
                          </div>

                          <div className="mb-2">
                            <label className="form-label small">Explanation</label>
                            <textarea
                              className="form-control form-control-sm"
                              rows="2"
                              value={editing[item.id]?.explanation || ""}
                              onChange={(e) =>
                                updateEditField(
                                  item.id,
                                  "explanation",
                                  e.target.value
                                )
                              }
                            />
                          </div>

                          <div className="d-flex gap-2 mt-3">
                            <button
                              className="btn btn-sm btn-outline-primary"
                              onClick={() => saveExtractedQuestion(item.id)}
                            >
                              Save
                            </button>

                            <button
                              className="btn btn-sm btn-success"
                              onClick={() => approveQuestion(item.id)}
                            >
                              Approve
                            </button>

                            <button
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => rejectQuestion(item.id)}
                            >
                              Reject
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          <h6 className="fw-bold">{item.question_text}</h6>

                          <ol type="A" className="small text-muted">
                            <li>{item.option_a}</li>
                            <li>{item.option_b}</li>
                            <li>{item.option_c}</li>
                            <li>{item.option_d}</li>
                          </ol>

                          <p className="small mb-0">
                            <strong>Correct:</strong>{" "}
                            {item.correct_answer || "Not set"}
                          </p>
                        </>
                      )}
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

export default AdminPdfImports;