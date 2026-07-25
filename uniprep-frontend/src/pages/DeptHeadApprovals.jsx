import { useEffect, useState } from "react";
import api from "../api/api";

const STATUS_COLORS = {
  draft: "secondary",
  submitted: "warning",
  approved: "success",
  rejected: "danger",
};

const DeptHeadApprovals = () => {
  const [questions, setQuestions] = useState([]);
  const [courses, setCourses] = useState([]);
  const [domains, setDomains] = useState([]);
  const [teachers, setTeachers] = useState([]);

  const [filters, setFilters] = useState({ course: "", domain: "", teacher_id: "" });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const [rejectModal, setRejectModal] = useState(null); // null | question
  const [rejectReason, setRejectReason] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMeta();
  }, []);

  useEffect(() => {
    fetchSubmitted();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page]);

  const loadMeta = async () => {
    try {
      const [cRes, dRes] = await Promise.all([
        api.get("/exit-exams/courses/"),
        api.get("/exit-exams/domains/"),
      ]);
      setCourses(cRes.data);
      setDomains(dRes.data);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  };

  const fetchSubmitted = async () => {
    try {
      const params = new URLSearchParams({ status: "submitted", page, page_size: 15 });
      if (filters.course) params.set("course", filters.course);
      if (filters.domain) params.set("domain", filters.domain);
      if (filters.teacher_id) params.set("teacher_id", filters.teacher_id);

      const res = await api.get(`/exit-exams/questions/search/?${params}`);
      setQuestions(res.data.results || []);
      setTotalPages(res.data.total_pages || 1);
      setTotalCount(res.data.count || 0);

      // Extract unique teachers from results for filter
      const teacherMap = {};
      (res.data.results || []).forEach((q) => {
        if (q.created_by_username) {
          teacherMap[q.created_by] = q.created_by_username;
        }
      });
      setTeachers(Object.entries(teacherMap).map(([id, name]) => ({ id, name })));
    } catch {
      setError("Failed to load questions.");
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
    setPage(1);
  };

  const approveQuestion = async (questionId) => {
    setError("");
    setSuccess("");
    try {
      await api.post(`/exit-exams/questions/${questionId}/approve/`);
      setSuccess("Question approved successfully.");
      await fetchSubmitted();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to approve question.");
    }
  };

  const openRejectModal = (question) => {
    setRejectModal(question);
    setRejectReason("");
  };

  const confirmReject = async () => {
    if (!rejectReason.trim()) {
      alert("Please provide a rejection reason.");
      return;
    }
    setError("");
    setSuccess("");
    try {
      await api.post(`/exit-exams/questions/${rejectModal.id}/reject/`, {
        rejection_reason: rejectReason,
      });
      setSuccess("Question rejected.");
      setRejectModal(null);
      await fetchSubmitted();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to reject question.");
    }
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
          <span className="dashboard-badge">Department Head</span>
          <h2 className="fw-bold mt-2 mb-1">Question Approval Queue</h2>
          <p className="text-muted mb-0">
            Review and approve or reject questions submitted by teachers.
          </p>
        </div>
        <div>
          <span className="badge bg-warning text-dark fs-6 px-3 py-2">
            {totalCount} pending
          </span>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger alert-dismissible">
          {error}
          <button className="btn-close" onClick={() => setError("")} />
        </div>
      )}
      {success && (
        <div className="alert alert-success alert-dismissible">
          {success}
          <button className="btn-close" onClick={() => setSuccess("")} />
        </div>
      )}

      {/* Filters */}
      <div className="card border-0 shadow-sm rounded-4 mb-4">
        <div className="card-body p-3">
          <div className="row g-2">
            <div className="col-md-4">
              <select
                name="course"
                className="form-select form-select-sm"
                value={filters.course}
                onChange={handleFilterChange}
              >
                <option value="">All Courses</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
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
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <div className="col-md-4">
              <select
                name="teacher_id"
                className="form-select form-select-sm"
                value={filters.teacher_id}
                onChange={handleFilterChange}
              >
                <option value="">All Teachers</option>
                {teachers.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Question List */}
      {questions.length === 0 ? (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-5 text-center">
            <div style={{ fontSize: "3rem" }}>🎉</div>
            <h5 className="fw-bold mt-3">No pending questions</h5>
            <p className="text-muted">All caught up! Questions from teachers will appear here.</p>
          </div>
        </div>
      ) : (
        <div className="d-grid gap-3">
          {questions.map((q) => (
            <div key={q.id} className="card border-0 shadow-sm rounded-4">
              <div className="card-body p-4">
                <div className="row">
                  <div className="col-lg-8">
                    {/* Badges */}
                    <div className="d-flex gap-2 flex-wrap mb-2">
                      <span className="badge bg-warning text-dark">Pending Review</span>
                      <span className="badge bg-light text-dark border">{q.difficulty}</span>
                      <span className="badge bg-light text-dark border">{q.bloom_level}</span>
                    </div>

                    <p className="fw-semibold mb-2">{q.text}</p>

                    <p className="small text-muted mb-2">
                      Topic: <strong>{q.topic_name || q.topic}</strong>
                      {q.created_by_username && (
                        <> &nbsp;·&nbsp; Teacher: <strong>{q.created_by_username}</strong></>
                      )}
                    </p>

                    {/* Choices */}
                    {q.choices && q.choices.length > 0 && (
                      <div className="mt-2">
                        {q.choices.map((c, i) => (
                          <div
                            key={c.id}
                            className={`small mb-1 ${c.is_correct ? "text-success fw-bold" : "text-muted"}`}
                          >
                            {String.fromCharCode(65 + i)}. {c.text}
                            {c.is_correct && " ✓"}
                          </div>
                        ))}
                      </div>
                    )}

                    {q.explanation && (
                      <div className="alert alert-light py-2 px-3 mt-2 mb-0 small">
                        <strong>Explanation:</strong> {q.explanation}
                      </div>
                    )}
                  </div>

                  <div className="col-lg-4 d-flex flex-column gap-2 justify-content-start align-items-lg-end mt-3 mt-lg-0">
                    <button
                      className="btn btn-success btn-sm w-100 w-lg-auto"
                      onClick={() => approveQuestion(q.id)}
                    >
                      ✅ Approve
                    </button>
                    <button
                      className="btn btn-outline-danger btn-sm w-100 w-lg-auto"
                      onClick={() => openRejectModal(q)}
                    >
                      ❌ Reject
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
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

      {/* Reject Modal */}
      {rejectModal && (
        <div className="modal show d-block" style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow rounded-4">
              <div className="modal-header border-0">
                <h5 className="modal-title fw-bold">Reject Question</h5>
                <button className="btn-close" onClick={() => setRejectModal(null)} />
              </div>
              <div className="modal-body">
                <p className="text-muted small mb-3 fst-italic">"{rejectModal.text}"</p>
                <label className="form-label fw-semibold">Reason for rejection</label>
                <textarea
                  className="form-control"
                  rows="3"
                  placeholder="Explain to the teacher what needs to be corrected…"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  required
                />
              </div>
              <div className="modal-footer border-0">
                <button className="btn btn-outline-secondary" onClick={() => setRejectModal(null)}>
                  Cancel
                </button>
                <button className="btn btn-danger" onClick={confirmReject}>
                  Reject Question
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeptHeadApprovals;
