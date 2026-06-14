import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/api";

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [imports, setImports] = useState([]);
  const [extractedQuestions, setExtractedQuestions] = useState([]);
  const [blueprints, setBlueprints] = useState([]);
  const [rules, setRules] = useState([]);
  const [availability, setAvailability] = useState([]);

  const [error, setError] = useState("");

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const [
        statsRes,
        importsRes,
        extractedRes,
        blueprintRes,
        ruleRes,
        availabilityRes,
      ] = await Promise.all([
        api.get("/exit-exams/admin-dashboard/"),
        api.get("/exit-exams/exam-pdf-imports/"),
        api.get("/exit-exams/extracted-questions/"),
        api.get("/exit-exams/exam-blueprints/"),
        api.get("/exit-exams/exam-blueprint-rules/"),
        api.get("/exit-exams/question-availability/"),
      ]);

      setStats(statsRes.data);
      setImports(importsRes.data);
      setExtractedQuestions(extractedRes.data);
      setBlueprints(blueprintRes.data);
      setRules(ruleRes.data);
      setAvailability(availabilityRes.data.availability || []);
    } catch (err) {
      setError("Failed to load admin dashboard.");
    }
  };

  const getDraftCount = () => {
    return extractedQuestions.filter((item) => item.status === "draft").length;
  };

  const getApprovedExtractedCount = () => {
    return extractedQuestions.filter((item) => item.status === "approved").length;
  };

  const getRejectedCount = () => {
    return extractedQuestions.filter((item) => item.status === "rejected").length;
  };

  const getRuleTotal = (blueprintId) => {
    return rules
      .filter((rule) => Number(rule.blueprint) === Number(blueprintId))
      .reduce((total, rule) => total + Number(rule.number_of_questions), 0);
  };

  const getInvalidBlueprintCount = () => {
    return blueprints.filter((blueprint) => {
      const ruleTotal = getRuleTotal(blueprint.id);
      return Number(ruleTotal) !== Number(blueprint.total_questions);
    }).length;
  };

  const getTotalAvailableQuestions = () => {
    return availability.reduce(
      (total, item) => total + Number(item.available_questions || 0),
      0
    );
  };

  const statusBadge = (status) => {
    if (status === "approved" || status === "completed") return "bg-success";
    if (status === "rejected" || status === "failed") return "bg-danger";
    if (status === "needs_review" || status === "processing")
      return "bg-warning text-dark";

    return "bg-secondary";
  };

  if (error) {
    return <div className="container py-5 alert alert-danger">{error}</div>;
  }

  if (!stats) {
    return <div className="container py-5">Loading admin dashboard...</div>;
  }

  return (
    <div className="container-fluid py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Admin Panel</span>
          <h2 className="fw-bold mt-2 mb-1">Admin Dashboard</h2>
          <p className="text-muted mb-0">
            Manage academic structure, question bank, PDF imports, and exam
            blueprints.
          </p>
        </div>

        <div className="d-flex gap-2 flex-wrap">
          <Link className="btn btn-primary" to="/admin/pdf-imports">
            Import PDF
          </Link>

          <Link className="btn btn-outline-primary" to="/admin/questions">
            Question Bank
          </Link>

          <Link className="btn btn-outline-dark" to="/admin/blueprints">
            Blueprints
          </Link>
        </div>
      </div>

      <div className="row g-3">
        <AdminStatCard
          title="Students"
          value={stats.users?.total_students || 0}
          subtitle="Registered students"
        />

        <AdminStatCard
          title="Question Bank"
          value={stats.question_bank?.total_questions || getTotalAvailableQuestions()}
          subtitle="Approved active questions"
        />

        <AdminStatCard
          title="Mock Exams"
          value={stats.exams?.total_mock_exams || 0}
          subtitle="Generated exams"
        />

        <AdminStatCard
          title="Attempts"
          value={stats.exams?.total_attempts || 0}
          subtitle="Student submissions"
        />
      </div>

      <div className="row g-3 mt-3">
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold">PDF Review Queue</h5>
              <p className="text-muted">
                Track extracted questions waiting for admin review.
              </p>

              <div className="review-count-grid">
                <div>
                  <strong>{getDraftCount()}</strong>
                  <span>Draft</span>
                </div>

                <div>
                  <strong>{getApprovedExtractedCount()}</strong>
                  <span>Approved</span>
                </div>

                <div>
                  <strong>{getRejectedCount()}</strong>
                  <span>Rejected</span>
                </div>
              </div>

              {getDraftCount() > 0 && (
                <div className="alert alert-warning mt-3 mb-0">
                  {getDraftCount()} extracted question(s) need review.
                </div>
              )}

              <Link
                className="btn btn-outline-primary w-100 mt-3"
                to="/admin/pdf-imports"
              >
                Review Extracted Questions
              </Link>
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold">Blueprint Health</h5>
              <p className="text-muted">
                Blueprints must have domain rules whose total equals exam size.
              </p>

              <div className="review-count-grid">
                <div>
                  <strong>{blueprints.length}</strong>
                  <span>Total</span>
                </div>

                <div>
                  <strong>{blueprints.length - getInvalidBlueprintCount()}</strong>
                  <span>Valid</span>
                </div>

                <div>
                  <strong>{getInvalidBlueprintCount()}</strong>
                  <span>Invalid</span>
                </div>
              </div>

              {getInvalidBlueprintCount() > 0 ? (
                <div className="alert alert-danger mt-3 mb-0">
                  Some blueprints have mismatched domain rule totals.
                </div>
              ) : (
                <div className="alert alert-success mt-3 mb-0">
                  All blueprints are balanced.
                </div>
              )}

              <Link
                className="btn btn-outline-primary w-100 mt-3"
                to="/admin/blueprints"
              >
                Manage Blueprints
              </Link>
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold">Quick Actions</h5>
              <p className="text-muted">
                Common admin tasks for preparing the Exit Exam system.
              </p>

              <div className="d-grid gap-2">
                <Link className="btn btn-primary" to="/admin/academic">
                  Manage Academic Structure
                </Link>

                <Link className="btn btn-outline-primary" to="/admin/questions">
                  Add Manual Question
                </Link>

                <Link className="btn btn-outline-primary" to="/admin/pdf-imports">
                  Upload Exam PDF
                </Link>

                <Link className="btn btn-outline-primary" to="/admin/blueprints">
                  Create Blueprint
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-3 mt-3">
        <div className="col-lg-6">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="fw-bold mb-0">Recent PDF Imports</h5>
                <Link className="btn btn-sm btn-outline-primary" to="/admin/pdf-imports">
                  View all
                </Link>
              </div>

              {imports.length === 0 ? (
                <p className="text-muted mb-0">No PDF imports yet.</p>
              ) : (
                <div className="d-grid gap-3">
                  {imports.slice(0, 5).map((item) => (
                    <div key={item.id} className="dashboard-list-item">
                      <div>
                        <strong>{item.title}</strong>
                        <p className="small text-muted mb-0">
                          {item.source_type} • {item.year || "No year"}
                        </p>
                      </div>

                      <span className={`badge ${statusBadge(item.status)}`}>
                        {item.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-6">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Questions Available by Domain</h5>

              {availability.length === 0 ? (
                <p className="text-muted mb-0">
                  No domain question availability found.
                </p>
              ) : (
                <div className="d-grid gap-3">
                  {availability.map((item) => (
                    <div key={item.domain_id} className="availability-row">
                      <div>
                        <strong>{item.domain}</strong>
                        <p className="small text-muted mb-0">{item.course}</p>
                      </div>

                      <span className="badge bg-primary">
                        {item.available_questions} questions
                      </span>
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

const AdminStatCard = ({ title, value, subtitle }) => {
  return (
    <div className="col-md-3">
      <div className="card border-0 shadow-sm rounded-4 h-100">
        <div className="card-body">
          <h6 className="text-muted">{title}</h6>
          <h2 className="fw-bold">{value}</h2>
          <p className="small text-muted mb-0">{subtitle}</p>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;