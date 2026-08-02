import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import {
  FileText, BookOpen, HelpCircle, Volume2, ArrowLeft,
  Download, Trash2, RefreshCw, Eye, EyeOff, Globe, Lock,
  Loader, RotateCcw, Play, Pause, StopCircle, ChevronDown,
  ChevronUp, FileCheck, AlertCircle, CheckCircle2, XCircle
} from "lucide-react";
import api from "../api/api";

const ASSET_CARDS = [
  { key: "summary", label: "Summary", icon: FileText, desc: "AI-generated summary and key points from the material." },
  { key: "flashcards", label: "Flashcards", icon: BookOpen, desc: "Study cards for students to review key concepts." },
  { key: "quiz", label: "Quiz", icon: HelpCircle, desc: "Multiple-choice quiz generated from the material content." },
  { key: "audio", label: "Audio", icon: Volume2, desc: "Text-to-speech playback of the generated summary." },
];

const TeacherMaterialDetail = () => {
  const { materialId } = useParams();

  const [material, setMaterial] = useState(null);
  const [summary, setSummary] = useState(null);
  const [flashcards, setFlashcards] = useState([]);
  const [quiz, setQuiz] = useState(null);
  const [loadingAction, setLoadingAction] = useState("");
  const [expandedAsset, setExpandedAsset] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ title: "", course: "", domain: "", topic: "" });
  const [courses, setCourses] = useState([]);
  const [domains, setDomains] = useState([]);
  const [topics, setTopics] = useState([]);

  /* Audio state */
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioInterval = useRef(null);

  useEffect(() => { fetchAll(); }, [materialId]);

  const fetchAll = async () => {
    try {
      const [matRes, coursesRes, domainsRes, topicsRes] = await Promise.all([
        api.get(`/rag/materials/${materialId}/`),
        api.get("/exit-exams/courses/"),
        api.get("/exit-exams/domains/"),
        api.get("/exit-exams/topics/"),
      ]);
      setMaterial(matRes.data);
      setCourses(coursesRes.data);
      setDomains(domainsRes.data);
      setTopics(topicsRes.data);

      if (matRes.data.has_summary) await loadSummary();
      if (matRes.data.has_flashcards) await loadFlashcards();
      if (matRes.data.has_quiz) await loadQuiz();
    } catch {
      setError("Failed to load material.");
    }
  };

  const refreshMaterial = async () => {
    try {
      const res = await api.get(`/rag/materials/${materialId}/`);
      setMaterial(res.data);
    } catch { /* ignore */ }
  };

  const loadSummary = async () => {
    try {
      const res = await api.get(`/rag/materials/${materialId}/summary/`);
      setSummary(res.data.summary);
    } catch { /* ignore */ }
  };

  const loadFlashcards = async () => {
    try {
      const res = await api.get(`/rag/materials/${materialId}/flashcards/`);
      setFlashcards(res.data.flashcards || []);
    } catch { /* ignore */ }
  };

  const loadQuiz = async () => {
    try {
      const res = await api.get(`/rag/materials/${materialId}/quiz/`);
      setQuiz(res.data);
    } catch { /* ignore */ }
  };

  const handleAssetAction = async (assetKey) => {
    setError(""); setSuccess(""); setLoadingAction(assetKey);
    try {
      switch (assetKey) {
        case "summary": {
          const res = await api.post(`/rag/materials/${materialId}/summary/`);
          setSummary(res.data.summary);
          setSuccess("Summary generated.");
          break;
        }
        case "flashcards": {
          const res = await api.post(`/rag/materials/${materialId}/flashcards/`);
          setFlashcards(res.data.flashcards || []);
          setSuccess(`${res.data.flashcards?.length || 0} flashcards generated.`);
          break;
        }
        case "quiz": {
          const res = await api.post(`/rag/materials/${materialId}/generate-quiz/`);
          setQuiz(res.data);
          setSuccess(`Quiz with ${res.data.questions?.length || 0} questions generated.`);
          break;
        }
        default: break;
      }
      await refreshMaterial();
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to generate ${assetKey}.`);
    } finally {
      setLoadingAction("");
    }
  };

  const reprocess = async () => {
    setError(""); setSuccess(""); setLoadingAction("process");
    try {
      await api.post(`/rag/materials/${materialId}/process/`);
      setSuccess("Reprocessing started. Refresh to see updates.");
      await refreshMaterial();
    } catch (err) {
      setError(err.response?.data?.detail || "Reprocessing failed.");
    } finally {
      setLoadingAction("");
    }
  };

  const togglePublish = async () => {
    const newStatus = material.publish_status === "published" ? "draft" : "published";
    try {
      await api.patch(`/rag/materials/${materialId}/`, { publish_status: newStatus });
      setSuccess(`Material ${newStatus === "published" ? "published" : "unpublished"}.`);
      await refreshMaterial();
    } catch {
      setError("Failed to update publish status.");
    }
  };

  const deleteMaterial = async () => {
    if (!window.confirm(`Permanently delete "${material?.title}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/rag/materials/${materialId}/`);
      window.location.href = "/teacher/materials";
    } catch {
      setError("Failed to delete material.");
    }
  };

  const startEditing = () => {
    setEditForm({
      title: material.title || "",
      course: material.course?.toString() || "",
      domain: material.domain?.toString() || "",
      topic: material.topic?.toString() || "",
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    setError(""); setSuccess("");
    try {
      await api.patch(`/rag/materials/${materialId}/`, {
        title: editForm.title,
        course: editForm.course || null,
        domain: editForm.domain || null,
        topic: editForm.topic || null,
      });
      setSuccess("Material updated.");
      setEditing(false);
      await refreshMaterial();
    } catch {
      setError("Failed to update material.");
    }
  };

  /* ── Audio ── */
  const speakSummary = () => {
    if (!summary?.summary_text) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(summary.summary_text);
    utter.onstart = () => setIsSpeaking(true);
    utter.onend = utter.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utter);
  };

  const stopSpeaking = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  const toggleAsset = (key) => {
    if (expandedAsset === key) {
      setExpandedAsset(null);
      return;
    }
    setExpandedAsset(key);
    if (key === "summary" && !summary && material?.has_summary) loadSummary();
    if (key === "flashcards" && flashcards.length === 0 && material?.has_flashcards) loadFlashcards();
    if (key === "quiz" && !quiz && material?.has_quiz) loadQuiz();
  };

  if (!material) return (
    <div className="container py-5 d-flex align-items-center gap-3 text-muted">
      <div className="spinner-border spinner-border-sm text-primary" /> Loading…
    </div>
  );

  const isCompleted = material.processing_status === "completed";

  return (
    <div className="container py-4">
      {/* Top bar */}
      <div className="d-flex align-items-center gap-2 mb-4">
        <Link to="/teacher/materials" className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1">
          <ArrowLeft size={14} /> Back
        </Link>
        <h2 className="fw-bold mb-0 ms-2">{material.title}</h2>
        <div className="ms-auto d-flex gap-2">
          {material.file && (
            <a href={material.file} className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1" download>
              <Download size={14} /> Download
            </a>
          )}
          <button className="btn btn-sm btn-outline-danger d-flex align-items-center gap-1" onClick={deleteMaterial}>
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger py-2">{error}</div>}
      {success && <div className="alert alert-success py-2">{success}</div>}

      <div className="row g-4 mb-4">
        {/* Metadata panel */}
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <div className="d-flex justify-content-between align-items-start mb-3">
                <h5 className="fw-bold mb-0">Details</h5>
                <button className="btn btn-sm btn-outline-secondary" onClick={editing ? saveEdit : startEditing}>
                  {editing ? "Save" : "Edit"}
                </button>
              </div>

              {editing ? (
                <div className="d-grid gap-2">
                  <div>
                    <label className="form-label small mb-1">Title</label>
                    <input className="form-control form-control-sm" value={editForm.title}
                      onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                  </div>
                  <div>
                    <label className="form-label small mb-1">Course</label>
                    <select className="form-select form-select-sm" value={editForm.course}
                      onChange={(e) => setEditForm({ ...editForm, course: e.target.value })}>
                      <option value="">-- Select --</option>
                      {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="form-label small mb-1">Domain</label>
                    <select className="form-select form-select-sm" value={editForm.domain}
                      onChange={(e) => setEditForm({ ...editForm, domain: e.target.value })}>
                      <option value="">-- Select --</option>
                      {domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="form-label small mb-1">Topic</label>
                    <select className="form-select form-select-sm" value={editForm.topic}
                      onChange={(e) => setEditForm({ ...editForm, topic: e.target.value })}>
                      <option value="">-- Select --</option>
                      {topics.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => setEditing(false)}>Cancel</button>
                </div>
              ) : (
                <div className="row g-3">
                  <div className="col-sm-6">
                    <p className="text-muted small mb-1">Course</p>
                    <p className="fw-semibold mb-0">{material.course_name || "—"}</p>
                  </div>
                  <div className="col-sm-6">
                    <p className="text-muted small mb-1">Domain</p>
                    <p className="fw-semibold mb-0">{material.domain_name || "—"}</p>
                  </div>
                  <div className="col-sm-6">
                    <p className="text-muted small mb-1">Topic</p>
                    <p className="fw-semibold mb-0">{material.topic_name || "—"}</p>
                  </div>
                  <div className="col-sm-6">
                    <p className="text-muted small mb-1">File Type</p>
                    <p className="fw-semibold mb-0">{material.file_type?.toUpperCase() || "—"}</p>
                  </div>
                  <div className="col-sm-6">
                    <p className="text-muted small mb-1">Upload Date</p>
                    <p className="fw-semibold mb-0">{new Date(material.uploaded_at).toLocaleDateString()}</p>
                  </div>
                  <div className="col-sm-6">
                    <p className="text-muted small mb-1">Owner</p>
                    <p className="fw-semibold mb-0">{material.owner_name || "—"}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Status panel */}
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Status</h5>

              <div className="d-grid gap-3">
                <div className="d-flex justify-content-between align-items-center">
                  <span className="text-muted small">Processing</span>
                  <span className={`badge ${material.processing_status === "completed" ? "bg-success" : material.processing_status === "processing" ? "bg-warning text-dark" : material.processing_status === "failed" ? "bg-danger" : "bg-secondary"}`}>
                    {material.processing_status}
                  </span>
                </div>

                <div className="d-flex justify-content-between align-items-center">
                  <span className="text-muted small">Chunks</span>
                  <span className="fw-semibold">{material.chunk_count ?? "—"}</span>
                </div>

                <div className="d-flex justify-content-between align-items-center">
                  <span className="text-muted small">Publish Status</span>
                  <button
                    className="btn btn-sm"
                    style={{
                      background: material.publish_status === "published" ? "#f0fdf4" : "#f8fafc",
                      border: `1px solid ${material.publish_status === "published" ? "#16a34a" : "#cbd5e1"}`,
                      color: material.publish_status === "published" ? "#16a34a" : "#64748b",
                    }}
                    onClick={togglePublish}
                  >
                    {material.publish_status === "published"
                      ? <><Globe size={12} className="me-1" />Published</>
                      : <><Lock size={12} className="me-1" />Draft</>
                    }
                  </button>
                </div>

                <div className="d-flex justify-content-between align-items-center">
                  <span className="text-muted small">Summary</span>
                  {material.has_summary
                    ? <span className="text-success small"><CheckCircle2 size={12} className="me-1" />Generated</span>
                    : <span className="text-muted small"><XCircle size={12} className="me-1" />None</span>
                  }
                </div>

                <div className="d-flex justify-content-between align-items-center">
                  <span className="text-muted small">Flashcards</span>
                  {material.has_flashcards
                    ? <span className="text-success small"><CheckCircle2 size={12} className="me-1" />Generated</span>
                    : <span className="text-muted small"><XCircle size={12} className="me-1" />None</span>
                  }
                </div>

                <div className="d-flex justify-content-between align-items-center">
                  <span className="text-muted small">Quiz</span>
                  {material.has_quiz
                    ? <span className="text-success small"><CheckCircle2 size={12} className="me-1" />Generated</span>
                    : <span className="text-muted small"><XCircle size={12} className="me-1" />None</span>
                  }
                </div>

                {material.error_message && (
                  <div className="alert alert-danger py-2 mb-0 small">
                    <AlertCircle size={14} className="me-1" />
                    {material.error_message}
                  </div>
                )}

                <button
                  className="btn btn-outline-primary btn-sm d-flex align-items-center justify-content-center gap-1"
                  onClick={reprocess}
                  disabled={loadingAction === "process"}
                >
                  {loadingAction === "process"
                    ? <><Loader size={14} className="spin-icon" />Processing...</>
                    : <><RefreshCw size={14} /> Reprocess Material</>
                  }
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Generated Assets section */}
      <div className="mb-3">
        <h5 className="fw-bold mb-1">Generated Assets</h5>
        <p className="text-muted small mb-3">Generate and preview AI learning assets for students.</p>
      </div>

      <div className="row g-3">
        {ASSET_CARDS.map(({ key, label, icon: Icon, desc }) => (
          <div key={key} className="col-md-6">
            <div className="card border-0 shadow-sm rounded-4">
              <div className="card-body p-4">
                <div className="d-flex align-items-start gap-3">
                  <div style={{
                    width: 40, height: 40, borderRadius: 10,
                    background: "#eff6ff", display: "grid", placeItems: "center", flexShrink: 0
                  }}>
                    <Icon size={18} color="#2563eb" />
                  </div>
                  <div className="flex-fill">
                    <div className="d-flex justify-content-between align-items-start">
                      <h6 className="fw-bold mb-0">{label}</h6>
                      {(key !== "audio") && (
                        <span className="badge bg-light text-dark small">
                          {key === "summary" && (summary ? "Ready" : "Not generated")}
                          {key === "flashcards" && `${flashcards.length} cards`}
                          {key === "quiz" && `${quiz?.questions?.length || 0} Q`}
                        </span>
                      )}
                    </div>
                    <p className="text-muted small mt-1 mb-2">{desc}</p>
                    <div className="d-flex gap-2 flex-wrap">
                      {key !== "audio" ? (
                        <>
                          <button
                            className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1"
                            onClick={() => toggleAsset(key)}
                          >
                            {expandedAsset === key ? <><EyeOff size={13} /> Hide</> : <><Eye size={13} /> Preview</>}
                          </button>
                          <button
                            className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
                            onClick={() => handleAssetAction(key)}
                            disabled={!isCompleted || loadingAction === key}
                          >
                            {loadingAction === key
                              ? <Loader size={13} className="spin-icon" />
                              : <RotateCcw size={13} />}
                            Regenerate
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1"
                            onClick={toggleAsset}
                          >
                            {expandedAsset === key ? "Hide" : "Preview"}
                          </button>
                          <button
                            className="btn btn-sm btn-primary d-flex align-items-center gap-1"
                            onClick={isSpeaking ? stopSpeaking : speakSummary}
                            disabled={!summary}
                          >
                            {isSpeaking
                              ? <><Pause size={13} /> Stop</>
                              : <><Play size={13} /> Play</>
                            }
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded preview */}
                {expandedAsset === key && (
                  <div className="mt-3 pt-3 border-top">
                    {/* Summary preview */}
                    {key === "summary" && (
                      summary ? (
                        <div>
                          <div className="p-3 rounded-3 mb-3" style={{ background: "#f8fafc", fontSize: "0.9rem", lineHeight: 1.8, color: "#1e293b", maxHeight: 300, overflowY: "auto" }}>
                            {summary.summary_text}
                          </div>
                          {summary.key_points?.length > 0 && (
                            <div>
                              <p className="fw-bold small mb-2">Key Points</p>
                              {summary.key_points.map((pt, i) => (
                                <div key={i} className="d-flex gap-2 mb-1 small" style={{ color: "#475569" }}>
                                  <span style={{ color: "#2563eb", fontWeight: 700 }}>{i + 1}.</span>
                                  {pt}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="text-muted small text-center mb-0">No summary generated yet. Click Regenerate.</p>
                      )
                    )}

                    {/* Flashcards preview */}
                    {key === "flashcards" && (
                      flashcards.length > 0 ? (
                        <div style={{ maxHeight: 400, overflowY: "auto" }}>
                          {flashcards.slice(0, 10).map((card, i) => (
                            <div key={card.id || i} className="p-2 mb-2 rounded-3" style={{ background: "#f8fafc" }}>
                              <p className="fw-semibold small mb-1" style={{ color: "#2563eb" }}>Q: {card.front}</p>
                              <p className="small mb-0" style={{ color: "#475569" }}>A: {card.back}</p>
                            </div>
                          ))}
                          {flashcards.length > 10 && (
                            <p className="text-muted small text-center mb-0">+ {flashcards.length - 10} more cards</p>
                          )}
                        </div>
                      ) : (
                        <p className="text-muted small text-center mb-0">No flashcards generated yet. Click Regenerate.</p>
                      )
                    )}

                    {/* Quiz preview */}
                    {key === "quiz" && (
                      quiz?.questions?.length > 0 ? (
                        <div style={{ maxHeight: 400, overflowY: "auto" }}>
                          {quiz.questions.map((q, i) => (
                            <div key={q.id || i} className="mb-3 p-2 rounded-3" style={{ background: "#f8fafc" }}>
                              <p className="fw-semibold small mb-2">{i + 1}. {q.question_text}</p>
                              <div className="d-grid gap-1">
                                {q.choices.map((ch, ci) => (
                                  <span key={ci} className={`small px-2 py-1 rounded-2 ${ch === q.correct_answer ? "fw-bold" : ""}`}
                                    style={{
                                      background: ch === q.correct_answer ? "#f0fdf4" : "transparent",
                                      color: ch === q.correct_answer ? "#16a34a" : "#64748b",
                                      fontSize: "0.8rem",
                                    }}>
                                    {["A","B","C","D"][ci]}. {ch}
                                    {ch === q.correct_answer && " ✓"}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-muted small text-center mb-0">No quiz generated yet. Click Regenerate.</p>
                      )
                    )}

                    {/* Audio preview */}
                    {key === "audio" && (
                      summary ? (
                        <div className="text-center p-3">
                          <div className="p-3 rounded-3 mb-3" style={{ background: "#f8fafc", maxHeight: 200, overflowY: "auto", fontSize: "0.85rem", lineHeight: 1.7, color: "#64748b" }}>
                            {summary.summary_text?.substring(0, 500)}...
                          </div>
                          <p className="text-muted small mb-2">{summary.summary_text?.split(" ").length || 0} words</p>
                          <div className="d-flex justify-content-center gap-2">
                            <button className="btn btn-primary btn-sm d-flex align-items-center gap-1" onClick={isSpeaking ? stopSpeaking : speakSummary}>
                              {isSpeaking ? <><Pause size={14} /> Stop</> : <><Play size={14} /> Listen</>}
                            </button>
                            <button className="btn btn-outline-secondary btn-sm" onClick={stopSpeaking} disabled={!isSpeaking}>
                              <StopCircle size={14} />
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-muted small text-center mb-0">Generate a summary first to enable audio playback.</p>
                      )
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TeacherMaterialDetail;
