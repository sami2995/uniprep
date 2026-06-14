import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import SidebarLayout from "./components/SidebarLayout";
import FloatingPomodoro from "./components/FloatingPomodoro";

import ProtectedRoute from "./routes/ProtectedRoute";

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
import StudentFocus from "./pages/StudentFocus";

import AdminDashboard from "./pages/AdminDashboard";
import AdminAcademic from "./pages/AdminAcademic";
import AdminQuestions from "./pages/AdminQuestions";
import AdminPdfImports from "./pages/AdminPdfImports";
import AdminBlueprints from "./pages/AdminBlueprints";

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

const StudentLayout = ({ children }) => {
  return (
    <ProtectedRoute role="student">
      <>
        <SidebarLayout>
          {children}
        </SidebarLayout>

        <FloatingPomodoro />
      </>
    </ProtectedRoute>
  );
};

const AdminLayout = ({ children }) => {
  return (
    <ProtectedRoute role="admin">
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

        {/* Admin pages */}
        <Route
          path="/admin/dashboard"
          element={
            <AdminLayout>
              <AdminDashboard />
            </AdminLayout>
          }
        />

        <Route
          path="/admin/academic"
          element={
            <AdminLayout>
              <AdminAcademic />
            </AdminLayout>
          }
        />

        <Route
          path="/admin/questions"
          element={
            <AdminLayout>
              <AdminQuestions />
            </AdminLayout>
          }
        />

        <Route
          path="/admin/pdf-imports"
          element={
            <AdminLayout>
              <AdminPdfImports />
            </AdminLayout>
          }
        />

        <Route
          path="/admin/blueprints"
          element={
            <AdminLayout>
              <AdminBlueprints />
            </AdminLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;