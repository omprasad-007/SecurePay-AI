function extensionOf(fileName) {
  const normalized = String(fileName || "").toLowerCase();
  if (!normalized.includes(".")) return "";
  return normalized.slice(normalized.lastIndexOf("."));
}

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) return parsed;
  return null;
}

function csvLineToValues(line) {
  const values = [];
  let current = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const ch = line[index];
    if (ch === '"') {
      const next = line[index + 1];
      if (quoted && next === '"') {
        current += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
      continue;
    }
    if (ch === "," && !quoted) {
      values.push(current);
      current = "";
      continue;
    }
    current += ch;
  }
  values.push(current);
  return values.map((value) => value.trim());
}

function parseCsvText(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return [];

  const headers = csvLineToValues(lines[0]).map((header, index) => header || `column_${index + 1}`);
  return lines.slice(1).map((line) => {
    const values = csvLineToValues(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    return row;
  });
}

function normalizeJsonPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === "object") {
    if (Array.isArray(payload.transactions)) return payload.transactions;
    return [payload];
  }
  return [];
}

function normalizeRow(row, index = 0) {
  if (!row || typeof row !== "object") return null;
  const rawDate = row.transaction_datetime || row.timestamp || row.date || row.transaction_date;
  const parsedDate = parseDate(rawDate);
  const amount = toNumber(row.transaction_amount ?? row.amount, 0);

  if (!parsedDate || amount <= 0) return null;

  return {
    transaction_id: String(row.transaction_id || row.id || `UPLOAD-${Date.now()}-${index}`),
    user_id: String(row.user_id || row.userId || "UPLOAD_USER"),
    merchant_name: String(row.merchant_name || row.merchant || "Uploaded Merchant"),
    transaction_amount: amount,
    transaction_status: String(row.transaction_status || row.status || "SUCCESS"),
    transaction_datetime: parsedDate.toISOString(),
    city: String(row.city || row.location?.city || "Unknown"),
    device_id: String(row.device_id || row.deviceId || ""),
    ip_address: String(row.ip_address || row.ip || ""),
    risk_score: row.risk_score ?? null,
    risk_reasons: Array.isArray(row.risk_reasons) ? row.risk_reasons : [],
  };
}

function previewShape(rows) {
  if (!rows.length) return { columns: [], rows: [] };

  const columns = Array.from(rows.reduce((set, row) => {
    Object.keys(row || {}).forEach((key) => set.add(key));
    return set;
  }, new Set()));

  return { columns, rows: rows.slice(0, 25) };
}

export async function parseUploadPreview(file) {
  if (!file) {
    return {
      extension: "",
      columns: [],
      rows: [],
      normalizedRows: [],
      note: "No file selected.",
    };
  }

  const extension = extensionOf(file.name);
  const metadataRows = [
    {
      file_name: file.name,
      file_type: extension || "unknown",
      file_size_kb: Math.max(1, Math.round(file.size / 1024)),
      preview: "Binary preview unavailable on browser parser.",
    },
  ];

  if (extension === ".csv") {
    const text = await file.text();
    const rows = parseCsvText(text);
    const normalizedRows = rows.map(normalizeRow).filter(Boolean);
    const preview = previewShape(rows);
    return {
      extension,
      columns: preview.columns,
      rows: preview.rows,
      normalizedRows,
      note:
        normalizedRows.length < rows.length
          ? "Some rows were skipped from normalization due to missing amount/date."
          : "",
    };
  }

  if (extension === ".json") {
    const text = await file.text();
    let payload;
    try {
      payload = JSON.parse(text);
    } catch {
      return {
        extension,
        columns: ["error"],
        rows: [{ error: "Invalid JSON file" }],
        normalizedRows: [],
        note: "Fix JSON format and re-upload.",
      };
    }

    const rows = normalizeJsonPayload(payload).filter((row) => row && typeof row === "object");
    const normalizedRows = rows.map(normalizeRow).filter(Boolean);
    const preview = previewShape(rows);
    return {
      extension,
      columns: preview.columns,
      rows: preview.rows,
      normalizedRows,
      note:
        normalizedRows.length < rows.length
          ? "Some rows were skipped from normalization due to missing amount/date."
          : "",
    };
  }

  if (extension === ".xlsx" || extension === ".pdf") {
    return {
      extension,
      columns: ["file_name", "file_type", "file_size_kb", "preview"],
      rows: metadataRows,
      normalizedRows: [],
      note: "Preview table shows file metadata. Full parsing will happen in backend analyzer.",
    };
  }

  return {
    extension,
    columns: ["error"],
    rows: [{ error: "Unsupported file format. Use PDF, Excel (.xlsx), CSV, or JSON." }],
    normalizedRows: [],
    note: "Upload blocked by client-side file type policy.",
  };
}

export function validateUploadSelection(file) {
  if (!file) return "Select a file before continuing.";
  const extension = extensionOf(file.name);
  const allowed = new Set([".pdf", ".xlsx", ".csv", ".json"]);
  if (!allowed.has(extension)) return "Unsupported file type. Allowed: PDF, XLSX, CSV, JSON.";
  if (file.size > 10 * 1024 * 1024) return "File exceeds 10MB upload limit.";
  const blocked = [".exe", ".bat", ".cmd", ".sh", ".ps1"];
  if (blocked.includes(extension)) return "Executable files are blocked.";
  return "";
}
