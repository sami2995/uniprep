import { useEffect, useState } from "react";
import api from "../api/api";

const StudentFocus = () => {
  const [summary, setSummary] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(
    localStorage.getItem("active_focus_session_id") || null
  );

  const [startedAt, setStartedAt] = useState(
    localStorage.getItem("active_focus_started_at") || null
  );

  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [sessionType, setSessionType] = useState("study");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchSummary();
  }, []);

  useEffect(() => {
    if (!startedAt) return;

    const timer = setInterval(() => {
      const startTime = new Date(startedAt).getTime();
      const now = Date.now();

      setElapsedSeconds(Math.floor((now - startTime) / 1000));
    }, 1000);

    return () => clearInterval(timer);
  }, [startedAt]);

  const fetchSummary = async () => {
    try {
      const response = await api.get("/analytics/focus/summary/");
      setSummary(response.data);

      if (response.data.active_session) {
        const { id, started_at: startTime } = response.data.active_session;
        setActiveSessionId(id);
        setStartedAt(startTime);
        localStorage.setItem("active_focus_session_id", id);
        localStorage.setItem("active_focus_started_at", startTime);
      } else {
        clearActiveFocus();
      }
    } catch (err) {
      setError("Failed to load focus summary.");
    }
  };

  const clearActiveFocus = () => {
    setActiveSessionId(null);
    setStartedAt(null);
    setElapsedSeconds(0);

    localStorage.removeItem("active_focus_session_id");
    localStorage.removeItem("active_focus_started_at");
  };

  const startFocus = async () => {
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      const response = await api.post("/analytics/focus/start/", {
        session_type: sessionType,
      });

      const sessionId =
        response.data.session_id ||
        response.data.id ||
        response.data.focus_session?.id;

      const startTime =
        response.data.started_at ||
        response.data.start_time ||
        new Date().toISOString();

      if (!sessionId) {
        setError("Focus session started, but session ID was not returned.");
        return;
      }

      setActiveSessionId(sessionId);
      setStartedAt(startTime);
      setElapsedSeconds(0);

      localStorage.setItem("active_focus_session_id", sessionId);
      localStorage.setItem("active_focus_started_at", startTime);

      setSuccess("Focus session started.");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start focus session.");
    } finally {
      setLoading(false);
    }
  };

  const endFocus = async () => {
    setError("");
    setSuccess("");

    if (!activeSessionId) {
      setError("No active focus session found.");
      return;
    }

    const confirmed = window.confirm("End current focus session?");
    if (!confirmed) return;

    setLoading(true);

    try {
      await api.post("/analytics/focus/end/", {
        session_id: Number(activeSessionId),
      });

      clearActiveFocus();

      setSuccess("Focus session ended successfully.");
      await fetchSummary();
    } catch (err) {
      if (err.response?.status === 404) {
        clearActiveFocus();
        setSuccess("The previous focus session was already ended. Timer reset.");
        await fetchSummary();
      } else {
        setError(err.response?.data?.detail || "Failed to end focus session.");
      }
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    return `${hrs.toString().padStart(2, "0")}:${mins
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const todayMinutes =
    summary?.today_minutes ||
    summary?.total_today_minutes ||
    summary?.today_focus_minutes ||
    0;

  const weekMinutes =
    summary?.week_minutes ||
    summary?.total_week_minutes ||
    summary?.weekly_focus_minutes ||
    0;

  const totalSessions =
    summary?.total_sessions ||
    summary?.session_count ||
    summary?.sessions_completed ||
    0;

  const averageSessionMinutes =
    summary?.recent_sessions?.length > 0
      ? Math.round(
          summary.recent_sessions.reduce(
            (total, session) => total + Number(session.duration_minutes || 0),
            0
          ) / summary.recent_sessions.length
        )
      : 0;

  const weeklyHours = (weekMinutes / 60).toFixed(1);

  const weeklyMessage =
    weekMinutes >= 600
      ? "Excellent work. You reached a strong weekly study target."
      : weekMinutes >= 300
      ? "Good progress. Keep building consistency this week."
      : weekMinutes > 0
      ? "You started studying this week. Try to add more focus sessions."
      : "No study time recorded this week yet.";

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-2">Focus Timer</h2>
      <p className="text-muted">
        Track your study time and build consistent preparation habits.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-5 text-center">
              <span
                className={`badge ${
                  activeSessionId ? "bg-success" : "bg-secondary"
                } mb-3`}
              >
                {activeSessionId ? "Focus Active" : "No Active Session"}
              </span>

              <h1 className="focus-timer-display">
                {formatTime(elapsedSeconds)}
              </h1>

              <p className="text-muted">
                {activeSessionId
                  ? "Stay focused. Your study session is being tracked."
                  : "Start a new focus session when you begin studying."}
              </p>

              {!activeSessionId && (
                <div className="mb-4">
                  <label className="form-label fw-semibold">
                    Session Type
                  </label>

                  <select
                    className="form-select focus-session-select mx-auto"
                    value={sessionType}
                    onChange={(e) => setSessionType(e.target.value)}
                  >
                    <option value="study">Study</option>
                    <option value="exam_practice">Exam Practice</option>
                    <option value="revision">Revision</option>
                    <option value="reading">Reading</option>
                  </select>
                </div>
              )}

              <div className="d-flex justify-content-center gap-3 flex-wrap">
                {!activeSessionId ? (
                  <button
                    className="btn btn-primary btn-lg px-5"
                    onClick={startFocus}
                    disabled={loading}
                  >
                    {loading ? "Starting..." : "Start Focus"}
                  </button>
                ) : (
                  <button
                    className="btn btn-danger btn-lg px-5"
                    onClick={endFocus}
                    disabled={loading}
                  >
                    {loading ? "Ending..." : "End Focus"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-4">Your Progress</h5>

              <div className="row g-3 text-center">
                <div className="col-4">
                  <div className="focus-stat-block">
                    <h3 className="fw-bold mb-0 text-primary">
                      {todayMinutes}
                    </h3>
                    <small className="text-muted d-block">min today</small>
                  </div>
                </div>

                <div className="col-4">
                  <div className="focus-stat-block">
                    <h3 className="fw-bold mb-0 text-success">
                      {weekMinutes}
                    </h3>
                    <small className="text-muted d-block">min this week</small>
                  </div>
                </div>

                <div className="col-4">
                  <div className="focus-stat-block">
                    <h3 className="fw-bold mb-0 text-warning">
                      {totalSessions}
                    </h3>
                    <small className="text-muted d-block">sessions done</small>
                  </div>
                </div>
              </div>

              <hr className="my-4" />

              <div className="d-flex justify-content-between align-items-center">
                <span className="text-muted small">Weekly average</span>
                <strong className="text-dark">
                  {averageSessionMinutes} min/session
                </strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-4 mt-0">
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <h5 className="fw-bold">Productivity Tip</h5>
              <p className="text-muted mb-0">
                Use 25-50 minute focus blocks, then take a short break. This
                helps you stay consistent while preparing for exams.
              </p>
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <h5 className="fw-bold mb-3">Recent Study Sessions</h5>

              {summary?.recent_sessions?.length === 0 ? (
                <p className="text-muted mb-0">
                  No completed focus sessions yet.
                </p>
              ) : (
                <div className="d-grid gap-3">
                  {summary?.recent_sessions?.slice(0, 4).map((session) => (
                    <div key={session.id} className="focus-session-item">
                      <div>
                        <strong>
                          {session.topic || session.course || "General Study"}
                        </strong>

                        <p className="small text-muted mb-0">
                          {new Date(session.started_at).toLocaleString()}
                        </p>
                      </div>

                      <span className="badge bg-primary">
                        {session.duration_minutes} min
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100 weekly-report-card">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <div>
                  <h5 className="fw-bold mb-1">Weekly Report Card</h5>
                  <p className="text-muted small mb-0">
                    Your study summary for this week
                  </p>
                </div>

                <span className="badge bg-dark">{weeklyHours} hrs</span>
              </div>

              <div className="row g-2">
                <div className="col-6">
                  <div className="weekly-mini-stat">
                    <span>Total Focus</span>
                    <strong>{weekMinutes} min</strong>
                  </div>
                </div>

                <div className="col-6">
                  <div className="weekly-mini-stat">
                    <span>Avg Session</span>
                    <strong>{averageSessionMinutes} min</strong>
                  </div>
                </div>

                <div className="col-6">
                  <div className="weekly-mini-stat">
                    <span>Today</span>
                    <strong>{todayMinutes} min</strong>
                  </div>
                </div>

                <div className="col-6">
                  <div className="weekly-mini-stat">
                    <span>Sessions</span>
                    <strong>{totalSessions}</strong>
                  </div>
                </div>
              </div>

              <div className="alert alert-info mt-3 mb-0">
                {weeklyMessage}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentFocus;
