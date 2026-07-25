import { useEffect, useState } from "react";
import api from "../api/api";

const BlueprintSettings = () => {
  const [blueprints, setBlueprints] = useState([]);
  const [rules, setRules] = useState([]);
  const [courses, setCourses] = useState([]);
  const [domains, setDomains] = useState([]);
  const [availability, setAvailability] = useState([]);

  const [blueprintForm, setBlueprintForm] = useState({
    course: "",
    title: "",
    total_questions: 100,
    duration_minutes: 180,
    pass_percentage: 50,
    marks_per_question: 1,
    difficulty_distribution: { easy: 30, medium: 50, hard: 20 },
    is_active: true,
  });

  const [ruleForm, setRuleForm] = useState({
    blueprint: "",
    domain: "",
    number_of_questions: 1,
  });

  const [validation, setValidation] = useState(null); // null | { valid, errors, warnings, summary }
  const [validatingId, setValidatingId] = useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [bpRes, ruleRes, courseRes, domainRes, availRes] = await Promise.all([
        api.get("/exit-exams/exam-blueprints/"),
        api.get("/exit-exams/exam-blueprint-rules/"),
        api.get("/exit-exams/courses/"),
        api.get("/exit-exams/domains/"),
        api.get("/exit-exams/question-availability/"),
      ]);
      setBlueprints(bpRes.data);
      setRules(ruleRes.data);
      setCourses(courseRes.data);
      setDomains(domainRes.data);
      setAvailability(availRes.data.availability || []);

      setBlueprintForm((f) => ({ ...f, course: courseRes.data[0]?.id || "" }));
      setRuleForm((f) => ({
        ...f,
        blueprint: bpRes.data[0]?.id || "",
        domain: domainRes.data[0]?.id || "",
      }));
    } catch {
      setError("Failed to load blueprint data.");
    }
  };

  const handleBpChange = (e) => {
    const { name, value, type, checked } = e.target;
    setBlueprintForm((f) => ({
      ...f,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleDiffChange = (key, value) => {
    setBlueprintForm((f) => ({
      ...f,
      difficulty_distribution: { ...f.difficulty_distribution, [key]: Number(value) },
    }));
  };

  const handleRuleChange = (e) => {
    const { name, value } = e.target;
    setRuleForm((f) => ({ ...f, [name]: value }));
  };

  const createBlueprint = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await api.post("/exit-exams/exam-blueprints/", {
        course: Number(blueprintForm.course),
        title: blueprintForm.title,
        total_questions: Number(blueprintForm.total_questions),
        duration_minutes: Number(blueprintForm.duration_minutes),
        pass_percentage: Number(blueprintForm.pass_percentage),
        marks_per_question: Number(blueprintForm.marks_per_question),
        difficulty_distribution: blueprintForm.difficulty_distribution,
        is_active: blueprintForm.is_active,
      });
      setSuccess("Blueprint created successfully.");
      setBlueprintForm((f) => ({ ...f, title: "" }));
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create blueprint.");
    }
  };

  const createRule = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await api.post("/exit-exams/exam-blueprint-rules/", {
        blueprint: Number(ruleForm.blueprint),
        domain: Number(ruleForm.domain),
        number_of_questions: Number(ruleForm.number_of_questions),
      });
      setSuccess("Domain rule added.");
      await fetchData();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to add rule. Domain may already exist."
      );
    }
  };

  const deleteBlueprint = async (id) => {
    if (!window.confirm("Delete this blueprint and all its domain rules?")) return;
    try {
      await api.delete(`/exit-exams/exam-blueprints/${id}/`);
      setSuccess("Blueprint deleted.");
      await fetchData();
    } catch {
      setError("Failed to delete blueprint.");
    }
  };

  const deleteRule = async (id) => {
    if (!window.confirm("Remove this domain rule?")) return;
    try {
      await api.delete(`/exit-exams/exam-blueprint-rules/${id}/`);
      setSuccess("Rule removed.");
      await fetchData();
    } catch {
      setError("Failed to remove rule.");
    }
  };

  const validateBlueprint = async (id) => {
    setValidatingId(id);
    setValidation(null);
    try {
      const res = await api.post(`/exit-exams/exam-blueprints/${id}/validate/`);
      setValidation(res.data);
    } catch (err) {
      setError("Validation request failed.");
    } finally {
      setValidatingId(null);
    }
  };

  const getAvailable = (domainId) => {
    const item = availability.find((a) => Number(a.domain_id) === Number(domainId));
    return item ? item.available_questions : 0;
  };

  const getRulesForBlueprint = (bpId) =>
    rules.filter((r) => Number(r.blueprint) === Number(bpId));

  const getRuleTotal = (bpId) =>
    getRulesForBlueprint(bpId).reduce((sum, r) => sum + Number(r.number_of_questions), 0);

  const diffTotal =
    (blueprintForm.difficulty_distribution.easy || 0) +
    (blueprintForm.difficulty_distribution.medium || 0) +
    (blueprintForm.difficulty_distribution.hard || 0);

  return (
    <div className="container-fluid py-4">
      {/* Hero */}
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Department Head</span>
          <h2 className="fw-bold mt-2 mb-1">Blueprint Settings</h2>
          <p className="text-muted mb-0">
            Configure exam structure, domain coverage, and grading parameters.
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

      {/* Validation Result */}
      {validation && (
        <div className={`alert ${validation.valid ? "alert-success" : "alert-danger"} rounded-4 mb-4`}>
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <strong>{validation.valid ? "✅ Blueprint is valid" : "❌ Blueprint has issues"}</strong>
              <p className="mb-1 small">{validation.summary?.title}</p>
            </div>
            <button className="btn-close" onClick={() => setValidation(null)} />
          </div>
          {validation.errors?.length > 0 && (
            <ul className="mb-1 small mt-2">
              {validation.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
          {validation.warnings?.length > 0 && (
            <>
              <strong className="small text-warning">Warnings:</strong>
              <ul className="mb-0 small">
                {validation.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </>
          )}
        </div>
      )}

      <div className="row g-4">
        {/* ── Create Blueprint ── */}
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4 mb-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Create Blueprint</h5>
              <form onSubmit={createBlueprint}>
                <div className="mb-3">
                  <label className="form-label fw-semibold">Course</label>
                  <select name="course" className="form-select" value={blueprintForm.course} onChange={handleBpChange} required>
                    {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label fw-semibold">Blueprint Title</label>
                  <input name="title" className="form-control" value={blueprintForm.title} onChange={handleBpChange} placeholder="e.g. CS Exit Exam 2025" required />
                </div>

                <div className="row">
                  <div className="col-6 mb-3">
                    <label className="form-label fw-semibold">Total Questions</label>
                    <input type="number" name="total_questions" className="form-control" value={blueprintForm.total_questions} onChange={handleBpChange} min="1" />
                  </div>
                  <div className="col-6 mb-3">
                    <label className="form-label fw-semibold">Duration (min)</label>
                    <input type="number" name="duration_minutes" className="form-control" value={blueprintForm.duration_minutes} onChange={handleBpChange} min="1" />
                  </div>
                </div>

                <div className="row">
                  <div className="col-6 mb-3">
                    <label className="form-label fw-semibold">Pass % </label>
                    <input type="number" name="pass_percentage" className="form-control" value={blueprintForm.pass_percentage} onChange={handleBpChange} min="1" max="100" step="0.5" />
                  </div>
                  <div className="col-6 mb-3">
                    <label className="form-label fw-semibold">Marks/Question</label>
                    <input type="number" name="marks_per_question" className="form-control" value={blueprintForm.marks_per_question} onChange={handleBpChange} min="0.1" step="0.5" />
                  </div>
                </div>

                {/* Difficulty distribution sliders */}
                <div className="mb-3">
                  <label className="form-label fw-semibold">
                    Difficulty Distribution{" "}
                    <span className={`badge ms-1 ${diffTotal === 100 ? "bg-success" : "bg-danger"}`}>
                      Total: {diffTotal}%
                    </span>
                  </label>
                  {[
                    { key: "easy", label: "Easy", color: "success" },
                    { key: "medium", label: "Medium", color: "warning" },
                    { key: "hard", label: "Hard", color: "danger" },
                  ].map(({ key, label, color }) => (
                    <div key={key} className="mb-2">
                      <div className="d-flex justify-content-between mb-1">
                        <span className="small fw-semibold">{label}</span>
                        <span className="small text-muted">
                          {blueprintForm.difficulty_distribution[key] || 0}%
                        </span>
                      </div>
                      <input
                        type="range"
                        className={`form-range`}
                        min="0" max="100"
                        value={blueprintForm.difficulty_distribution[key] || 0}
                        onChange={(e) => handleDiffChange(key, e.target.value)}
                      />
                    </div>
                  ))}
                </div>

                <div className="form-check mb-3">
                  <input type="checkbox" className="form-check-input" name="is_active" id="bpActive" checked={blueprintForm.is_active} onChange={handleBpChange} />
                  <label className="form-check-label" htmlFor="bpActive">Active blueprint</label>
                </div>

                <button className="btn btn-primary w-100">Save Blueprint</button>
              </form>
            </div>
          </div>

          {/* Add Domain Rule */}
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Add Domain Rule</h5>
              <form onSubmit={createRule}>
                <div className="mb-3">
                  <label className="form-label fw-semibold">Blueprint</label>
                  <select name="blueprint" className="form-select" value={ruleForm.blueprint} onChange={handleRuleChange} required>
                    {blueprints.map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
                  </select>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-semibold">Domain</label>
                  <select name="domain" className="form-select" value={ruleForm.domain} onChange={handleRuleChange} required>
                    {domains.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} — {getAvailable(d.id)} available
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-semibold">Number of Questions</label>
                  <input type="number" name="number_of_questions" className="form-control" value={ruleForm.number_of_questions} onChange={handleRuleChange} min="1" />
                </div>
                <button className="btn btn-primary w-100">Add Rule</button>
              </form>
            </div>
          </div>
        </div>

        {/* ── Blueprint List ── */}
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Existing Blueprints</h5>

              {blueprints.length === 0 ? (
                <p className="text-muted">No blueprints yet.</p>
              ) : (
                <div className="d-grid gap-4">
                  {blueprints.map((bp) => {
                    const ruleTotal = getRuleTotal(bp.id);
                    const balanced = ruleTotal === Number(bp.total_questions);
                    const bpRules = getRulesForBlueprint(bp.id);

                    return (
                      <div key={bp.id} className="blueprint-card">
                        <div className="d-flex justify-content-between gap-3 align-items-start">
                          <div className="flex-grow-1">
                            <h6 className="fw-bold mb-1">{bp.title}</h6>
                            <p className="text-muted small mb-2">
                              Course: {bp.course_name || bp.course}
                              {bp.created_by_username && ` · Created by ${bp.created_by_username}`}
                            </p>
                            <div className="d-flex gap-2 flex-wrap mb-2">
                              <span className="badge bg-primary">{bp.total_questions}Q</span>
                              <span className="badge bg-dark">{bp.duration_minutes}min</span>
                              <span className="badge bg-info text-dark">
                                Pass: {bp.pass_percentage}%
                              </span>
                              <span className="badge bg-secondary">
                                {bp.marks_per_question} marks/Q
                              </span>
                              {bp.is_active ? (
                                <span className="badge bg-success">Active</span>
                              ) : (
                                <span className="badge bg-secondary">Inactive</span>
                              )}
                              <span className={`badge ${balanced ? "bg-success" : "bg-warning text-dark"}`}>
                                Rules: {ruleTotal}/{bp.total_questions}
                              </span>
                            </div>

                            {/* Difficulty Distribution display */}
                            {bp.difficulty_distribution && Object.keys(bp.difficulty_distribution).length > 0 && (
                              <div className="d-flex gap-2 mb-2">
                                {Object.entries(bp.difficulty_distribution).map(([k, v]) => (
                                  <span key={k} className="badge bg-light text-dark border small">
                                    {k}: {v}%
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          <div className="d-flex flex-column gap-1 flex-shrink-0">
                            <button
                              className="btn btn-sm btn-outline-primary"
                              onClick={() => validateBlueprint(bp.id)}
                              disabled={validatingId === bp.id}
                            >
                              {validatingId === bp.id ? "…" : "Validate"}
                            </button>
                            <button
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => deleteBlueprint(bp.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </div>

                        {/* Domain Rules */}
                        <h6 className="fw-bold mt-3 mb-2 small">Domain Rules</h6>
                        {bpRules.length === 0 ? (
                          <p className="text-muted small">No domain rules yet.</p>
                        ) : (
                          <div className="d-grid gap-2">
                            {bpRules.map((rule) => {
                              const avail = getAvailable(rule.domain);
                              const sufficient = avail >= Number(rule.number_of_questions);
                              return (
                                <div key={rule.id} className="blueprint-rule-row">
                                  <div>
                                    <strong className="small">{rule.domain_name || rule.domain}</strong>
                                    <p className="small text-muted mb-0">
                                      Requires: {rule.number_of_questions} ·{" "}
                                      <span className={sufficient ? "text-success" : "text-danger"}>
                                        Available: {avail}
                                      </span>
                                    </p>
                                  </div>
                                  <button
                                    className="btn btn-sm btn-outline-danger"
                                    onClick={() => deleteRule(rule.id)}
                                  >
                                    Remove
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlueprintSettings;
