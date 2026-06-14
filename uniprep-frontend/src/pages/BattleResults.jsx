import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/api";

const BattleResults = () => {
  const { roomCode } = useParams();

  const [room, setRoom] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchLeaderboard();
  }, [roomCode]);

  const fetchLeaderboard = async () => {
    try {
      const response = await api.get(
        `/collaboration/challenges/${roomCode}/leaderboard/`
      );

      setRoom(response.data.room);
      setLeaderboard(response.data.leaderboard || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load leaderboard.");
    }
  };

  if (error) {
    return <div className="container py-5 alert alert-danger">{error}</div>;
  }

  if (!room) {
    return <div className="container py-5">Loading leaderboard...</div>;
  }

  return (
    <div className="container-fluid py-4">
      <div className="dashboard-hero mb-4">
        <div>
          <span className="dashboard-badge">Battle Results</span>
          <h2 className="fw-bold mt-2 mb-1">{room.title}</h2>
          <p className="text-muted mb-0">
            Room Code: <strong>{room.room_code}</strong>
          </p>
        </div>

        <Link className="btn btn-primary" to="/student/battle">
          New Battle
        </Link>
      </div>

      <div className="card border-0 shadow-sm rounded-4">
        <div className="card-body p-4">
          <h5 className="fw-bold mb-3">Leaderboard</h5>

          {leaderboard.length === 0 ? (
            <p className="text-muted mb-0">
              No submissions yet. Wait for participants to finish.
            </p>
          ) : (
            <div className="table-responsive">
              <table className="table align-middle">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Student</th>
                    <th>Score</th>
                    <th>Duration</th>
                    <th>Submitted</th>
                  </tr>
                </thead>

                <tbody>
                  {leaderboard.map((item) => (
                    <tr key={item.student_id}>
                      <td>
                        <span className="battle-rank">#{item.rank}</span>
                      </td>

                      <td>{item.username}</td>

                      <td>
                        <span className="badge bg-primary">
                          {item.score}%
                        </span>
                      </td>

                      <td>{item.duration_seconds}s</td>

                      <td className="text-muted small">
                        {item.submitted_at
                          ? new Date(item.submitted_at).toLocaleString()
                          : "Not submitted"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BattleResults;