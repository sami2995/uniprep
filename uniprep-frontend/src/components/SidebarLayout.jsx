import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Archive,
  BarChart3,
  BookOpen,
  Brain,
  Building2,
  CheckSquare,
  CircleHelp,
  FileText,
  GraduationCap,
  Home,
  Network,
  ScrollText,
  Settings,
  Settings2,
  Timer,
  UserCheck,
  Users,
  Zap,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { SIDEBAR_LINKS, normalizeRole, getDefaultPathForRole } from "../routes/roleRoutes";
import NotificationBell from "./NotificationBell";
import ProfileDropdown from "./ProfileDropdown";

const ICONS = {
  Archive,
  BarChart3,
  BookOpen,
  Brain,
  Building2,
  CheckSquare,
  CircleHelp,
  FileText,
  GraduationCap,
  Home,
  Network,
  ScrollText,
  Settings,
  Settings2,
  Timer,
  UserCheck,
  Users,
  Zap,
};

const PORTAL_LABELS = {
  student: "Student Portal",
  teacher: "Teacher Portal",
  department_head: "Department Head",
  system_admin: "System Admin",
};

const SidebarLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const role = normalizeRole(user?.role);
  const links = (SIDEBAR_LINKS[role] || []).filter((link) => {
    if (role !== "student" || user?.verification === "verified") return true;
    return !["/student/exams", "/student/battle"].includes(link.path);
  });

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to={getDefaultPathForRole(role)} className="sidebar-logo">
          <span className="sidebar-logo-icon">U</span>
          <div>
            <strong>UniPrep AI</strong>
            <small>{PORTAL_LABELS[role] || "Portal"}</small>
          </div>
        </Link>

        <nav className="sidebar-nav">
          {links.map((link) => {
            const Icon = ICONS[link.icon] || Home;
            const currentUrl = `${location.pathname}${location.search}`;
            const isQueryLink = link.path.includes("?");
            const isActive = isQueryLink
              ? currentUrl === link.path
              : location.pathname === link.path;

            return (
              <NavLink
                key={`${link.path}-${link.label}`}
                to={link.path}
                className={isActive ? "sidebar-link active" : "sidebar-link"}
              >
                <Icon size={18} strokeWidth={2.2} aria-hidden="true" />
                {link.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {role === "student" && (
            <div className="sidebar-notifications">
              <span>Notifications</span>
              <NotificationBell />
            </div>
          )}

          <ProfileDropdown user={user} role={role} onLogout={handleLogout} />
        </div>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  );
};

export default SidebarLayout;
