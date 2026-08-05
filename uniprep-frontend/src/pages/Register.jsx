import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: "",
    email: "",
    student_id: "",
    department: "Computer Science",
    program: "Computer Science",
    year_of_study: 4,
    password: "",
    password2: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
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
      setError("Registration failed. Check your inputs.");
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
                    <label className="form-label">Department</label>
                    <input
                      name="department"
                      className="form-control"
                      value={form.department}
                      onChange={handleChange}
                    />
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
