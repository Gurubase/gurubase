import { useEffect, useState } from "react";

import {
  getHistogram,
  getStatCards,
  getTableData,
  METRIC_TYPES
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
