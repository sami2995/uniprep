import { useEffect, useMemo, useState } from "react";
import api from "../api/api";

const groupByCourseDomain = (assignments) => {
  const map = new Map();

  assignments.forEach((a) => {
    const courseId = a.course_id ?? `course-${a.course ?? "unknown"}`;
    const courseName = a.course_name || "Uncategorised";
    const domainName = a.domain_name || "(Uncategorised)";
    const topicId = a.topic;
    const topicName = a.topic_name || `Topic #${topicId}`;

    if (!map.has(courseId)) {
      map.set(courseId, {
        courseId,
        courseName,
        departmentId: a.department_id,
        domains: new Map(),
      });
    }

    const courseEntry = map.get(courseId);
    if (!courseEntry.domains.has(domainName)) {
      courseEntry.domains.set(domainName, {
        domainName,
        topics: [],
      });
    }

    courseEntry.domains.get(domainName).topics.push({
      id: a.id,
      topicId,
      topicName,
      assignedAt: a.assigned_at,
      assignedBy: a.assigned_by_username,
    });
  });

  return Array.from(map.values()).map((c) => ({
    ...c,
    domains: Array.from(c.domains.values()),
  }));
};

const TeacherCourses = () => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAssignedTopics();
  }, []);

  const fetchAssignedTopics = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/exit-exams/my-assigned-topics/");
      setAssignments(Array.isArray(response.data) ? response.data : []);
    } catch {
      setError("Failed to load assigned topics.");
    } finally {
      setLoading(false);
    }
  };

  const grouped = useMemo(() => groupByCourseDomain(assignments), [assignments]);

  const totalTopics = assignments.length;
  const totalDomains = new Set(assignments.map((a) => a.domain_name)).size;
  const totalCourses = new Set(assignments.map((a) => a.course_id)).size;
  const lastUpdated = useMemo(() => {
    const ts = assignments
      .map((a) => new Date(a.assigned_at).getTime())
      .filter(Boolean)
      .sort();
    return ts.length ? new Date(ts[ts.length - 1]).toLocaleString() : "—";
  }, [assignments]);

  if (loading) {
    return (
      <div className="container py-5">
        Loading your topic assignments...
      </div>
    );
  }

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Teacher Portal</span>
          <h2 className="fw-bold mt-2 mb-1">My Teaching Topics</h2>
          <p className="text-muted mb-0">
            Topics assigned to you by your department head. Topics are grouped
            under their domain and exit exam year.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {totalTopics === 0 && !error ? (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-4">
            <h5 className="fw-bold">No assigned topics yet</h5>
            <p className="text-muted mb-0">
              Topics will appear here after a department head assigns you to
              one.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Summary strip */}
          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <div className="card border-0 shadow-sm rounded-4 h-100">
                <div className="card-body p-3">
                  <p className="text-muted small mb-1">Assigned topics</p>
                  <h4 className="fw-bold mb-0">{totalTopics}</h4>
                </div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="card border-0 shadow-sm rounded-4 h-100">
                <div className="card-body p-3">
                  <p className="text-muted small mb-1">Domains</p>
                  <h4 className="fw-bold mb-0">{totalDomains}</h4>
                </div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="card border-0 shadow-sm rounded-4 h-100">
                <div className="card-body p-3">
                  <p className="text-muted small mb-1">Exit Exam Years</p>
                  <h4 className="fw-bold mb-0">{totalCourses}</h4>
                </div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="card border-0 shadow-sm rounded-4 h-100">
                <div className="card-body p-3">
                  <p className="text-muted small mb-1">Last updated</p>
                  <h6 className="fw-bold mb-0">{lastUpdated}</h6>
                </div>
              </div>
            </div>
          </div>

          {/* Hierarchy: Course → Domain → Topics */}
          <div className="d-grid gap-4">
            {grouped.map((course) => (
              <div
                key={course.courseId}
                className="card border-0 shadow-sm rounded-4"
              >
                <div className="card-body p-4">
                  <div className="d-flex align-items-center gap-2 mb-3">
                    <div
                      className="rounded-circle bg-primary bg-opacity-10 text-primary d-flex align-items-center justify-content-center fw-bold"
                      style={{ width: 40, height: 40, fontSize: "1rem" }}
                    >
                      {course.courseName.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <h5 className="fw-bold mb-0">{course.courseName}</h5>
                      <p className="text-muted small mb-0">Exit Exam Year</p>
                    </div>
                  </div>

                  <div className="d-grid gap-3 ps-2">
                    {course.domains.map((domain) => (
                      <div key={domain.domainName}>
                        <div className="d-flex align-items-center gap-2 mb-2">
                          <div
                            className="rounded-circle bg-secondary bg-opacity-25 text-dark d-flex align-items-center justify-content-center fw-bold"
                            style={{ width: 28, height: 28, fontSize: "0.8rem" }}
                          >
                            {domain.domainName.charAt(0).toUpperCase()}
                          </div>
                          <h6 className="fw-bold mb-0">{domain.domainName}</h6>
                        </div>

                        <ul className="list-group list-group-flush ps-4">
                          {domain.topics.map((t) => (
                            <li
                              key={t.id}
                              className="list-group-item px-0 d-flex justify-content-between align-items-center"
                            >
                              <span className="fw-semibold small">
                                {t.topicName}
                              </span>
                              <span className="badge bg-light text-dark border">
                                Assigned{" "}
                                {new Date(t.assignedAt).toLocaleDateString()}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default TeacherCourses;