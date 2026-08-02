import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import SidebarLayout from "./components/SidebarLayout";
import FloatingPomodoro from "./components/FloatingPomodoro";

import ProtectedRoute from "./routes/ProtectedRoute";
import {
  ROLES,
  getDefaultPathForRole,
} from "./routes/roleRoutes";
import { useAuth } from "./auth/AuthContext";

import LandingPage from "./pages/LandingPage";
import Login from "./pages/Login";
import Register from "./pages/Register";

import StudentDashboard from "./pages/StudentDashboard";
import StudentExams from "./pages/StudentExams";
import TakeExam from "./pages/TakeExam";
import Results from "./pages/Results";
import ResultDetail from "./pages/ResultDetail";
import StudentMaterials from "./pages/StudentMaterials";
import StudyMaterialDetail from "./pages/StudyMaterialDetail";
import TeacherMaterials from "./pages/TeacherMaterials";
import TeacherMaterialDetail from "./pages/TeacherMaterialDetail";
import StudentFocus from "./pages/StudentFocus";
import AdaptiveLearningPage from "./pages/AdaptiveLearningPage";

import AdminDashboard from "./pages/AdminDashboard";
import AdminAcademic from "./pages/AdminAcademic";
import AdminQuestions from "./pages/AdminQuestions";
import AdminPdfImports from "./pages/AdminPdfImports";
import AdminBlueprints from "./pages/AdminBlueprints";
import Departments from "./pages/Departments";
import RolePlaceholderPage from "./pages/RolePlaceholderPage";
import TeacherCourses from "./pages/TeacherCourses";
import TeacherAnalytics from "./pages/TeacherAnalytics";
import DepartmentHeadAnalytics from "./pages/DepartmentHeadAnalytics";
// Phase 2 pages
import TeacherDashboard from "./pages/TeacherDashboard";
import TeacherQuestionBank from "./pages/TeacherQuestionBank";
import ExamBankDashboard from "./pages/ExamBankDashboard";
import DeptHeadApprovals from "./pages/DeptHeadApprovals";
import BlueprintSettings from "./pages/BlueprintSettings";
import TeacherAssignments from "./pages/TeacherAssignments";
import AuditLogs from "./pages/AuditLogs";
import ProfilePage from "./pages/ProfilePage";

import SystemAdminDashboard from "./pages/SystemAdminDashboard";
import UserManagement from "./pages/UserManagement";
import SystemSettingsPage from "./pages/SystemSettingsPage";
import ActivityLog from "./pages/ActivityLog";

import StudentBattle from "./pages/StudentBattle";
import BattleLobby from "./pages/BattleLobby";
import BattlePlay from "./pages/BattlePlay";
import BattleResults from "./pages/BattleResults";

const PublicLayout = ({ children }) => {
  return (
    <>
      <Navbar />
      {children}
    </>
  );
};

const DashboardRedirect = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getDefaultPathForRole(user.role)} replace />;
};

const StudentLayout = ({ children }) => {
  return (
    <ProtectedRoute role={ROLES.STUDENT}>
      <>
        <SidebarLayout>
          {children}
        </SidebarLayout>

        <FloatingPomodoro />
      </>
    </ProtectedRoute>
  );
};

const RoleLayout = ({ children, roles }) => {
  return (
    <ProtectedRoute roles={roles}>
      <SidebarLayout>
        {children}
      </SidebarLayout>
    </ProtectedRoute>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public pages */}
        <Route
          path="/"
          element={
            <PublicLayout>
              <LandingPage />
            </PublicLayout>
          }
        />

        <Route
          path="/login"
          element={
            <PublicLayout>
              <Login />
            </PublicLayout>
          }
        />

        <Route
          path="/register"
          element={
            <PublicLayout>
              <Register />
            </PublicLayout>
          }
        />

        <Route path="/dashboard" element={<DashboardRedirect />} />

        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <SidebarLayout>
                <ProfilePage />
              </SidebarLayout>
            </ProtectedRoute>
          }
        />

        {/* Student pages */}
        <Route
          path="/student/dashboard"
          element={
            <StudentLayout>
              <StudentDashboard />
            </StudentLayout>
          }
        />

        <Route
          path="/student/exams"
          element={
            <StudentLayout>
              <StudentExams />
            </StudentLayout>
          }
        />

        <Route
          path="/student/exam/:examId"
          element={
            <StudentLayout>
              <TakeExam />
            </StudentLayout>
          }
        />

        <Route
          path="/student/results"
          element={
            <StudentLayout>
              <Results />
            </StudentLayout>
          }
        />

        <Route
          path="/student/results/:attemptId"
          element={
            <StudentLayout>
              <ResultDetail />
            </StudentLayout>
          }
        />

        <Route
          path="/student/materials"
          element={
            <StudentLayout>
              <StudentMaterials />
            </StudentLayout>
          }
        />

        <Route
          path="/student/materials/:materialId"
          element={
            <StudentLayout>
              <StudyMaterialDetail />
            </StudentLayout>
          }
        />

        <Route
          path="/student/focus"
          element={
            <StudentLayout>
              <StudentFocus />
            </StudentLayout>
          }
        />

        <Route
          path="/student/learning"
          element={
            <StudentLayout>
              <AdaptiveLearningPage />
            </StudentLayout>
          }
        />
        <Route
  path="/student/battle"
  element={
    <StudentLayout>
      <StudentBattle />
    </StudentLayout>
  }
