import { useEffect, useState } from "react";
import api from "../api/api";

const ACTION_COLORS = {
  created: "primary",
  updated: "secondary",
  submitted: "warning",
  approved: "success",
  rejected: "danger",
  blueprint_changed: "info",
  assignment_changed: "dark",
};

const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const [filters, setFilters] = useState({
    entity_type: "",
    action: "",
    user_id: "",
  });

  const [expandedId, setExpandedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: 25 });
      if (filters.entity_type) params.set("entity_type", filters.entity_type);
      if (filters.action) params.set("action", filters.action);
      if (filters.user_id) params.set("user_id", filters.user_id);

      const res = await api.get(`/exit-exams/audit-logs/?${params}`);
      setLogs(res.data.results || []);
      setTotalPages(res.data.total_pages || 1);
      setTotalCount(res.data.count || 0);
    } catch {
      setError("Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
    setPage(1);
  };

  const toggleExpand = (id) => setExpandedId(expandedId === id ? null : id);

  return (
    <div className="container-fluid py-4">
      {/* Hero */}
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Department Head</span>
          <h2 className="fw-bold mt-2 mb-1">Audit Logs</h2>
          <p className="text-muted mb-0">
            Full history of question, blueprint, and assignment changes.
          </p>
        </div>
        <span className="badge bg-secondary fs-6 px-3 py-2">{totalCount} entries</span>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {/* Filters */}
      <div className="card border-0 shadow-sm rounded-4 mb-4">
        <div className="card-body p-3">
          <div className="row g-2">
            <div className="col-md-3">
              <select
                name="entity_type"
                className="form-select form-select-sm"
                value={filters.entity_type}
                onChange={handleFilterChange}
              >
                <option value="">All Entity Types</option>
                <option value="question">Question</option>
                <option value="blueprint">Blueprint</option>
                <option value="assignment">Assignment</option>
              </select>
            </div>
            <div className="col-md-3">
              <select
                name="action"
                className="form-select form-select-sm"
                value={filters.action}
                onChange={handleFilterChange}
              >
                <option value="">All Actions</option>
                <option value="created">Created</option>
                <option value="updated">Updated</option>
                <option value="submitted">Submitted</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="blueprint_changed">Blueprint Changed</option>
                <option value="assignment_changed">Assignment Changed</option>
              </select>
            </div>
            <div className="col-md-3">
              <input
                name="user_id"
                className="form-control form-control-sm"
                placeholder="Filter by User ID…"
                value={filters.user_id}
                onChange={handleFilterChange}
              />
            </div>
            <div className="col-md-3">
              <button
                className="btn btn-sm btn-outline-secondary w-100"
                onClick={() => {
                  setFilters({ entity_type: "", action: "", user_id: "" });
                  setPage(1);
                }}
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Log Table */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status" />
        </div>
      ) : logs.length === 0 ? (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-5 text-center">
            <div style={{ fontSize: "3rem" }}>📋</div>
            <h5 className="fw-bold mt-3">No audit logs found</h5>
            <p className="text-muted">Logs will appear as actions are performed.</p>
          </div>
        </div>
      ) : (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead className="table-light">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="py-3">User</th>
                    <th className="py-3">Action</th>
                    <th className="py-3">Entity</th>
                    <th className="py-3">Description</th>
                    <th className="py-3">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <>
                      <tr key={log.id}>
                        <td className="px-4 py-3 text-muted small text-nowrap">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="py-3">
                          <span className="fw-semibold small">{log.username}</span>
                        </td>
                        <td className="py-3">
                          <span
                            className={`badge bg-${ACTION_COLORS[log.action] || "secondary"} text-capitalize`}
                          >
                            {log.action.replace("_", " ")}
                          </span>
                        </td>
                        <td className="py-3 small">
                          <span className="text-capitalize">{log.entity_type}</span>
                          <span className="text-muted"> #{log.entity_id}</span>
                        </td>
                        <td className="py-3 small text-muted" style={{ maxWidth: 260 }}>
                          <span className="text-truncate d-block">{log.description || "—"}</span>
                        </td>
                        <td className="py-3">
                          {(Object.keys(log.previous_value || {}).length > 0 ||
                            Object.keys(log.new_value || {}).length > 0) && (
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => toggleExpand(log.id)}
                            >
                              {expandedId === log.id ? "Hide" : "Show"}
                            </button>
                          )}
                        </td>
                      </tr>
                      {expandedId === log.id && (
                        <tr key={`${log.id}-detail`} className="table-light">
                          <td colSpan={6} className="px-4 py-3">
                            <div className="row g-3">
                              {Object.keys(log.previous_value || {}).length > 0 && (
                                <div className="col-md-6">
                                  <h6 className="fw-bold small text-muted mb-2">Before</h6>
                                  <pre
                                    className="small bg-white border rounded p-2 mb-0"
                                    style={{ fontSize: "0.75rem", maxHeight: 200, overflowY: "auto" }}
                                  >
                                    {JSON.stringify(log.previous_value, null, 2)}
                                  </pre>
                                </div>
                              )}
                              {Object.keys(log.new_value || {}).length > 0 && (
                                <div className="col-md-6">
                                  <h6 className="fw-bold small text-muted mb-2">After</h6>
                                  <pre
                                    className="small bg-white border rounded p-2 mb-0"
                                    style={{ fontSize: "0.75rem", maxHeight: 200, overflowY: "auto" }}
                                  >
                                    {JSON.stringify(log.new_value, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="d-flex justify-content-center gap-2 mt-4">
          <button
            className="btn btn-sm btn-outline-secondary"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            ← Prev
          </button>
          <span className="btn btn-sm btn-light disabled">
            {page} / {totalPages}
          </span>
          <button
            className="btn btn-sm btn-outline-secondary"
            disabled={page === totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
};

export default AuditLogs;
