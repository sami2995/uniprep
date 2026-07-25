import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/api";

const STATUS_COLORS = {
  draft: "secondary",
  submitted: "warning",
  approved: "success",
  rejected: "danger",
};

const TeacherDashboard = () => {
  const [stats, setStats] = useState(null);
  const [recentQuestions, setRecentQuestions] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [questionsRes, coursesRes] = await Promise.all([
        api.get("/exit-exams/questions/search/?page_size=5"),
        api.get("/exit-exams/my-assigned-courses/"),
      ]);

      const questions = questionsRes.data.results || [];
      const allCount = questionsRes.data.count || 0;

      // Count by status from search endpoint
      const [draftRes, pendingRes, approvedRes, rejectedRes] = await Promise.all([
        api.get("/exit-exams/questions/search/?status=draft&page_size=1"),
        api.get("/exit-exams/questions/search/?status=submitted&page_size=1"),
        api.get("/exit-exams/questions/search/?status=approved&page_size=1"),
        api.get("/exit-exams/questions/search/?status=rejected&page_size=1"),
      ]);

      setStats({
        total: allCount,
        draft: draftRes.data.count || 0,
        pending: pendingRes.data.count || 0,
        approved: approvedRes.data.count || 0,
        rejected: rejectedRes.data.count || 0,
        courses: coursesRes.data.length,
      });

      setRecentQuestions(questions);
      setCourses(coursesRes.data);
    } catch {
      setError("Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
        <p className="mt-3 text-muted">Loading dashboard…</p>
      </div>
    );
  }

  return (
    <div className="container-fluid py-4">
      {/* Hero */}
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Teacher Portal</span>
          <h2 className="fw-bold mt-2 mb-1">Teacher Dashboard</h2>
          <p className="text-muted mb-0">
            Manage your questions, track approvals, and monitor your courses.
          </p>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <Link className="btn btn-primary" to="/teacher/questions">
            + New Question
          </Link>
          <Link className="btn btn-outline-primary" to="/teacher/courses">
            My Courses
          </Link>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {/* Stat Cards */}
      {stats && (
        <div className="row g-3 mb-4">
          <StatCard
            title="Total Questions"
            value={stats.total}
            icon="📝"
            color="primary"
            subtitle="All my questions"
          />
          <StatCard
            title="Pending Approval"
            value={stats.pending}
            icon="⏳"
            color="warning"
            subtitle="Awaiting dept head review"
            urgent={stats.pending > 0}
          />
          <StatCard
            title="Approved"
            value={stats.approved}
            icon="✅"
            color="success"
            subtitle="Live in question bank"
          />
          <StatCard
            title="Rejected"
            value={stats.rejected}
            icon="❌"
            color="danger"
            subtitle="Need revision"
            urgent={stats.rejected > 0}
          />
        </div>
      )}

      <div className="row g-4">
        {/* Recent Questions */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="fw-bold mb-0">Recent Questions</h5>
                <Link className="btn btn-sm btn-outline-primary" to="/teacher/questions">
                  View all
                </Link>
              </div>

              {recentQuestions.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-muted mb-3">No questions yet.</p>
                  <Link className="btn btn-primary" to="/teacher/questions">
                    Create your first question
                  </Link>
                </div>
              ) : (
                <div className="d-grid gap-3">
                  {recentQuestions.map((q) => (
                    <div key={q.id} className="dashboard-list-item">
                      <div className="flex-grow-1" style={{ minWidth: 0 }}>
                        <p
                          className="fw-semibold mb-1 text-truncate"
                          style={{ maxWidth: "100%" }}
                        >
                          {q.text}
                        </p>
                        <div className="d-flex gap-2 flex-wrap">
                          <span className="badge bg-light text-dark border">
                            {q.topic_name || "No topic"}
                          </span>
                          <span className="badge bg-light text-dark border">
                            {q.difficulty}
                          </span>
                          <span className="badge bg-light text-dark border">
                            {q.bloom_level}
                          </span>
                        </div>
                      </div>
                      <span
                        className={`badge bg-${STATUS_COLORS[q.status] || "secondary"} text-capitalize flex-shrink-0`}
                      >
                        {q.status === "submitted" ? "Pending" : q.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="col-lg-4">
          {/* Quick Actions */}
          <div className="card border-0 shadow-sm rounded-4 mb-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Quick Actions</h5>
              <div className="d-grid gap-2">
                <Link className="btn btn-primary" to="/teacher/questions">
                  Create Question
                </Link>
                <Link className="btn btn-outline-warning" to="/teacher/questions?filter=rejected">
                  Fix Rejected ({stats?.rejected || 0})
                </Link>
                <Link className="btn btn-outline-secondary" to="/teacher/courses">
                  View My Courses
                </Link>
                <Link className="btn btn-outline-primary" to="/teacher/analytics">
                  View Analytics
                </Link>
              </div>
            </div>
          </div>

          {/* Assigned Courses */}
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Assigned Courses</h5>
              {courses.length === 0 ? (
                <p className="text-muted small">No courses assigned yet.</p>
              ) : (
                <div className="d-grid gap-2">
                  {courses.map((a) => (
                    <div key={a.id} className="d-flex align-items-center gap-2">
                      <span className="badge bg-primary rounded-pill">📘</span>
                      <span className="fw-semibold small">{a.course_name}</span>
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

const StatCard = ({ title, value, icon, color, subtitle, urgent }) => (
  <div className="col-md-6 col-xl-3">
    <div className={`card border-0 shadow-sm rounded-4 h-100${urgent ? " border-start border-4 border-" + color : ""}`}>
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-start mb-2">
          <span style={{ fontSize: "1.5rem" }}>{icon}</span>
          <span className={`badge bg-${color} bg-opacity-10 text-${color} rounded-pill px-3 py-2`}>
            {color === "warning" ? "⚠" : ""}
          </span>
        </div>
        <h6 className="text-muted mb-1 small">{title}</h6>
        <h2 className="fw-bold mb-0">{value}</h2>
        <p className="text-muted small mb-0 mt-1">{subtitle}</p>
      </div>
    </div>
  </div>
);

export default TeacherDashboard;