/>

<Route
  path="/student/battle/:roomCode/lobby"
  element={
    <StudentLayout>
      <BattleLobby />
    </StudentLayout>
  }
/>

<Route
  path="/student/battle/:roomCode/play"
  element={
    <StudentLayout>
      <BattlePlay />
    </StudentLayout>
  }
/>

<Route
  path="/student/battle/:roomCode/results"
  element={
    <StudentLayout>
      <BattleResults />
    </StudentLayout>
  }
/>

        {/* Teacher pages */}
        <Route
          path="/teacher/dashboard"
          element={
            <RoleLayout roles={[ROLES.TEACHER]}>
              <TeacherDashboard />
            </RoleLayout>
          }
        />

        <Route
          path="/teacher/courses"
          element={
            <RoleLayout roles={[ROLES.TEACHER]}>
              <TeacherCourses />
            </RoleLayout>
          }
        />

        <Route
          path="/teacher/questions"
          element={
            <RoleLayout roles={[ROLES.TEACHER]}>
              <TeacherQuestionBank />
            </RoleLayout>
          }
        />

        <Route
          path="/teacher/pdf-imports"
          element={
            <RoleLayout roles={[ROLES.TEACHER]}>
              <AdminPdfImports />
            </RoleLayout>
          }
        />

        <Route
          path="/teacher/import-previous-exit-exam"
          element={<Navigate to="/teacher/pdf-imports" replace />}
        />

        <Route
          path="/teacher/import-history"
          element={<Navigate to="/teacher/pdf-imports?filter=all" replace />}
        />

        <Route
          path="/teacher/drafts"
          element={<Navigate to="/teacher/questions?filter=draft" replace />}
        />

        <Route
          path="/teacher/pending-approval"
          element={<Navigate to="/teacher/questions?filter=submitted" replace />}
        />

        <Route
          path="/teacher/materials"
          element={
            <RoleLayout roles={[ROLES.TEACHER]}>
              <TeacherMaterials />
            </RoleLayout>
          }
        />

        <Route
          path="/teacher/materials/:materialId"
          element={
            <RoleLayout roles={[ROLES.TEACHER]}>
              <TeacherMaterialDetail />
            </RoleLayout>
          }
        />

        <Route
          path="/teacher/analytics"
          element={
            <RoleLayout roles={[ROLES.TEACHER]}>
              <TeacherAnalytics />
            </RoleLayout>
          }
        />

        {/* Department head pages */}
        <Route
          path="/department-head/dashboard"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <AdminDashboard />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/academic"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <AdminAcademic />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/question-approval"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <DeptHeadApprovals />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/pdf-imports"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <AdminPdfImports />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/exam-bank"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <ExamBankDashboard />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/analytics"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <DepartmentHeadAnalytics />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/blueprints"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <BlueprintSettings />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/teacher-assignments"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <TeacherAssignments />
            </RoleLayout>
          }
        />

        <Route
          path="/department-head/audit-logs"
          element={
            <RoleLayout roles={[ROLES.DEPARTMENT_HEAD]}>
              <AuditLogs />
            </RoleLayout>
          }
        />

        {/* System admin pages */}
        <Route
          path="/system-admin/dashboard"
          element={
            <RoleLayout roles={[ROLES.SYSTEM_ADMIN]}>
              <SystemAdminDashboard />
            </RoleLayout>
          }
        />

        <Route
          path="/system-admin/users"
          element={
            <RoleLayout roles={[ROLES.SYSTEM_ADMIN]}>
              <UserManagement />
            </RoleLayout>
          }
        />

        <Route
          path="/system-admin/departments"
          element={
            <RoleLayout roles={[ROLES.SYSTEM_ADMIN]}>
              <Departments />
            </RoleLayout>
          }
        />

        <Route
          path="/system-admin/settings"
          element={
            <RoleLayout roles={[ROLES.SYSTEM_ADMIN]}>
              <SystemSettingsPage />
            </RoleLayout>
          }
        />

        <Route
          path="/system-admin/audit-logs"
          element={
            <RoleLayout roles={[ROLES.SYSTEM_ADMIN]}>
              <ActivityLog />
            </RoleLayout>
          }
        />

        {/* Legacy admin redirects */}
        <Route path="/admin/dashboard" element={<Navigate to="/department-head/dashboard" replace />} />
        <Route path="/admin/academic" element={<Navigate to="/department-head/academic" replace />} />
        <Route path="/admin/questions" element={<Navigate to="/department-head/exam-bank" replace />} />
        <Route path="/admin/pdf-imports" element={<Navigate to="/department-head/question-approval" replace />} />
        <Route path="/admin/blueprints" element={<Navigate to="/department-head/blueprints" replace />} />

        <Route
          path="*"
          element={
            <PublicLayout>
              <Navigate to="/" replace />
            </PublicLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
