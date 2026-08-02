import { useEffect, useState } from "react";
import api from "../api/api";
import {
  FileText,
  Users,
  GraduationCap,
  Building2,
  BookOpen,
  CheckCircle,
  Clock,
  FileCode,
  XCircle,
  Archive,
  BarChart2,
} from "lucide-react";

const STATUS_BADGES = {
  approved: { label: "Approved", class: "bg-success text-white", icon: CheckCircle },
  pending: { label: "Pending Review", class: "bg-warning text-dark", icon: Clock },
  draft: { label: "Draft", class: "bg-secondary text-white", icon: FileCode },
  rejected: { label: "Rejected", class: "bg-danger text-white", icon: XCircle },
  archived: { label: "Archived", class: "bg-dark text-white", icon: Archive },
};

const SystemAdminDashboard = () => {
  const [bankStats, setBankStats] = useState(null);
  const [dashStats, setDashStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError("");
    try {
      const [bankRes, dashRes] = await Promise.all([
        api.get("/exit-exams/exam-bank-stats/"),
        api.get("/exit-exams/admin-dashboard/"),
      ]);
      setBankStats(bankRes.data);
      setDashStats(dashRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load admin dashboard stats.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="small text-muted mt-2">Loading system admin overview...</p>
      </div>
    );
  }

  const statusCounts = bankStats?.status_counts || {};
  const totalQuestions = statusCounts.total || 0;

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">System Admin</span>
          <h2 className="fw-bold mt-2 mb-1">Platform Overview</h2>
          <p className="text-muted mb-0">
            System-wide question bank metrics, institutional stats, and status breakdowns.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger mb-4">{error}</div>}

      {/* Top Metric Cards */}
      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 p-3 h-100">
            <div className="d-flex align-items-center gap-3">
              <div className="p-3 bg-primary-subtle text-primary rounded-3">
                <FileText size={24} />
              </div>
              <div>
                <small className="text-muted text-uppercase fw-semibold">Total Questions</small>
                <h3 className="fw-bold mb-0">{totalQuestions}</h3>
              </div>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 p-3 h-100">
            <div className="d-flex align-items-center gap-3">
              <div className="p-3 bg-success-subtle text-success rounded-3">
                <Users size={24} />
              </div>
              <div>
                <small className="text-muted text-uppercase fw-semibold">Total Students</small>
                <h3 className="fw-bold mb-0">{dashStats?.users?.total_students || 0}</h3>
              </div>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 p-3 h-100">
            <div className="d-flex align-items-center gap-3">
              <div className="p-3 bg-info-subtle text-info rounded-3">
                <GraduationCap size={24} />
              </div>
              <div>
                <small className="text-muted text-uppercase fw-semibold">Total Teachers</small>
                <h3 className="fw-bold mb-0">{dashStats?.users?.total_teachers || 0}</h3>
              </div>
            </div>
          </div>
        </div>

        <div className="col-sm-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 p-3 h-100">
            <div className="d-flex align-items-center gap-3">
              <div className="p-3 bg-warning-subtle text-warning rounded-3">
                <Building2 size={24} />
              </div>
              <div>
                <small className="text-muted text-uppercase fw-semibold">Departments</small>
                <h3 className="fw-bold mb-0">{dashStats?.academic_structure?.total_departments || 0}</h3>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Question Status Distribution */}
      <div className="card border-0 shadow-sm rounded-4 mb-4">
        <div className="card-header bg-transparent border-0 pt-4 px-4 pb-0">
          <h5 className="fw-bold mb-0">Question Bank Status Breakdown</h5>
        </div>
        <div className="card-body p-4">
          <div className="row g-3">
            {["approved", "pending", "draft", "rejected", "archived"].map((stKey) => {
              const count = statusCounts[stKey] || 0;
              const pct = totalQuestions > 0 ? Math.round((count / totalQuestions) * 100) : 0;
              const badgeConfig = STATUS_BADGES[stKey] || { label: stKey, class: "bg-secondary" };
              const IconComp = badgeConfig.icon;

              return (
                <div key={stKey} className="col">
                  <div className="p-3 rounded-3 border bg-light text-center h-100 d-flex flex-column justify-content-between">
                    <div>
                      <span className={`badge ${badgeConfig.class} mb-2 d-inline-flex align-items-center gap-1`}>
                        {IconComp && <IconComp size={12} />}
                        {badgeConfig.label}
                      </span>
                      <h4 className="fw-bold mb-1">{count}</h4>
                    </div>
                    <div className="progress mt-2" style={{ height: "6px" }}>
                      <div
                        className={`progress-bar ${stKey === "approved" ? "bg-success" : stKey === "pending" ? "bg-warning" : stKey === "rejected" ? "bg-danger" : "bg-secondary"}`}
                        role="progressbar"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Breakdown by Course & Domain */}
      <div className="row g-4 mb-4">
        {/* Questions by Course */}
        <div className="col-lg-6">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-header bg-transparent border-0 pt-4 px-4 pb-0 d-flex justify-content-between align-items-center">
              <div className="d-flex align-items-center gap-2 fw-bold text-dark">
                <BookOpen size={20} className="text-primary" />
                <span>Questions per Course</span>
              </div>
            </div>
            <div className="card-body p-4">
              {bankStats?.by_course?.length === 0 ? (
                <p className="text-muted mb-0">No course data available.</p>
              ) : (
                <div className="d-grid gap-3">
                  {bankStats?.by_course?.map((item) => {
                    const pct = totalQuestions > 0 ? Math.round((item.count / totalQuestions) * 100) : 0;
                    return (
                      <div key={item.course_id || item.course}>
                        <div className="d-flex justify-content-between align-items-center mb-1">
                          <span className="fw-medium text-dark">{item.course}</span>
                          <span className="small text-muted fw-bold">{item.count} questions ({pct}%)</span>
                        </div>
                        <div className="progress" style={{ height: "8px" }}>
                          <div className="progress-bar bg-primary" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Questions by Domain */}
        <div className="col-lg-6">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-header bg-transparent border-0 pt-4 px-4 pb-0 d-flex justify-content-between align-items-center">
              <div className="d-flex align-items-center gap-2 fw-bold text-dark">
                <BarChart2 size={20} className="text-success" />
                <span>Questions per Domain</span>
              </div>
            </div>
            <div className="card-body p-4">
              {bankStats?.by_domain?.length === 0 ? (
                <p className="text-muted mb-0">No domain data available.</p>
              ) : (
                <div className="table-responsive">
                  <table className="table table-sm align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th>Domain Name</th>
                        <th className="text-end">Question Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bankStats?.by_domain?.map((item) => (
                        <tr key={item.domain_id || item.domain}>
                          <td className="fw-medium">{item.domain}</td>
                          <td className="text-end fw-bold text-primary">{item.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemAdminDashboard;
