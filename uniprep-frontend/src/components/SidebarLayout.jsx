import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const SidebarLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const studentLinks = [
    { label: "Dashboard", path: "/student/dashboard", icon: "🏠" },
    { label: "Exams", path: "/student/exams", icon: "📝" },
    { label: "Battle", path: "/student/battle", icon: "⚔️" },
    { label: "Results", path: "/student/results", icon: "📊" },
    { label: "Materials", path: "/student/materials", icon: "📚" },
    { label: "Focus", path: "/student/focus", icon: "⏱" },
  ];

  const adminLinks = [
    { label: "Dashboard", path: "/admin/dashboard", icon: "🏠" },
    { label: "Academic", path: "/admin/academic", icon: "🎓" },
    { label: "Questions", path: "/admin/questions", icon: "❓" },
    { label: "PDF Imports", path: "/admin/pdf-imports", icon: "📄" },
    { label: "Blueprints", path: "/admin/blueprints", icon: "🧩" },
  ];

  const links = user?.role === "admin" ? adminLinks : studentLinks;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" className="sidebar-logo">
          <span className="sidebar-logo-icon">U</span>
          <div>
            <strong>UniPrep AI</strong>
            <small>{user?.role === "admin" ? "Admin Panel" : "Student Portal"}</small>
          </div>
        </Link>

        <nav className="sidebar-nav">
          {links.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              className={({ isActive }) =>
                isActive ? "sidebar-link active" : "sidebar-link"
              }
            >
              <span>{link.icon}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <strong>{user?.username}</strong>
            <small>{user?.role}</small>
          </div>

          <button className="sidebar-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default SidebarLayout;