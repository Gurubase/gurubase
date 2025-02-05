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
  page
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
          page
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
  }, [guruType, metricType, interval, filterType, page]);

  return { data, loading, error };
};

export const useDataSourceQuestions = (
  guruType,
  url,
  filterType,
  interval,
  initialPage = 1
) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(initialPage);
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
          page
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

    if (url && guruType) {
      fetchData();
    }
  }, [guruType, url, filterType, interval, page]);

  return {
    data,
    loading,
    error,
    page,
    setPage
  };
};
