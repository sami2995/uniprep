import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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

  const [recentResults, setRecentResults] = useState([]);
  const [recentMaterials, setRecentMaterials] = useState([]);
  const [recentSessions, setRecentSessions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [dailyGoal, setDailyGoal] = useState(getDailyGoalMinutes());
  const [goalInput, setGoalInput] = useState(getDailyGoalMinutes());
  const [streak, setStreak] = useState(getStudyStreak());

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError("");

      const [dashboardRes, resultsRes, materialsRes, focusRes] =
        await Promise.all([
          api.get("/analytics/dashboard/"),
          api.get("/exit-exams/my-results/"),
          api.get("/rag/materials/"),
          api.get("/analytics/focus/summary/"),
        ]);

      const dashboardData = dashboardRes.data;
      const focusData = focusRes.data || {};

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
        <div className="col-md-6">
          <WeakTopicsCard weakTopics={dashboard?.weak_topics || []} />
        </div>

        <div className="col-md-6">
          <SpacedRepetitionCard
            dueItems={dashboard?.spaced_repetition_due || []}
          />
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

export default StudentDashboard;