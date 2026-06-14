const DAILY_GOAL_KEY = "daily_study_goal_minutes";
const STREAK_KEY = "study_streak_data";

export const getTodayDateString = () => {
  return new Date().toISOString().split("T")[0];
};

export const getYesterdayDateString = () => {
  const date = new Date();
  date.setDate(date.getDate() - 1);
  return date.toISOString().split("T")[0];
};

export const getDailyGoalMinutes = () => {
  return Number(localStorage.getItem(DAILY_GOAL_KEY)) || 120;
};

export const setDailyGoalMinutes = (minutes) => {
  localStorage.setItem(DAILY_GOAL_KEY, String(minutes));
};

export const getStudyStreak = () => {
  const raw = localStorage.getItem(STREAK_KEY);

  if (!raw) {
    return {
      count: 0,
      lastStudyDate: null,
    };
  }

  return JSON.parse(raw);
};

export const markStudyActivity = () => {
  const today = getTodayDateString();
  const yesterday = getYesterdayDateString();

  const streak = getStudyStreak();

  if (streak.lastStudyDate === today) {
    return streak;
  }

  let newCount = 1;

  if (streak.lastStudyDate === yesterday) {
    newCount = streak.count + 1;
  }

  const updated = {
    count: newCount,
    lastStudyDate: today,
  };

  localStorage.setItem(STREAK_KEY, JSON.stringify(updated));

  return updated;
};

export const getGoalProgressPercent = (todayMinutes, goalMinutes) => {
  if (!goalMinutes || goalMinutes <= 0) return 0;

  return Math.min(100, Math.round((todayMinutes / goalMinutes) * 100));
};