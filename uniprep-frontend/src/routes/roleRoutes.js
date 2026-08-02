export const ROLES = {
  STUDENT: "student",
  TEACHER: "teacher",
  DEPARTMENT_HEAD: "department_head",
  SYSTEM_ADMIN: "system_admin",
};

export const LEGACY_ADMIN_ROLE = "admin";

export const ROLE_HOME_PATHS = {
  [ROLES.STUDENT]: "/student/dashboard",
  [ROLES.TEACHER]: "/teacher/dashboard",
  [ROLES.DEPARTMENT_HEAD]: "/department-head/dashboard",
  [ROLES.SYSTEM_ADMIN]: "/system-admin/dashboard",
  [LEGACY_ADMIN_ROLE]: "/department-head/dashboard",
};

export const ADMINISTRATIVE_ROLES = [
  ROLES.DEPARTMENT_HEAD,
  ROLES.SYSTEM_ADMIN,
  LEGACY_ADMIN_ROLE,
];

export const SIDEBAR_LINKS = {
  [ROLES.STUDENT]: [
    { label: "Dashboard", path: "/student/dashboard", icon: "Home" },
    { label: "Exams", path: "/student/exams", icon: "FileText" },
    { label: "Results", path: "/student/results", icon: "BarChart3" },
    { label: "Materials", path: "/student/materials", icon: "BookOpen" },
    { label: "Focus", path: "/student/focus", icon: "Timer" },
    { label: "Adaptive Learning Engine", path: "/student/learning", icon: "Brain" },
    { label: "Battle", path: "/student/battle", icon: "Zap" },
  ],
  [ROLES.TEACHER]: [
    { label: "Dashboard", path: "/teacher/dashboard", icon: "Home" },
    { label: "My Courses", path: "/teacher/courses", icon: "GraduationCap" },
    { label: "My Questions", path: "/teacher/questions", icon: "CircleHelp" },
    { label: "Import Previous Exit Exam", path: "/teacher/pdf-imports", icon: "FileText" },
    { label: "Create Question", path: "/teacher/questions", icon: "CircleHelp" },
    { label: "My Drafts", path: "/teacher/questions?filter=draft", icon: "FileText" },
    { label: "Pending Approval", path: "/teacher/questions?filter=submitted", icon: "CheckSquare" },
    { label: "Import History", path: "/teacher/pdf-imports?filter=all", icon: "ScrollText" },
    { label: "Materials", path: "/teacher/materials", icon: "BookOpen" },
    { label: "Analytics", path: "/teacher/analytics", icon: "BarChart3" },
  ],
  [ROLES.DEPARTMENT_HEAD]: [
    { label: "Dashboard", path: "/department-head/dashboard", icon: "Home" },
    { label: "Academic Structure", path: "/department-head/academic", icon: "Network" },
    { label: "Question Approval", path: "/department-head/question-approval", icon: "CheckSquare" },
    { label: "PDF Imports", path: "/department-head/pdf-imports", icon: "FileText" },
    { label: "Exam Bank", path: "/department-head/exam-bank", icon: "Archive" },
    { label: "Analytics", path: "/department-head/analytics", icon: "BarChart3" },
    { label: "Blueprint Settings", path: "/department-head/blueprints", icon: "Settings2" },
    { label: "Teacher Assignments", path: "/department-head/teacher-assignments", icon: "UserCheck" },
    { label: "Audit Logs", path: "/department-head/audit-logs", icon: "ScrollText" },
  ],
  [ROLES.SYSTEM_ADMIN]: [
    { label: "Dashboard", path: "/system-admin/dashboard", icon: "Home" },
    { label: "Users", path: "/system-admin/users", icon: "Users" },
    { label: "Departments", path: "/system-admin/departments", icon: "Building2" },
    { label: "Settings", path: "/system-admin/settings", icon: "Settings" },
    { label: "Activity Log", path: "/system-admin/audit-logs", icon: "ScrollText" },
  ],
};

export const getDefaultPathForRole = (role) => {
  return ROLE_HOME_PATHS[role] || "/login";
};

export const normalizeRole = (role) => {
  return role === LEGACY_ADMIN_ROLE ? ROLES.DEPARTMENT_HEAD : role;
};

export const roleCanAccess = (userRole, allowedRoles) => {
  if (!allowedRoles || allowedRoles.length === 0) {
    return true;
  }

  const normalizedUserRole = normalizeRole(userRole);
  return allowedRoles.includes(normalizedUserRole) || allowedRoles.includes(userRole);
};
