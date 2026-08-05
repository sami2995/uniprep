import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";

import {
  dateLabel,
  formatRelativeTime,
  metaFor,
  routeForNotification,
} from "../notifications/notificationMeta";

const CTA_LABEL = {
  learning_path_ready: "Open Learning Path",
  learning_step_unlocked: "Open Learning Path",
  learning_path_completed: "View Path",
  weak_topic: "Start Review",
  mock_available: "Take Exam",
  battle_invite: "Open Lobby",
  material_uploaded: "Open Materials",
  weekly_reminder: "Go to Dashboard",
};

const NotificationCard = ({ notification, onNavigate, onMarkRead, compact }) => {
  const navigate = useNavigate();
  const [marked, setMarked] = useState(notification.is_read);

  const meta = metaFor(notification.notification_type);
  const Icon = meta.icon;
  const target = routeForNotification(notification);
  const unread = !marked;

  const modifier = meta.label.toLowerCase().replace(/\s+/g, "-");

  const handleClick = () => {
    if (target) {
      if (onNavigate) onNavigate(notification);
      navigate(target);
      if (unread) handleMarkRead();
    }
  };

  const handleMarkRead = (e) => {
    if (e) e.stopPropagation();
    setMarked(true);
    if (onMarkRead) onMarkRead(notification.id);
  };

  return (
    <div
      className={`nc-card nc-card--${modifier}${unread ? " nc-card--unread" : ""}`}
      onClick={handleClick}
      role={target ? "button" : undefined}
      tabIndex={target ? 0 : undefined}
      style={{
        "--nc-accent": meta.color.accent,
        "--nc-bg": meta.color.bg,
        "--nc-fg": meta.color.fg,
      }}
    >
      {unread && <span className="nc-card__dot" aria-hidden="true" />}

      <span
        className="nc-card__icon"
        style={{ background: meta.color.bg, color: meta.color.fg }}
      >
        <Icon size={18} aria-hidden="true" />
      </span>

      <div className="nc-card__body">
        <div className="nc-card__header">
          <strong className="nc-card__title" title={meta.label}>
            {Icon ? meta.label : notification.title}
          </strong>
          <span
            className="nc-card__time"
            title={dateLabel(notification.created_at)}
          >
            {formatRelativeTime(notification.created_at)}
          </span>
        </div>

        <p className="nc-card__message">{notification.message}</p>

        {(target || unread) && (
          <div className="nc-card__actions">
            {target && (
              <button
                type="button"
                className="nc-card__cta"
                onClick={handleClick}
                style={{ color: meta.color.fg }}
              >
                {CTA_LABEL[notification.notification_type] || "Open"}
              </button>
            )}
            {unread && (
              <button
                type="button"
                className="nc-card__read"
                onClick={handleMarkRead}
                aria-label="Mark as read"
              >
                <Check size={14} aria-hidden="true" /> Mark read
              </button>
            )}
          </div>
        )}
      </div>

      {!compact && null}
    </div>
  );
};

export default NotificationCard;