import { useEffect, useState } from "react";
import api from "../api/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend,
} from "recharts";

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8", "#82CA9D"];

const STATUS_BADGE = {
  draft:      { label: "Draft",     tone: "secondary" },
  submitted:  { label: "Pending",   tone: "warning" },
  approved:   { label: "Approved",  tone: "success"  },
  rejected:   { label: "Rejected",  tone: "danger"   },
  archived:   { label: "Archived",  tone: "secondary" },
  created:    { label: "Created",    tone: "primary"  },
  updated:    { label: "Updated",    tone: "info"     },
  assignment_changed: { label: "Assignment", tone: "dark" },
  blueprint_changed:  { label: "Blueprint",  tone: "info" },
};

const TeacherAnalytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTeacherAnalytics();
  }, []);

  const fetchTeacherAnalytics = async () => {
    try {
      const res = await api.get("/analytics/teacher-dashboard/");
      setData(res.data);
    } catch (err) {
      console.error("Failed to fetch teacher analytics:", err);
      setError(err?.response?.data?.detail || "Failed to load analytics data.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container py-5">
        <p className="text-center text-muted">Loading analytics…</p>
      </div>
    );
  }

  return (
    <div className="container-fluid py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Teacher Portal</span>
          <h2 className="fw-bold mt-2 mb-1">Analytics</h2>
          <p className="text-muted mb-0">
            Insights into your questions, approvals, student reach and productivity.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {!data ? (
        <div className="card border-0 shadow-sm rounded-4 bg-light">
          <div className="card-body text-center py-5">
            <p className="text-muted mb-0">No analytics data available.</p>
          </div>
        </div>
      ) : (
        <>
          <SectionPipeline pipeline={data.pipeline} />

          {data.coverage && (
            <SectionCoverage coverage={data.coverage} />
          )}

          <SectionQuality quality={data.question_quality} />

          <SectionStudentImpact impact={data.student_impact} />

          <SectionApprovalHistory approval={data.approval_history} />

          <SectionActivityTimeline timeline={data.activity_timeline} />

          <SectionProductivity productivity={data.productivity} />
        </>
      )}
    </div>
  );
};

const Card = ({ title, children, className = "" }) => (
  <div className={`card border-0 shadow-sm rounded-4 ${className}`}>
    <div className="card-header bg-white border-bottom">
      <h5 className="fw-bold mb-0">{title}</h5>
    </div>
    <div className="card-body">{children}</div>
  </div>
);

const StatPill = ({ value, label, tone = "primary" }) => (
  <div className="card border-0 shadow-sm rounded-4 h-100">
    <div className="card-body p-4">
      <h6 className="text-muted small mb-1">{label}</h6>
      <h2 className={`fw-bold text-${tone} mb-0`}>{value}</h2>
    </div>
  </div>
);

const StatCol = ({ cols = "col-md-6 col-xl-3", children }) => (
  <div className={`${cols} mb-3`}>{children}</div>
);

const Badge = ({ tone = "secondary", children }) => (
  <span className={`badge bg-${tone} bg-opacity-10 text-${tone} rounded-pill px-3 py-2`}>
    {children}
  </span>
);

// ---------------------------------------------------------------------
// Section 1 — My Question Pipeline
// ---------------------------------------------------------------------
const SectionPipeline = ({ pipeline }) => {
  if (!pipeline) return null;
  return (
    <>
      <div className="row g-3 mb-4">
        <StatCol><StatPill value={pipeline.total_questions} label="Total Questions" tone="primary" /></StatCol>
        <StatCol><StatPill value={pipeline.draft} label="Draft" tone="secondary" /></StatCol>
        <StatCol><StatPill value={pipeline.submitted} label="Pending Review" tone="warning" /></StatCol>
        <StatCol><StatPill value={pipeline.approved} label="Approved" tone="success" /></StatCol>
        <StatCol><StatPill value={pipeline.rejected} label="Rejected" tone="danger" /></StatCol>
        <StatCol><StatPill value={pipeline.archived} label="Archived" tone="dark" /></StatCol>
        <StatCol><StatPill value={`${pipeline.approval_rate}%`} label="Approval Rate" tone="success" /></StatCol>
        <StatCol><StatPill value={`${pipeline.rejection_rate}%`} label="Rejection Rate" tone="danger" /></StatCol>
        <StatCol><StatPill value={`${pipeline.average_review_time_hours} h`} label="Avg Review Time" tone="info" /></StatCol>
      </div>
    </>
  );
};

