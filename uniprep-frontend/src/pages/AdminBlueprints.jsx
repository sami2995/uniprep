import { useEffect, useState } from "react";
import api from "../api/api";

const AdminBlueprints = () => {
  const [blueprints, setBlueprints] = useState([]);
  const [rules, setRules] = useState([]);
  const [courses, setCourses] = useState([]);
  const [domains, setDomains] = useState([]);

  const [blueprintForm, setBlueprintForm] = useState({
    course: "",
    title: "",
    total_questions: 100,
    duration_minutes: 180,
    is_active: true,
  });

  const [ruleForm, setRuleForm] = useState({
    blueprint: "",
    domain: "",
    number_of_questions: 1,
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [availability, setAvailability] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [blueprintRes, ruleRes, courseRes, domainRes , availabilityRes] = await Promise.all([
        api.get("/exit-exams/exam-blueprints/"),
        api.get("/exit-exams/exam-blueprint-rules/"),
        api.get("/exit-exams/courses/"),
        api.get("/exit-exams/domains/"),
        api.get("/exit-exams/question-availability/"),
      ]);

      setBlueprints(blueprintRes.data);
      setRules(ruleRes.data);
      setCourses(courseRes.data);
      setDomains(domainRes.data);
      setAvailability(availabilityRes.data.availability || []);

      setBlueprintForm((prev) => ({
        ...prev,
        course: courseRes.data[0]?.id || "",
      }));

      setRuleForm((prev) => ({
        ...prev,
        blueprint: blueprintRes.data[0]?.id || "",
        domain: domainRes.data[0]?.id || "",
      }));
    } catch (err) {
      setError("Failed to load blueprint data.");
    }
  };

  const handleBlueprintChange = (e) => {
    const { name, value, type, checked } = e.target;

    setBlueprintForm({
      ...blueprintForm,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  const handleRuleChange = (e) => {
    const { name, value } = e.target;

    setRuleForm({
      ...ruleForm,
      [name]: value,
    });
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
        is_active: blueprintForm.is_active,
      });

      setSuccess("Blueprint created successfully.");

      setBlueprintForm({
        ...blueprintForm,
        title: "",
        total_questions: 100,
        duration_minutes: 180,
        is_active: true,
      });

      await fetchData();
    } catch (err) {
      setError("Failed to create blueprint.");
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

      setSuccess("Blueprint rule added successfully.");

      setRuleForm({
        ...ruleForm,
        number_of_questions: 1,
      });

      await fetchData();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to create rule. Maybe this domain already exists in the blueprint."
      );
    }
  };

  const deleteBlueprint = async (id) => {
    const confirmed = window.confirm(
      "Delete this blueprint? Its domain rules will also be deleted."
    );

    if (!confirmed) return;

    try {
      await api.delete(`/exit-exams/exam-blueprints/${id}/`);
      setSuccess("Blueprint deleted.");
      await fetchData();
    } catch (err) {
      setError("Failed to delete blueprint.");
    }
  };

  const deleteRule = async (id) => {
    const confirmed = window.confirm("Delete this rule?");
    if (!confirmed) return;

    try {
      await api.delete(`/exit-exams/exam-blueprint-rules/${id}/`);
      setSuccess("Rule deleted.");
      await fetchData();
    } catch (err) {
      setError("Failed to delete rule.");
    }
  };

  const getRulesForBlueprint = (blueprintId) => {
    return rules.filter((rule) => Number(rule.blueprint) === Number(blueprintId));
  };

  const getRuleTotal = (blueprintId) => {
    return getRulesForBlueprint(blueprintId).reduce(
      (total, rule) => total + Number(rule.number_of_questions),
      0
    );
  };
  const getAvailableQuestions = (domainId) => {
    const item = availability.find(
      (entry) => Number(entry.domain_id) === Number(domainId)
  );

    return item ? item.available_questions : 0;
  };

  return (
    <div className="container py-4">
      <h2 className="fw-bold mb-2">Exam Blueprints</h2>
      <p className="text-muted">
        Define how many questions should come from each domain for official-style
        Exit Exam simulation.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="row g-4">
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Create Blueprint</h5>

              <form onSubmit={createBlueprint}>
                <div className="mb-3">
                  <label className="form-label">Course</label>
                  <select
                    name="course"
                    className="form-select"
                    value={blueprintForm.course}
                    onChange={handleBlueprintChange}
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
                  <label className="form-label">Blueprint Title</label>
                  <input
                    name="title"
                    className="form-control"
                    value={blueprintForm.title}
                    onChange={handleBlueprintChange}
                    placeholder="Computer Science BSc Exit Exam Blueprint"
                    required
                  />
                </div>

                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Total Questions</label>
                    <input
                      type="number"
                      name="total_questions"
                      className="form-control"
                      value={blueprintForm.total_questions}
                      onChange={handleBlueprintChange}
                      min="1"
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Duration Minutes</label>
                    <input
                      type="number"
                      name="duration_minutes"
                      className="form-control"
                      value={blueprintForm.duration_minutes}
                      onChange={handleBlueprintChange}
                      min="1"
                    />
                  </div>
                </div>

                <div className="form-check mb-3">
                  <input
                    type="checkbox"
                    name="is_active"
                    className="form-check-input"
                    checked={blueprintForm.is_active}
                    onChange={handleBlueprintChange}
                    id="blueprintActive"
                  />
                  <label className="form-check-label" htmlFor="blueprintActive">
                    Active blueprint
                  </label>
                </div>

                <button className="btn btn-primary w-100">
                  Save Blueprint
                </button>
              </form>
            </div>
          </div>

          <div className="card border-0 shadow-sm rounded-4 mt-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Add Domain Rule</h5>

              <form onSubmit={createRule}>
                <div className="mb-3">
                  <label className="form-label">Blueprint</label>
                  <select
                    name="blueprint"
                    className="form-select"
                    value={ruleForm.blueprint}
                    onChange={handleRuleChange}
                    required
                  >
                    {blueprints.map((blueprint) => (
                      <option key={blueprint.id} value={blueprint.id}>
                        {blueprint.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Domain</label>
                  <select
                    name="domain"
                    className="form-select"
                    value={ruleForm.domain}
                    onChange={handleRuleChange}
                    required
                  >
                    {domains.map((domain) => (
                      <option key={domain.id} value={domain.id}>
                        {domain.name} - {getAvailableQuestions(domain.id)} available
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label">Number of Questions</label>
                  <input
                    type="number"
                    name="number_of_questions"
                    className="form-control"
                    value={ruleForm.number_of_questions}
                    onChange={handleRuleChange}
                    min="1"
                  />
                </div>

                <button className="btn btn-primary w-100">
                  Add Rule
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Blueprint List</h5>

              {blueprints.length === 0 ? (
                <p className="text-muted">No blueprints created yet.</p>
              ) : (
                <div className="d-grid gap-4">
                  {blueprints.map((blueprint) => {
                    const ruleTotal = getRuleTotal(blueprint.id);
                    const isBalanced =
                      Number(ruleTotal) === Number(blueprint.total_questions);

                    return (
                      <div key={blueprint.id} className="blueprint-card">
                        <div className="d-flex justify-content-between gap-3">
                          <div>
                            <h5 className="fw-bold mb-1">{blueprint.title}</h5>

                            <p className="text-muted small mb-2">
                              Course: {blueprint.course_name || blueprint.course}
                            </p>

                            <div className="d-flex gap-2 flex-wrap mb-3">
                              <span className="badge bg-primary">
                                {blueprint.total_questions} Questions
                              </span>

                              <span className="badge bg-dark">
                                {blueprint.duration_minutes} Minutes
                              </span>

                              {blueprint.is_active ? (
                                <span className="badge bg-success">Active</span>
                              ) : (
                                <span className="badge bg-secondary">Inactive</span>
                              )}

                              {isBalanced ? (
                                <span className="badge bg-success">
                                  Rules Balanced
                                </span>
                              ) : (
                                <span className="badge bg-warning text-dark">
                                  Rules Total: {ruleTotal}/
                                  {blueprint.total_questions}
                                </span>
                              )}
                            </div>
                          </div>

                          <button
                            className="btn btn-sm btn-outline-danger align-self-start"
                            onClick={() => deleteBlueprint(blueprint.id)}
                          >
                            Delete
                          </button>
                        </div>

                        <h6 className="fw-bold mt-3">Domain Rules</h6>

                        {getRulesForBlueprint(blueprint.id).length === 0 ? (
                          <p className="text-muted small">
                            No domain rules added yet.
                          </p>
                        ) : (
                          <div className="d-grid gap-2">
                            {getRulesForBlueprint(blueprint.id).map((rule) => (
                              <div key={rule.id} className="blueprint-rule-row">
                                <div>
                                  <strong>
                                    {rule.domain_name || rule.domain}
                                  </strong>
                                  <p className="small text-muted mb-0">
                                    Rule: {rule.number_of_questions} questions - Available:{" "}
                                    {getAvailableQuestions(rule.domain)}
                                  </p>
                                </div>

                                <button
                                  className="btn btn-sm btn-outline-danger"
                                  onClick={() => deleteRule(rule.id)}
                                >
                                  Remove
                                </button>
                              </div>
                            ))}
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

export default AdminBlueprints;
