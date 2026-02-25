import React from "react";

export default function UploadPreviewTable({ preview }) {
  const columns = Array.isArray(preview?.columns) ? preview.columns : [];
  const rows = Array.isArray(preview?.rows) ? preview.rows : [];

  return (
    <section className="card ai-plugin-card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">File Preview</h3>
        <span className="ai-plugin-subtle">{rows.length} rows shown</span>
      </div>

      {preview?.note && <p className="ai-plugin-subtle">{preview.note}</p>}

      {!columns.length && <p className="ai-plugin-subtle">Upload a file to preview structured data before analysis.</p>}

      {!!columns.length && (
        <div className="ai-table-wrap">
          <table className="ai-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={`${rowIndex}-${columns[0] || "row"}`}>
                  {columns.map((column) => (
                    <td key={`${rowIndex}-${column}`}>{String(row?.[column] ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
