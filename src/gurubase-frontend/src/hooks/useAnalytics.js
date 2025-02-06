import { useEffect, useRef, useState } from "react";

import {
  getDataSourceQuestions,
  getHistogram,
  getStatCards,
  getTableData
} from "@/services/analyticsService";

export const useStatCards = (guruType, interval) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestCounter = useRef(0);

  useEffect(() => {
    const currentRequestId = ++requestCounter.current;

    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await getStatCards(guruType, interval);

        // Only update state if this is still the most recent request
        if (currentRequestId === requestCounter.current && result) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (currentRequestId === requestCounter.current) {
          setError(err.message);
        }
      } finally {
        if (currentRequestId === requestCounter.current) {
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [guruType, interval]);

  return { data, loading, error };
};

export const useHistogram = (guruType, metricType, interval) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestCounter = useRef(0);

  if (metricType === null) return { data: null, loading: false, error: null };

  useEffect(() => {
    const currentRequestId = ++requestCounter.current;

    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await getHistogram(guruType, metricType, interval);

        // Only update state if this is still the most recent request
        if (currentRequestId === requestCounter.current && result) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (currentRequestId === requestCounter.current) {
          setError(err.message);
        }
      } finally {
        if (currentRequestId === requestCounter.current) {
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [guruType, metricType, interval]);

  return { data, loading, error };
};

export const useTableData = (
  guruType,
  metricType,
  interval,
  filterType,
  page,
  searchQuery = "",
  sortOrder,
  timeRange
) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestCounter = useRef(0);

  useEffect(() => {
    const currentRequestId = ++requestCounter.current;

    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await getTableData(
          guruType,
          metricType,
          interval,
          filterType,
          page,
          searchQuery,
          sortOrder,
          timeRange
        );

        // Only update state if this is still the most recent request
        if (currentRequestId === requestCounter.current && result) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (currentRequestId === requestCounter.current) {
          setError(err.message);
        }
      } finally {
        if (currentRequestId === requestCounter.current) {
          setLoading(false);
        }
      }
    };

    fetchData();
  }, [
    guruType,
    metricType,
    interval,
    filterType,
    page,
    searchQuery,
    sortOrder,
    timeRange
  ]);

  return {
    data,
    loading,
    error,
    sortOrder
  };
};

export const useDataSourceQuestions = (
  guruType,
  url,
  filterType,
  interval,
  initialPage = 1,
  searchQuery = "",
  initialSortOrder = "desc"
) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(initialPage);
  const [sortOrder, setSortOrder] = useState(initialSortOrder);
  const requestCounter = useRef(0);

  useEffect(() => {
    const currentRequestId = ++requestCounter.current;

    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await getDataSourceQuestions(
          guruType,
          url,
          filterType,
          interval,
          page,
          searchQuery,
          sortOrder
        );

        if (currentRequestId === requestCounter.current && result) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (currentRequestId === requestCounter.current) {
          setError(err.message);
        }
      } finally {
        if (currentRequestId === requestCounter.current) {
          setLoading(false);
        }
      }
    };

    if (url && guruType) {
      fetchData();
    }
  }, [guruType, url, filterType, interval, page, searchQuery, sortOrder]);

  return {
    data,
    loading,
    error,
    page,
    setPage,
    sortOrder,
    setSortOrder
  };
};
