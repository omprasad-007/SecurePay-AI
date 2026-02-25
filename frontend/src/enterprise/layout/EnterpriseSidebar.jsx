import React from "react";
import { NavLink } from "react-router-dom";
import { menuByRole } from "../rbac/permissions";

export default function EnterpriseSidebar({ role, user, organization, onLogout }) {
  const items = menuByRole(role);

  return (
    <aside className="bg-[var(--card)] border-r border-slate-200/50 px-5 py-6 lg:min-h-screen">
      <div className="mb-6">
        <h2 className="text-lg font-semibold">SecurePay Enterprise</h2>
        <p className="text-xs text-muted mt-1">Multi-tenant fraud operations</p>
      </div>
      <div className="mb-6 rounded-xl border border-slate-200/50 p-3">
        <p className="text-xs text-muted">Organization</p>
        <p className="text-sm font-semibold">{organization?.name || "Unknown"}</p>
        <p className="text-xs text-muted mt-2">Signed in as</p>
        <p className="text-sm">{user?.email || "-"}</p>
        <p className="text-xs text-muted mt-1">Role: {role}</p>
      </div>

      <nav className="space-y-2">
        {items.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) =>
              `block rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                isActive ? "bg-[var(--primary)] text-white" : "text-slate-600 hover:bg-slate-100"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <button className="btn-outline mt-6 w-full" onClick={onLogout} type="button">
        Sign Out
      </button>
    </aside>
  );
}
