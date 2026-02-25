import React, { useRef, useState } from "react";

const ACCEPT = ".pdf,.xlsx,.csv,.json";

export default function UploadDropzone({ file, onSelectFile, onAnalyze, analyzing, message, error }) {
  const inputRef = useRef(null);
  const [active, setActive] = useState(false);

  return (
    <section className="card ai-plugin-card space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Manual Transaction Upload</h3>
        <p className="ai-plugin-subtle mt-1">Upload PDF, Excel, CSV, or JSON and run audit-risk analysis.</p>
      </div>

      <div
        className={`ai-dropzone ${active ? "is-active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setActive(true);
        }}
        onDragLeave={() => setActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setActive(false);
          onSelectFile(event.dataTransfer.files?.[0]);
        }}
      >
        <p className="font-medium">Drag and drop file here</p>
        <p className="ai-plugin-subtle mt-1">Accepted formats: PDF, Excel (.xlsx), CSV, JSON</p>
        <button className="btn-outline mt-3" type="button" onClick={() => inputRef.current?.click()}>
          Choose File
        </button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={ACCEPT}
          onChange={(event) => onSelectFile(event.target.files?.[0])}
        />
      </div>

      <p className="ai-plugin-subtle">{file ? `${file.name} (${Math.round(file.size / 1024)} KB)` : "No file selected."}</p>

      <button className="btn-primary w-full" type="button" onClick={onAnalyze} disabled={analyzing || !file}>
        {analyzing ? "Analyzing..." : "Analyze & Store"}
      </button>

      {message && <p className="text-sm text-emerald-600">{message}</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}
    </section>
  );
}
