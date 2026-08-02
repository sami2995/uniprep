import { useEffect, useState } from "react";
import api from "../api/api";
import { Settings, Save, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";

const SystemSettingsPage = () => {
  const [settings, setSettings] = useState({
    default_passing_score: 50,
    default_exam_duration_minutes: 60,
    max_battle_participants: 8,
    mastery_threshold_accuracy: 80,
    mastery_minimum_attempts: 3,
    quiz_unlock_score: 70,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/admin/settings/");
      setSettings({
        default_passing_score: response.data.default_passing_score,
        default_exam_duration_minutes: response.data.default_exam_duration_minutes,
        max_battle_participants: response.data.max_battle_participants,
        mastery_threshold_accuracy: response.data.mastery_threshold_accuracy ?? 80,
        mastery_minimum_attempts: response.data.mastery_minimum_attempts ?? 3,
        quiz_unlock_score: response.data.quiz_unlock_score ?? 70,
      });
      setUpdatedAt(response.data.updated_at);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load system settings.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const response = await api.patch("/admin/settings/", {
        default_passing_score: Number(settings.default_passing_score),
        default_exam_duration_minutes: Number(settings.default_exam_duration_minutes),
        max_battle_participants: Number(settings.max_battle_participants),
        mastery_threshold_accuracy: Number(settings.mastery_threshold_accuracy),
        mastery_minimum_attempts: Number(settings.mastery_minimum_attempts),
        quiz_unlock_score: Number(settings.quiz_unlock_score),
      });

      setSettings({
        default_passing_score: response.data.default_passing_score,
        default_exam_duration_minutes: response.data.default_exam_duration_minutes,
        max_battle_participants: response.data.max_battle_participants,
        mastery_threshold_accuracy: response.data.mastery_threshold_accuracy ?? 80,
        mastery_minimum_attempts: response.data.mastery_minimum_attempts ?? 3,
        quiz_unlock_score: response.data.quiz_unlock_score ?? 70,
      });
      setUpdatedAt(response.data.updated_at);
      setSuccess("System settings updated successfully.");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save system settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">System Admin</span>
          <h2 className="fw-bold mt-2 mb-1">System Settings</h2>
          <p className="text-muted mb-0">
            Configure platform-wide default thresholds, exam rules, and battle parameters.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {success && (
        <div className="alert alert-success d-flex align-items-center gap-2 mb-4">
          <CheckCircle size={18} />
          <div>{success}</div>
        </div>
      )}

      <div className="row g-4">
        <div className="col-lg-8 col-xl-6">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-header bg-transparent border-0 pt-4 px-4 pb-0">
              <div className="d-flex align-items-center gap-2 text-primary fw-bold">
                <Settings size={20} />
                <span>Global Configuration</span>
              </div>
            </div>

            <div className="card-body p-4">
              {loading ? (
                <div className="text-center py-4">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  <p className="small text-muted mt-2">Loading configuration...</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit}>
                  <div className="mb-4">
                    <label className="form-label fw-medium">Default Passing Score (%)</label>
                    <input
                      type="number"
                      className="form-control form-control-lg rounded-3"
                      min="1"
                      max="100"
                      value={settings.default_passing_score}
                      onChange={(e) =>
                        setSettings({ ...settings, default_passing_score: e.target.value })
                      }
                      required
                    />
                    <small className="form-text text-muted">
                      Fallback threshold used when a course has no active blueprint pass mark set.
                    </small>
                  </div>

                  <div className="mb-4">
                    <label className="form-label fw-medium">Default Exam Duration (Minutes)</label>
                    <input
                      type="number"
                      className="form-control form-control-lg rounded-3"
                      min="1"
                      max="600"
                      value={settings.default_exam_duration_minutes}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          default_exam_duration_minutes: e.target.value,
                        })
                      }
                      required
                    />
                    <small className="form-text text-muted">
                      Default time allocated for mock exams generated without specific duration rules.
                    </small>
                  </div>

                  <div className="mb-4">
                    <label className="form-label fw-medium">Max Battle Participants</label>
                    <input
                      type="number"
                      className="form-control form-control-lg rounded-3"
                      min="2"
                      max="64"
                      value={settings.max_battle_participants}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          max_battle_participants: e.target.value,
                        })
                      }
                      required
                    />
                    <small className="form-text text-muted">
                      Maximum number of student participants allowed in a multi-player battle room.
                    </small>
                  </div>

                  <hr className="my-4" />
                  <h6 className="fw-bold text-primary mb-3">Adaptive Learning Engine Thresholds</h6>

                  <div className="mb-4">
                    <label className="form-label fw-medium">Mastery Threshold Accuracy (%)</label>
                    <input
                      type="number"
                      className="form-control form-control-lg rounded-3"
                      min="1"
                      max="100"
                      value={settings.mastery_threshold_accuracy}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          mastery_threshold_accuracy: e.target.value,
                        })
                      }
                      required
                    />
                    <small className="form-text text-muted">
                      Minimum accuracy required to consider a topic mastered in adaptive topic selection.
                    </small>
                  </div>

                  <div className="mb-4">
                    <label className="form-label fw-medium">Mastery Minimum Attempts</label>
                    <input
                      type="number"
                      className="form-control form-control-lg rounded-3"
                      min="1"
                      max="50"
                      value={settings.mastery_minimum_attempts}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          mastery_minimum_attempts: e.target.value,
                        })
                      }
                      required
                    />
                    <small className="form-text text-muted">
                      Minimum number of total question attempts required before mastery accuracy threshold is applied.
                    </small>
                  </div>

                  <div className="mb-4">
                    <label className="form-label fw-medium">Quiz Unlock Score (%)</label>
                    <input
                      type="number"
                      className="form-control form-control-lg rounded-3"
                      min="1"
                      max="100"
                      value={settings.quiz_unlock_score}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          quiz_unlock_score: e.target.value,
                        })
                      }
                      required
                    />
                    <small className="form-text text-muted">
                      Score needed on the Quiz step of a learning path to unlock the Mini Mock step.
                    </small>
                  </div>

                  {updatedAt && (
                    <p className="small text-muted mb-4">
                      Last updated: {new Date(updatedAt).toLocaleString()}
                    </p>
                  )}

                  <div className="d-flex align-items-center gap-3">
                    <button
                      type="submit"
                      className="btn btn-primary btn-lg rounded-3 px-4 d-flex align-items-center gap-2"
                      disabled={saving}
                    >
                      {saving ? (
                        <>
                          <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save size={18} />
                          Save Settings
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-lg rounded-3"
                      onClick={fetchSettings}
                      disabled={saving || loading}
                    >
                      <RefreshCw size={18} />
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-4 col-xl-6">
          <div className="card border-0 shadow-sm rounded-4 bg-light">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">System Settings Info</h5>
              <ul className="text-muted small mb-0 d-grid gap-2">
                <li>
                  <strong>Passing Score:</strong> Overridden on a per-course basis if an active Exam Blueprint specifies a <code>pass_percentage</code>.
                </li>
                <li>
                  <strong>Exam Duration:</strong> Applied during automatic mock exam generation unless overridden by custom exam settings.
                </li>
                <li>
                  <strong>Battle Participants:</strong> Enforced by live multiplayer room logic.
                </li>
                <li>
                  <strong>Audit Logging:</strong> All settings updates are logged to the central Audit Log with your admin identity.
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemSettingsPage;
