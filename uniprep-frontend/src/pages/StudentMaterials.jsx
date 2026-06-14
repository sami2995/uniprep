import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/api";

const StudentMaterials = () => {
  const [materials, setMaterials] = useState([]);
  const [courses, setCourses] = useState([]);
  const [domains, setDomains] = useState([]);
  const [topics, setTopics] = useState([]);

  const [form, setForm] = useState({
    title: "",
    course: "",
    domain: "",
    topic: "",
    file_type: "pdf",
    file: null,
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [materialsRes, coursesRes, domainsRes, topicsRes] =
        await Promise.all([
          api.get("/rag/materials/"),
          api.get("/exit-exams/courses/"),
          api.get("/exit-exams/domains/"),
          api.get("/exit-exams/topics/"),
        ]);

      setMaterials(materialsRes.data);
      setCourses(coursesRes.data);
      setDomains(domainsRes.data);
      setTopics(topicsRes.data);

      setForm((prev) => ({
        ...prev,
        course: coursesRes.data[0]?.id || "",
        domain: domainsRes.data[0]?.id || "",
        topic: topicsRes.data[0]?.id || "",
      }));
    } catch (err) {
      setError("Failed to load materials data.");
    }
  };

  const handleChange = (e) => {
    const { name, value, files } = e.target;

    setForm({
      ...form,
      [name]: files ? files[0] : value,
    });
  };

  const uploadMaterial = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.file) {
      setError("Please select a file.");
      return;
    }

    setUploading(true);

    try {
      const data = new FormData();

      data.append("title", form.title);
      data.append("course", form.course);
      data.append("domain", form.domain);
      data.append("topic", form.topic);
      data.append("file_type", form.file_type);
      data.append("file", form.file);

      await api.post("/rag/materials/", data, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setSuccess("Study material uploaded successfully.");
      setForm({
        ...form,
        title: "",
        file: null,
      });

      await fetchInitialData();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const processMaterial = async (materialId) => {
    setError("");
    setSuccess("");
    setProcessingId(materialId);

    try {
      await api.post(`/rag/materials/${materialId}/process/`);
      setSuccess("Material processed successfully.");
      await fetchInitialData();
    } catch (err) {
      setError(err.response?.data?.detail || "Processing failed.");
    } finally {
      setProcessingId(null);
    }
  };

  const getStatusBadge = (status) => {
    if (status === "completed") return "bg-success";
    if (status === "processing") return "bg-warning text-dark";
    if (status === "failed") return "bg-danger";
    return "bg-secondary";
  };

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-2">Study Materials</h2>
      <p className="text-muted">
        Upload your PDFs or DOCX files and use AI study tools.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="row g-4">
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Upload Material</h5>

              <form onSubmit={uploadMaterial}>
                <div className="mb-3">
                  <label className="form-label">Title</label>
                  <input
                    name="title"
                    className="form-control"
                    value={form.title}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Course</label>
                  <select
                    name="course"
                    className="form-select"
                    value={form.course}
                    onChange={handleChange}
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
                  <label className="form-label">Domain</label>
                  <select
                    name="domain"
                    className="form-select"
                    value={form.domain}
                    onChange={handleChange}
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
                  <label className="form-label">Topic</label>
                  <select
                    name="topic"
                    className="form-select"
                    value={form.topic}
                    onChange={handleChange}
                    required
                  >
                    {topics.map((topic) => (
                      <option key={topic.id} value={topic.id}>
                        {topic.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">File Type</label>
                  <select
                    name="file_type"
                    className="form-select"
                    value={form.file_type}
                    onChange={handleChange}
                  >
                    <option value="pdf">PDF</option>
                    <option value="docx">DOCX</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">File</label>
                  <input
                    type="file"
                    name="file"
                    className="form-control"
                    accept=".pdf,.docx"
                    onChange={handleChange}
                    required
                  />
                </div>

                <button className="btn btn-primary w-100" disabled={uploading}>
                  {uploading ? "Uploading..." : "Upload Material"}
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">My Materials</h5>

              {materials.length === 0 ? (
                <p className="text-muted">No study materials uploaded yet.</p>
              ) : (
                <div className="d-grid gap-3">
                  {materials.map((material) => (
                    <div
                      key={material.id}
                      className="material-item border rounded-4 p-3"
                    >
                      <div className="d-flex justify-content-between align-items-start gap-3">
                        <div>
                          <h6 className="fw-bold mb-1">{material.title}</h6>
                          <p className="text-muted small mb-2">
                            Type: {material.file_type?.toUpperCase()}
                          </p>

                          <span
                            className={`badge ${getStatusBadge(
                              material.processing_status
                            )}`}
                          >
                            {material.processing_status}
                          </span>
                        </div>

                        <div className="d-flex gap-2 flex-wrap justify-content-end">
                          {material.processing_status !== "completed" && (
                            <button
                              className="btn btn-sm btn-outline-primary"
                              onClick={() => processMaterial(material.id)}
                              disabled={processingId === material.id}
                            >
                              {processingId === material.id
                                ? "Processing..."
                                : "Process"}
                            </button>
                          )}

                          <Link
                            className="btn btn-sm btn-primary"
                            to={`/student/materials/${material.id}`}
                          >
                            Open
                          </Link>
                        </div>
                      </div>

                      {material.error_message && (
                        <p className="text-danger small mt-2 mb-0">
                          {material.error_message}
                        </p>
                      )}
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

export default StudentMaterials;