import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import api from "../api/api";

const formatNotificationDate = (value) => {
  if (!value) return "";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return date.toLocaleDateString();
};

const NotificationBell = () => {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      const [listRes, countRes] = await Promise.all([
        api.get("/notifications/"),
        api.get("/notifications/unread-count/"),
      ]);

      setNotifications(Array.isArray(listRes.data) ? listRes.data : []);
      setUnreadCount(countRes.data?.unread_count || 0);
    } catch (err) {
      console.error("Failed to load notifications:", err);
    }
  };

  const markAsRead = async (id) => {
    try {
      await api.post(`/notifications/read/${id}/`);
      setNotifications((items) =>
        items.map((item) =>
          item.id === id ? { ...item, is_read: true } : item
        )
      );
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  };

  return (
    <div className="notification-bell">
      <button
        type="button"
        className="notification-bell-btn"
        onClick={() => setOpen((value) => !value)}
        aria-label="Notifications"
      >
        <Bell size={18} aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount}</span>
        )}
      </button>

      {open && (
        <div className="notification-menu">
          <div className="notification-menu-header">
            <strong>Notifications</strong>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={fetchNotifications}
            >
              Refresh
            </button>
          </div>

          {notifications.length === 0 ? (
            <p className="text-muted small mb-0 p-3">No notifications yet.</p>
          ) : (
            <div className="notification-list">
              {notifications.slice(0, 6).map((item) => (
                <div
                  key={item.id}
                  className={`notification-item ${
                    item.is_read ? "" : "unread"
                  }`}
                >
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.message}</p>
                    <span>{formatNotificationDate(item.created_at)}</span>
                  </div>

                  {!item.is_read && (
                    <button
                      type="button"
                      className="notification-read-btn"
                      onClick={() => markAsRead(item.id)}
                      aria-label="Mark as read"
                    >
                      <Check size={15} aria-hidden="true" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
