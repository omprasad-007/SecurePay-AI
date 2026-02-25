import React, { useState } from "react";
import "../styles.css";
import UploadDropzone from "../components/UploadDropzone";
import UploadPreviewTable from "../components/UploadPreviewTable";
import UploadResultPanel from "../components/UploadResultPanel";
import { uploadAuditTransactions } from "../services/auditApi";
import { parseUploadPreview, validateUploadSelection } from "../services/uploadPreview";

export default function AuditUploadPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const onSelectFile = async (pickedFile) => {
    if (!pickedFile) return;

    setError("");
    setMessage("");
    setResult(null);

    const validation = validateUploadSelection(pickedFile);
    if (validation) {
      setFile(null);
      setPreview(null);
      setError(validation);
      return;
    }

    setFile(pickedFile);
    const parsed = await parseUploadPreview(pickedFile);
    setPreview(parsed);
  };

  const onAnalyze = async () => {
    if (!file) {
      setError("Select a file first.");
      return;
    }

    setAnalyzing(true);
    setError("");
    setMessage("");
    try {
      const payload = await uploadAuditTransactions(file, preview?.normalizedRows || []);
      setResult(payload);
      setMessage("Analysis complete and records stored.");
      window.dispatchEvent(new Event("audit-intelligence-updated"));
    } catch (err) {
      setError(err?.message || "Failed to analyze uploaded file.");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="card" style={{ padding: "1rem 1.1rem" }}>
        <h1 style={{ margin: 0, fontSize: "1.35rem", fontWeight: 700 }}>Manual Transaction Upload</h1>
        <p className="text-muted" style={{ marginTop: "0.35rem" }}>
          Drag and drop audit files, preview structured rows, and run fraud scoring with analyze-and-store workflow.
        </p>
      </div>

      <div className="ai-plugin-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
        <UploadDropzone
          file={file}
          onSelectFile={onSelectFile}
          onAnalyze={onAnalyze}
          analyzing={analyzing}
          message={message}
          error={error}
        />

        <UploadPreviewTable preview={preview} />
      </div>

      <UploadResultPanel result={result} />
    </div>
  );
}
