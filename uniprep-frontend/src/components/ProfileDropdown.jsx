import { useState } from "react";
import { ChevronDown, LogOut, UserRound } from "lucide-react";
import { Link } from "react-router-dom";

const ROLE_LABELS = {
  student: "Student",
  teacher: "Teacher",
  department_head: "Department Head",
  system_admin: "System Admin",
};

const ProfileDropdown = ({ user, role, onLogout }) => {
  const [open, setOpen] = useState(false);
  const roleLabel = ROLE_LABELS[role] || role || "User";

  return (
    <div className="profile-dropdown">
      <button
        className="sidebar-user profile-dropdown-toggle"
        type="button"
        onClick={() => setOpen((isOpen) => !isOpen)}
        aria-expanded={open}
        aria-label="Open profile menu"
      >
        <span className="sidebar-avatar">
          {user?.username?.slice(0, 1)?.toUpperCase() || "U"}
        </span>
        <span className="profile-dropdown-name">
          <strong>{user?.username || "User"}</strong>
          <small>{roleLabel}</small>
        </span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>

      {open && (
        <div className="profile-dropdown-menu">
          <Link to="/profile" onClick={() => setOpen(false)}>
            <UserRound size={16} aria-hidden="true" />
            Profile
          </Link>
          <button type="button" onClick={onLogout}>
            <LogOut size={16} aria-hidden="true" />
            Logout
          </button>
        </div>
      )}
    </div>
  );
};

export default ProfileDropdown;
