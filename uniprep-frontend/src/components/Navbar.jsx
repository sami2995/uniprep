import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-white border-bottom">
      <div className="container">
        <Link className="navbar-brand fw-bold text-primary" to="/">
          UniPrep AI
        </Link>

        <div className="d-flex gap-2 align-items-center flex-wrap">
          {user ? (
            <>
              {user.role === "admin" ? (
                <>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/admin/dashboard"
                  >
                    Admin Dashboard
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/admin/academic"
                  >
                    Academic
                  </Link>
                  <Link
  className="btn btn-outline-primary btn-sm"
  to="/admin/questions"
>
  Questions
</Link>
<Link
  className="btn btn-outline-primary btn-sm"
  to="/admin/pdf-imports"
>
  PDF Imports
</Link>
<Link
  className="btn btn-outline-primary btn-sm"
  to="/admin/blueprints"
>
  Blueprints
</Link>
                </>
              ) : (
                <>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/student/dashboard"
                  >
                    Dashboard
                  </Link>

                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/student/exams"
                  >
                    Exams
                  </Link>

                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/student/results"
                  >
                    Results
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/student/materials"
                  >
                    Materials
</Link>
<Link
  className="btn btn-outline-primary btn-sm"
  to="/student/focus"
>
  Focus
</Link>
                </>
              )}

              <span className="small text-muted ms-2">
                {user.username}
              </span>

              <button
                className="btn btn-danger btn-sm"
                onClick={handleLogout}
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link className="btn btn-outline-primary btn-sm" to="/login">
                Login
              </Link>

              <Link className="btn btn-primary btn-sm" to="/register">
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;