// ---------------------------------------------------------------------
// Section 2 — Content Coverage
// ---------------------------------------------------------------------
const SectionCoverage = ({ coverage }) => (
  <Card title="Content Coverage" className="mb-4">
    <div className="row g-3 mb-3">
      <StatCol cols="col-md-3"><StatPill value={coverage.assigned_topics} label="Assigned Topics" tone="primary" /></StatCol>
      <StatCol cols="col-md-3"><StatPill value={coverage.topics_with_questions} label="Topics With Questions" tone="success" /></StatCol>
      <StatCol cols="col-md-3"><StatPill value={coverage.topics_missing_questions.length} label="Topics Missing" tone="danger" /></StatCol>
      <StatCol cols="col-md-3"><StatPill value={coverage.questions_per_domain.reduce((s, d) => s + d.count, 0)} label="My Questions" tone="info" /></StatCol>
    </div>

    {coverage.topics_missing_questions.length > 0 && (
      <div className="alert alert-warning mb-3">
        <strong>Topics with no questions yet:</strong>{" "}
        {coverage.topics_missing_questions.map((t) => t.topic_name).join(", ")}
      </div>
    )}

    <div className="row g-3">
      <div className="col-lg-6">
        <h6 className="text-muted mb-2">Questions per Topic</h6>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={coverage.questions_per_topic} layout="vertical" margin={{ left: 30 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="topic_name" width={160} fontSize={12} />
            <Tooltip />
            <Bar dataKey="count" fill="#0088FE" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="col-lg-6">
        <h6 className="text-muted mb-2">Questions per Domain</h6>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={coverage.questions_per_domain} dataKey="count" nameKey="domain_name"
                 cx="50%" cy="50%" outerRadius={90} label>
              {coverage.questions_per_domain.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="col-lg-6">
        <h6 className="text-muted mb-2">Questions per Bloom Level</h6>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={coverage.questions_per_bloom_level}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="bloom_level" fontSize={12} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#8884D8" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="col-lg-6">
        <h6 className="text-muted mb-2">Questions per Difficulty</h6>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={coverage.questions_per_difficulty}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="difficulty" fontSize={12} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#FFBB28" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  </Card>
);

// ---------------------------------------------------------------------
// Section 3 — Question Quality
// ---------------------------------------------------------------------
const QualityTable = ({ title, rows, emptyText }) => {
  if (!rows || rows.length === 0) {
    return (
      <div className="col-lg-6 mb-3">
        <h6 className="text-muted mb-2">{title}</h6>
        <p className="text-muted small">{emptyText}</p>
      </div>
    );
  }
  return (
    <div className="col-lg-4 mb-3">
      <h6 className="text-muted mb-2">{title}</h6>
      <div className="table-responsive">
        <table className="table table-sm table-hover mb-0">
          <thead className="table-light">
            <tr>
              <th style={{ width: "55%" }}>Question</th>
              <th>Attempts</th>
              <th>Accuracy</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 10).map((q) => (
              <tr key={q.question_id}>
                <td className="text-truncate" style={{ maxWidth: 220 }} title={q.text}>
                  {q.text}
                </td>
                <td>{q.total_attempts}</td>
                <td>
                  <Badge tone={q.accuracy >= 60 ? "success" : (q.accuracy >= 30 ? "warning" : "danger")}>
                    {q.accuracy}%
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const SectionQuality = ({ quality }) => {
  if (!quality) return null;
  return (
    <Card title="Question Quality" className="mb-4">
      <div className="row g-3 mb-3">
        <StatCol cols="col-md-3"><StatPill value={quality.times_used_total} label="Times Used Total" tone="info" /></StatCol>
      </div>
      {quality.times_used_total === 0 ? (
        <p className="text-muted small">
          No student attempts recorded on your questions yet. Quality metrics will
          appear once students start answering your questions.
        </p>
      ) : (
        <div className="row">
          <QualityTable title="Most Missed" rows={quality.most_missed} emptyText="No data yet." />
          <QualityTable title="Easiest"     rows={quality.easiest}    emptyText="No data yet." />
          <QualityTable title="Hardest"     rows={quality.hardest}    emptyText="No data yet." />
        </div>
      )}
      {(quality.most_missed && quality.most_missed.length > 0) && (
        <div className="row">
          <div className="col-12">
            <h6 className="text-muted mb-2">Top 10 — Most Missed (detailed)</h6>
            <div className="table-responsive">
              <table className="table table-sm table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th>Question</th><th>Attempts</th><th>Correct</th>
                    <th>Wrong</th><th>Accuracy</th><th>Avg Time (s)</th>
                  </tr>
                </thead>
                <tbody>
                  {quality.most_missed.map((q) => (
                    <tr key={q.question_id}>
                      <td className="text-truncate" style={{ maxWidth: 320 }} title={q.text}>{q.text}</td>
                      <td>{q.total_attempts}</td>
                      <td>{q.correct_count}</td>
                      <td>{q.wrong_count}</td>
                      <td><Badge tone="danger">{q.accuracy}%</Badge></td>
                      <td>{q.avg_response_time_seconds}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

// ---------------------------------------------------------------------
// Section 4 — Student Impact
// ---------------------------------------------------------------------
const SectionStudentImpact = ({ impact }) => {
  if (!impact) return null;
  const trendData = (impact.trend || []).map((t) => ({
    date: t.date,
    attempts: t.attempts,
    accuracy: t.average_accuracy,
  }));
  return (
    <Card title="Student Impact" className="mb-4">
      <div className="row g-3 mb-3">
        <StatCol cols="col-md-3"><StatPill value={impact.total_student_attempts} label="Attempts On My Questions" tone="info" /></StatCol>
        <StatCol cols="col-md-3"><StatPill value={impact.unique_students} label="Unique Students Reached" tone="primary" /></StatCol>
        <StatCol cols="col-md-3"><StatPill value={`${impact.average_accuracy}%`} label="Avg Accuracy" tone="success" /></StatCol>
        <StatCol cols="col-md-3"><StatPill value={`${impact.pass_rate}%`} label="Pass Rate" tone="warning" /></StatCol>
        <StatCol cols="col-md-3"><StatPill value={`${impact.average_score}%`} label="Avg Score" tone="info" /></StatCol>
      </div>

      {trendData.length > 0 ? (
        <>
          <h6 className="text-muted mb-2">Last 30 Days — Accuracy Trend</h6>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" fontSize={12} />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="accuracy" name="Avg Accuracy %" stroke="#2563eb" strokeWidth={3} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </>
      ) : (
        <p className="text-muted small">
          No student attempts on your questions in the last 30 days.
        </p>
      )}
    </Card>
  );
};

// ---------------------------------------------------------------------
// Section 5 — Approval History
// ---------------------------------------------------------------------
const SectionApprovalHistory = ({ approval }) => {
  if (!approval) return null;
  return (
    <Card title="Approval History" className="mb-4">
      <div className="row g-3 mb-3">
        <StatCol cols="col-md-3"><StatPill value={`${approval.average_approval_time_hours} h`} label="Avg Approval Time" tone="info" /></StatCol>
      </div>
      <div className="row g-3">
        <div className="col-lg-4">
          <h6 className="text-muted mb-2">Pending Review ({approval.pending_review.length})</h6>
          {approval.pending_review.length === 0 ? (
            <p className="text-muted small">No questions awaiting review.</p>
          ) : (
            <ul className="list-group list-group-flush">
              {approval.pending_review.map((q) => (
                <li key={q.question_id} className="list-group-item px-0 py-2">
                  <div className="fw-semibold text-truncate" title={q.text} style={{ maxWidth: 300 }}>{q.text}</div>
                  <small className="text-muted">{q.topic_name} · submitted {formatDateTime(q.submitted_at)}</small>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="col-lg-4">
          <h6 className="text-muted mb-2">Recently Approved ({approval.recently_approved.length})</h6>
          {approval.recently_approved.length === 0 ? (
            <p className="text-muted small">No approvals yet.</p>
          ) : (
            <ul className="list-group list-group-flush">
              {approval.recently_approved.map((q) => (
                <li key={q.question_id} className="list-group-item px-0 py-2">
                  <div className="fw-semibold text-truncate" title={q.text} style={{ maxWidth: 300 }}>{q.text}</div>
                  <small className="text-muted">{q.topic_name} · {formatDateTime(q.approved_at)}</small>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="col-lg-4">
          <h6 className="text-muted mb-2">Recently Rejected ({approval.recently_rejected.length})</h6>
          {approval.recently_rejected.length === 0 ? (
            <p className="text-muted small">No rejections yet.</p>
          ) : (
            <ul className="list-group list-group-flush">
              {approval.recently_rejected.map((q) => (
                <li key={q.question_id} className="list-group-item px-0 py-2">
                  <div className="fw-semibold text-truncate" title={q.text} style={{ maxWidth: 300 }}>{q.text}</div>
                  <small className="text-muted">{q.topic_name} · {formatDateTime(q.reviewed_at)}</small>
                  <div className="text-danger small mt-1">“{q.rejection_reason}”</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {approval.common_rejection_reasons.length > 0 && (
        <>
          <h6 className="text-muted mt-4 mb-2">Common Rejection Reasons</h6>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={approval.common_rejection_reasons} layout="vertical" margin={{ left: 60 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="reason" width={220} fontSize={11} />
              <Tooltip />
              <Bar dataKey="count" fill="#dc3545" />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </Card>
  );
};

// ---------------------------------------------------------------------
// Section 6 — Activity Timeline
// ---------------------------------------------------------------------
const SectionActivityTimeline = ({ timeline }) => {
  if (!timeline || timeline.length === 0) {
    return (
      <Card title="Activity Timeline" className="mb-4">
        <p className="text-muted small mb-0">No recent activity.</p>
      </Card>
    );
  }
  return (
    <Card title="Activity Timeline" className="mb-4">
      <div className="table-responsive">
        <table className="table table-sm table-hover mb-0">
          <thead className="table-light">
            <tr>
              <th style={{ width: 130 }}>When</th>
              <th style={{ width: 140 }}>Action</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {timeline.map((log) => {
              const meta = STATUS_BADGE[log.action] || { label: log.action, tone: "secondary" };
              return (
                <tr key={log.id}>
                  <td className="text-muted small">{formatDateTime(log.timestamp)}</td>
                  <td><Badge tone={meta.tone}>{meta.label}</Badge></td>
                  <td className="small">
                    {log.description}
                    <span className="text-muted ms-2">· {log.username}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

// ---------------------------------------------------------------------
// Section 7 — Productivity
// ---------------------------------------------------------------------
const SectionProductivity = ({ productivity }) => {
  if (!productivity) return null;
  const m = productivity.this_month || {};
  const trend = productivity.monthly_trend || [];
  return (
    <Card title="Productivity" className="mb-4">
      <div className="row g-3 mb-3">
        <StatCol cols="col-md-6 col-xl"><StatPill value={m.created} label="Created (this month)" tone="primary" /></StatCol>
        <StatCol cols="col-md-6 col-xl"><StatPill value={m.submitted} label="Submitted (this month)" tone="warning" /></StatCol>
        <StatCol cols="col-md-6 col-xl"><StatPill value={m.approved} label="Approved (this month)" tone="success" /></StatCol>
        <StatCol cols="col-md-6 col-xl"><StatPill value={m.rejected} label="Rejected (this month)" tone="danger" /></StatCol>
        <StatCol cols="col-md-6 col-xl"><StatPill value={m.updated} label="Updated (this month)" tone="info" /></StatCol>
      </div>

      {trend.length > 0 && (
        <>
          <h6 className="text-muted mb-2">6-Month Trend</h6>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" fontSize={12} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="created"  stroke="#0088FE" />
              <Line type="monotone" dataKey="submitted" stroke="#FFBB28" />
              <Line type="monotone" dataKey="approved"  stroke="#28a745" />
              <Line type="monotone" dataKey="rejected"  stroke="#dc3545" />
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </Card>
  );
};

// ---------------------------------------------------------------------
function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

export default TeacherAnalytics;