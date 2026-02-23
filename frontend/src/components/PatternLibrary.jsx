import React from "react";

export default function PatternLibrary({ patterns = [] }) {
  const library = [
    "Smurfing",
    "Rapid-fire microtransactions",
    "Circular flow",
    "Dormant activation"
  ];

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold mb-3">Fraud Pattern Library</h3>
      <div className="grid gap-2">
        {library.map((item) => {
          const detected = patterns.includes(item);
          return (
            <div key={item} className="flex items-center justify-between rounded-xl px-3 py-2 border border-slate-200">
              <span className="text-sm">{item}</span>
              <span className={`badge ${detected ? "badge-high" : "badge-low"}`}>{detected ? "Detected" : "Not Found"}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
