import { useMemo, useState } from "react";

function isoDate(value) {
  return value.toISOString().slice(0, 10);
}

export function useHeatmapFilters() {
  const initial = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 30);
    return {
      start_date: isoDate(start),
      end_date: isoDate(end),
      risk_level: "",
      min_amount: "",
      max_amount: "",
      user_segment: "",
      device_type: "",
      limit: 2000,
    };
  }, []);

  const [filters, setFilters] = useState(initial);
  const [refreshKey, setRefreshKey] = useState(0);

  const normalizedFilters = useMemo(() => {
    const payload = { ...filters };
    if (payload.min_amount === "") delete payload.min_amount;
    if (payload.max_amount === "") delete payload.max_amount;
    if (!payload.risk_level) delete payload.risk_level;
    if (!payload.user_segment) delete payload.user_segment;
    if (!payload.device_type) delete payload.device_type;
    return payload;
  }, [filters]);

  return {
    filters,
    normalizedFilters,
    refreshKey,
    setField: (name, value) => setFilters((prev) => ({ ...prev, [name]: value })),
    refresh: () => setRefreshKey((prev) => prev + 1),
    reset: () => setFilters(initial),
  };
}

