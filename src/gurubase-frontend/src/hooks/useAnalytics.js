import { useEffect, useState } from "react";

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

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await getStatCards(guruType, interval);

        setData(result);
        setError(null);
      } catch (err) {
        console.log("Error fetching data", err);
        setError(err.message);
      } finally {
        setLoading(false);
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

  if (metricType === null) return { data: null, loading: false, error: null };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await getHistogram(guruType, metricType, interval);

        setData(result);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
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

  useEffect(() => {
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

        setData(result);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [guruType, metricType, interval, filterType, page]);

  return { data, loading, error };
};

export const useDataSourceQuestions = (guruType, url, initialPage = 1) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(initialPage);

  console.log("guruType", guruType);
  console.log("url", url);
  console.log("page", page);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        console.log("fetching data");
        const result = await getDataSourceQuestions(guruType, url, page);

        console.log("result", result);
        setData(result);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (url && guruType) {
      fetchData();
    }
  }, [guruType, url, page]);

  return {
    data,
    loading,
    error,
    page,
    setPage
  };
};
