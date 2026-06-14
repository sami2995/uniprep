import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/api";
import { useAuth } from "../auth/AuthContext";

const BattleLobby = () => {
  const { roomCode } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [room, setRoom] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    fetchRoom();

    const interval = setInterval(fetchRoom, 4000);

    return () => clearInterval(interval);
  }, [roomCode]);

  const fetchRoom = async () => {
    try {
      const response = await api.get(`/collaboration/challenges/${roomCode}/`);

      setRoom(response.data.room);
      setParticipants(response.data.participants || []);

      if (response.data.room?.status === "active") {
        navigate(`/student/battle/${roomCode}/play`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load battle room.");
    }
  };

  const startBattle = async () => {
    setError("");
    setStarting(true);

    try {
      await api.post(`/collaboration/challenges/${roomCode}/start/`);
      navigate(`/student/battle/${roomCode}/play`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start battle.");
    } finally {
      setStarting(false);
    }
  };

  if (error) {
    return <div className="container py-5 alert alert-danger">{error}</div>;
  }

  if (!room) {
    return <div className="container py-5">Loading battle lobby...</div>;
  }

  const isCreator =
    Number(room.created_by) === Number(user?.id) ||
    room.created_by_username === user?.username;

  return (
    <div className="container-fluid py-4">
      <div className="battle-lobby-hero mb-4">
        <div>
          <span className="dashboard-badge">Lobby</span>
          <h2 className="fw-bold mt-2 mb-1">{room.title}</h2>
          <p className="text-muted mb-0">
            Share this room code with classmates.
          </p>
        </div>

        <div className="battle-room-code">{room.room_code}</div>
      </div>

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold mb-3">Participants</h5>

              {participants.length === 0 ? (
                <p className="text-muted">No participants yet.</p>
              ) : (
                <div className="d-grid gap-3">
                  {participants.map((participant) => (
                    <div key={participant.id} className="dashboard-list-item">
                      <div>
                        <strong>{participant.username}</strong>
                        <p className="small text-muted mb-0">
                          {participant.is_creator ? "Room creator" : "Player"}
                        </p>
                      </div>

                      {participant.is_creator && (
                        <span className="badge bg-primary">Creator</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body p-4">
              <h5 className="fw-bold">Battle Details</h5>

              <div className="battle-detail-grid mt-3">
                <div>
                  <strong>{room.total_questions}</strong>
                  <span>Questions</span>
                </div>

                <div>
                  <strong>{room.duration_minutes}</strong>
                  <span>Minutes</span>
                </div>

                <div>
                  <strong>{room.status}</strong>
                  <span>Status</span>
                </div>
              </div>

              {isCreator ? (
                <button
                  className="btn btn-success w-100 mt-4"
                  onClick={startBattle}
                  disabled={starting}
                >
                  {starting ? "Starting..." : "Start Battle"}
                </button>
              ) : (
                <div className="alert alert-info mt-4 mb-0">
                  Waiting for the room creator to start the battle.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BattleLobby;