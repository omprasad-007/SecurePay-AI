import React, { useState } from "react";
import { NavLink } from "react-router-dom";

const links = [
  { name: "Dashboard", path: "/" },
  { name: "Transactions", path: "/transactions" },
  { name: "Fraud Analytics", path: "/analytics" },
  { name: "Fraud Heatmap", path: "/heatmap" },
  { name: "Simulation Lab", path: "/simulation" },
  { name: "Excel Upload", path: "/excel-upload" },
  { name: "About", path: "/about" }
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <aside className="bg-[var(--card)] border-r border-slate-200/50 px-6 py-6 lg:min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-xl font-semibold">SecurePay AI</h2>
          <p className="text-sm text-muted">Fraud Defense Suite</p>
        </div>
        <button className="btn-outline lg:hidden" onClick={() => setOpen((prev) => !prev)}>{open ? "Close" : "Menu"}</button>
      </div>
      <nav className={`space-y-3 ${open ? "block" : "hidden"} lg:block`}>
        {links.map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            end={link.path === "/"}
            className={({ isActive }) =>
              `block px-4 py-3 rounded-xl font-medium transition ${isActive ? "bg-[var(--primary)] text-white shadow" : "text-slate-600 hover:bg-slate-100"}`
            }
          >
            {link.name}
          </NavLink>
        ))}
      </nav>
      <div className="mt-8 p-4 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-cyan-400/10">
        <p className="text-sm font-semibold">Live Defense Status</p>
        <p className="text-xs text-muted mt-2">Adaptive risk, graph intelligence, decision engine, and Excel intelligence are active.</p>
      </div>
    </aside>
  );
}
