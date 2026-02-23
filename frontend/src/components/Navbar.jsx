import React from "react";
import ThemeToggle from "./ThemeToggle.jsx";
import { ROLES } from "../utils/themeManager";

export default function Navbar({ user, role, onRoleChange, onLogout }) {
  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between px-6 py-5 border-b border-slate-200/50">
      <div>
        <p className="text-sm text-muted">SecurePay AI</p>
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome back, <span className="gradient-text">{user?.email?.split("@")[0] || "Analyst"}</span>
        </h1>
      </div>
      <div className="flex items-center gap-3">
        <select className="btn-outline" value={role} onChange={(e) => onRoleChange(e.target.value)}>
          <option value={ROLES.ADMIN}>Admin</option>
          <option value={ROLES.ANALYST}>Risk Analyst</option>
          <option value={ROLES.AUDITOR}>Auditor</option>
        </select>
        <ThemeToggle />
        <button className="btn-outline" onClick={onLogout}>Logout</button>
      </div>
    </header>
  );
}
