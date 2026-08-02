import { useEffect, useState, useCallback } from "react";
import api from "../api/api";
import { useAuth } from "../auth/AuthContext";
import {
  Users,
  Search,
  Filter,
  UserCheck,
  UserX,
  Key,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  X,
  Plus,
  UserPlus,
} from "lucide-react";

const ROLE_LABELS = {
  student: "Student",
  teacher: "Teacher",
  department_head: "Department Head",
  system_admin: "System Admin",
};

const UserManagement = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);

  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // New user form state
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    role: "student",
    department_id: "",
  });
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [formSuccess, setFormSuccess] = useState("");

  // Password reset modal state
  const [resetModalUser, setResetModalUser] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState("");

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = {
        page,
        page_size: 10,
      };
      if (search) params.search = search;
      if (roleFilter) params.role = roleFilter;
      if (statusFilter) params.is_active = statusFilter;

      const response = await api.get("/admin/users/", { params });
      setUsers(response.data.results || []);
      setTotalCount(response.data.count || 0);
      setTotalPages(response.data.total_pages || 1);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load users list.");
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter, statusFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  useEffect(() => {
    const loadDepartments = async () => {
      try {
        const response = await api.get("/exit-exams/departments/");
        setDepartments(response.data);
      } catch (err) {
        setFormError("Failed to load departments.");
      }
    };
    loadDepartments();
  }, []);

  const isDepartmentRequired = (role) =>
    role === "teacher" || role === "department_head";

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => {
      const next = { ...prev, [name]: value };
      if (name === "role" && !isDepartmentRequired(value)) {
        next.department_id = "";
      }
      return next;
    });
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    setFormSuccess("");

    if (isDepartmentRequired(form.role) && !form.department_id) {
      setFormError("Department is required for this role.");
      return;
    }

    setFormLoading(true);
    try {
      const payload = {
        username: form.username,
        email: form.email,
        password: form.password,
        role: form.role,
      };
      if (form.department_id) {
        payload.department_id = form.department_id;
      }

      await api.post("/users/admin-create-user/", payload);
      setForm({
        username: "",
        email: "",
        password: "",
        role: "student",
        department_id: "",
      });
      setFormSuccess("User created successfully.");
      await fetchUsers();
    } catch (err) {
      const data = err.response?.data;
      const messages = [];
      if (data) {
        Object.entries(data).forEach(([field, value]) => {
          const label = field === "detail" ? "" : `${field}: `;
          if (Array.isArray(value)) {
            messages.push(`${label}${value.join(" ")}`);
          } else {
            messages.push(`${label}${value}`);
          }
        });
      }
      setFormError(
        messages.length ? messages.join(" ") : "Failed to create user."
      );
    } finally {
      setFormLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleToggleActive = async (targetUser) => {
    if (targetUser.id === currentUser?.id) {
      setError("You cannot deactivate your own account.");
      return;
    }

    const actionText = targetUser.is_active ? "deactivate" : "reactivate";
    if (!window.confirm(`Are you sure you want to ${actionText} user "${targetUser.username}"?`)) {
      return;
    }

    setError("");
    setSuccess("");
    try {
      const res = await api.post(`/admin/users/${targetUser.id}/toggle-active/`);
      setSuccess(`User ${targetUser.username} has been ${res.data.is_active ? "reactivated" : "deactivated"}.`);
      fetchUsers();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to update user status.");
    }
  };

  const openResetModal = (user) => {
    setResetModalUser(user);
    setNewPassword("");
    setResetError("");
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!newPassword || newPassword.length < 8) {
      setResetError("Password must be at least 8 characters long.");
      return;
    }

    setResetLoading(true);
    setResetError("");
    try {
      await api.post(`/admin/users/${resetModalUser.id}/reset-password/`, {
        new_password: newPassword,
      });
      setSuccess(`Password successfully reset for ${resetModalUser.username}.`);
      setResetModalUser(null);
      setNewPassword("");
    } catch (err) {
      const errorMsg = err.response?.data?.error;
      if (Array.isArray(errorMsg)) {
        setResetError(errorMsg.join(" "));
      } else {
        setResetError(errorMsg || "Failed to reset password.");
      }
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">System Admin</span>
          <h2 className="fw-bold mt-2 mb-1">User Management</h2>
          <p className="text-muted mb-0">
            View, search, filter, activate/deactivate, and manage credentials for all platform users.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {success && (
        <div className="alert alert-success d-flex align-items-center gap-2 mb-4">
          <CheckCircle size={18} />
          <div>{success}</div>
        </div>
      )}

      {/* Create User Form */}
      <div className="card border-0 shadow-sm rounded-4 mb-4">
        <div className="card-body p-4">
          <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
            <UserPlus size={18} className="text-primary" />
            <span>New User</span>
          </h5>

          {formError && (
            <div className="alert alert-danger d-flex align-items-center gap-2 mb-3">
              <AlertCircle size={18} />
              <div>{formError}</div>
            </div>
          )}

          {formSuccess && (
            <div className="alert alert-success d-flex align-items-center gap-2 mb-3">
              <CheckCircle size={18} />
              <div>{formSuccess}</div>
            </div>
          )}

          <form onSubmit={handleFormSubmit}>
            <div className="row g-3">
              <div className="col-md-6 col-lg-3">
                <label className="form-label fw-medium">Username</label>
                <input
                  type="text"
                  name="username"
                  className="form-control rounded-3"
                  placeholder="Username"
                  value={form.username}
                  onChange={handleFormChange}
                  required
                />
              </div>

              <div className="col-md-6 col-lg-3">
                <label className="form-label fw-medium">Email</label>
                <input
                  type="email"
                  name="email"
                  className="form-control rounded-3"
                  placeholder="Email"
                  value={form.email}
                  onChange={handleFormChange}
                  required
                />
              </div>

              <div className="col-md-6 col-lg-3">
                <label className="form-label fw-medium">Password</label>
                <input
                  type="password"
                  name="password"
                  className="form-control rounded-3"
                  placeholder="Password"
                  value={form.password}
                  onChange={handleFormChange}
                  required
                  minLength={6}
                />
              </div>

              <div className="col-md-6 col-lg-2">
                <label className="form-label fw-medium">Role</label>
                <select
                  name="role"
                  className="form-select rounded-3"
                  value={form.role}
                  onChange={handleFormChange}
                  required
                >
                  <option value="student">Student</option>
                  <option value="teacher">Teacher</option>
                  <option value="department_head">Department Head</option>
                </select>
              </div>

              <div className="col-md-6 col-lg-3">
                <label className="form-label fw-medium">
                  Department
                  {isDepartmentRequired(form.role) && (
                    <span className="text-danger">*</span>
                  )}
                </label>
                <select
                  name="department_id"
                  className="form-select rounded-3"
                  value={form.department_id}
                  onChange={handleFormChange}
                  required={isDepartmentRequired(form.role)}
                >
                  <option value="">
                    {isDepartmentRequired(form.role)
                      ? "Select department"
                      : "— Optional —"}
                  </option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="col-md-6 col-lg-2 d-flex align-items-end">
                <button
                  type="submit"
                  className="btn btn-primary w-100 rounded-3"
                  disabled={formLoading}
                >
                  {formLoading ? (
                    "Creating..."
                  ) : (
                    <>
                      <Plus size={16} className="me-1" />
                      Create User
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card border-0 shadow-sm rounded-4 mb-4">
        <div className="card-body p-4">
          <form onSubmit={handleSearchSubmit} className="row g-3 align-items-center">
            <div className="col-lg-5">
              <div className="input-group">
                <span className="input-group-text bg-white border-end-0">
                  <Search size={18} className="text-muted" />
                </span>
                <input
                  type="text"
                  className="form-control border-start-0 ps-0"
                  placeholder="Search by username, email, or name..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            <div className="col-md-3 col-lg-3">
              <div className="input-group">
                <span className="input-group-text bg-white border-end-0">
                  <Filter size={18} className="text-muted" />
                </span>
                <select
                  className="form-select border-start-0 ps-0"
                  value={roleFilter}
                  onChange={(e) => {
                    setRoleFilter(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">All Roles</option>
                  <option value="student">Student</option>
                  <option value="teacher">Teacher</option>
                  <option value="department_head">Department Head</option>
                  <option value="system_admin">System Admin</option>
                </select>
              </div>
            </div>

            <div className="col-md-3 col-lg-2">
              <select
                className="form-select"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Statuses</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </div>

            <div className="col-md-2 col-lg-2 d-flex gap-2">
              <button type="submit" className="btn btn-primary w-100">
                Search
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Users Table */}
      <div className="card border-0 shadow-sm rounded-4">
        <div className="card-header bg-transparent border-0 pt-4 px-4 pb-0 d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-2 fw-bold text-dark">
            <Users size={20} className="text-primary" />
            <span>Users ({totalCount})</span>
          </div>
        </div>

        <div className="card-body p-4">
          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="small text-muted mt-2">Loading users...</p>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <Users size={48} className="mb-2 opacity-50" />
              <p className="mb-0">No users found matching your filter criteria.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead className="table-light">
                  <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>Department</th>
                    <th>Status</th>
                    <th>Joined</th>
                    <th className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div className="fw-semibold">{u.username}</div>
                        <div className="small text-muted">{u.email}</div>
                      </td>
                      <td>
                        <span className={`badge ${u.role === "system_admin" ? "bg-purple text-white" : u.role === "department_head" ? "bg-info text-dark" : u.role === "teacher" ? "bg-primary" : "bg-secondary"}`}>
                          {ROLE_LABELS[u.role] || u.role}
                        </span>
                      </td>
                      <td>
                        <span className="small text-dark">
                          {u.department || <span className="text-muted">—</span>}
                        </span>
                      </td>
                      <td>
                        {u.is_active ? (
                          <span className="badge bg-success-subtle text-success border border-success-subtle">
                            Active
                          </span>
                        ) : (
                          <span className="badge bg-danger-subtle text-danger border border-danger-subtle">
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="small text-muted">
                        {u.date_joined ? new Date(u.date_joined).toLocaleDateString() : "—"}
                      </td>
                      <td className="text-end">
                        <div className="btn-group">
                          <button
                            className={`btn btn-sm ${u.is_active ? "btn-outline-danger" : "btn-outline-success"}`}
                            onClick={() => handleToggleActive(u)}
                            disabled={u.id === currentUser?.id}
                            title={u.id === currentUser?.id ? "Cannot deactivate yourself" : u.is_active ? "Deactivate Account" : "Reactivate Account"}
                          >
                            {u.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                          </button>
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() => openResetModal(u)}
                            title="Reset Password"
                          >
                            <Key size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center pt-3 border-top mt-3">
              <span className="small text-muted">
                Page {page} of {totalPages} ({totalCount} total)
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

      {/* Password Reset Modal */}
      {resetModalUser && (
        <div
          className="modal fade show d-block"
          tabIndex="-1"
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow rounded-4">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold">
                  Reset Password for {resetModalUser.username}
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setResetModalUser(null)}
                />
              </div>

              <form onSubmit={handleResetPassword}>
                <div className="modal-body py-4">
                  {resetError && (
                    <div className="alert alert-danger small mb-3">
                      {resetError}
                    </div>
                  )}

                  <div className="mb-3">
                    <label className="form-label fw-medium">New Password</label>
                    <input
                      type="password"
                      className="form-control rounded-3"
                      placeholder="Enter new temporary password (min 8 chars)"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={8}
                    />
                    <small className="form-text text-muted">
                      Admin password reset does not require entering the old password.
                    </small>
                  </div>
                </div>

                <div className="modal-footer border-0 pt-0">
                  <button
                    type="button"
                    className="btn btn-secondary rounded-3"
                    onClick={() => setResetModalUser(null)}
                    disabled={resetLoading}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary rounded-3 px-4"
                    disabled={resetLoading}
                  >
                    {resetLoading ? "Resetting..." : "Confirm Reset"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
