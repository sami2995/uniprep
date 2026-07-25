import { useEffect, useState } from "react";
import api from "../api/api";
import { Building2, Plus, Edit2, Trash2, BookOpen, AlertCircle, CheckCircle } from "lucide-react";

const Departments = () => {
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({
    name: "",
    code: "",
    description: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Edit modal state
  const [editingDept, setEditingDept] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", code: "", description: "" });
  const [editLoading, setEditLoading] = useState(false);

  useEffect(() => {
    fetchDepartments();
  }, []);

  const fetchDepartments = async () => {
    try {
      const response = await api.get("/exit-exams/departments/");
      setDepartments(response.data);
    } catch (err) {
      setError("Failed to load departments.");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      await api.post("/exit-exams/departments/", form);
      setForm({ name: "", code: "", description: "" });
      setSuccess("Department created successfully.");
      await fetchDepartments();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create department.");
    }
  };

  const openEditModal = (dept) => {
    setEditingDept(dept);
    setEditForm({
      name: dept.name,
      code: dept.code,
      description: dept.description || "",
    });
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setEditLoading(true);
    setError("");
    setSuccess("");

    try {
      await api.patch(`/admin/departments/${editingDept.id}/`, editForm);
      setSuccess(`Department "${editForm.name}" updated successfully.`);
      setEditingDept(null);
      await fetchDepartments();
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || "Failed to update department.");
    } finally {
      setEditLoading(false);
    }
  };

  const handleDelete = async (dept) => {
    if (!window.confirm(`Are you sure you want to delete department "${dept.name}" (${dept.code})?`)) {
      return;
    }

    setError("");
    setSuccess("");

    try {
      await api.delete(`/admin/departments/${dept.id}/`);
      setSuccess(`Department "${dept.name}" deleted successfully.`);
      await fetchDepartments();
    } catch (err) {
      const errMsg = err.response?.data?.error || err.response?.data?.detail || "Failed to delete department.";
      setError(errMsg);
    }
  };

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">System Admin</span>
          <h2 className="fw-bold mt-2 mb-1">Departments</h2>
          <p className="text-muted mb-0">
            Manage institutional departments used by academic courses.
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

      <div className="row g-4">
        {/* Create Department Form */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
                <Plus size={18} className="text-primary" />
                <span>Create Department</span>
              </h5>

              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label className="form-label fw-medium">Department Name</label>
                  <input
                    className="form-control rounded-3"
                    placeholder="e.g. Computer Science"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-medium">Department Code</label>
                  <input
                    className="form-control rounded-3"
                    placeholder="e.g. CS"
                    value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value })}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label fw-medium">Description</label>
                  <textarea
                    className="form-control rounded-3"
                    rows="3"
                    placeholder="Brief description of department scope..."
                    value={form.description}
                    onChange={(e) =>
                      setForm({ ...form, description: e.target.value })
                    }
                  />
                </div>

                <button className="btn btn-primary w-100 rounded-3">
                  Add Department
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Department List */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
                <Building2 size={18} className="text-primary" />
                <span>Department List</span>
              </h5>

              {departments.length === 0 ? (
                <p className="text-muted mb-0">No departments configured yet.</p>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle">
                    <thead className="table-light">
                      <tr>
                        <th>Code</th>
                        <th>Name & Description</th>
                        <th>Courses</th>
                        <th className="text-end">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {departments.map((dept) => (
                        <tr key={dept.id}>
                          <td>
                            <span className="badge bg-primary-subtle text-primary border border-primary-subtle fw-bold">
                              {dept.code}
                            </span>
                          </td>
                          <td>
                            <strong className="d-block">{dept.name}</strong>
                            <small className="text-muted">
                              {dept.description || "No description provided"}
                            </small>
                          </td>
                          <td>
                            <span className="badge bg-light text-dark border d-inline-flex align-items-center gap-1">
                              <BookOpen size={13} />
                              {dept.course_count ?? 0} {dept.course_count === 1 ? "course" : "courses"}
                            </span>
                          </td>
                          <td className="text-end">
                            <div className="btn-group">
                              <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => openEditModal(dept)}
                                title="Edit Department"
                              >
                                <Edit2 size={14} />
                              </button>
                              <button
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => handleDelete(dept)}
                                title="Delete Department"
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
      </div>

      {/* Edit Department Modal */}
      {editingDept && (
        <div
          className="modal fade show d-block"
          tabIndex="-1"
          style={{ backgroundColor: "rgba(0,0,0,0.5)" }}
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow rounded-4">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold">
                  Edit Department: {editingDept.code}
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setEditingDept(null)}
                />
              </div>

              <form onSubmit={handleEditSubmit}>
                <div className="modal-body py-4">
                  <div className="mb-3">
                    <label className="form-label fw-medium">Department Name</label>
                    <input
                      className="form-control rounded-3"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      required
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label fw-medium">Department Code</label>
                    <input
                      className="form-control rounded-3"
                      value={editForm.code}
                      onChange={(e) => setEditForm({ ...editForm, code: e.target.value })}
                      required
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label fw-medium">Description</label>
                    <textarea
                      className="form-control rounded-3"
                      rows="3"
                      value={editForm.description}
                      onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    />
                  </div>
                </div>

                <div className="modal-footer border-0 pt-0">
                  <button
                    type="button"
                    className="btn btn-secondary rounded-3"
                    onClick={() => setEditingDept(null)}
                    disabled={editLoading}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary rounded-3 px-4"
                    disabled={editLoading}
                  >
                    {editLoading ? "Saving..." : "Save Changes"}
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

export default Departments;
