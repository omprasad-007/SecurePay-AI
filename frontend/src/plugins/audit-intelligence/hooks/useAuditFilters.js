import { useMemo, useState } from "react";
import { defaultDateRange } from "../services/auditApi";

const DEFAULTS = {
  ...defaultDateRange(30),
  risk_level: "",
  transaction_status: "",
  user_id: "",
};

export function useAuditFilters(initial = {}) {
  const [filters, setFilters] = useState(() => ({ ...DEFAULTS, ...initial }));
  const [refreshKey, setRefreshKey] = useState(0);

  const normalizedFilters = useMemo(() => {
    const next = { ...filters };
    Object.keys(next).forEach((key) => {
      if (next[key] === undefined || next[key] === null || next[key] === "") {
        delete next[key];
      }
    });
    return next;
  }, [filters]);

  const setField = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const apply = () => setRefreshKey((value) => value + 1);
  const reset = () => setFilters({ ...DEFAULTS, ...initial });

  return {
    filters,
    normalizedFilters,
    setField,
    apply,
    reset,
    refreshKey,
  };
}
