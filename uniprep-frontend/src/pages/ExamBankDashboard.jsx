import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const PIE_COLORS = {
  approved: "#22c55e",
  pending: "#f59e0b",
  draft: "#94a3b8",
  rejected: "#ef4444",
  archived: "#6366f1",
};

const ExamBankDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/exit-exams/exam-bank-stats/")
      .then((res) => setStats(res.data))
      .catch(() => setError("Failed to load exam bank statistics."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
        <p className="mt-3 text-muted">Loading exam bank data…</p>
      </div>
    );
  }

  if (error) return <div className="container py-5 alert alert-danger">{error}</div>;
  if (!stats) return null;

  const { status_counts, status_distribution, by_domain, by_course, by_topic, recent_activity } = stats;

  const pieData = status_distribution.map((s) => ({
    name: s.status.charAt(0).toUpperCase() + s.status.slice(1),
    value: s.count,
    fill: PIE_COLORS[s.status] || "#6b7280",
  }));

  return (
    <div className="container-fluid py-4">
      {/* Hero */}
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Department Head</span>
          <h2 className="fw-bold mt-2 mb-1">Exam Bank Dashboard</h2>
          <p className="text-muted mb-0">
            Monitor question health, coverage, and teacher activity across your department.
          </p>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <Link className="btn btn-primary" to="/department-head/question-approval">
            Review Submissions
          </Link>
          <Link className="btn btn-outline-primary" to="/department-head/blueprints">
            Blueprints
          </Link>
        </div>
      </div>

      {/* Status Summary Cards */}
      <div className="row g-3 mb-4">
        {[
          { key: "total", label: "Total Questions", icon: "📚", color: "primary" },
          { key: "approved", label: "Approved", icon: "✅", color: "success" },
          { key: "pending", label: "Pending Review", icon: "⏳", color: "warning" },
          { key: "rejected", label: "Rejected", icon: "❌", color: "danger" },
          { key: "draft", label: "Drafts", icon: "📝", color: "secondary" },
        ].map(({ key, label, icon, color }) => (
          <div className="col-md-4 col-xl" key={key}>
            <div className="card border-0 shadow-sm rounded-4 h-100">
              <div className="card-body p-4">
                <div className="d-flex justify-content-between mb-2">
                  <span style={{ fontSize: "1.4rem" }}>{icon}</span>
                  <span className={`badge bg-${color} bg-opacity-10 text-${color} rounded-pill px-2`}>
                    {key}
                  </span>
                </div>
                <h2 className="fw-bold mb-0">{status_counts[key] ?? 0}</h2>
                <p className="text-muted small mb-0 mt-1">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="row g-4 mb-4">
        {/* Bar chart — by domain */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-4">Questions by Domain</h5>
              {by_domain.length === 0 ? (
                <p className="text-muted">No domain data available.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={by_domain} margin={{ left: -10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="domain"
                      tick={{ fontSize: 11 }}
                      angle={-25}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(val) => [`${val} questions`, "Count"]}
                    />
                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* Pie chart — status distribution */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-4">Status Distribution</h5>
              {pieData.length === 0 ? (
                <p className="text-muted">No data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="45%"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(val, name) => [`${val}`, name]} />
                    <Legend iconType="circle" iconSize={10} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tables Row */}
      <div className="row g-4 mb-4">
        {/* By Course */}
        <div className="col-lg-6">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Questions per Course</h5>
              {by_course.length === 0 ? (
                <p className="text-muted">No data.</p>
              ) : (
                <table className="table table-sm">
                  <thead>
                    <tr className="text-muted small">
                      <th>Course</th>
                      <th className="text-end">Questions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {by_course.map((row) => (
                      <tr key={row.course_id}>
                        <td className="fw-semibold">{row.course}</td>
                        <td className="text-end">
                          <span className="badge bg-primary">{row.count}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* Top Topics */}
        <div className="col-lg-6">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Top Topics</h5>
              {by_topic.length === 0 ? (
                <p className="text-muted">No data.</p>
              ) : (
                <div className="d-grid gap-2">
                  {by_topic.slice(0, 10).map((row) => {
                    const pct = status_counts.total
                      ? Math.round((row.count / status_counts.total) * 100)
                      : 0;
                    return (
                      <div key={row.topic_id}>
                        <div className="d-flex justify-content-between mb-1">
                          <span className="small fw-semibold">{row.topic}</span>
                          <span className="small text-muted">{row.count}</span>
                        </div>
                        <div className="progress" style={{ height: 6 }}>
                          <div
                            className="progress-bar bg-primary"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card border-0 shadow-sm rounded-4">
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold mb-0">Recent Teacher Activity</h5>
            <Link
              className="btn btn-sm btn-outline-primary"
              to="/department-head/audit-logs"
            >
              View all logs
            </Link>
          </div>
          {recent_activity.length === 0 ? (
            <p className="text-muted">No recent activity.</p>
          ) : (
            <div className="d-grid gap-2">
              {recent_activity.map((log) => (
                <div key={log.id} className="dashboard-list-item">
                  <div>
                    <strong>{log.username}</strong>
                    <span className="text-muted mx-2">·</span>
                    <span className="badge bg-light text-dark border text-capitalize">
                      {log.action}
                    </span>
                    <p className="small text-muted mb-0 mt-1">{log.description}</p>
                  </div>
                  <span className="text-muted small flex-shrink-0">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExamBankDashboard;
