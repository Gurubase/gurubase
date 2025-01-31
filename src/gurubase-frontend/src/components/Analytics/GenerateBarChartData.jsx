export const generateBarChartData = (interval) => {
  const now = new Date();

  switch (interval) {
    case "today":
    case "yesterday": {
      const baseDate =
        interval === "today" ? now : new Date(now.getTime() - 86400000);
      return Array.from({ length: 24 }, (_, i) => {
        const date = new Date(baseDate);
        date.setHours(i, 0, 0, 0);
        return {
          date: date.toISOString(),
          questions: Math.floor(Math.random() * 30) + 5
        };
      });
    }
    case "7d": {
      return Array.from({ length: 7 }, (_, i) => {
        const date = new Date(now);
        date.setDate(date.getDate() - (6 - i));
        date.setHours(0, 0, 0, 0);
        return {
          date: date.toISOString(),
          questions: Math.floor(Math.random() * 100) + 20
        };
      });
    }
    case "30d": {
      return Array.from({ length: 30 }, (_, i) => {
        const date = new Date(now);
        date.setDate(date.getDate() - (29 - i));
        date.setHours(0, 0, 0, 0);
        return {
          date: date.toISOString(),
          questions: Math.floor(Math.random() * 100) + 20
        };
      });
    }
    default:
      return [];
  }
};
