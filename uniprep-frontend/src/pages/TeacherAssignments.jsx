import { useEffect, useState } from "react";
import api from "../api/api";

const TeacherAssignments = () => {
  const [assignments, setAssignments] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [courses, setCourses] = useState([]);
  const [form, setForm] = useState({ teacher: "", course: "" });
  const [filterTeacher, setFilterTeacher] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [User] = await Promise.all([
        api.get("/users/"),
      ]);
      // users endpoint may not exist — use assignments list to derive teachers
    } catch { /* ignore */ }

    try {
      const [assignRes, courseRes] = await Promise.all([
        api.get("/exit-exams/teacher-course-assignments/"),
        api.get("/exit-exams/courses/"),
      ]);

      setAssignments(assignRes.data);
      setCourses(courseRes.data);

      // Derive teacher list from assignments
      const teacherMap = {};
      assignRes.data.forEach((a) => {
        if (a.teacher && a.teacher_username) {
          teacherMap[a.teacher] = a.teacher_username;
        }
      });
      setTeachers(Object.entries(teacherMap).map(([id, name]) => ({ id, name })));
    } catch {
      setError("Failed to load assignments.");
    } finally {
      setLoading(false);
    }
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const createAssignment = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.teacher || !form.course) {
      setError("Please select both a teacher and a course.");
      return;
    }

    try {
      await api.post("/exit-exams/teacher-course-assignments/", {
        teacher: Number(form.teacher),
        course: Number(form.course),
      });
      setSuccess("Teacher assigned to course successfully.");
      setForm({ teacher: "", course: "" });
      await loadData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.non_field_errors?.[0] ||
          "Failed to create assignment."
      );
    }
  };

  const deleteAssignment = async (id) => {
    if (!window.confirm("Remove this teacher assignment?")) return;
    setError("");
    setSuccess("");
    try {
      await api.delete(`/exit-exams/teacher-course-assignments/${id}/`);
      setSuccess("Assignment removed.");
      await loadData();
    } catch {
      setError("Failed to remove assignment.");
    }
  };

  // Group assignments by teacher for a nicer view
  const byTeacher = {};
  assignments.forEach((a) => {
    const tName = a.teacher_username || `Teacher #${a.teacher}`;
    if (!byTeacher[tName]) byTeacher[tName] = [];
    byTeacher[tName].push(a);
  });

  const filteredTeachers = filterTeacher
    ? Object.entries(byTeacher).filter(([name]) =>
        name.toLowerCase().includes(filterTeacher.toLowerCase())
      )
    : Object.entries(byTeacher);

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  return (
    <div className="container-fluid py-4">
      {/* Hero */}
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Department Head</span>
          <h2 className="fw-bold mt-2 mb-1">Teacher Assignments</h2>
          <p className="text-muted mb-0">
            Assign teachers to courses they can create questions for.
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
        {/* ── Assign Form ── */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 mb-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">New Assignment</h5>
              <form onSubmit={createAssignment}>
                <div className="mb-3">
                  <label className="form-label fw-semibold">Teacher ID</label>
                  <input
                    name="teacher"
                    className="form-control"
                    type="number"
                    value={form.teacher}
                    onChange={handleFormChange}
                    placeholder="Enter teacher user ID…"
                    required
                  />
                  <div className="form-text">
                    Enter the user ID of the teacher to assign.
                  </div>
                </div>

                <div className="mb-3">
                  <label className="form-label fw-semibold">Course</label>
                  <select
                    name="course"
                    className="form-select"
                    value={form.course}
                    onChange={handleFormChange}
                    required
                  >
                    <option value="">Select a course…</option>
                    {courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <button className="btn btn-primary w-100">Assign Teacher</button>
              </form>
            </div>
          </div>

          {/* Summary Card */}
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Summary</h5>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Total assignments</span>
                <strong>{assignments.length}</strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Unique teachers</span>
                <strong>{Object.keys(byTeacher).length}</strong>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted">Courses with assignments</span>
                <strong>
                  {new Set(assignments.map((a) => a.course)).size}
                </strong>
              </div>
            </div>
          </div>
        </div>

        {/* ── Assignment List ── */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="fw-bold mb-0">Current Assignments</h5>
                <input
                  className="form-control form-control-sm"
                  style={{ maxWidth: 220 }}
                  placeholder="Search teacher…"
                  value={filterTeacher}
                  onChange={(e) => setFilterTeacher(e.target.value)}
                />
              </div>

              {filteredTeachers.length === 0 ? (
                <p className="text-muted text-center py-4">No assignments found.</p>
              ) : (
                <div className="d-grid gap-4">
                  {filteredTeachers.map(([teacherName, teacherAssignments]) => (
                    <div key={teacherName}>
                      <div className="d-flex align-items-center gap-2 mb-2">
                        <div
                          className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center fw-bold"
                          style={{ width: 36, height: 36, fontSize: "0.9rem" }}
                        >
                          {teacherName.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="fw-bold mb-0">{teacherName}</p>
                          <p className="text-muted small mb-0">
                            {teacherAssignments.length} course(s) assigned
                          </p>
                        </div>
                      </div>

                      <div className="d-grid gap-2 ps-4">
                        {teacherAssignments.map((a) => (
                          <div key={a.id} className="d-flex justify-content-between align-items-center blueprint-rule-row">
                            <div>
                              <span className="fw-semibold small">{a.course_name}</span>
                              <p className="text-muted small mb-0">
                                Assigned {new Date(a.assigned_at).toLocaleDateString()}
                              </p>
                            </div>
                            <button
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => deleteAssignment(a.id)}
                            >
                              Remove
                            </button>
                          </div>
                        ))}
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
