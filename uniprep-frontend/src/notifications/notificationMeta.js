import {
  AlertTriangle,
  Bell,
  BookOpen,
  Brain,
  CheckCircle2,
  Clock,
  FileText,
  GraduationCap,
  Info,
  Trophy,
  Zap,
  XCircle,
} from "lucide-react";

export const NOTIFICATION_CATEGORIES = [
  "All",
  "Academic",
  "Approval",
  "AI",
  "Exam",
  "Assignment",
  "System",
];

const gray = { bg: "#f1f5f9", fg: "#64748b", accent: "#94a3b8" };
const green = { bg: "#dcfce7", fg: "#15803d", accent: "#22c55e" };
const blue = { bg: "#dbeafe", fg: "#1d4ed8", accent: "#3b82f6" };
const purple = { bg: "#ede9fe", fg: "#6d28d9", accent: "#8b5cf6" };
const orange = { bg: "#ffedd5", fg: "#c2410c", accent: "#f97316" };
const red = { bg: "#fee2e2", fg: "#b91c1c", accent: "#ef4444" };

export const NOTIFICATION_META = {
  learning_path_ready: {
    icon: Brain,
    color: purple,
    category: "Academic",
    label: "Learning Path Ready",
  },
  learning_step_unlocked: {
    icon: Trophy,
    color: blue,
    category: "Academic",
    label: "Step Unlocked",
  },
  learning_path_completed: {
    icon: GraduationCap,
    color: green,
    category: "Academic",
    label: "Path Completed",
  },
  weak_topic: {
    icon: AlertTriangle,
    color: red,
    category: "Academic",
    label: "Weak Topic",
  },
  mock_available: {
    icon: FileText,
    color: blue,
    category: "Exam",
    label: "Mock Available",
  },
  battle_invite: {
    icon: Zap,
    color: orange,
    category: "Academic",
    label: "Battle Invite",
  },
  material_uploaded: {
    icon: BookOpen,
    color: blue,
    category: "Academic",
    label: "Material Uploaded",
  },
  weekly_reminder: {
    icon: Clock,
    color: orange,
    category: "System",
    label: "Weekly Reminder",
  },
};

const DEFAULT_META = {
  icon: Bell,
  color: gray,
  category: "System",
  label: "Notification",
};

// Approved = green, Assignment = blue, AI = purple, Reminder = orange,
// Rejected = red, System = gray.
export const PRIORITY_COLOR = {
  Approved: green,
  Approval: green,
  Assignment: blue,
  AI: purple,
  Exam: blue,
  Reminder: orange,
  Rejected: red,
  Warning: red,
  System: gray,
};

export const metaFor = (notificationType) =>
  NOTIFICATION_META[notificationType] || DEFAULT_META;

export const categoryFor = (notificationType) =>
  metaFor(notificationType).category;

const startOfDay = (date) => {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
};

export const formatRelativeTime = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 30) return "just now";
  if (diffMinutes < 1) return `${diffSeconds}s ago`;
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

export const relativeBucket = (value) => {
  if (!value) return "Earlier";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Earlier";

  const today = startOfDay(new Date());
  const target = startOfDay(date);
  const dayMs = 24 * 60 * 60 * 1000;
  const dayDiff = Math.round((today.getTime() - target.getTime()) / dayMs);

  if (dayDiff <= 0) return "Today";
  if (dayDiff === 1) return "Yesterday";
  return "Earlier";
};

export const dateLabel = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

// Routing helper — never hardcodes inside components. Uses target_url from
// the backend when present, otherwise derives a route from the type.
export const routeForNotification = (notification) => {
  if (!notification) return null;
  if (notification.target_url) return notification.target_url;
  switch (notification.notification_type) {
    case "learning_path_ready":
    case "learning_step_unlocked":
    case "learning_path_completed":
    case "weak_topic":
      return "/student/learning";
    case "mock_available":
      return "/student/exams";
    case "battle_invite":
      return "/student/battle";
    case "material_uploaded":
      return "/student/materials";
    case "weekly_reminder":
      return "/student/dashboard";
    default:
      return null;
  }
};

export { CheckCircle2, Info, XCircle };