import { useEffect, useState } from "react";
import api from "../api/api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const TeacherAnalytics = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTeacherAnalytics();
  }, []);

  const fetchTeacherAnalytics = async () => {
    try {
      // Fetch assigned courses
      const coursesRes = await api.get("/exit-exams/my-assigned-courses/");
      
      // Fetch dashboard stats
      const statsRes = await api.get("/exit-exams/admin-dashboard/");

      setStats({
        courses: coursesRes.data,
        systemStats: statsRes.data,
      });
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
      setError("Failed to load analytics data.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container py-5">
        <p className="text-center text-muted">Loading analytics...</p>
      </div>
    );
  }

  const totalCourses = stats?.courses?.length || 0;
  const systemStats = stats?.systemStats || {};
  const distributionData = systemStats.question_bank?.distribution_by_domain || [];
  const questionStats = systemStats.question_bank || {};
  const examStats = systemStats.exams || {};

  const COLORS = [
    "#0088FE",
    "#00C49F",
    "#FFBB28",
    "#FF8042",
    "#8884D8",
    "#82CA9D",
  ];

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Teacher Portal</span>
          <h2 className="fw-bold mt-2 mb-1">Analytics</h2>
          <p className="text-muted mb-0">
            Monitor your assigned courses and student performance metrics.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {/* Summary Cards */}
      <div className="row mb-4">
        <div className="col-md-3 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Assigned Courses</p>
              <h3 className="fw-bold text-primary">{totalCourses}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-3 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Questions Created</p>
              <h3 className="fw-bold text-success">{questionStats.total_questions || 0}</h3>
              <small className="text-muted">
                {questionStats.active_questions || 0} approved
              </small>
            </div>
          </div>
        </div>

        <div className="col-md-3 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Student Attempts</p>
              <h3 className="fw-bold text-info">{examStats.total_attempts || 0}</h3>
              <small className="text-muted">
                Avg: {examStats.average_exam_score || 0}%
              </small>
            </div>
          </div>
        </div>

        <div className="col-md-3 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Readiness Score</p>
              <h3 className="fw-bold text-warning">
                {systemStats.readiness?.average_readiness_score || 0}%
              </h3>
            </div>
          </div>
        </div>
      </div>

      {/* Courses Section */}
      {totalCourses > 0 && (
        <div className="card border-0 shadow-sm rounded-4 mb-4">
          <div className="card-header bg-white border-bottom">
            <h5 className="fw-bold mb-0">Your Assigned Courses</h5>
          </div>
          <div className="card-body">
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th>Course Name</th>
                    <th>Department</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.courses.map((assignment) => (
                    <tr key={assignment.id}>
                      <td className="fw-bold">{assignment.course_name}</td>
                      <td>
                        <span className="badge bg-light text-dark">
                          {assignment.department_name || "N/A"}
                        </span>
                      </td>
                      <td className="text-muted small">
                        {assignment.course_description || "No description"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Question Distribution Chart */}
      {distributionData.length > 0 && (
        <div className="row mb-4">
          <div className="col-lg-6">
            <div className="card border-0 shadow-sm rounded-4">
              <div className="card-header bg-white border-bottom">
                <h5 className="fw-bold mb-0">Questions by Domain</h5>
              </div>
              <div className="card-body">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={distributionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="domain"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      fontSize={12}
                    />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="total_questions" fill="#0088FE" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Pie Chart */}
          {distributionData.length <= 5 && (
            <div className="col-lg-6">
              <div className="card border-0 shadow-sm rounded-4">
                <div className="card-header bg-white border-bottom">
                  <h5 className="fw-bold mb-0">Domain Distribution</h5>
                </div>
                <div className="card-body">
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={distributionData}
                        dataKey="total_questions"
                        nameKey="domain"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                      >
                        {distributionData.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Info Box */}
      {totalCourses === 0 && (
        <div className="card border-0 shadow-sm rounded-4 bg-light">
          <div className="card-body text-center py-5">
            <p className="text-muted mb-0">
              No analytics available yet. Once courses are assigned, analytics will appear here.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherAnalytics;
