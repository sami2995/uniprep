import { useEffect, useState } from "react";
import api from "../api/api";
import { useAuth } from "../auth/AuthContext";
import { ROLES, normalizeRole } from "../routes/roleRoutes";

const AdminAcademic = () => {
  const { user } = useAuth();
  const role = normalizeRole(user?.role);
  const isSystemAdmin = role === ROLES.SYSTEM_ADMIN || user?.is_staff;

  const [courses, setCourses] = useState([]);

  const [domains, setDomains] = useState([]);
  const [topics, setTopics] = useState([]);

  const [courseForm, setCourseForm] = useState({
    name: "",
    description: "",
  });

  const [domainForm, setDomainForm] = useState({
    course: "",
    name: "",
    importance_weight: 1,
  });

  const [topicForm, setTopicForm] = useState({
    domain: "",
    name: "",
    importance_weight: 1,
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [courseRes, domainRes, topicRes] = await Promise.all([
        api.get("/exit-exams/courses/"),
        api.get("/exit-exams/domains/"),
        api.get("/exit-exams/topics/"),
      ]);

      setCourses(courseRes.data);
      setDomains(domainRes.data);
      setTopics(topicRes.data);

      setDomainForm((prev) => ({
        ...prev,
        course: courseRes.data[0]?.id || "",
      }));

      setTopicForm((prev) => ({
        ...prev,
        domain: domainRes.data[0]?.id || "",
      }));
    } catch (err) {
      setError("Failed to load academic structure.");
    }
  };

  const createCourse = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      await api.post("/exit-exams/courses/", courseForm);

      setCourseForm({
        name: "",
        description: "",
      });

      setSuccess("Course created successfully.");
      await fetchData();
    } catch (err) {
      setError("Failed to create course.");
    }
  };

  const createDomain = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      await api.post("/exit-exams/domains/", {
        course: Number(domainForm.course),
        name: domainForm.name,
        importance_weight: Number(domainForm.importance_weight),
      });

      setDomainForm({
        ...domainForm,
        name: "",
        importance_weight: 1,
      });

      setSuccess("Domain created successfully.");
      await fetchData();
    } catch (err) {
      setError("Failed to create domain.");
    }
  };

  const createTopic = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      await api.post("/exit-exams/topics/", {
        domain: Number(topicForm.domain),
        name: topicForm.name,
        importance_weight: Number(topicForm.importance_weight),
      });

      setTopicForm({
        ...topicForm,
        name: "",
        importance_weight: 1,
      });

      setSuccess("Topic created successfully.");
      await fetchData();
    } catch (err) {
      setError("Failed to create topic.");
    }
  };

  const deleteCourse = async (id) => {
    const confirmed = window.confirm("Delete this course?");
    if (!confirmed) return;

    try {
      await api.delete(`/exit-exams/courses/${id}/`);
      await fetchData();
    } catch (err) {
      setError("Failed to delete course.");
    }
  };

  const deleteDomain = async (id) => {
    const confirmed = window.confirm("Delete this domain?");
    if (!confirmed) return;

    try {
      await api.delete(`/exit-exams/domains/${id}/`);
      await fetchData();
    } catch (err) {
      setError("Failed to delete domain.");
    }
  };

  const deleteTopic = async (id) => {
    const confirmed = window.confirm("Delete this topic?");
    if (!confirmed) return;

    try {
      await api.delete(`/exit-exams/topics/${id}/`);
      await fetchData();
    } catch (err) {
      setError("Failed to delete topic.");
    }
  };

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-2">Academic Structure</h2>
      <p className="text-muted">
        Manage exit exam years, domains, and topics used for Exit Exam practice.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="row g-4">
        {/* Exit Exams */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Exit Exams</h5>

              {isSystemAdmin ? (
                <>
                  <form onSubmit={createCourse}>
                    <div className="mb-3">
                      <label className="form-label">Exit Exam Name</label>
                      <input
                        className="form-control"
                        value={courseForm.name}
                        onChange={(e) =>
                          setCourseForm({
                            ...courseForm,
                            name: e.target.value,
                          })
                        }
                        placeholder="e.g. Computer Science BSc Exit Exam"
                        required
                      />
                    </div>

                    <div className="mb-3">
                      <label className="form-label">Description</label>
                      <textarea
                        className="form-control"
                        rows="3"
                        value={courseForm.description}
                        onChange={(e) =>
                          setCourseForm({
                            ...courseForm,
                            description: e.target.value,
                          })
                        }
                      />
                    </div>

                    <button className="btn btn-primary w-100">
                      Add Exit Exam
                    </button>
                  </form>

                  <hr />
                </>
              ) : (
                <div className="alert alert-info small mb-3">
                  <strong>Curriculum Courses</strong> are managed centrally by System Administrators. As Department Head, you can create and manage Domains and Topics under your department&apos;s existing courses below.
                </div>
              )}

              <div className="d-grid gap-2">
                {courses.map((course) => (
                  <div
                    key={course.id}
                    className="admin-list-item"
                  >
                    <div>
                      <strong>{course.name}</strong>
                      <p className="small text-muted mb-0">
                        {course.description || "No description"}
                      </p>
                    </div>

                    {isSystemAdmin && (
                      <button
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => deleteCourse(course.id)}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Domains */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Domains</h5>

              <form onSubmit={createDomain}>
                <div className="mb-3">
                  <label className="form-label">Exit Exam Year</label>
                  <select
                    className="form-select"
                    value={domainForm.course}
                    onChange={(e) =>
                      setDomainForm({
                        ...domainForm,
                        course: e.target.value,
                      })
                    }
                    required
                  >
                    {courses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Domain Name</label>
                  <input
                    className="form-control"
                    value={domainForm.name}
                    onChange={(e) =>
                      setDomainForm({
                        ...domainForm,
                        name: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Importance Weight</label>
                  <input
                    type="number"
                    step="0.1"
                    className="form-control"
                    value={domainForm.importance_weight}
                    onChange={(e) =>
                      setDomainForm({
                        ...domainForm,
                        importance_weight: e.target.value,
                      })
                    }
                  />
                </div>

                <button className="btn btn-primary w-100">
                  Add Domain
                </button>
              </form>

              <hr />

              <div className="d-grid gap-2">
                {domains.map((domain) => (
                  <div
                    key={domain.id}
                    className="admin-list-item"
                  >
                    <div>
                      <strong>{domain.name}</strong>
                      <p className="small text-muted mb-0">
                        Exit Exam Year: {domain.course_name || domain.course}
                      </p>
                    </div>

                    <button
                      className="btn btn-sm btn-outline-danger"
                      onClick={() => deleteDomain(domain.id)}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Topics */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Topics</h5>

              <form onSubmit={createTopic}>
                <div className="mb-3">
                  <label className="form-label">Domain</label>
                  <select
                    className="form-select"
                    value={topicForm.domain}
                    onChange={(e) =>
                      setTopicForm({
                        ...topicForm,
                        domain: e.target.value,
                      })
                    }
                    required
                  >
                    {domains.map((domain) => (
                      <option key={domain.id} value={domain.id}>
                        {domain.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Topic Name</label>
                  <input
                    className="form-control"
                    value={topicForm.name}
                    onChange={(e) =>
                      setTopicForm({
                        ...topicForm,
                        name: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Importance Weight</label>
                  <input
                    type="number"
                    step="0.1"
                    className="form-control"
                    value={topicForm.importance_weight}
                    onChange={(e) =>
                      setTopicForm({
                        ...topicForm,
                        importance_weight: e.target.value,
                      })
                    }
                  />
                </div>

                <button className="btn btn-primary w-100">
                  Add Topic
                </button>
              </form>

              <hr />

              <div className="d-grid gap-2">
                {topics.map((topic) => (
                  <div
                    key={topic.id}
                    className="admin-list-item"
                  >
                    <div>
                      <strong>{topic.name}</strong>
                      <p className="small text-muted mb-0">
                        Domain: {topic.domain_name || topic.domain}
                      </p>
                    </div>

                    <button
                      className="btn btn-sm btn-outline-danger"
                      onClick={() => deleteTopic(topic.id)}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminAcademic;
