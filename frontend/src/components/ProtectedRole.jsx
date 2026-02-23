import React from "react";

export default function ProtectedRole({ allow = [], role, children, fallback = null }) {
  if (!allow.includes(role)) return fallback;
  return children;
}
