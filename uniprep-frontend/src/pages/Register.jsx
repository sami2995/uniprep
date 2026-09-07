import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import api from "../api/api";

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: "",
    email: "",
    student_id: "",
    department: "",
    program: "Computer Science",
    year_of_study: 4,
    password: "",
    password2: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [departmentsLoading, setDepartmentsLoading] = useState(true);

  useEffect(() => {
    const loadDepartments = async () => {
      try {
        const response = await api.get("/users/registration-departments/");
        setDepartments(response.data || []);
      } catch {
        // Allow registering without departments if DB has no departments
        setDepartments([]);
      } finally {
        setDepartmentsLoading(false);
      }
    };

    loadDepartments();
  }, []);

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const getErrorMessage = (err) => {
    if (!err) return "Registration failed. Please try again.";

    if (err.code === "ERR_NETWORK" || err.message?.toLowerCase().includes("network")) {
      return "Cannot connect to server. Please check your internet connection or verify the backend service status.";
    }

    const response = err.response;
    if (!response) {
      return err.message || "Registration failed. Please try again.";
    }

    const { status, data } = response;

    if (status >= 500) {
      return `Server error (${status}): The backend database or service is temporarily unavailable. Please try again in a moment.`;
    }

    if (typeof data === "string") {
      if (data.includes("<html") || data.includes("<!DOCTYPE")) {
        return `Server returned an error page (${status}). Please try again later.`;
      }
      return data;
    }

    if (typeof data === "object" && data !== null) {
      if (data.detail) return data.detail;
      if (data.error) return data.error;

      const entries = Object.entries(data);
      if (entries.length > 0) {
        return entries
          .map(([field, value]) => {
            const formattedField = field
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase());
            const text = Array.isArray(value) ? value.join(" ") : String(value);
            return field === "non_field_errors" ? text : `${formattedField}: ${text}`;
          })
          .join(" | ");
      }
    }

    return `Registration failed (${status}). Please check your inputs and try again.`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (form.password !== form.password2) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await register(form);
      navigate("/login");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="container py-5">
        <div className="row justify-content-center">
          <div className="col-md-7">
            <div className="card auth-card shadow-sm border-0 rounded-4">
              <div className="card-body p-4">
                <div className="auth-brand mb-4">
                  <span className="auth-brand-icon" aria-hidden="true">
                    <GraduationCap size={20} />
                  </span>
                  <span className="auth-brand-name">UniPrep AI</span>
                </div>

                <h3 className="fw-bold mb-1 auth-title">Create your account</h3>
                <p className="auth-subtitle mb-4">
                  Start practicing with your department&rsquo;s approved
                  question bank.
                </p>

                {error && <div className="alert alert-danger">{error}</div>}

                <form onSubmit={handleSubmit}>
                  <div className="row">
                    <div className="col-md-6 mb-3">
                      <label className="form-label">Username</label>
                      <input
                        name="username"
                        className="form-control"
                        value={form.username}
                        onChange={handleChange}
                        required
                      />
                    </div>

                    <div className="col-md-6 mb-3">
                      <label className="form-label">Email</label>
                      <input
                        type="email"
                        name="email"
                        className="form-control"
                        value={form.email}
                        onChange={handleChange}
                        required
                      />
                    </div>
                  </div>

                  <div className="row">
                    <div className="col-md-6 mb-3">
                      <label className="form-label">Student ID</label>
                      <input
                        name="student_id"
                        className="form-control"
                        value={form.student_id}
                        onChange={handleChange}
                        placeholder="Optional"
                      />
                    </div>

                    <div className="col-md-6 mb-3">
                      <label className="form-label">Year of Study</label>
                      <input
                        type="number"
                        name="year_of_study"
                        className="form-control"
                        value={form.year_of_study}
                        onChange={handleChange}
                      />
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label">
                      Department <span className="text-muted small fw-normal">(optional)</span>
                    </label>
                    {departments.length > 0 ? (
                      <select
                        name="department"
                        className="form-control"
                        value={form.department}
                        onChange={handleChange}
                        disabled={departmentsLoading}
                      >
                        <option value="">
                          {departmentsLoading ? "Loading departments..." : "Select your department (optional)"}
                        </option>
                        {departments.map((department) => (
                          <option key={department.id} value={department.name}>
                            {department.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        name="department"
                        className="form-control"
                        placeholder="e.g. Computer Science (optional)"
                        value={form.department}
                        onChange={handleChange}
                        disabled={departmentsLoading}
                      />
                    )}
                  </div>

                  <div className="mb-3">
                    <label className="form-label">Program</label>
                    <input
                      name="program"
                      className="form-control"
                      value={form.program}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="row">
                    <div className="col-md-6 mb-3">
                      <label className="form-label">Password</label>
                      <input
                        type="password"
                        name="password"
                        className="form-control"
                        value={form.password}
                        onChange={handleChange}
                        required
                      />
                    </div>

                    <div className="col-md-6 mb-4">
                      <label className="form-label">Confirm Password</label>
                      <input
                        type="password"
                        name="password2"
                        className="form-control"
                        value={form.password2}
                        onChange={handleChange}
                        required
                      />
                    </div>
                  </div>

                  <button className="btn btn-primary w-100" disabled={loading}>
                    {loading ? "Creating account..." : "Register"}
                  </button>
                </form>

                <p className="small text-muted mt-3 mb-0">
                  Already have an account? <Link to="/login">Login here</Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
