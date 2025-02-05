import { makeAuthenticatedRequest } from "@/app/actions";

export const METRIC_TYPES = {
  QUESTIONS: "questions",
  OUT_OF_CONTEXT: "out_of_context",
  REFERENCED_SOURCES: "referenced_sources"
};

const handleRequestError = (error, context = {}) => {
  console.error("Analytics request failed:", {
    error: error.message,
    stack: error.stack,
    ...context
  });

  return { error: true, message: error.message };
};

export const getStatCards = async (guruType, interval) => {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/analytics/stats?interval=${interval}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      },
      true
    );

    if (!response?.data) return null;

    console.log("response", response);
    return response.data;
  } catch (error) {
    return handleRequestError(error, {
      context: "getStatCards",
      guruType,
      interval
    });
  }
};

export const getHistogram = async (guruType, metricType, interval) => {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/analytics/histogram?metric_type=${metricType}&interval=${interval}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      },
      true
    );

    console.log("response", response);
    if (!response?.data) return null;

    return response.data;
  } catch (error) {
    return handleRequestError(error, {
      context: "getHistogram",
      guruType,
      metricType,
      interval
    });
  }
};

export const getTableData = async (
  guruType,
  metricType,
  interval,
  filterType,
  page
) => {
  try {
    const params = new URLSearchParams({
      metric_type: metricType,
      interval,
      filter_type: filterType,
      page: page.toString()
    });

    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/analytics/table?${params}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      },
      true
    );

    if (!response) return null;

    return response;
  } catch (error) {
    return handleRequestError(error, {
      context: "getTableData",
      guruType,
      metricType,
      interval,
      filterType,
      page
    });
  }
};

export const getDataSourceQuestions = async (
  guruType,
  url,
  filterType,
  interval,
  page
) => {
  try {
    const params = new URLSearchParams({
      url: url,
      filter_type: filterType,
      interval: interval,
      page: page.toString()
    });

    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/data-source-questions/?${params}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      },
      true
    );

    if (!response) return null;

    return response;
  } catch (error) {
    return handleRequestError(error, {
      context: "getDataSourceQuestions",
      guruType,
      url,
      filterType,
      interval,
      page
    });
  }
};
