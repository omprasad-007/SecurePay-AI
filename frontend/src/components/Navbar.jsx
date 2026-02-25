import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle.jsx";
import API_BASE_URL from "../config/api";
import { auth } from "../utils/firebase";
import { ROLES, getStoredRole } from "../utils/themeManager";

export default function Navbar({ user, role, onRoleChange, onLogout }) {
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  const loadAlerts = useCallback(async () => {
    try {
      const headers = {
        "X-User-Role": getStoredRole(),
      };
      if (auth.currentUser) {
        const token = await auth.currentUser.getIdToken();
        headers.Authorization = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/alerts?limit=20`, {
        method: "GET",
        headers,
      });

      if (!response.ok) return;
      const payload = await response.json();
      setUnreadAlerts(Number(payload?.unread_count || 0));
    } catch {
      setUnreadAlerts(0);
    }
  }, []);

  useEffect(() => {
    loadAlerts();
    const interval = window.setInterval(loadAlerts, 60000);
    window.addEventListener("audit-intelligence-updated", loadAlerts);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("audit-intelligence-updated", loadAlerts);
    };
  }, [loadAlerts]);

  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between px-6 py-5 border-b border-slate-200/50">
      <div>
        <p className="text-sm text-muted">SecurePay AI</p>
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome back, <span className="gradient-text">{user?.email?.split("@")[0] || "Analyst"}</span>
        </h1>
      </div>
      <div className="flex items-center gap-3">
        <Link to="/risk-intelligence" className="btn-outline" style={{ position: "relative", textDecoration: "none" }}>
          Alerts
          {unreadAlerts > 0 && (
            <span
              className="badge badge-high"
              style={{
                position: "absolute",
                top: "-0.55rem",
                right: "-0.45rem",
                minWidth: "1.35rem",
                textAlign: "center",
                padding: "0.2rem 0.38rem",
              }}
            >
              {unreadAlerts > 99 ? "99+" : unreadAlerts}
            </span>
          )}
        </Link>
        <select className="btn-outline" value={role} onChange={(e) => onRoleChange(e.target.value)}>
          <option value={ROLES.ADMIN}>Admin</option>
          <option value={ROLES.ANALYST}>Risk Analyst</option>
          <option value={ROLES.AUDITOR}>Auditor</option>
        </select>
        <ThemeToggle />
        <button className="btn-outline" onClick={onLogout}>
          Logout
        </button>
      </div>
    </header>
  );
}
