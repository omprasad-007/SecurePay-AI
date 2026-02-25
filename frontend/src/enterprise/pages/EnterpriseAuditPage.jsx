import React, { useState } from "react";
import { exportAuditLogs, getAuditLogs } from "../services/auditApi";
import { downloadBlob } from "../utils";

export default function EnterpriseAuditPage() {
  const [rows, setRows] = useState([]);

  const loadLogs = async () => {
    const response = await getAuditLogs({ page: 1, page_size: 50 });
    setRows(response.items || []);
  };

  const downloadCsv = async () => {
    const blob = await exportAuditLogs({ format: "csv" });
    downloadBlob(blob, "audit_logs.csv");
  };

  return (
    <div className="space-y-4">
      <div className="card p-4 flex items-center gap-3">
        <button className="btn-primary" onClick={loadLogs}>Load Audit Logs</button>
        <button className="btn-outline" onClick={downloadCsv}>Export CSV</button>
      </div>
      <div className="card p-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted">
              <th className="py-2">Timestamp</th>
              <th className="py-2">User</th>
              <th className="py-2">Action</th>
              <th className="py-2">Entity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.log_id} className="border-t border-slate-200/30">
                <td className="py-2">{new Date(row.timestamp).toLocaleString()}</td>
                <td className="py-2">{row.user_id}</td>
                <td className="py-2">{row.action_type}</td>
                <td className="py-2">{row.entity_type}</td>
              </tr>
            ))}
            {!rows.length && (
              <tr><td colSpan={4} className="py-4 text-muted">No audit logs loaded</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
