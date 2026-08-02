import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { normalizeRole, getDefaultPathForRole } from "../routes/roleRoutes";
import NotificationBell from "./NotificationBell";

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const normalizedRole = user ? normalizeRole(user.role) : null;
  const isStudent = normalizedRole === "student";
  const isTeacher = normalizedRole === "teacher";
  const isDepartmentHead = normalizedRole === "department_head";
  const isSystemAdmin = normalizedRole === "system_admin";

  const brandTo =
    user && normalizedRole ? getDefaultPathForRole(normalizedRole) : "/";

  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-white border-bottom">
      <div className="container">
        <Link className="navbar-brand fw-bold text-primary" to={brandTo}>
          UniPrep AI
        </Link>

        <div className="d-flex gap-2 align-items-center flex-wrap">
          {user ? (
            <>
              {isStudent && (
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

              {isTeacher && (
                <>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/teacher/dashboard"
                  >
                    Dashboard
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/teacher/courses"
                  >
                    My Courses
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/teacher/questions"
                  >
                    Questions
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/teacher/materials"
                  >
                    Materials
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/teacher/analytics"
                  >
                    Analytics
                  </Link>
                </>
              )}

              {isDepartmentHead && (
                <>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/department-head/dashboard"
                  >
                    Dashboard
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/department-head/academic"
                  >
                    Academic Structure
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/department-head/question-approval"
                  >
                    Question Approval
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/department-head/exam-bank"
                  >
                    Exam Bank
                  </Link>
                </>
              )}

              {isSystemAdmin && (
                <>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/system-admin/dashboard"
                  >
                    Dashboard
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/system-admin/departments"
                  >
                    Departments
                  </Link>
                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/system-admin/users"
                  >
                    Users
                  </Link>
                </>
              )}

              <span className="small text-muted ms-2">
                {user.username}
              </span>

              <NotificationBell />

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
