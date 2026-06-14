import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import api from "../api/api";
import { markStudyActivity } from "../utils/productivity";

const FOCUS_SECONDS = 25 * 60;
const BREAK_SECONDS = 5 * 60;

const FloatingPomodoro = () => {
  const { user } = useAuth();

  const [mode, setMode] = useState(
    localStorage.getItem("pomodoro_mode") || "focus"
  );

  const [remainingSeconds, setRemainingSeconds] = useState(() => {
    const saved = localStorage.getItem("pomodoro_remaining_seconds");
    return saved ? Number(saved) : FOCUS_SECONDS;
  });

  const [isRunning, setIsRunning] = useState(
    localStorage.getItem("pomodoro_running") === "true"
  );

  const [activeSessionId, setActiveSessionId] = useState(
    localStorage.getItem("active_focus_session_id") || null
  );

  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const isStudent = user?.role === "student";
  const [focusModeEnabled, setFocusModeEnabled] = useState(
    localStorage.getItem("focus_mode_enabled") === "true"
  );

  useEffect(() => {
    if (!isStudent || !isRunning) return;

    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          handleTimerComplete();
          return 0;
        }

        const nextValue = prev - 1;
        localStorage.setItem("pomodoro_remaining_seconds", nextValue);
        return nextValue;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isRunning, isStudent, mode, activeSessionId]);

  useEffect(() => {
    localStorage.setItem("pomodoro_mode", mode);
    localStorage.setItem("pomodoro_remaining_seconds", remainingSeconds);
    localStorage.setItem("pomodoro_running", isRunning);
  }, [mode, remainingSeconds, isRunning]);

  useEffect(() => {
    if (focusModeEnabled) {
      document.body.classList.add("focus-mode-enabled");
    } else {
      document.body.classList.remove("focus-mode-enabled");
    }

    localStorage.setItem("focus_mode_enabled", focusModeEnabled);
  }, [focusModeEnabled]);

  if (!isStudent) {
    return null;
  }

  const startBackendFocusSession = async () => {
    let response;

    try {
      response = await api.post("/analytics/focus/start/", {
        session_type: "pomodoro",
      });
    } catch (error) {
      if (
        error.response?.status === 400 &&
        error.response?.data?.session_id
      ) {
        response = error.response;
      } else {
        throw error;
      }
    }

    const sessionId =
      response.data.session_id ||
      response.data.id ||
      response.data.focus_session?.id;

    const startTime =
      response.data.started_at ||
      response.data.start_time ||
      new Date().toISOString();

    if (!sessionId) {
      throw new Error("Focus session ID was not returned.");
    }

    setActiveSessionId(sessionId);

    localStorage.setItem("active_focus_session_id", sessionId);
    localStorage.setItem("active_focus_started_at", startTime);

    return sessionId;
  };

  const endBackendFocusSession = async () => {
    const storedSessionId =
      activeSessionId || localStorage.getItem("active_focus_session_id");

    if (!storedSessionId) return;

    try {
      await api.post("/analytics/focus/end/", {
        session_id: Number(storedSessionId),
      });
      markStudyActivity();
    } catch (error) {
      if (error.response?.status !== 404) {
        throw error;
      }
    }

    setActiveSessionId(null);
    localStorage.removeItem("active_focus_session_id");
    localStorage.removeItem("active_focus_started_at");
  };

  const handleStartPause = async () => {
    if (isRunning) {
      setIsRunning(false);
      return;
    }

    setLoading(true);

    try {
      if (mode === "focus") {
        await startBackendFocusSession();
      }

      setIsRunning(true);
    } catch (error) {
      alert(
        error.response?.data?.detail ||
          error.message ||
          "Failed to start Pomodoro session."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    const confirmed = window.confirm(
      "Stop this Pomodoro session? Your focus time will be saved."
    );

    if (!confirmed) return;

    setLoading(true);

    try {
      if (mode === "focus" && activeSessionId) {
        await endBackendFocusSession();
      }

      resetPomodoro();
    } catch (error) {
      alert(error.response?.data?.detail || "Failed to stop session.");
    } finally {
      setLoading(false);
    }
  };

  const handleTimerComplete = async () => {
    setIsRunning(false);

    if (mode === "focus") {
      try {
        await endBackendFocusSession();
      } catch (error) {
        console.error("Failed to end focus session:", error);
      }

      setMode("break");
      setRemainingSeconds(BREAK_SECONDS);
      setIsRunning(true);
    } else {
      setMode("focus");
      setRemainingSeconds(FOCUS_SECONDS);
      setIsRunning(false);
    }
  };

  const resetPomodoro = () => {
    setMode("focus");
    setRemainingSeconds(FOCUS_SECONDS);
    setIsRunning(false);
    setActiveSessionId(null);

    localStorage.removeItem("active_focus_session_id");
    localStorage.removeItem("active_focus_started_at");

    localStorage.setItem("pomodoro_mode", "focus");
    localStorage.setItem("pomodoro_remaining_seconds", FOCUS_SECONDS);
    localStorage.setItem("pomodoro_running", "false");
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;

    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  };

  return (
    <div className="pomodoro-widget">
      {isOpen && (
        <div className="pomodoro-panel shadow-lg">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <div>
              <h6 className="fw-bold mb-0">Pomodoro Focus</h6>
              <small className="text-muted">
                {mode === "focus" ? "25 min focus" : "5 min break"}
              </small>
            </div>

            <button
              className="btn btn-sm btn-light"
              onClick={() => setIsOpen(false)}
              aria-label="Close Pomodoro panel"
            >
              &times;
            </button>
          </div>

          <div className="text-center my-3">
            <span
              className={`badge ${
                mode === "focus" ? "bg-primary" : "bg-success"
              } mb-2`}
            >
              {mode === "focus" ? "Focus Mode" : "Break Time"}
            </span>

            <h1 className="pomodoro-time">
              {formatTime(remainingSeconds)}
            </h1>

            <p className="small text-muted mb-0">
              {isRunning ? "Timer is running" : "Timer is paused"}
            </p>
          </div>

          <div className="form-check form-switch mb-3">
            <input
              className="form-check-input"
              type="checkbox"
              id="focusModeSwitch"
              checked={focusModeEnabled}
              onChange={(e) => setFocusModeEnabled(e.target.checked)}
            />

            <label className="form-check-label small" htmlFor="focusModeSwitch">
              Focus Mode
            </label>
          </div>

          <div className="d-flex gap-2">
            <button
              className="btn btn-primary flex-fill"
              onClick={handleStartPause}
              disabled={loading}
            >
              {loading ? "..." : isRunning ? "Pause" : "Start"}
            </button>

            <button
              className="btn btn-outline-danger flex-fill"
              onClick={handleStop}
              disabled={loading}
            >
              Stop
            </button>
          </div>
        </div>
      )}

      <button
        className={`pomodoro-floating-btn ${isRunning ? "running" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>Timer</span>
        <strong>{formatTime(remainingSeconds)}</strong>
      </button>
    </div>
  );
};

export default FloatingPomodoro;
