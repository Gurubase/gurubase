import {
  getAnalyticsDataSourceQuestions,
  getAnalyticsHistogram,
  getAnalyticsStats,
  getAnalyticsTable
} from "@/utils/clientActions";

export const METRIC_TYPES = {
  QUESTIONS: "questions",
  OUT_OF_CONTEXT: "out_of_context",
  REFERENCED_SOURCES: "referenced_sources"
};

const handleRequestError = (error) => {
  // console.error("Analytics request failed:", {
  //   error: error.message,
  //   stack: error.stack,
  //   ...context
  // });

  return { error: true, message: error.message };
};

export const getStatCards = async (guruType, interval) => {
  try {
    const data = await getAnalyticsStats(guruType, interval);

    return data;
  } catch (error) {
    return handleRequestError(error);
  }
};

export const getHistogram = async (guruType, metricType, interval) => {
  try {
    const data = await getAnalyticsHistogram(guruType, metricType, interval);

    return data;
  } catch (error) {
    return handleRequestError(error);
  }
};

export const getTableData = async (
  guruType,
  metricType,
  interval,
  filterType,
  page,
  searchQuery = "",
  sortOrder = "desc"
) => {
  try {
    const data = await getAnalyticsTable(
      guruType,
      metricType,
      interval,
      filterType,
      page,
      searchQuery,
      sortOrder
    );

    return data;
  } catch (error) {
    return handleRequestError(error);
  }
};

export const getDataSourceQuestions = async (
  guruType,
  url,
  filterType,
  interval,
  page,
  searchQuery = "",
  sortOrder = "desc"
) => {
  try {
    const data = await getAnalyticsDataSourceQuestions(
      guruType,
      url,
      filterType,
      interval,
      page,
      searchQuery,
      sortOrder
    );

    return data;
  } catch (error) {
    return handleRequestError(error);
  }
};
