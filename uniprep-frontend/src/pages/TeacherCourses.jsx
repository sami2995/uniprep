import { useEffect, useState } from "react";
import api from "../api/api";

const TeacherCourses = () => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAssignedCourses();
  }, []);

  const fetchAssignedCourses = async () => {
    try {
      const response = await api.get("/exit-exams/my-assigned-courses/");
      setAssignments(response.data);
    } catch (err) {
      setError("Failed to load assigned courses.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="container py-5">Loading assigned courses...</div>;
  }

  return (
    <div className="container py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Teacher Portal</span>
          <h2 className="fw-bold mt-2 mb-1">My Courses</h2>
          <p className="text-muted mb-0">
            Courses assigned by your department head.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      {assignments.length === 0 && !error ? (
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-4">
            <h5 className="fw-bold">No assigned courses yet</h5>
            <p className="text-muted mb-0">
              Assigned courses will appear here after a department head links
              you to a course.
            </p>
          </div>
        </div>
      ) : (
        <div className="row g-3">
          {assignments.map((assignment) => (
            <div key={assignment.id} className="col-md-6 col-xl-4">
              <div className="card border-0 shadow-sm rounded-4 h-100">
                <div className="card-body p-4">
                  <h5 className="fw-bold">{assignment.course_name}</h5>
                  <p className="text-muted mb-2">
                    Assignment ID: {assignment.id}
                  </p>
                  <span className="badge bg-primary">
                    Assigned {new Date(assignment.assigned_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeacherCourses;
