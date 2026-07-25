import { useEffect, useState, useCallback } from "react";
import api from "../api/api";
import {
  ScrollText,
  Filter,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  User,
  Clock,
} from "lucide-react";

const ACTION_LABELS = {
  created: "Created",
  updated: "Updated",
  submitted: "Submitted",
  approved: "Approved",
  rejected: "Rejected",
  blueprint_changed: "Blueprint Changed",
  assignment_changed: "Assignment Changed",
  system_settings_updated: "System Settings Updated",
  user_deactivated: "User Deactivated",
  user_reactivated: "User Reactivated",
  password_reset_by_admin: "Password Reset By Admin",
};

const ACTION_BADGES = {
  approved: "bg-success text-white",
  created: "bg-primary text-white",
  updated: "bg-info text-dark",
  submitted: "bg-warning text-dark",
  rejected: "bg-danger text-white",
  system_settings_updated: "bg-purple text-white",
  user_deactivated: "bg-danger text-white",
  user_reactivated: "bg-success text-white",
  password_reset_by_admin: "bg-warning text-dark",
};

const ActivityLog = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [error, setError] = useState("");

  const fetchAuditLogs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = {
        page,
        page_size: 20,
      };
      if (actionFilter) params.action = actionFilter;

      const response = await api.get("/admin/audit-log/", { params });
      setLogs(response.data.results || []);
      setTotalCount(response.data.count || 0);
      setTotalPages(response.data.total_pages || 1);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  }, [page, actionFilter]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">System Admin</span>
          <h2 className="fw-bold mt-2 mb-1">Activity Log</h2>
          <p className="text-muted mb-0">
            System-wide audit trail tracking administrative updates, user management actions, and content changes.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {/* Filter Bar */}
      <div className="card border-0 shadow-sm rounded-4 mb-4">
        <div className="card-body p-4">
          <div className="row g-3 align-items-center">
            <div className="col-md-6 col-lg-4">
              <div className="input-group">
                <span className="input-group-text bg-white border-end-0">
                  <Filter size={18} className="text-muted" />
                </span>
                <select
                  className="form-select border-start-0 ps-0"
                  value={actionFilter}
                  onChange={(e) => {
                    setActionFilter(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">All Action Types</option>
                  <option value="system_settings_updated">System Settings Updated</option>
                  <option value="user_deactivated">User Deactivated</option>
                  <option value="user_reactivated">User Reactivated</option>
                  <option value="password_reset_by_admin">Password Reset By Admin</option>
                  <option value="created">Created</option>
                  <option value="updated">Updated</option>
                  <option value="submitted">Submitted</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                  <option value="blueprint_changed">Blueprint Changed</option>
                  <option value="assignment_changed">Assignment Changed</option>
                </select>
              </div>
            </div>

            <div className="col-md-6 col-lg-8 text-md-end">
              <span className="small text-muted">
                Showing {logs.length} of {totalCount} total audit events
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="card border-0 shadow-sm rounded-4">
        <div className="card-header bg-transparent border-0 pt-4 px-4 pb-0">
          <div className="d-flex align-items-center gap-2 fw-bold text-dark">
            <ScrollText size={20} className="text-primary" />
            <span>Audit Trail ({totalCount})</span>
          </div>
        </div>

        <div className="card-body p-4">
          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="small text-muted mt-2">Loading audit events...</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <ScrollText size={48} className="mb-2 opacity-50" />
              <p className="mb-0">No audit log records found for the selected action type.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead className="table-light">
                  <tr>
                    <th>Timestamp</th>
                    <th>Actor</th>
                    <th>Action</th>
                    <th>Target Entity</th>
                    <th>Description & Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => {
                    const badgeClass = ACTION_BADGES[log.action] || "bg-secondary text-white";
                    const actionLabel = ACTION_LABELS[log.action] || log.action;

                    return (
                      <tr key={log.id}>
                        <td className="small text-nowrap text-muted">
                          <div className="d-flex align-items-center gap-1">
                            <Clock size={14} />
                            <span>{new Date(log.timestamp).toLocaleString()}</span>
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-2">
                            <User size={15} className="text-primary" />
                            <span className="fw-semibold">
                              {log.user_username || log.username || (log.user ? `User #${log.user}` : "System")}
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${badgeClass}`}>
                            {actionLabel}
                          </span>
                        </td>
                        <td>
                          <span className="small text-muted">
                            {log.entity_type ? `${log.entity_type} #${log.entity_id}` : "N/A"}
                          </span>
                        </td>
                        <td>
                          <div className="small">
                            {log.description && <div className="fw-medium text-dark mb-1">{log.description}</div>}
                            {log.new_value && Object.keys(log.new_value).length > 0 && (
                              <code className="text-muted bg-light p-1 rounded d-inline-block" style={{ fontSize: "0.8em" }}>
                                {JSON.stringify(log.new_value)}
                              </code>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center pt-3 border-top mt-3">
              <span className="small text-muted">
                Page {page} of {totalPages}
              </span>
              <div className="btn-group">
                <button
                  className="btn btn-outline-secondary btn-sm"
                  disabled={page <= 1 || loading}
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                >
                  <ChevronLeft size={16} /> Prev
                </button>
                <button
                  className="btn btn-outline-secondary btn-sm"
                  disabled={page >= totalPages || loading}
                  onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ActivityLog;
