import { useEffect, useState, useCallback, useMemo } from "react";
import api from "../api/api";
import { useAuth } from "../auth/AuthContext";

const TeacherAssignments = () => {
  const { user } = useAuth();
  const [teachers, setTeachers] = useState([]);
  const [topics, setTopics] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [selectedTeacherId, setSelectedTeacherId] = useState("");
  const [filterTeacher, setFilterTeacher] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [pendingState, setPendingState] = useState({});

  const loadMetaData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [teacherRes, topicRes] = await Promise.all([
        api.get("/admin/teachers/"),
        api.get("/exit-exams/topics/"),
      ]);

      setTeachers(teacherRes.data);
      setTopics(topicRes.data);
    } catch {
      setError("Failed to load assignment data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMetaData();
  }, [loadMetaData]);

  const fetchAssignments = useCallback(async (teacherId) => {
    if (!teacherId) {
      setAssignments([]);
      setPendingState({});
      setDirty(false);
      return;
    }
    setError("");
    try {
      const res = await api.get(
        `/exit-exams/teacher-topic-assignments/?teacher_id=${teacherId}`
      );
      setAssignments(res.data);
      const stateMap = {};
      res.data.forEach((a) => {
        if (a.active) stateMap[a.topic] = a.id;
      });
      setPendingState(stateMap);
      setDirty(false);
    } catch {
      setError("Failed to load this teacher's current topic assignments.");
    }
  }, []);

  const handleTeacherChange = (e) => {
    const value = e.target.value;
    setSelectedTeacherId(value);
    setSuccess("");
    fetchAssignments(value);
  };

  const toggleTopic = (topicId) => {
    setPendingState((prev) => {
      const next = { ...prev };
      if (next[topicId]) {
        delete next[topicId];
      } else {
        next[topicId] = "new";
      }
      return next;
    });
    setDirty(true);
  };

  // Group topics under their domain.
  const topicsByDomain = useMemo(() => {
    const groups = {};
    topics.forEach((t) => {
      const domainName = t.domain_name || "(Uncategorised)";
      if (!groups[domainName]) {
        groups[domainName] = { domainName, topics: [] };
      }
      groups[domainName].topics.push(t);
    });
    return Object.values(groups).sort((a, b) =>
      a.domainName.localeCompare(b.domainName)
    );
  }, [topics]);

  const selectedTeacher = useMemo(
    () => teachers.find((t) => String(t.id) === String(selectedTeacherId)),
    [teachers, selectedTeacherId]
  );

  const currentAssignedCount = useMemo(
    () => assignments.filter((a) => a.active).length,
    [assignments]
  );

  const pendingAssignedCount = useMemo(
    () => Object.keys(pendingState).length,
    [pendingState]
  );

  const lastUpdated = useMemo(() => {
    if (!assignments.length) return "—";
    const ts = assignments
      .map((a) => new Date(a.assigned_at).getTime())
      .filter(Boolean)
      .sort();
    if (!ts.length) return "—";
    return new Date(ts[ts.length - 1]).toLocaleString();
  }, [assignments]);

  const saveAssignment = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!selectedTeacherId) {
      setError("Please select a teacher first.");
      return;
    }

    setSaving(true);
    const teacherId = Number(selectedTeacherId);
    const errors = [];

    // 1) Remove unchecked topics that previously had an active assignment.
    for (const a of assignments) {
      if (a.active && !pendingState[a.topic]) {
        try {
          await api.delete(`/exit-exams/teacher-topic-assignments/${a.id}/`);
        } catch (err) {
          errors.push(
            err.response?.data?.detail ||
              `Failed to remove assignment for topic #${a.topic}.`
          );
        }
      }
    }

    // 2) Create assignments for newly-checked topics.
    for (const topicIdStr of Object.keys(pendingState)) {
      const topicId = Number(topicIdStr);
      if (pendingState[topicIdStr] === "new") {
        try {
          await api.post("/exit-exams/teacher-topic-assignments/", {
            teacher: teacherId,
            topic: topicId,
            active: true,
          });
        } catch (err) {
          errors.push(
            err.response?.data?.detail ||
              err.response?.data?.non_field_errors?.[0] ||
              `Failed to assign topic #${topicId}.`
          );
        }
      }
    }

    setSaving(false);
    setDirty(false);

    if (errors.length) {
      setError(errors.join(" "));
    } else {
      setSuccess("Topic assignments saved successfully.");
      await fetchAssignments(selectedTeacherId);
    }
  };

  const filteredTeachers = filterTeacher
    ? teachers.filter((t) =>
        t.username.toLowerCase().includes(filterTeacher.toLowerCase())
      )
    : teachers;

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  return (
    <div className="container-fluid py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Department Head</span>
          <h2 className="fw-bold mt-2 mb-1">Teacher Assignments</h2>
          <p className="text-muted mb-0">
            Assign teachers to the specific topics they are responsible for,
            grouped by domain.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger alert-dismissible">
          {error}
          <button className="btn-close" onClick={() => setError("")} />
        </div>
      )}
      {success && (
        <div className="alert alert-success alert-dismissible">
          {success}
          <button className="btn-close" onClick={() => setSuccess("")} />
        </div>
      )}

      <div className="row g-4">
        {/* Assign Form */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 mb-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">New Assignment</h5>
              <form onSubmit={saveAssignment}>
                <div className="mb-3">
                  <label className="form-label fw-semibold">Teacher</label>
                  <select
                    className="form-select"
                    value={selectedTeacherId}
                    onChange={handleTeacherChange}
                    required
                  >
                    <option value="">Select a teacher...</option>
                    {filteredTeachers
                      .filter((t) => t.is_active)
                      .map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.username}
                          {t.email ? ` (${t.email})` : ""}
                        </option>
                      ))}
                  </select>
                  <small className="form-text text-muted">
                    {teachers.length === 0 &&
                      "No teachers found in your department."}
                  </small>
                </div>

                <div className="mb-3">
                  <input
                    className="form-control form-control-sm"
                    placeholder="Search teacher by username..."
                    value={filterTeacher}
                    onChange={(e) => setFilterTeacher(e.target.value)}
                  />
                </div>

                <div className="mb-3 d-flex justify-content-between align-items-center">
                  <span className="text-muted small">
                    Topics assigned:{" "}
                    <strong>
                      {selectedTeacherId ? pendingAssignedCount : 0}
                    </strong>
                  </span>
                  {dirty && (
                    <span className="badge bg-warning text-dark">
                      Unsaved changes
                    </span>
                  )}
                </div>

                <button
                  className="btn btn-primary w-100"
                  disabled={!selectedTeacherId || saving || !dirty}
                >
                  {saving ? "Saving..." : "Save Assignment"}
                </button>
              </form>
            </div>
          </div>

          {/* Summary Card */}
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">
                {selectedTeacher ? selectedTeacher.username : "Teacher summary"}
              </h5>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Department</span>
                <strong>
                  {selectedTeacher?.department_name ||
                    selectedTeacher?.department ||
                    user?.department_name ||
                    "—"}
                </strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Assigned topics</span>
                <strong>{currentAssignedCount}</strong>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted">Last updated</span>
                <strong>{lastUpdated}</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Topic Checklist */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="fw-bold mb-0">
                  {selectedTeacher
                    ? `Assigned Topics — ${selectedTeacher.username}`
                    : "Assigned Topics"}
                </h5>
                <span className="text-muted small">
                  Check the topics this teacher is responsible for.
                </span>
              </div>

              {!selectedTeacherId ? (
                <p className="text-muted text-center py-4">
                  Select a teacher to manage their topic assignments.
                </p>
              ) : topicsByDomain.length === 0 ? (
                <p className="text-muted text-center py-4">
                  No topics found in your department.
                </p>
              ) : (
                <div className="d-grid gap-4">
                  {topicsByDomain.map((group) => (
                    <div key={group.domainName}>
                      <div className="d-flex align-items-center gap-2 mb-2">
                        <div className="rounded-circle bg-secondary bg-opacity-25 text-dark d-flex align-items-center justify-content-center fw-bold"
                          style={{ width: 32, height: 32, fontSize: "0.8rem" }}
                        >
                          {group.domainName.charAt(0).toUpperCase()}
                        </div>
                        <h6 className="fw-bold mb-0">{group.domainName}</h6>
                      </div>

                      <div className="d-grid gap-2 ps-4">
                        {group.topics.map((t) => {
                          const checked = Boolean(pendingState[t.id]);
                          return (
                            <label
                              key={t.id}
                              className="d-flex align-items-center gap-2 blueprint-rule-row"
                            >
                              <input
                                type="checkbox"
                                className="form-check-input"
                                checked={checked}
                                onChange={() => toggleTopic(t.id)}
                              />
                              <span className="fw-semibold small">{t.name}</span>
                            </label>
                          );
                        })}
                      </div>
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

export default TeacherAssignments;