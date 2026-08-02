import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../api/api";

import {
  getDailyGoalMinutes,
  setDailyGoalMinutes,
  getStudyStreak,
  markStudyActivity,
  getGoalProgressPercent,
} from "../utils/productivity";

const WEEKLY_FOCUS_TARGET_MINUTES = 600;
const RECENT_LIMIT = 5;

const getArrayData = (data) => {
  if (Array.isArray(data)) return data;
  return data?.results || [];
};

const getWeakTopicsFromHierarchy = (data) => {
  const courses = data?.courses || (data?.domains ? [data] : []);

  return courses.flatMap((course) =>
    (course.domains || []).flatMap((domain) =>
      (domain.topics || [])
        .filter((topic) => Number(topic.accuracy) < 60)
        .map((topic) => ({
          ...topic,
          course: course.course,
          domain: domain.name,
        }))
    )
  );
};

const getNumberValue = (...values) => {
  for (const value of values) {
    if (value !== undefined && value !== null && value !== "") {
      const number = Number(value);

      if (Number.isFinite(number) && number >= 0) {
        return number;
      }
    }
  }

  return 0;
};

const getTodayMinutes = (focusData, dashboardData) => {
  return getNumberValue(
    focusData?.today_minutes,
    focusData?.total_today_minutes,
    focusData?.today_focus_minutes,
    dashboardData?.focus_summary?.today_minutes,
    dashboardData?.focus_summary?.total_today_minutes,
    dashboardData?.focus_summary?.today_focus_minutes
  );
};

const getWeekMinutes = (focusData, dashboardData) => {
  return getNumberValue(
    focusData?.week_minutes,
    focusData?.total_week_minutes,
    focusData?.weekly_focus_minutes,
    dashboardData?.focus_summary?.week_minutes,
    dashboardData?.focus_summary?.total_week_minutes,
    dashboardData?.focus_summary?.weekly_focus_minutes
  );
};

const formatDate = (dateValue, includeTime = false) => {
  if (!dateValue) return "—";

  const date = new Date(dateValue);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return includeTime ? date.toLocaleString() : date.toLocaleDateString();
};

const formatScore = (score) => {
  const number = Number(score || 0);
  return `${Number.isInteger(number) ? number : number.toFixed(1)}%`;
};

const getMaterialStatusBadge = (status) => {
  if (status === "completed") return "bg-success";
  if (status === "processing") return "bg-warning text-dark";
  if (status === "failed") return "bg-danger";
  return "bg-secondary";
};

const StudentDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [focusSummary, setFocusSummary] = useState(null);
  const [weakTopics, setWeakTopics] = useState([]);
  const [weakDomains, setWeakDomains] = useState([]);
  const [recentResults, setRecentResults] = useState([]);
  const [recentMaterials, setRecentMaterials] = useState([]);
  const [recentSessions, setRecentSessions] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [streak, setStreak] = useState(getStudyStreak());
  const [dailyGoal, setDailyGoal] = useState(getDailyGoalMinutes());
  const [goalInput, setGoalInput] = useState(String(getDailyGoalMinutes()));
  const [adaptivePath, setAdaptivePath] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError("");

      const dashboardRes = await api.get("/analytics/dashboard/");
      const dashboardData = dashboardRes.data;

      const settled = await Promise.allSettled([
        api.get("/exit-exams/my-results/"),
        api.get("/rag/materials/"),
        api.get("/analytics/focus/summary/"),
        api.get("/adaptive-learning/current/"),
      ]);

      const resultsRes = settled[0].status === "fulfilled" ? settled[0].value : { data: [] };
      const materialsRes = settled[1].status === "fulfilled" ? settled[1].value : { data: [] };
      const focusRes = settled[2].status === "fulfilled" ? settled[2].value : { data: dashboardData?.focus_summary || {} };
      const adaptiveRes = settled[3].status === "fulfilled" ? settled[3].value : null;

      if (adaptiveRes && adaptiveRes.data) {
        setAdaptivePath(adaptiveRes.data);
      } else {
        setAdaptivePath(null);
      }

      const focusData = (focusRes && focusRes.data) || {};

      setDashboard(dashboardData);
      setFocusSummary(focusData);

      setRecentResults(getArrayData(resultsRes.data).slice(0, RECENT_LIMIT));
      setRecentMaterials(getArrayData(materialsRes.data).slice(0, RECENT_LIMIT));
      setRecentSessions((focusData.recent_sessions || []).slice(0, RECENT_LIMIT));

      const todayMinutes = getTodayMinutes(focusData, dashboardData);

      if (todayMinutes > 0) {
        const updatedStreak = markStudyActivity();
        setStreak(updatedStreak);
      }

      const [weaknessResult, recommendationsResult, trendResult] =
        await Promise.allSettled([
          api.get("/analytics/student/weakness/"),
          api.get("/analytics/student/recommendations/"),
          api.get("/analytics/student/trend/"),
        ]);

      if (weaknessResult.status === "fulfilled") {
        const wData = weaknessResult.value.data;
        setWeakTopics(getWeakTopicsFromHierarchy(wData));
        setWeakDomains(wData.weak_domains || wData.domains || dashboardData?.weak_domains || []);
      } else {
        setWeakTopics(dashboardData?.weak_topics || []);
        setWeakDomains(dashboardData?.weak_domains || []);
        console.error("Failed to load weakness analytics:", weaknessResult.reason);
      }

      if (recommendationsResult.status === "fulfilled") {
        setRecommendations(getArrayData(recommendationsResult.value.data));
      } else {
        setRecommendations([]);
        console.error(
          "Failed to load student recommendations:",
          recommendationsResult.reason
        );
      }

      if (trendResult.status === "fulfilled") {
        setTrendData(getArrayData(trendResult.value.data));
      } else {
        setTrendData([]);
        console.error("Failed to load trend analytics:", trendResult.reason);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load student dashboard.");
    } finally {
      setLoading(false);
    }
  };

  const saveDailyGoal = (e) => {
    e.preventDefault();

    const minutes = Number(goalInput);

    if (!minutes || minutes <= 0) {
      return;
    }

    setDailyGoalMinutes(minutes);
    setDailyGoal(minutes);
  };

  if (loading) {
    return (
      <div className="container py-5">
        <div className="text-muted">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return <div className="container py-5 alert alert-danger">{error}</div>;
  }

  const readiness = dashboard?.readiness_scores?.[0];

  const readinessScore = getNumberValue(
    readiness?.score,
    readiness?.readiness_score,
    readiness?.value
  );

  const readinessCourse =
    readiness?.course || readiness?.course_name || "No score yet";

  const todayMinutes = getTodayMinutes(focusSummary, dashboard);
  const weekMinutes = getWeekMinutes(focusSummary, dashboard);

  const dailyProgress = Number(getGoalProgressPercent(todayMinutes, dailyGoal)) || 0;
  const dailyProgressWidth = Math.min(100, dailyProgress);

  const weeklyProgress = Math.min(
    100,
    Math.round((weekMinutes / WEEKLY_FOCUS_TARGET_MINUTES) * 100)
  );

  const remainingWeekMinutes = Math.max(
    0,
    WEEKLY_FOCUS_TARGET_MINUTES - weekMinutes
  );

  const weeklyAverage = Math.round(weekMinutes / 7);

  return (
    <div className="container-fluid py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Student Portal</span>

          <h2 className="fw-bold mt-2 mb-1">Welcome back</h2>

          <p className="text-muted mb-0">
            Track your readiness, practice exams, study materials, and study
            productivity in one place.
          </p>
        </div>

        <div className="d-flex gap-2 flex-wrap">
          <Link className="btn btn-primary" to="/student/exams">
            Start Exam
          </Link>

          <Link className="btn btn-outline-primary" to="/student/materials">
            Study Materials
          </Link>

          <Link className="btn btn-outline-dark" to="/student/focus">
            Focus Timer
          </Link>
          <Link className="btn btn-outline-success" to="/student/battle">
  Battle Mode
</Link>
        </div>
      </div>

      <div className="row g-3">
        <DashboardStatCard
          title="Readiness Score"
          value={`${readinessScore}%`}
          subtitle={readinessCourse}
        />

        <DashboardStatCard
          title="Today Focus"
          value={`${todayMinutes} min`}
          subtitle="Study time today"
        />

        <DashboardStatCard
          title="This Week"
          value={`${weekMinutes} min`}
          subtitle="Weekly focus minutes"
        />

        <DashboardStatCard
          title="Study Streak"
          value={`🔥 ${streak.count}`}
          subtitle={`day${streak.count === 1 ? "" : "s"} in a row`}
          special
        />
      </div>
        <div className="row g-3 mt-3">
          <div className="col-12">
            <AdaptiveLearningCard path={adaptivePath} />
          </div>
        </div>

        <div className="row g-3 mt-3">
          <div className="col-lg-12">
            <div className="battle-dashboard-card">
              <div>
                <span className="dashboard-badge">Competitive Learning</span>
                <h4 className="fw-bold mt-2 mb-1">Battle Mode</h4>
                <p className="text-muted mb-0">
                  Challenge classmates using the same approved exam questions. Compete
                  by score and completion time on the leaderboard.
                </p>
              </div>

              <Link className="btn btn-success" to="/student/battle">
                Start Battle
              </Link>
            </div>
          </div>
        </div>
      <div className="row g-3 mt-3">
        <div className="col-lg-5">
          <DailyStudyGoalCard
            todayMinutes={todayMinutes}
            dailyGoal={dailyGoal}
            goalInput={goalInput}
            setGoalInput={setGoalInput}
            progress={dailyProgress}
            progressWidth={dailyProgressWidth}
            onSave={saveDailyGoal}
          />
        </div>

        <div className="col-lg-7">
          <WeeklyFocusOverview
            weekMinutes={weekMinutes}
            weeklyProgress={weeklyProgress}
            remainingWeekMinutes={remainingWeekMinutes}
            weeklyAverage={weeklyAverage}
          />
        </div>
      </div>

      <div className="row g-3 mt-3">
        <div className="col-12">
          <RecentExamAttempts recentResults={recentResults} />
        </div>
      </div>

      <div className="row g-3 mt-3">
        <div className="col-lg-6">
          <RecentStudyMaterials recentMaterials={recentMaterials} />
        </div>

        <div className="col-lg-6">
          <RecentFocusSessions recentSessions={recentSessions} />
        </div>
      </div>

      <div className="row g-3 mt-3">
        <div className="col-lg-5">
          <AdvancedWeakTopicsCard
            weakTopics={
              weakTopics.length > 0 ? weakTopics : dashboard?.weak_topics || []
            }
            weakDomains={
              weakDomains.length > 0 ? weakDomains : dashboard?.weak_domains || []
            }
          />
        </div>

        <div className="col-lg-7">
          <RecommendationsCard recommendations={recommendations} />
        </div>
      </div>

      <div className="row g-3 mt-3">
        <div className="col-lg-7">
          <TrendChart trendData={trendData} />
        </div>

        <div className="col-lg-5">
          <SpacedRepetitionCard dueItems={dashboard?.spaced_repetition_due || []} />
        </div>
      </div>
    </div>
  );
};

const DashboardStatCard = ({ title, value, subtitle, special }) => {
  return (
    <div className="col-md-3">
      <div
        className={`card border-0 shadow-sm rounded-4 h-100 ${
          special ? "streak-card" : ""
        }`}
      >
        <div className="card-body">
          <h6 className="text-muted">{title}</h6>
          <h2 className="fw-bold">{value}</h2>
          <p className="small text-muted mb-0">{subtitle}</p>
        </div>
      </div>
    </div>
  );
};

const DailyStudyGoalCard = ({
  todayMinutes,
  dailyGoal,
  goalInput,
  setGoalInput,
  progress,
  progressWidth,
  onSave,
}) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <h5 className="fw-bold">Daily Study Goal</h5>

        <p className="text-muted">
          Set a daily goal and track your progress as Pomodoro sessions are
          completed.
        </p>

        <div className="d-flex justify-content-between mb-2">
          <strong>
            {todayMinutes} / {dailyGoal} min
          </strong>

          <strong>{progress}%</strong>
        </div>

        <div className="progress daily-goal-progress mb-3">
          <div
            className="progress-bar"
            style={{ width: `${progressWidth}%` }}
          >
            {progress >= 100 ? "Goal reached" : ""}
          </div>
        </div>

        {progress >= 100 && (
          <div className="alert alert-success py-2">
            Great job! You reached your daily study goal.
          </div>
        )}

        <form onSubmit={onSave} className="d-flex gap-2">
          <input
            type="number"
            className="form-control"
            value={goalInput}
            onChange={(e) => setGoalInput(e.target.value)}
            min="1"
            placeholder="Goal minutes"
          />

          <button className="btn btn-primary">Save</button>
        </form>
      </div>
    </div>
  );
};

const WeeklyFocusOverview = ({
  weekMinutes,
  weeklyProgress,
  remainingWeekMinutes,
  weeklyAverage,
}) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-start gap-3 mb-3">
          <div>
            <h5 className="fw-bold mb-1">Weekly Focus Overview</h5>

            <p className="text-muted mb-0">
              Monitor your weekly focus progress and stay consistent with your
              study target.
            </p>
          </div>

          <Link className="btn btn-sm btn-outline-primary" to="/student/focus">
            Open Focus
          </Link>
        </div>

        <div className="d-flex justify-content-between align-items-end mb-2">
          <div>
            <h2 className="fw-bold mb-0">{weekMinutes} min</h2>
            <span className="small text-muted">
              of {WEEKLY_FOCUS_TARGET_MINUTES} min weekly target
            </span>
          </div>

          <span className="badge bg-primary">{weeklyProgress}%</span>
        </div>

        <div className="progress mb-3" style={{ height: "12px" }}>
          <div
            className="progress-bar"
            style={{ width: `${weeklyProgress}%` }}
          ></div>
        </div>

        <div className="row g-2">
          <div className="col-md-4">
            <div className="border rounded-4 p-3 h-100">
              <h6 className="text-muted mb-1">Remaining</h6>
              <strong>{remainingWeekMinutes} min</strong>
            </div>
          </div>

          <div className="col-md-4">
            <div className="border rounded-4 p-3 h-100">
              <h6 className="text-muted mb-1">Daily Average</h6>
              <strong>{weeklyAverage} min/day</strong>
            </div>
          </div>

          <div className="col-md-4">
            <div className="border rounded-4 p-3 h-100">
              <h6 className="text-muted mb-1">Target</h6>
              <strong>{WEEKLY_FOCUS_TARGET_MINUTES} min</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const RecentExamAttempts = ({ recentResults }) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Recent Exam Attempts</h5>

          <Link className="btn btn-sm btn-outline-primary" to="/student/results">
            View all
          </Link>
        </div>

        {recentResults.length === 0 ? (
          <p className="text-muted mb-0">
            No exam attempts yet. Start your first mock exam.
          </p>
        ) : (
          <div className="table-responsive">
            <table className="table align-middle mb-0">
              <thead>
                <tr>
                  <th>Exam</th>
                  <th>Score</th>
                  <th>Date</th>
                  <th className="text-end">Action</th>
                </tr>
              </thead>

              <tbody>
                {recentResults.map((result) => {
                  const attemptId = result.attempt_id || result.id;

                  return (
                    <tr key={attemptId}>
                      <td>
                        {result.exam_title ||
                          result.mock_exam_title ||
                          result.title ||
                          "Mock Exam"}
                      </td>

                      <td>
                        <span className="badge bg-primary">
                          {formatScore(result.score)}
                        </span>
                      </td>

                      <td className="text-muted small">
                        {formatDate(result.submitted_at || result.started_at)}
                      </td>

                      <td className="text-end">
                        <Link
                          className="btn btn-sm btn-outline-primary"
                          to={`/student/results/${attemptId}`}
                        >
                          Review
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const RecentStudyMaterials = ({ recentMaterials }) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Recent Study Materials</h5>

          <Link className="btn btn-sm btn-outline-primary" to="/student/materials">
            View all
          </Link>
        </div>

        {recentMaterials.length === 0 ? (
          <p className="text-muted mb-0">
            No materials uploaded yet. Upload your first PDF or DOCX.
          </p>
        ) : (
          <div className="d-grid gap-3">
            {recentMaterials.map((material) => (
              <div key={material.id} className="dashboard-list-item">
                <div>
                  <strong>{material.title || "Untitled Material"}</strong>

                  <p className="small text-muted mb-0">
                    {(material.file_type || "file").toUpperCase()} material
                  </p>
                </div>

                <div className="d-flex gap-2 align-items-center">
                  <span
                    className={`badge ${getMaterialStatusBadge(
                      material.processing_status
                    )}`}
                  >
                    {material.processing_status || "unknown"}
                  </span>

                  <Link
                    className="btn btn-sm btn-outline-primary"
                    to={`/student/materials/${material.id}`}
                  >
                    Open
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const RecentFocusSessions = ({ recentSessions }) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Recent Focus Sessions</h5>

          <Link className="btn btn-sm btn-outline-primary" to="/student/focus">
            Open focus
          </Link>
        </div>

        {recentSessions.length === 0 ? (
          <p className="text-muted mb-0">No completed focus sessions yet.</p>
        ) : (
          <div className="d-grid gap-3">
            {recentSessions.map((session) => (
              <div key={session.id} className="dashboard-list-item">
                <div>
                  <strong>
                    {session.topic || session.course || "General Study"}
                  </strong>

                  <p className="small text-muted mb-0">
                    {formatDate(session.started_at, true)}
                  </p>
                </div>

                <span className="badge bg-success">
                  {session.duration_minutes || 0} min
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const AdvancedWeakTopicsCard = ({ weakTopics, weakDomains = [] }) => {
  const [expandedDomains, setExpandedDomains] = useState({});

  const toggleDomain = (domainId) => {
    setExpandedDomains((prev) => ({
      ...prev,
      [domainId]: !prev[domainId],
    }));
  };

  const domainGroups = weakDomains.length > 0 ? weakDomains : Object.values(
    (weakTopics || []).reduce((acc, topic) => {
      const dName = topic.domain || "General Domain";
      if (!acc[dName]) {
        acc[dName] = {
          id: dName,
          name: dName,
          accuracy: topic.accuracy,
          topics: [],
        };
      }
      acc[dName].topics.push(topic);
      return acc;
    }, {})
  );

  const getStatusBadge = (status, accuracy) => {
    if (status === "not_attempted" || accuracy === null || accuracy === undefined) {
      return <span className="badge bg-secondary">Not Attempted</span>;
    }
    if (status === "weak" || accuracy < 60) {
      return <span className="badge bg-danger">Weak ({accuracy}%)</span>;
    }
    return <span className="badge bg-success">Strong ({accuracy}%)</span>;
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Weak Topics & Domain Drill-down</h5>
          <span className="badge bg-secondary">{domainGroups.length} Domains</span>
        </div>

        {domainGroups.length === 0 ? (
          <p className="text-muted mb-0">No weak domains or topics detected.</p>
        ) : (
          <div className="d-grid gap-3">
            {domainGroups.map((domain, index) => {
              const domainId = domain.id || domain.name || index;
              const isExpanded = Boolean(expandedDomains[domainId]);
              const topics = domain.topics || [];

              return (
                <div key={domainId} className="border rounded-3 p-3 bg-light">
                  <div
                    className="d-flex justify-content-between align-items-center"
                    style={{ cursor: "pointer" }}
                    onClick={() => toggleDomain(domainId)}
                  >
                    <div>
                      <strong className="fs-6 me-2">📂 {domain.name || domain.domain}</strong>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                      <span className="badge bg-danger">{domain.accuracy || 0}% avg</span>
                      <button className="btn btn-sm btn-outline-dark py-0 px-2 fw-bold">
                        {isExpanded ? "▲ Collapse" : "▼ Expand Topics"}
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-3 pt-2 border-top">
                      <p className="small text-muted mb-2 fw-bold">Domain Topics & Accuracy Breakdown:</p>
                      <div className="d-grid gap-2">
                        {topics.map((t, tIdx) => (
                          <div
                            key={t.topic_id || t.id || tIdx}
                            className="bg-white p-2 rounded border d-flex justify-content-between align-items-center"
                          >
                            <span className="fw-semibold small">📌 {t.topic || t.name}</span>
                            <div className="d-flex align-items-center gap-2">
                              {getStatusBadge(t.status, t.accuracy)}
                              {t.total_attempts !== undefined && (
                                <span className="small text-muted">({t.total_attempts} attempt{t.total_attempts === 1 ? "" : "s"})</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

const RecommendationsCard = ({ recommendations }) => {
  const getPriorityBadge = (priority) => {
    if (priority === "high") return <span className="badge bg-danger">high</span>;
    if (priority === "medium") return <span className="badge bg-warning text-dark">medium</span>;
    return <span className="badge bg-secondary">low</span>;
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <h5 className="fw-bold">Enhanced Recommendations</h5>

        {recommendations.length === 0 ? (
          <p className="text-muted mb-0">
            Recommendations appear after weak topics are detected.
          </p>
        ) : (
          <div className="d-grid gap-3">
            {recommendations.map((item, idx) => {
              const sequence = item.study_sequence || [
                "Read AI Summary",
                "Practice Flashcards",
                "Take Quiz",
                "Retry Mock Exam"
              ];

              return (
                <div key={item.topic_id || item.topic || idx} className="recommendation-panel p-3 border rounded-3 bg-white">
                  <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
                    <div className="d-flex align-items-center gap-2">
                      <strong className="fs-6">{item.topic}</strong>
                      {getPriorityBadge(item.priority)}
                    </div>

                    <span className="badge bg-warning text-dark">{item.accuracy}%</span>
                  </div>

                  {item.weakest_subtopic && (
                    <div className="small text-muted mb-2">
                      <strong>Weakest Subtopic:</strong> {item.weakest_subtopic}
                    </div>
                  )}

                  <div className="mb-3 p-2 bg-light rounded border">
                    <div className="small fw-bold text-primary mb-1">Study Sequence:</div>
                    <ol className="mb-0 ps-3 small text-muted">
                      {sequence.map((step) => (
                        <li key={step} className="mb-1">
                          <span className="fw-semibold text-dark">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div className="d-flex gap-2 flex-wrap">
                    {(item.recommendations || []).map((action) => (
                      <span key={action} className="recommendation-chip">
                        {action}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

const TrendChart = ({ trendData }) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="fw-bold mb-0">Topic Accuracy Trend</h5>
          <span className="small text-muted">Last 3 mock attempts</span>
        </div>

        {trendData.length === 0 ? (
          <p className="text-muted mb-0">
            Trend data appears after exam attempts.
          </p>
        ) : (
          <div>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="topic"
                  fontSize={12}
                  tick={({ x, y, payload }) => {
                    const item = trendData.find((t) => t.topic === payload.value);
                    const arrow = item?.trend_arrow || "—";
                    return (
                      <text x={x} y={y + 12} textAnchor="middle" fill="#666" fontSize={11}>
                        {payload.value} {arrow}
                      </text>
                    );
                  }}
                />
                <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
                <Tooltip
                  formatter={(value, name, props) => [
                    `${value}% (${props.payload.improvement_label || "First attempt"})`,
                    "Accuracy",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#2563eb"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>

            <div className="mt-3 pt-3 border-top">
              <div className="small fw-bold mb-2 text-muted">Topic Performance & Improvement:</div>
              <div className="d-flex gap-2 flex-wrap">
                {trendData.map((item, idx) => {
                  const arrow = item.trend_arrow || "—";
                  const label = item.improvement_label || "First attempt";

                  let badgeClass = "bg-secondary text-white";
                  if (item.trend_direction === "improving") badgeClass = "bg-success text-white";
                  if (item.trend_direction === "declining") badgeClass = "bg-danger text-white";

                  return (
                    <span key={item.topic_id || item.topic || idx} className={`badge p-2 ${badgeClass}`}>
                      {item.topic}: {item.accuracy}% {arrow} ({label})
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const WeakTopicsCard = ({ weakTopics }) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <h5 className="fw-bold">Weak Topics</h5>

        {weakTopics.length === 0 ? (
          <p className="text-muted mb-0">No weak topics yet.</p>
        ) : (
          <ul className="list-group list-group-flush">
            {weakTopics.map((item) => (
              <li key={item.topic_id || item.id} className="list-group-item px-0">
                <strong>{item.topic}</strong>
                <span className="text-muted"> — {item.accuracy}%</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

const SpacedRepetitionCard = ({ dueItems }) => {
  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      <div className="card-body p-4">
        <h5 className="fw-bold">Spaced Repetition Due</h5>

        {dueItems.length === 0 ? (
          <p className="text-muted mb-0">No review due today.</p>
        ) : (
          <ul className="list-group list-group-flush">
            {dueItems.map((item) => (
              <li key={item.id} className="list-group-item px-0">
                {item.question}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

const AdaptiveLearningCard = ({ path }) => {
  const getPriorityBadge = (priority) => {
    if (priority === "high") return <span className="badge bg-danger">High Priority</span>;
    if (priority === "medium") return <span className="badge bg-warning text-dark">Medium Priority</span>;
    return <span className="badge bg-secondary">Low Priority</span>;
  };

  const steps = path?.steps || [];
  const completedCount = steps.filter((s) => s.completed).length;
  const progressPercent = Math.round((completedCount / 4) * 100);

  return (
    <div className="card border-0 shadow-sm rounded-4 h-100 bg-white">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
          <div>
            <span className="dashboard-badge mb-1">Adaptive Learning Engine</span>
            <h4 className="fw-bold mt-1 mb-1">
              {path ? `Topic: ${path.topic}` : "Today's Learning Path"}
            </h4>
            <p className="text-muted small mb-0">
              {path
                ? `Current step: ${path.current_step?.replace("_", " ")?.toUpperCase()}`
                : "Ties summary, flashcards, quiz, mini-mock & spaced repetition into one journey."}
            </p>
          </div>
          {path && getPriorityBadge(path.priority)}
        </div>

        {path ? (
          <div>
            <div className="d-flex justify-content-between align-items-center mb-2">
              <span className="small fw-semibold text-muted">
                Step Progress ({completedCount} of 4 completed)
              </span>
              <span className="fw-bold text-primary">{progressPercent}%</span>
            </div>
            <div className="progress mb-3" style={{ height: "10px" }}>
              <div
                className="progress-bar bg-primary progress-bar-striped progress-bar-animated"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            <div className="d-flex gap-1 mb-3">
              {["summary", "flashcards", "quiz", "mini_mock"].map((st) => {
                const sObj = steps.find((s) => s.step_type === st);
                let bgClass = "bg-secondary text-white";
                if (sObj?.completed) bgClass = "bg-success text-white";
                else if (path.current_step === st) bgClass = "bg-primary text-white";

                return (
                  <div
                    key={st}
                    className={`flex-fill text-center py-1 rounded small fw-semibold ${bgClass}`}
                    style={{ fontSize: "11px" }}
                  >
                    {st.replace("_", " ")}
                  </div>
                );
              })}
            </div>

            <Link className="btn btn-primary w-100 fw-bold rounded-3" to="/student/learning">
              Continue Learning →
            </Link>
          </div>
        ) : (
          <div>
            <p className="text-muted small mb-3">
              No active learning path in progress. Click below to automatically generate your next highest-priority topic journey based on your weakest areas and spaced repetition queue.
            </p>
            <Link className="btn btn-primary w-100 fw-bold rounded-3" to="/student/learning">
              Start Learning Path →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default StudentDashboard;
