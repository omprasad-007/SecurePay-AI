import React, { useMemo, useRef, useState } from "react";
import { apiFetch } from "../utils/api";
import ExcelSummaryPanel from "../components/ExcelSummaryPanel.jsx";
import DatasetInsights from "../components/DatasetInsights.jsx";
import { validateUploadFile, fileToBase64 } from "../utils/fileParser";
import {
  getTransactions,
  getExcelSummary,
  getDatasetInsights,
  getDetectedPatterns,
  saveTransactions,
  saveDatasetInsights,
  saveExcelSummary,
  saveDetectedPatterns,
} from "../utils/fraudUtils";

function normalizeTransactionRow(tx, index) {
  const id = String(tx?.id || tx?.transaction_id || tx?.transactionId || `TXNUP-${Date.now()}-${index}`);
  return {
    id,
    userId: String(tx?.userId || tx?.user_id || "USER1"),
    receiverId: String(tx?.receiverId || tx?.receiver_id || "MERCH1"),
    amount: Number(tx?.amount || 0),
    deviceId: String(tx?.deviceId || tx?.device_id || "DEV-UP-0"),
    merchant: String(tx?.merchant || "Unknown"),
    channel: String(tx?.channel || "UPI"),
    ip: String(tx?.ip || "0.0.0.0"),
    location: tx?.location || { city: "Unknown", lat: 20.5937, lon: 78.9629 },
    timestamp: tx?.timestamp || new Date().toISOString(),
    finalScore: tx?.finalScore ?? tx?.final_score ?? null,
    riskLevel: tx?.riskLevel || tx?.risk_level || "LOW",
    features: tx?.features || {}
  };
}

export default function ExcelUpload() {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [summary, setSummary] = useState(() => getExcelSummary());
  const [insights, setInsights] = useState(() => getDatasetInsights());
  const [patterns, setPatterns] = useState(() => getDetectedPatterns());
  const [report, setReport] = useState("");
  const [pendingTransactions, setPendingTransactions] = useState([]);

  const fileLabel = useMemo(() => (file ? `${file.name} (${Math.round(file.size / 1024)} KB)` : "No file selected"), [file]);

  const onFilePicked = (picked) => {
    const validation = validateUploadFile(picked);
    if (validation) {
      setError(validation);
      setFile(null);
      return;
    }
    setError("");
    setFile(picked);
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please choose a file first");
      return;
    }

    setLoading(true);
    setError("");
    setToast("");
    setProgress(5);

    const interval = setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 10 : prev));
    }, 250);

    try {
      const history = getTransactions();
      const contentBase64 = await fileToBase64(file);
      const response = await apiFetch("/upload-excel", {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          content_base64: contentBase64,
          history,
        }),
      });

      const incoming = (response.transactions || []).map((tx, index) => normalizeTransactionRow(tx, index));
      setPendingTransactions(incoming);

      saveExcelSummary(response.analytics_summary || null);
      saveDatasetInsights(response.dataset_insights || null);
      saveDetectedPatterns(response.detected_patterns || []);

      setSummary(response.analytics_summary || null);
      setInsights(response.dataset_insights || null);
      setPatterns(response.detected_patterns || []);
      setToast(`Upload successful: ${incoming.length} transactions ready to add`);
      setProgress(100);
      window.dispatchEvent(new Event("transactions-updated"));
      setTimeout(() => setProgress(0), 1000);
    } catch (err) {
      setError(err.message || "Upload failed");
      setProgress(0);
    } finally {
      clearInterval(interval);
      setLoading(false);
    }
  };

  const addUploadedTransactions = () => {
    if (!pendingTransactions.length) {
      setError("No uploaded transactions to add");
      return;
    }

    const existing = getTransactions();
    const existingIds = new Set(existing.map((tx) => tx.id));
    const toAdd = pendingTransactions.filter((tx) => tx?.id && !existingIds.has(tx.id));
    const skipped = pendingTransactions.length - toAdd.length;
    const merged = [...toAdd, ...existing];

    saveTransactions(merged);
    localStorage.setItem("securepay_transactions_updated_at", new Date().toISOString());
    setPendingTransactions([]);
    setError("");
    setToast(
      skipped > 0
        ? `Added ${toAdd.length} transactions (${skipped} duplicates skipped)`
        : `Added ${toAdd.length} transactions`
    );
    window.dispatchEvent(new Event("transactions-updated"));
  };

  const generateReport = async () => {
    const readySummary = summary || getExcelSummary();
    const readyInsights = insights || getDatasetInsights();
    const readyPatterns = patterns.length ? patterns : getDetectedPatterns();

    if (!readySummary || !readyInsights) {
      setError("Upload a dataset before generating report");
      return;
    }
    try {
      setError("");
      setToast("");
      setSummary(readySummary);
      setInsights(readyInsights);
      setPatterns(readyPatterns);
      const response = await apiFetch("/upload-excel/report", {
        method: "POST",
        body: JSON.stringify({
          summary: readySummary,
          insights: readyInsights,
          patterns: readyPatterns,
        }),
      });
      setReport(response.report_markdown || "");
      setToast("Report generated successfully");
    } catch (err) {
      setError(err.message || "Report generation failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-2">AI Excel Intelligence</h2>
        <p className="text-sm text-muted mb-4">Upload CSV/XLSX, auto-map columns, clean data, run fraud scoring, and inject into existing transaction storage.</p>

        <div
          className={`upload-zone rounded-2xl p-8 text-center ${dragActive ? "upload-zone-active" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            onFilePicked(e.dataTransfer.files?.[0]);
          }}
        >
          <p className="text-sm mb-2">Drag & drop .csv/.xlsx file here</p>
          <button className="btn-outline" onClick={() => fileInputRef.current?.click()} type="button">Choose File</button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".csv,.xlsx"
            onChange={(e) => onFilePicked(e.target.files?.[0])}
          />
          <p className="text-xs text-muted mt-3">{fileLabel}</p>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button className="btn-primary" type="button" onClick={handleUpload} disabled={loading}>
            {loading ? "Processing..." : "Upload & Analyze"}
          </button>
          <button className="btn-primary" type="button" onClick={addUploadedTransactions} disabled={loading || !pendingTransactions.length}>
            Add Transactions {pendingTransactions.length ? `(${pendingTransactions.length})` : ""}
          </button>
          <button className="btn-outline" type="button" onClick={generateReport}>Generate Report</button>
        </div>

        {progress > 0 && (
          <div className="mt-4">
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-2 bg-sky-500 transition-all" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-xs text-muted mt-1">{progress}%</p>
          </div>
        )}

        {toast && <p className="mt-3 text-sm text-emerald-600">{toast}</p>}
        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
      </div>

      <ExcelSummaryPanel summary={summary} />
      <DatasetInsights insights={insights} />

      {report && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-3">Generated Documentation</h3>
          <pre className="whitespace-pre-wrap text-xs bg-slate-50 p-4 rounded-xl border border-slate-200">{report}</pre>
        </div>
      )}
    </div>
  );
}
