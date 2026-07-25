import { useEffect, useState } from "react";
import { KeyRound, Save, UserRound } from "lucide-react";
import api from "../api/api";
import { useAuth } from "../auth/AuthContext";
import { normalizeRole } from "../routes/roleRoutes";

const ROLE_LABELS = {
  student: "Student",
  teacher: "Teacher",
  department_head: "Department Head",
  system_admin: "System Admin",
};

const ProfilePage = () => {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [form, setForm] = useState({ username: "", email: "", student_profile: {} });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  const role = normalizeRole(user?.role);
  const profile = form.student_profile || {};
  const assignedCourses = Array.isArray(user?.assigned_courses)
    ? user.assigned_courses
    : [];

  useEffect(() => {
    if (user) {
      setForm({
        username: user.username || "",
        email: user.email || "",
        student_profile: user.student_profile || {},
      });
    }
  }, [user]);

  const updateForm = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const updateStudentProfile = (field, value) => {
    setForm((current) => ({
      ...current,
      student_profile: { ...current.student_profile, [field]: value },
    }));
  };

  const saveProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    setNotice("");
    setError("");
    try {
      await api.patch("/users/me/", form);
      await refreshUser();
      setNotice("Profile updated successfully.");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to update your profile.");
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (event) => {
    event.preventDefault();
    setChangingPassword(true);
    setNotice("");
    setError("");
    try {
      await api.post("/users/change-password/", passwordForm);
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
      setNotice("Password changed successfully.");
    } catch (requestError) {
      const data = requestError.response?.data;
      setError(data?.detail || data?.new_password?.[0] || data?.current_password?.[0] || "Unable to change your password.");
    } finally {
      setChangingPassword(false);
    }
  };

  const metricItems = {
    teacher: [
      ["Assigned courses", assignedCourses.length],
      ["Questions authored", user?.questions_authored ?? 0],
    ],
    department_head: [["Courses managed", user?.courses_managed ?? 0]],
    system_admin: [
      ["Total students", user?.total_students ?? 0],
      ["Total teachers", user?.total_teachers ?? 0],
    ],
  }[role] || [];

  return (
    <div className="profile-page container py-4">
      <div className="profile-page-header">
        <div className="profile-identity-mark"><UserRound size={28} /></div>
        <div>
          <p className="profile-eyebrow">Account</p>
          <h1>{user?.username || "Profile"}</h1>
          <p>{ROLE_LABELS[role] || "UniPrep user"}{user?.department_name ? ` · ${user.department_name}` : ""}</p>
        </div>
      </div>

      {notice && <div className="alert alert-success">{notice}</div>}
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="rag-tabs profile-tabs">
        <button className={activeTab === "overview" ? "active" : ""} onClick={() => setActiveTab("overview")}>
          Overview
        </button>
        <button className={activeTab === "settings" ? "active" : ""} onClick={() => setActiveTab("settings")}>
          Account Settings
        </button>
      </div>

      {activeTab === "overview" && (
        <section className="profile-overview">
          <div className="profile-summary-panel">
            <span className="profile-large-avatar">{user?.username?.slice(0, 1)?.toUpperCase() || "U"}</span>
            <div>
              <h2>{user?.username}</h2>
              <p>{user?.email}</p>
              <span className="profile-role-badge">{ROLE_LABELS[role] || role}</span>
            </div>
          </div>

          <div className="profile-metrics">
            {metricItems.map(([label, value]) => (
              <div className="profile-metric" key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>

          <div className="profile-details-panel">
            <h2>Account details</h2>
            <dl>
              <div><dt>Username</dt><dd>{user?.username || "-"}</dd></div>
              <div><dt>Email</dt><dd>{user?.email || "-"}</dd></div>
              <div><dt>Department</dt><dd>{user?.department_name || "Not assigned"}</dd></div>
              {role === "student" && user?.student_profile && (
                <>
                  <div><dt>Student ID</dt><dd>{user.student_profile.student_id || "-"}</dd></div>
                  <div><dt>Program</dt><dd>{user.student_profile.program || "-"}</dd></div>
                  <div><dt>Year of study</dt><dd>{user.student_profile.year_of_study || "-"}</dd></div>
                </>
              )}
            </dl>
            {role === "teacher" && (
              <div className="profile-course-list">
                <h3>Assigned courses</h3>
                {assignedCourses.length > 0 ? (
                  <ul>
                    {assignedCourses.map((courseName) => (
                      <li key={courseName}>{courseName}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No courses assigned.</p>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      {activeTab === "settings" && (
        <section className="profile-settings-grid">
          <form className="profile-form-panel" onSubmit={saveProfile}>
            <div className="profile-panel-heading"><UserRound size={18} /><h2>Profile information</h2></div>
            <label>Username<input value={form.username} onChange={(event) => updateForm("username", event.target.value)} required /></label>
            <label>Email<input type="email" value={form.email} onChange={(event) => updateForm("email", event.target.value)} required /></label>
            {role === "student" && form.student_profile && (
              <>
                <label>Student ID<input value={profile.student_id || ""} onChange={(event) => updateStudentProfile("student_id", event.target.value)} /></label>
                <label>Program<input value={profile.program || ""} onChange={(event) => updateStudentProfile("program", event.target.value)} /></label>
                <label>Year of study<input type="number" min="1" value={profile.year_of_study || ""} onChange={(event) => updateStudentProfile("year_of_study", event.target.value ? Number(event.target.value) : null)} /></label>
              </>
            )}
            <button className="btn btn-primary" type="submit" disabled={saving}><Save size={16} />{saving ? "Saving..." : "Save changes"}</button>
          </form>

          <form className="profile-form-panel" onSubmit={changePassword}>
            <div className="profile-panel-heading"><KeyRound size={18} /><h2>Change password</h2></div>
            <label>Current password<input type="password" value={passwordForm.current_password} onChange={(event) => setPasswordForm({ ...passwordForm, current_password: event.target.value })} required /></label>
            <label>New password<input type="password" value={passwordForm.new_password} onChange={(event) => setPasswordForm({ ...passwordForm, new_password: event.target.value })} required /></label>
            <label>Confirm new password<input type="password" value={passwordForm.confirm_password} onChange={(event) => setPasswordForm({ ...passwordForm, confirm_password: event.target.value })} required /></label>
            <button className="btn btn-outline-primary" type="submit" disabled={changingPassword}><KeyRound size={16} />{changingPassword ? "Updating..." : "Update password"}</button>
          </form>
        </section>
      )}
    </div>
  );
};

export default ProfilePage;
