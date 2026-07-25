import { useEffect, useState } from "react";
import api from "../api/api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";

const DepartmentHeadAnalytics = () => {
  const [stats, setStats] = useState(null);
  const [courseOverview, setCourseOverview] = useState(null);
  const [topicDifficulty, setTopicDifficulty] = useState([]);
  const [scoreTrend, setScoreTrend] = useState(null);
  const [atRiskStudents, setAtRiskStudents] = useState(null);
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCourses();
    fetchDepartmentAnalytics("");
  }, []);

  const fetchCourses = async () => {
    try {
      const res = await api.get("/exit-exams/courses/");
      setCourses(Array.isArray(res.data) ? res.data : res.data.results || []);
    } catch (err) {
      console.error("Failed to fetch courses:", err);
    }
  };

  const fetchDepartmentAnalytics = async (courseId) => {
    try {
      setLoading(true);
      setError("");
      const query = courseId ? `?course=${courseId}` : "";

      const [statsRes, overviewRes, difficultyRes, trendRes, atRiskRes] = await Promise.all([
        api.get(`/exit-exams/admin-dashboard/${query}`),
        api.get(`/analytics/course-overview/${query}`),
        api.get(`/analytics/topic-difficulty/${query}`),
        api.get(`/analytics/score-trend/${query}`),
        api.get(`/analytics/at-risk-students/${query}`),
      ]);

      setStats(statsRes.data);
      setCourseOverview(overviewRes.data);
      setTopicDifficulty(Array.isArray(difficultyRes.data) ? difficultyRes.data : []);
      setScoreTrend(trendRes.data);
      setAtRiskStudents(atRiskRes.data);
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
      setError("Failed to load department analytics.");
    } finally {
      setLoading(false);
    }
  };

  const handleCourseChange = (courseId) => {
    setSelectedCourse(courseId);
    fetchDepartmentAnalytics(courseId);
  };

  if (loading && !stats) {
    return (
      <div className="container py-5">
        <p className="text-center text-muted">Loading analytics...</p>
      </div>
    );
  }

  const users = stats?.users || {};
  const academicStructure = stats?.academic_structure || {};
  const questionBank = stats?.question_bank || {};
  const exams = stats?.exams || {};
  const readiness = stats?.readiness || {};
  const distributionData = questionBank.distribution_by_domain || [];
  const weakestTopics = stats?.weakest_topics || [];

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4 d-flex justify-content-between align-items-center flex-wrap gap-3">
        <div>
          <span className="dashboard-badge">Department Head Portal</span>
          <h2 className="fw-bold mt-2 mb-1">Department Analytics</h2>
          <p className="text-muted mb-0">
            Monitor academic structure, question bank, and student performance.
          </p>
        </div>

        <div className="d-flex align-items-center gap-2">
          <label htmlFor="course-select" className="fw-bold small text-muted text-nowrap mb-0">
            Course Filter:
          </label>
          <select
            id="course-select"
            className="form-select shadow-sm"
            style={{ minWidth: "220px" }}
            value={selectedCourse}
            onChange={(e) => handleCourseChange(e.target.value)}
          >
            <option value="">All Courses</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <CourseOverviewCards overview={courseOverview} />

      <div className="row g-3 mb-4">
        <div className="col-lg-7">
          <TopicDifficultyTable topics={topicDifficulty} />
        </div>

        <div className="col-lg-5">
          <TopicDifficultyHeatmap topics={topicDifficulty} />
        </div>
      </div>

      <ScoreTrendCard trendData={scoreTrend} />

      {/* Department Overview Cards */}
      <div className="row mb-4">
        <div className="col-md-2 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Departments</p>
              <h3 className="fw-bold text-primary">{academicStructure.total_departments || 0}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-2 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Courses</p>
              <h3 className="fw-bold text-info">{academicStructure.total_courses || 0}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-2 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Teachers</p>
              <h3 className="fw-bold text-success">{users.total_teachers || 0}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-2 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Students</p>
              <h3 className="fw-bold text-warning">{users.total_students || 0}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-2 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Active Questions</p>
              <h3 className="fw-bold">{questionBank.active_questions || 0}</h3>
            </div>
          </div>
        </div>

        <div className="col-md-2 mb-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">Avg Readiness</p>
              <h3 className="fw-bold text-danger">{readiness.average_readiness_score || 0}%</h3>
            </div>
          </div>
        </div>
      </div>

      {/* Academic Structure */}
      <div className="row mb-4">
        <div className="col-md-6">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-header bg-white border-bottom">
              <h5 className="fw-bold mb-0">Academic Structure</h5>
            </div>
            <div className="card-body">
              <div className="row text-center">
                <div className="col-6 mb-3">
                  <h6 className="text-muted">Domains</h6>
                  <h3 className="fw-bold text-primary">{academicStructure.total_domains || 0}</h3>
                </div>
                <div className="col-6 mb-3">
                  <h6 className="text-muted">Topics</h6>
                  <h3 className="fw-bold text-info">{academicStructure.total_topics || 0}</h3>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-md-6">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-header bg-white border-bottom">
              <h5 className="fw-bold mb-0">Exam Statistics</h5>
            </div>
            <div className="card-body">
              <div className="row text-center">
                <div className="col-6 mb-3">
                  <h6 className="text-muted">Total Attempts</h6>
                  <h3 className="fw-bold text-success">{exams.total_attempts || 0}</h3>
                </div>
                <div className="col-6 mb-3">
                  <h6 className="text-muted">Avg Score</h6>
                  <h3 className="fw-bold text-warning">{exams.average_exam_score || 0}%</h3>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Question Distribution Chart */}
      {distributionData.length > 0 && (
        <div className="card border-0 shadow-sm rounded-4 mb-4">
          <div className="card-header bg-white border-bottom">
            <h5 className="fw-bold mb-0">Question Distribution by Domain</h5>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={400}>
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
      )}

      {/* Weakest Topics */}
      {weakestTopics.length > 0 && (
        <div className="card border-0 shadow-sm rounded-4 mb-4">
          <div className="card-header bg-white border-bottom">
            <h5 className="fw-bold mb-0">Areas for Improvement</h5>
            <p className="text-muted small mb-0">Top topics where students need support</p>
          </div>
          <div className="card-body">
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th>Student</th>
                    <th>Domain</th>
                    <th>Topic</th>
                    <th>Accuracy</th>
                    <th>Progress</th>
                  </tr>
                </thead>
                <tbody>
                  {weakestTopics.map((item, idx) => (
                    <tr key={idx}>
                      <td className="fw-bold">{item.student}</td>
                      <td>{item.domain}</td>
                      <td>{item.topic}</td>
                      <td>
                        <span className="badge bg-danger">
                          {(item.accuracy * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td>
                        <small className="text-muted">
                          {item.correct_attempts}/{item.total_attempts}
                        </small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <AtRiskStudentsCard atRiskData={atRiskStudents} />

      {/* Empty State */}
      {!distributionData.length && !weakestTopics.length && (
        <div className="card border-0 shadow-sm rounded-4 bg-light mt-4">
          <div className="card-body text-center py-5">
            <p className="text-muted mb-0">
              Analytics data will appear as teachers create questions and students take exams.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

const CourseOverviewCards = ({ overview }) => {
  const cards = [
    {
      label: "Students",
      value: overview?.students || 0,
      tone: "text-primary",
    },
    {
      label: "Average Score",
      value: `${overview?.average_score || 0}%`,
      tone: "text-info",
    },
    {
      label: "Pass Rate",
      value: `${overview?.pass_rate || 0}%`,
      tone: "text-success",
    },
    {
      label: "Fail Rate",
      value: `${overview?.fail_rate || 0}%`,
      tone: "text-danger",
    },
  ];

  return (
    <div className="row g-3 mb-4">
      {cards.map((card) => (
        <div key={card.label} className="col-md-3">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <p className="text-muted small mb-2">{card.label}</p>
              <h3 className={`fw-bold ${card.tone}`}>{card.value}</h3>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const TopicDifficultyTable = ({ topics }) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-header bg-white border-bottom">
        <h5 className="fw-bold mb-0">Most Difficult Topics</h5>
      </div>

      <div className="card-body">
        {topics.length === 0 ? (
          <p className="text-muted mb-0">Topic difficulty appears after submitted exams.</p>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover mb-0">
              <thead className="table-light">
                <tr>
                  <th>Topic</th>
                  <th>Failure Count</th>
                </tr>
              </thead>
              <tbody>
                {topics.slice(0, 10).map((item) => (
                  <tr key={item.topic}>
                    <td className="fw-bold">{item.topic}</td>
                    <td>{item.failure_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const getDifficultyClass = (failureCount, maxFailures) => {
  if (!maxFailures || failureCount <= maxFailures * 0.33) {
    return "heatmap-easy";
  }

  if (failureCount <= maxFailures * 0.66) {
    return "heatmap-medium";
  }

  return "heatmap-difficult";
};

const TopicDifficultyHeatmap = ({ topics }) => {
  const maxFailures = Math.max(...topics.map((item) => item.failure_count), 0);

  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-header bg-white border-bottom">
        <h5 className="fw-bold mb-0">Difficulty Heatmap</h5>
      </div>

      <div className="card-body">
        {topics.length === 0 ? (
          <p className="text-muted mb-0">No heatmap data yet.</p>
        ) : (
          <div className="topic-heatmap">
            {topics.slice(0, 12).map((item) => (
              <div
                key={item.topic}
                className={`topic-heatmap-cell ${getDifficultyClass(
                  item.failure_count,
                  maxFailures
                )}`}
              >
                <strong>{item.topic}</strong>
                <span>{item.failure_count} failures</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const ScoreTrendCard = ({ trendData }) => {
  const data = trendData?.trend || [];
  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4">
      <div className="card-header bg-white border-bottom d-flex justify-content-between align-items-center">
        <div>
          <h5 className="fw-bold mb-0">Average Score Trend</h5>
          <p className="text-muted small mb-0">Monthly mean of each student's latest exam attempt score</p>
        </div>
        <span className="badge bg-primary">{trendData?.course || "All Courses"}</span>
      </div>
      <div className="card-body">
        {data.length === 0 ? (
          <p className="text-muted mb-0">No score trend data available.</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" fontSize={12} />
              <YAxis domain={[0, 100]} tickFormatter={(val) => `${val}%`} />
              <Tooltip formatter={(val) => [val !== null ? `${val}%` : "No Data", "Average Score"]} />
              <Line
                type="monotone"
                dataKey="average_score"
                stroke="#2563eb"
                strokeWidth={3}
                connectNulls={false}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

const AtRiskStudentsCard = ({ atRiskData }) => {
  const students = atRiskData?.students || [];
  const passMark = atRiskData?.pass_mark || 50;
  const totalAtRisk = atRiskData?.total_at_risk || 0;

  const getBadge = (score) => {
    if (score < 40) return <span className="badge bg-danger">{score}%</span>;
    return <span className="badge bg-warning text-dark">{score}%</span>;
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mt-4">
      <div className="card-header bg-white border-bottom d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div>
          <h5 className="fw-bold mb-0">At-Risk Students</h5>
          <p className="text-muted small mb-0">
            Students with readiness score below pass mark ({passMark}%)
          </p>
        </div>
        <span className="badge bg-danger">{totalAtRisk} Total At-Risk</span>
      </div>
      <div className="card-body">
        {students.length === 0 ? (
          <p className="text-muted mb-0">No at-risk students detected.</p>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover mb-0">
              <thead className="table-light">
                <tr>
                  <th>Student Name</th>
                  <th>Latest Exam Score</th>
                  <th>Weakest Topic</th>
                  <th>Readiness Score</th>
                </tr>
              </thead>
              <tbody>
                {students.map((st) => (
                  <tr key={st.student_id}>
                    <td className="fw-bold">{st.name}</td>
                    <td>{st.latest_score}%</td>
                    <td>
                      <span className="badge bg-light text-dark border">{st.weakest_topic}</span>
                    </td>
                    <td>{getBadge(st.readiness_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default DepartmentHeadAnalytics;
