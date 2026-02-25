import React from "react";

const FORMAT_OPTIONS = [
  { value: "pdf", label: "PDF" },
  { value: "xlsx", label: "Excel (.xlsx)" },
  { value: "csv", label: "CSV" },
  { value: "json", label: "JSON" },
];

export default function AuditExportPanel({
  format,
  onFormatChange,
  onDownload,
  downloading,
  email,
  onEmailChange,
  onSendEmail,
  sendingEmail,
}) {
  return (
    <section className="card ai-plugin-card space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Advanced Export</h3>
        <p className="ai-plugin-subtle mt-1">Download filtered audit reports or send PDF export by email.</p>
      </div>

      <label>
        <span className="ai-plugin-subtle">Export Format</span>
        <select className="ai-plugin-select" value={format} onChange={(event) => onFormatChange(event.target.value)}>
          {FORMAT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <button className="btn-primary w-full" type="button" onClick={onDownload} disabled={downloading}>
        {downloading ? "Preparing export..." : "Download Report"}
      </button>

      <div className="pt-2 border-t border-slate-200/50">
        <label>
          <span className="ai-plugin-subtle">Email Audit Report</span>
          <input
            type="email"
            className="ai-plugin-input"
            placeholder="compliance@bank.com"
            value={email}
            onChange={(event) => onEmailChange(event.target.value)}
          />
        </label>

        <button
          className="btn-outline w-full mt-3"
          type="button"
          onClick={onSendEmail}
          disabled={sendingEmail || !String(email).trim()}
        >
          {sendingEmail ? "Sending..." : "Send Audit Report via Email"}
        </button>
      </div>
    </section>
  );
}
