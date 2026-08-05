import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, X } from "lucide-react";

import { useNotifications } from "../notifications/NotificationContext";
import {
  NOTIFICATION_CATEGORIES,
  categoryFor,
  relativeBucket,
} from "../notifications/notificationMeta";
import NotificationCard from "./NotificationCard";

const NotificationBell = () => {
  const {
    notifications,
    unreadCount,
    connected,
    markRead,
    markAllRead,
    refresh,
  } = useNotifications();
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState("All");
  const containerRef = useRef(null);
  const lastUnreadRef = useRef(unreadCount);

  // Re-fetch when the dropdown opens (cheap & keeps the bell fresh without
  // relying solely on the WS / poll loop).
  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return undefined;
    const handleClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  // Quiet "all read" indicator (no churn if unread did not change).
  useEffect(() => {
    lastUnreadRef.current = unreadCount;
  }, [unreadCount]);

  const filtered = useMemo(() => {
    if (activeCategory === "All") return notifications;
    return notifications.filter(
      (item) => categoryFor(item.notification_type) === activeCategory
    );
  }, [activeCategory, notifications]);

  const grouped = useMemo(() => {
    const buckets = { Today: [], Yesterday: [], Earlier: [] };
    filtered.forEach((item) => {
      buckets[relativeBucket(item.created_at)].push(item);
    });
    return buckets;
  }, [filtered]);

  const hasAny = filtered.length > 0;

  return (
    <div className="notification-bell" ref={containerRef}>
      <button
        type="button"
        className="notification-bell-btn"
        onClick={() => setOpen((value) => !value)}
        aria-label="Notifications"
        aria-expanded={open}
      >
        <Bell size={18} aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
        )}
        <span
          className={`notification-bell-pulse${
            connected ? " notification-bell-pulse--on" : ""
          }`}
          title={connected ? "Live" : "Refreshing"}
        />
      </button>

      {open && (
        <div className="notification-menu">
          <div className="notification-menu-header">
            <strong>Notifications</strong>
            <div className="notification-menu-header-actions">
              {unreadCount > 0 && (
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary"
                  onClick={markAllRead}
                >
                  Mark all read
                </button>
              )}
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={refresh}
              >
                Refresh
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary notification-menu-close"
                onClick={() => setOpen(false)}
                aria-label="Close"
              >
                <X size={14} aria-hidden="true" />
              </button>
            </div>
          </div>

          <div className="notification-tabs">
            {NOTIFICATION_CATEGORIES.map((category) => (
              <button
                key={category}
                type="button"
                className={`notification-tab${
                  activeCategory === category ? " active" : ""
                }`}
                onClick={() => setActiveCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>

          {!hasAny ? (
            <div className="notification-empty">
              <Bell size={22} aria-hidden="true" />
              <p>No notifications yet.</p>
            </div>
          ) : (
            <div className="notification-list">
              {["Today", "Yesterday", "Earlier"].map((bucket) =>
                grouped[bucket].length === 0 ? null : (
                  <div key={bucket} className="notification-group">
                    <div className="notification-group__label">{bucket}</div>
                    {grouped[bucket].slice(0, 8).map((item) => (
                      <NotificationCard
                        key={item.id}
                        notification={item}
                        onMarkRead={markRead}
                        onNavigate={() => setOpen(false)}
                      />
                    ))}
                  </div>
                )
              )}
            </div>
          )}

          <div className="notification-menu-footer">
            <Link to="/notifications" onClick={() => setOpen(false)}>
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;