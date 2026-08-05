import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, CheckCheck, RefreshCw } from "lucide-react";

import { useNotifications } from "../notifications/NotificationContext";
import {
  NOTIFICATION_CATEGORIES,
  categoryFor,
  relativeBucket,
} from "../notifications/notificationMeta";
import NotificationCard from "../components/NotificationCard";

const Notifications = () => {
  const {
    notifications,
    unreadCount,
    connected,
    refresh,
    markRead,
    markAllRead,
  } = useNotifications();
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState("All");

  const countsByCategory = useMemo(() => {
    const counts = {};
    NOTIFICATION_CATEGORIES.forEach((c) => (counts[c] = 0));
    notifications.forEach((item) => {
      counts.All += 1;
      counts[categoryFor(item.notification_type)] += 1;
    });
    return counts;
  }, [notifications]);

  const filtered = useMemo(() => {
    if (activeCategory === "All") return notifications;
    return notifications.filter(
      (item) => categoryFor(item.notification_type) === activeCategory
    );
  }, [activeCategory, notifications]);

  const grouped = useMemo(() => {
    const buckets = { Today: [], Yesterday: [], Earlier: [] };
    filtered.forEach((item) => buckets[relativeBucket(item.created_at)].push(item));
    return buckets;
  }, [filtered]);

  const hasAny = filtered.length > 0;

  return (
    <div className="notifications-page">
      <div className="notifications-page__top">
        <div>
          <h1 className="notifications-page__title">Notifications</h1>
          <p className="notifications-page__subtitle">
            {connected
              ? "Live · updates stream in real time."
              : `Showing ${notifications.length} most recent. Synced ${
                  notifications.length ? "on demand" : "when you generate activity"
                }.`}
          </p>
        </div>
        <div className="notifications-page__actions">
          {unreadCount > 0 && (
            <button
              type="button"
              className="btn btn-sm btn-outline-primary"
              onClick={markAllRead}
            >
              <CheckCheck size={15} /> Mark all read
            </button>
          )}
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={refresh}
          >
            <RefreshCw size={15} /> Refresh
          </button>
        </div>
      </div>

      <div className="notification-tabs notification-tabs--page">
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
            {countsByCategory[category] > 0 && (
              <span className="notification-tab__count">
                {countsByCategory[category]}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="notification-legend">
        {[
          { label: "Approved", cls: "green" },
          { label: "Assignment", cls: "blue" },
          { label: "AI", cls: "purple" },
          { label: "Reminder", cls: "orange" },
          { label: "Rejected", cls: "red" },
          { label: "System", cls: "gray" },
        ].map((entry) => (
          <span key={entry.label} className={`notification-legend__chip is-${entry.cls}`}>
            {entry.label}
          </span>
        ))}
      </div>

      {!hasAny ? (
        <div className="notification-empty notification-empty--large">
          <Bell size={32} aria-hidden="true" />
          <p>No notifications yet.</p>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={() => navigate(-1)}
          >
            Go back
          </button>
        </div>
      ) : (
        <div className="notifications-page__list">
          {["Today", "Yesterday", "Earlier"].map((bucket) =>
            grouped[bucket].length === 0 ? null : (
              <section key={bucket} className="notification-group">
                <div className="notification-group__label">{bucket}</div>
                {grouped[bucket].map((item) => (
                  <NotificationCard
                    key={item.id}
                    notification={item}
                    onMarkRead={markRead}
                  />
                ))}
              </section>
            )
          )}
        </div>
      )}
    </div>
  );
};

export default Notifications;