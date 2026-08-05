import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import api from "../api/api";
import { useAuth } from "../auth/AuthContext";
import { metaFor, routeForNotification } from "./notificationMeta";

const NotificationContext = createContext(null);

const POLL_INTERVAL_MS = 30_000;
const RECONNECT_BASE_MS = 2_000;
const RECONNECT_MAX_MS = 30_000;
const KNOWN_IDS_LIMIT = 200;

export const NotificationProvider = ({ children }) => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [connected, setConnected] = useState(false);

  const wsRef = useRef(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef(null);
  const pollTimer = useRef(null);
  const knownIds = useRef(new Set());
  const mountedRef = useRef(true);

  const authed = Boolean(user);

  const rememberIds = useCallback((items) => {
    items.forEach((item) => knownIds.current.add(item.id));
    const arr = Array.from(knownIds.current);
    if (arr.length > KNOWN_IDS_LIMIT) {
      knownIds.current = new Set(arr.slice(arr.length - KNOWN_IDS_LIMIT));
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!authed) return;
    try {
      const [listRes, countRes] = await Promise.all([
        api.get("/notifications/"),
        api.get("/notifications/unread-count/"),
      ]);
      const list = Array.isArray(listRes.data) ? listRes.data : [];
      rememberIds(list);
      setNotifications(list);
      setUnreadCount(Number(countRes.data?.unread_count || 0));
    } catch (err) {
      // Non-fatal; polling/WS will retry.
      // eslint-disable-next-line no-console
      console.error("Failed to load notifications:", err);
    }
  }, [authed, rememberIds]);

  const markRead = useCallback(async (id) => {
    setNotifications((items) =>
      items.map((item) =>
        item.id === id ? { ...item, is_read: true } : item
      )
    );
    setUnreadCount((count) => Math.max(0, count - 1));
    try {
      await api.post(`/notifications/read/${id}/`);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Failed to mark notification as read:", err);
    }
  }, []);

  const markAllRead = useCallback(async () => {
    setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
    setUnreadCount(0);
    try {
      await api.post("/notifications/read-all/");
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Failed to mark all notifications as read:", err);
    }
  }, []);

  const handleIncoming = useCallback(
    (payload) => {
      if (!payload || typeof payload !== "object") return;
      if (knownIds.current.has(payload.id)) return;
      knownIds.current.add(payload.id);

      setNotifications((items) => [payload, ...items].slice(0, 100));
      setUnreadCount((count) => count + 1);

      const meta = metaFor(payload.notification_type);
      const target = routeForNotification(payload);
      const Icon = meta.icon;
      toast.custom(
        (t) => (
          <div
            className="nc-toast"
            style={{ borderLeftColor: meta.color.accent }}
            onClick={() => {
              toast.dismiss(t.id);
              if (target) {
                navigate(target);
                markRead(payload.id);
              }
            }}
            role="button"
            tabIndex={0}
          >
            <span
              className="nc-toast__icon"
              style={{ background: meta.color.bg, color: meta.color.fg }}
            >
              <Icon size={16} aria-hidden="true" />
            </span>
            <span className="nc-toast__body">
              <strong>{payload.title}</strong>
              <span>{payload.message}</span>
            </span>
          </div>
        ),
        { duration: 6000, position: "bottom-right" }
      );
    },
    [navigate, markRead]
  );

  const startPolling = useCallback(() => {
    if (pollTimer.current) return;
    refresh();
    pollTimer.current = setInterval(refresh, POLL_INTERVAL_MS);
  }, [refresh]);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const connectWs = useCallback(() => {
    if (!authed) return;
    const token = localStorage.getItem("access_token");
    if (!token) {
      startPolling();
      return;
    }

    try {
      const base = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
      const wsBase = base
        .replace(/^http:/, "ws:")
        .replace(/^https:/, "wss:")
        .replace(/\/api\/?$/, "");
      const url = `${wsBase}/ws/notifications/?token=${encodeURIComponent(token)}`;

      const socket = new WebSocket(url);
      wsRef.current = socket;

      socket.onopen = () => {
        if (!mountedRef.current) return;
        reconnectAttempt.current = 0;
        setConnected(true);
        stopPolling();
      };

      socket.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const payload = JSON.parse(event.data);
          handleIncoming(payload);
        } catch (err) {
          // eslint-disable-next-line no-console
          console.error("Bad notification payload:", err);
        }
      };

      socket.onerror = () => {
        // Real-time delivery will degrade to polling; logged for diagnostics.
      };

      socket.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        wsRef.current = null;
        startPolling();
        scheduleReconnect();
      };
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Unable to open notification socket:", err);
      startPolling();
    }
  }, [authed, handleIncoming, startPolling, stopPolling]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimer.current) return;
    if (reconnectAttempt.current >= 8) return; // give up gracefully
    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** reconnectAttempt.current,
      RECONNECT_MAX_MS
    );
    reconnectAttempt.current += 1;
    reconnectTimer.current = setTimeout(() => {
      reconnectTimer.current = null;
      connectWs();
    }, delay);
  }, [connectWs]);

  useEffect(() => {
    mountedRef.current = true;
    if (!authed) {
      setNotifications([]);
      setUnreadCount(0);
      setConnected(false);
      stopPolling();
      return undefined;
    }

    knownIds.current = new Set();
    refresh();
    connectWs();

    return () => {
      mountedRef.current = false;
      stopPolling();
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed]);

  const value = {
    notifications,
    unreadCount,
    connected,
    refresh,
    markRead,
    markAllRead,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => useContext(NotificationContext);