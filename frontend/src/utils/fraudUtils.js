import { auth } from "./firebase";

const STORAGE_KEY = "securepay_transactions";
const EXCEL_SUMMARY_KEY = "securepay_excel_summary";
const DATASET_INSIGHTS_KEY = "securepay_dataset_insights";
const DETECTED_PATTERNS_KEY = "securepay_detected_patterns";

const devicePool = ["DEV-AX21", "DEV-BX99", "DEV-CY88", "DEV-DZ10"];
const merchantPool = ["Flipkart", "Amazon", "Zomato", "PaytmMall", "IRCTC", "Swiggy"];
const locations = [
  { city: "Mumbai", lat: 19.076, lon: 72.8777 },
  { city: "Delhi", lat: 28.7041, lon: 77.1025 },
  { city: "Bengaluru", lat: 12.9716, lon: 77.5946 },
  { city: "Hyderabad", lat: 17.385, lon: 78.4867 },
  { city: "Chennai", lat: 13.0827, lon: 80.2707 }
];

function randomFrom(array) {
  return array[Math.floor(Math.random() * array.length)];
}

function userScopedKey(baseKey) {
  const uid = auth.currentUser?.uid;
  return uid ? `${baseKey}_${uid}` : `${baseKey}_anonymous`;
}

export function getTransactions() {
  const raw = localStorage.getItem(userScopedKey(STORAGE_KEY));
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveTransactions(transactions) {
  localStorage.setItem(userScopedKey(STORAGE_KEY), JSON.stringify(transactions));
}

export function saveExcelSummary(summary) {
  localStorage.setItem(userScopedKey(EXCEL_SUMMARY_KEY), JSON.stringify(summary || null));
}

export function getExcelSummary() {
  const raw = localStorage.getItem(userScopedKey(EXCEL_SUMMARY_KEY));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveDatasetInsights(insights) {
  localStorage.setItem(userScopedKey(DATASET_INSIGHTS_KEY), JSON.stringify(insights || null));
}

export function getDatasetInsights() {
  const raw = localStorage.getItem(userScopedKey(DATASET_INSIGHTS_KEY));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveDetectedPatterns(patterns) {
  localStorage.setItem(userScopedKey(DETECTED_PATTERNS_KEY), JSON.stringify(patterns || []));
}

export function getDetectedPatterns() {
  const raw = localStorage.getItem(userScopedKey(DETECTED_PATTERNS_KEY));
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function seedTransactions() {
  return getTransactions();
}

export function createTransaction(input = {}) {
  const location = randomFrom(locations);
  const activeUserId = auth.currentUser?.uid || "";
  return {
    id: input.id || `TXN${Math.floor(Math.random() * 90000) + 10000}`,
    userId: input.userId || activeUserId,
    receiverId: input.receiverId || `MERCH${Math.floor(Math.random() * 8) + 1}`,
    amount: input.amount || Math.floor(Math.random() * 15000) + 100,
    deviceId: input.deviceId || randomFrom(devicePool),
    merchant: input.merchant || randomFrom(merchantPool),
    channel: input.channel || "UPI",
    ip: input.ip || `192.168.0.${Math.floor(Math.random() * 200) + 10}`,
    location,
    timestamp: input.timestamp || new Date().toISOString(),
    finalScore: input.finalScore ?? null,
    riskLevel: input.riskLevel || "Low",
    features: input.features || {}
  };
}

export function addTransaction(transaction) {
  const transactions = getTransactions();
  const updated = [transaction, ...transactions];
  saveTransactions(updated);
  return updated;
}

export function updateTransaction(updatedTxn) {
  const transactions = getTransactions();
  const updated = transactions.map((tx) => (tx.id === updatedTxn.id ? updatedTxn : tx));
  saveTransactions(updated);
  return updated;
}

export function getStats(transactions) {
  const total = transactions.length;
  const highRisk = transactions.filter((tx) =>
    ["High", "HIGH", "CRITICAL"].includes(tx.riskLevel)
  ).length;
  const fraudRate = total > 0 ? ((highRisk / total) * 100).toFixed(1) : 0;
  return { total, highRisk, fraudRate };
}

export function buildGraph(transactions) {
  const nodes = [];
  const links = [];
  const nodeMap = new Map();

  transactions.forEach((tx) => {
    if (!nodeMap.has(tx.userId)) {
      nodeMap.set(tx.userId, { id: tx.userId, label: tx.userId.replace("USER", "U"), flagged: false });
    }
    if (!nodeMap.has(tx.receiverId)) {
      nodeMap.set(tx.receiverId, { id: tx.receiverId, label: tx.receiverId.replace("MERCH", "M"), flagged: false });
    }
    links.push({ source: tx.userId, target: tx.receiverId });
    if (tx.riskLevel === "High") {
      const node = nodeMap.get(tx.userId);
      if (node) node.flagged = true;
    }
  });

  nodes.push(...nodeMap.values());
  return { nodes, links };
}

export function summarizeRiskSeries(transactions) {
  return transactions
    .slice()
    .reverse()
    .slice(-10)
    .map((tx, index) => ({
      name: `T${index + 1}`,
      score: tx.finalScore || 0,
      amount: tx.amount
    }));
}
