import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText, Upload, Trash2, RefreshCw, Eye, Download,
  BookOpen, Filter, CheckCircle2, FileX, Loader, Plus,
  FileCheck, Globe, Lock, AlertCircle
} from "lucide-react";
import api from "../api/api";

const TeacherMaterials = () => {
  const [materials, setMaterials] = useState([]);
  const [courses, setCourses] = useState([]);
  const [domains, setDomains] = useState([]);
  const [topics, setTopics] = useState([]);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const [form, setForm] = useState({
    title: "",
    course: "",
    domain: "",
    topic: "",
    file_type: "pdf",
    file: null,
  });

  const [editForm, setEditForm] = useState({
    title: "",
    course: "",
    domain: "",
    topic: "",
  });

  const [filterStatus, setFilterStatus] = useState("all");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState(null);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
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
        course: prev.course || coursesRes.data[0]?.id || "",
        domain: prev.domain || domainsRes.data[0]?.id || "",
        topic: prev.topic || topicsRes.data[0]?.id || "",
      }));
    } catch {
      setError("Failed to load materials.");
    }
  };

  const handleChange = (e) => {
    const { name, value, files } = e.target;
    setForm({ ...form, [name]: files ? files[0] : value });
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditForm({ ...editForm, [name]: value });
  };

  const uploadMaterial = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");
    if (!form.file) { setError("Please select a file."); return; }
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
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSuccess("Material uploaded successfully.");
      setForm({ ...form, title: "", file: null });
      setShowUploadForm(false);
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const processMaterial = async (materialId) => {
    setError(""); setSuccess("");
    setProcessingId(materialId);
    try {
      await api.post(`/rag/materials/${materialId}/process/`);
      setSuccess("Processing started.");
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Processing failed.");
    } finally {
      setProcessingId(null);
    }
  };

  const deleteMaterial = async (materialId, title) => {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/rag/materials/${materialId}/`);
      setSuccess("Material deleted.");
      await fetchData();
    } catch {
      setError("Failed to delete material.");
    }
  };

  const startEditing = (material) => {
    setEditingId(material.id);
    setEditForm({
      title: material.title,
      course: material.course?.toString() || "",
      domain: material.domain?.toString() || "",
      topic: material.topic?.toString() || "",
    });
  };

  const cancelEditing = () => setEditingId(null);

  const saveEdit = async (materialId) => {
    setError(""); setSuccess("");
    try {
      await api.patch(`/rag/materials/${materialId}/`, {
        title: editForm.title,
        course: editForm.course || null,
        domain: editForm.domain || null,
        topic: editForm.topic || null,
      });
      setSuccess("Material updated.");
      setEditingId(null);
      await fetchData();
    } catch {
      setError("Failed to update material.");
    }
  };

  const togglePublish = async (material) => {
    const newStatus = material.publish_status === "published" ? "draft" : "published";
    try {
      await api.patch(`/rag/materials/${material.id}/`, {
        publish_status: newStatus,
      });
      await fetchData();
    } catch {
      setError("Failed to update publish status.");
    }
  };

  const getStatusBadge = (status) => {
    if (status === "completed") return "bg-success";
    if (status === "processing") return "bg-warning text-dark";
    if (status === "failed") return "bg-danger";
    return "bg-secondary";
  };

  const filtered = filterStatus === "all"
    ? materials
    : materials.filter((m) => m.processing_status === filterStatus);

  const stats = {
    total: materials.length,
    completed: materials.filter((m) => m.processing_status === "completed").length,
    published: materials.filter((m) => m.publish_status === "published").length,
    draft: materials.filter((m) => m.publish_status === "draft").length,
    failed: materials.filter((m) => m.processing_status === "failed").length,
  };

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h2 className="fw-bold mb-1">Materials</h2>
          <p className="text-muted mb-0">
            Upload, manage, and generate AI learning assets for your courses.
          </p>
        </div>
        <button
          className="btn btn-primary d-flex align-items-center gap-2"
          onClick={() => setShowUploadForm(!showUploadForm)}
        >
          <Plus size={16} /> Upload Material
        </button>
      </div>

      {error && <div className="alert alert-danger py-2">{error}</div>}
      {success && <div className="alert alert-success py-2">{success}</div>}

      {/* Stats row */}
      <div className="row g-3 mb-4">
        {[
          { label: "Total", value: stats.total, icon: FileText, color: "#2563eb" },
          { label: "Processed", value: stats.completed, icon: FileCheck, color: "#16a34a" },
          { label: "Published", value: stats.published, icon: Globe, color: "#7c3aed" },
          { label: "Draft", value: stats.draft, icon: Lock, color: "#64748b" },
        ].map((s) => (
          <div key={s.label} className="col-sm-6 col-lg-3">
            <div className="card border-0 shadow-sm rounded-3 h-100">
              <div className="card-body p-3 d-flex align-items-center gap-3">
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: `${s.color}15`, display: "grid", placeItems: "center", flexShrink: 0
                }}>
                  <s.icon size={18} color={s.color} />
                </div>
                <div>
                  <p className="text-muted small mb-0">{s.label}</p>
                  <p className="fw-bold mb-0" style={{ fontSize: "1.25rem" }}>{s.value}</p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Upload form */}
      {showUploadForm && (
        <div className="card border-0 shadow-sm rounded-4 mb-4">
          <div className="card-body p-4">
            <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
              <Upload size={18} /> Upload New Material
            </h5>
            <form onSubmit={uploadMaterial}>
              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label">Title</label>
                  <input name="title" className="form-control" value={form.title} onChange={handleChange} required />
                </div>
                <div className="col-md-6">
                  <label className="form-label">File Type</label>
                  <select name="file_type" className="form-select" value={form.file_type} onChange={handleChange}>
                    <option value="pdf">PDF</option>
                    <option value="docx">DOCX</option>
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="form-label">Course</label>
                  <select name="course" className="form-select" value={form.course} onChange={handleChange} required>
                    {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="form-label">Domain</label>
                  <select name="domain" className="form-select" value={form.domain} onChange={handleChange} required>
                    {domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="form-label">Topic</label>
                  <select name="topic" className="form-select" value={form.topic} onChange={handleChange} required>
                    {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className="form-label">File</label>
                  <input type="file" name="file" className="form-control" accept=".pdf,.docx" onChange={handleChange} required />
                </div>
                <div className="col-md-6 d-flex align-items-end gap-2">
                  <button className="btn btn-primary" disabled={uploading}>
                    {uploading ? <><Loader size={14} className="me-2 spin-icon" />Uploading...</> : "Upload"}
                  </button>
                  <button type="button" className="btn btn-outline-secondary" onClick={() => setShowUploadForm(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="d-flex align-items-center gap-2 mb-3">
        <Filter size={16} className="text-muted" />
        <span className="text-muted small">Filter by status:</span>
        {["all", "completed", "processing", "pending", "failed"].map((s) => (
          <button
            key={s}
            className={`btn btn-sm ${filterStatus === s ? "btn-primary" : "btn-outline-secondary"}`}
            onClick={() => setFilterStatus(s)}
            style={{ textTransform: "capitalize" }}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Materials table */}
      <div className="card border-0 shadow-sm rounded-4">
        <div className="card-body p-0">
          {filtered.length === 0 ? (
            <div className="text-center py-5">
              <FileX size={40} color="#cbd5e1" className="mb-3" />
              <p className="text-muted mb-0">No materials found.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th className="ps-4">Material</th>
                    <th>Course</th>
                    <th>Status</th>
                    <th>Published</th>
                    <th>Assets</th>
                    <th className="text-end pe-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((material) => (
                    <tr key={material.id}>
                      <td className="ps-4">
                        {editingId === material.id ? (
                          <div className="d-flex flex-column gap-1" style={{ minWidth: 200 }}>
                            <input
                              name="title" className="form-control form-control-sm"
                              value={editForm.title} onChange={handleEditChange}
                            />
                            <select name="course" className="form-select form-select-sm" value={editForm.course} onChange={handleEditChange}>
                              <option value="">-- Course --</option>
                              {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                            <select name="domain" className="form-select form-select-sm" value={editForm.domain} onChange={handleEditChange}>
                              <option value="">-- Domain --</option>
                              {domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                            </select>
                            <select name="topic" className="form-select form-select-sm" value={editForm.topic} onChange={handleEditChange}>
                              <option value="">-- Topic --</option>
                              {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                            </select>
                            <div className="d-flex gap-1 mt-1">
                              <button className="btn btn-sm btn-primary" onClick={() => saveEdit(material.id)}>Save</button>
                              <button className="btn btn-sm btn-outline-secondary" onClick={cancelEditing}>Cancel</button>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <p className="fw-semibold mb-0">{material.title}</p>
                            <p className="text-muted small mb-0">
                              {material.file_type?.toUpperCase()} &middot;{" "}
                              {material.chunk_count != null ? `${material.chunk_count} chunks` : "—"}
                              {" "}&middot;{" "}
                              {new Date(material.uploaded_at).toLocaleDateString()}
                            </p>
                          </div>
                        )}
                      </td>
                      <td>
                        <p className="mb-0 small">{material.course_name || "—"}</p>
                        {material.domain_name && (
                          <p className="text-muted small mb-0">{material.domain_name}</p>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${getStatusBadge(material.processing_status)}`}>
                          {material.processing_status}
                        </span>
                        {material.error_message && (
                          <p className="text-danger small mb-0 mt-1" title={material.error_message}>
                            <AlertCircle size={12} className="me-1" />
                            {material.error_message.substring(0, 40)}...
                          </p>
                        )}
                      </td>
                      <td>
                        <button
                          className="btn btn-sm"
                          style={{
                            background: material.publish_status === "published" ? "#f0fdf4" : "#f8fafc",
                            border: `1px solid ${material.publish_status === "published" ? "#16a34a" : "#cbd5e1"}`,
                            color: material.publish_status === "published" ? "#16a34a" : "#64748b",
                          }}
                          onClick={() => togglePublish(material)}
                          title={material.publish_status === "published" ? "Click to unpublish" : "Click to publish"}
                        >
                          {material.publish_status === "published"
                            ? <><Globe size={12} className="me-1" />Published</>
                            : <><Lock size={12} className="me-1" />Draft</>
                          }
                        </button>
                      </td>
                      <td>
                        <div className="d-flex gap-1">
                          {material.has_summary && (
                            <span className="badge bg-light text-dark" title="Summary"><FileText size={11} /></span>
                          )}
                          {material.has_flashcards && (
                            <span className="badge bg-light text-dark" title="Flashcards"><BookOpen size={11} /></span>
                          )}
                          {material.has_quiz && (
                            <span className="badge bg-light text-dark" title="Quiz"><CheckCircle2 size={11} /></span>
                          )}
                          {!material.has_summary && !material.has_flashcards && !material.has_quiz && (
                            <span className="text-muted small">—</span>
                          )}
                        </div>
                      </td>
                      <td className="text-end pe-4">
                        <div className="d-flex gap-1 justify-content-end flex-wrap">
                          {material.processing_status !== "completed" && (
                            <button
                              className="btn btn-sm btn-outline-primary"
                              title="Process"
                              onClick={() => processMaterial(material.id)}
                              disabled={processingId === material.id}
                            >
                              {processingId === material.id
                                ? <Loader size={14} className="spin-icon" />
                                : <RefreshCw size={14} />}
                            </button>
                          )}
                          <Link
                            className="btn btn-sm btn-outline-primary"
                            title="Preview"
                            to={`/teacher/materials/${material.id}`}
                          >
                            <Eye size={14} />
                          </Link>
                          {material.file && (
                            <a
                              className="btn btn-sm btn-outline-secondary"
                              href={material.file}
                              title="Download"
                              download
                            >
                              <Download size={14} />
                            </a>
                          )}
                          {editingId !== material.id && (
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              title="Edit metadata"
                              onClick={() => startEditing(material)}
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                            </button>
                          )}
                          <button
                            className="btn btn-sm btn-outline-danger"
                            title="Delete"
                            onClick={() => deleteMaterial(material.id, material.title)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeacherMaterials;
