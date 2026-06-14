import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";

const StudentBattle = () => {
  const navigate = useNavigate();

  const [courses, setCourses] = useState([]);
  const [availability, setAvailability] = useState([]);

  const [createForm, setCreateForm] = useState({
    course_id: "",
    title: "Exit Exam Battle",
    total_questions: 1,
    duration_minutes: 10,
  });

  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState("");
  const [loadingAction, setLoadingAction] = useState("");

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    setError("");

    try {
      const coursesRes = await api.get("/exit-exams/courses/");
      const coursesData = coursesRes.data || [];

      setCourses(coursesData);

      let availabilityData = [];

      try {
        const availabilityRes = await api.get(
          "/exit-exams/question-availability/"
        );

        availabilityData = availabilityRes.data.availability || [];
        setAvailability(availabilityData);
      } catch (availabilityError) {
        console.log("Availability failed:", availabilityError.response);
        setAvailability([]);
      }

      const courseWithQuestions = coursesData.find((course) => {
        const count = availabilityData
          .filter((item) => Number(item.course_id) === Number(course.id))
          .reduce(
            (total, item) => total + Number(item.available_questions || 0),
            0
          );

        return count > 0;
      });

      const bscCourse = coursesData.find((course) =>
        course.name.toLowerCase().includes("bsc")
      );

      const defaultCourse = courseWithQuestions || bscCourse || coursesData[0];

      if (defaultCourse) {
        setCreateForm((prev) => ({
          ...prev,
          course_id: String(defaultCourse.id),
        }));
      }
    } catch (err) {
      console.log("Course load error:", err.response);
      setError("Failed to load courses.");
    }
  };

  const getAvailableQuestionsForCourse = (courseId) => {
    return availability
      .filter((item) => Number(item.course_id) === Number(courseId))
      .reduce(
        (total, item) => total + Number(item.available_questions || 0),
        0
      );
  };

  const handleCreateChange = (e) => {
    setCreateForm({
      ...createForm,
      [e.target.name]: e.target.value,
    });
  };

  const createBattle = async (e) => {
    e.preventDefault();
    setError("");
    setLoadingAction("create");

    try {
      const response = await api.post("/collaboration/challenges/create/", {
        course_id: Number(createForm.course_id),
        title: createForm.title,
        total_questions: Number(createForm.total_questions),
        duration_minutes: Number(createForm.duration_minutes),
      });

      const roomCode = response.data.room?.room_code || response.data.room_code;

      if (!roomCode) {
        setError("Challenge created, but room code was not returned.");
        return;
      }

      navigate(`/student/battle/${roomCode}/lobby`);
    } catch (err) {
      console.log("Create battle error:", err.response);

      setError(
        err.response?.data?.detail ||
          err.response?.data?.error ||
          `Failed to create battle. Status: ${err.response?.status || "unknown"}`
      );
    } finally {
      setLoadingAction("");
    }
  };

  const joinBattle = async (e) => {
    e.preventDefault();
    setError("");
    setLoadingAction("join");

    try {
      const code = joinCode.trim().toUpperCase();

      const response = await api.post("/collaboration/challenges/join/", {
        room_code: code,
      });

      const roomCode = response.data.room?.room_code || code;

      navigate(`/student/battle/${roomCode}/lobby`);
    } catch (err) {
      console.log("Join battle error:", err.response);

      setError(
        err.response?.data?.detail ||
          err.response?.data?.error ||
          "Failed to join battle room."
      );
    } finally {
      setLoadingAction("");
    }
  };

  return (
    <div className="container-fluid py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Battle Mode</span>
          <h2 className="fw-bold mt-2 mb-1">Challenge your classmates</h2>
          <p className="text-muted mb-0">
            Create a battle room, invite classmates with a code, and compete on
            the same approved exam questions.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Create Battle Room</h5>

              <form onSubmit={createBattle}>
                <div className="mb-3">
                  <label className="form-label">Battle Title</label>
                  <input
                    name="title"
                    className="form-control"
                    value={createForm.title}
                    onChange={handleCreateChange}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">Course</label>
                  <select
                    name="course_id"
                    className="form-select"
                    value={createForm.course_id}
                    onChange={handleCreateChange}
                    required
                  >
                    <option value="">Select course</option>

                    {courses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.name} —{" "}
                        {getAvailableQuestionsForCourse(course.id)} questions
                      </option>
                    ))}
                  </select>

                  <div className="form-text">
                    For your current data, choose{" "}
                    <strong>Computer Science BSc Exit Exam</strong>.
                  </div>
                </div>

                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Questions</label>
                    <input
                      type="number"
                      name="total_questions"
                      className="form-control"
                      min="1"
                      value={createForm.total_questions}
                      onChange={handleCreateChange}
                    />
                  </div>

                  <div className="col-md-6 mb-3">
                    <label className="form-label">Duration Minutes</label>
                    <input
                      type="number"
                      name="duration_minutes"
                      className="form-control"
                      min="1"
                      value={createForm.duration_minutes}
                      onChange={handleCreateChange}
                    />
                  </div>
                </div>

                <button
                  className="btn btn-primary w-100"
                  disabled={loadingAction === "create"}
                >
                  {loadingAction === "create"
                    ? "Creating..."
                    : "Create Battle Room"}
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Join Battle Room</h5>

              <form onSubmit={joinBattle}>
                <div className="mb-3">
                  <label className="form-label">Room Code</label>
                  <input
                    className="form-control battle-code-input"
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                    placeholder="ABC123"
                    required
                  />
                </div>

                <button
                  className="btn btn-success w-100"
                  disabled={loadingAction === "join"}
                >
                  {loadingAction === "join" ? "Joining..." : "Join Battle"}
                </button>
              </form>

              <div className="battle-info-box mt-4">
                <h6 className="fw-bold">How it works</h6>
                <p className="mb-0">
                  The creator starts the battle. All participants answer the
                  same questions. The leaderboard ranks by score and completion
                  time.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentBattle;