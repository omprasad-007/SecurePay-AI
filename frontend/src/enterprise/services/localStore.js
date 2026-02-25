import { getCurrentOrganization, getCurrentUser } from "../auth/sessionStore";

const ORGS_KEY = "enterprise_local_organizations";
const INVITES_KEY = "enterprise_local_invites";

function readJson(key, fallback) {
  const raw = localStorage.getItem(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function uid(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}_${Date.now().toString(36)}`;
}

function slugify(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function usersKey(orgId) {
  return `enterprise_local_users_${orgId}`;
}

function transactionsKey(orgId) {
  return `enterprise_local_transactions_${orgId}`;
}

function auditKey(orgId) {
  return `enterprise_local_audit_${orgId}`;
}

function commentsKey(orgId) {
  return `enterprise_local_comments_${orgId}`;
}

function apiKeysKey(orgId) {
  return `enterprise_local_api_keys_${orgId}`;
}

export function nowIso() {
  return new Date().toISOString();
}

export function getSessionContext() {
  const organization = getCurrentOrganization();
  const user = getCurrentUser();
  if (!organization || !organization.id || !user || !user.id) {
    throw new Error("Enterprise session is not initialized");
  }
  return { organization, user };
}

export function getOrganizations() {
  return readJson(ORGS_KEY, []);
}

export function saveOrganizations(organizations) {
  writeJson(ORGS_KEY, organizations || []);
}

export function createOrganizationRecord(name, fraudThreshold = 70) {
  const organizations = getOrganizations();
  let slug = slugify(name);
  if (!slug) slug = `org-${uid("slug").slice(-6)}`;
  if (organizations.some((org) => org.slug === slug)) {
    slug = `${slug}-${Math.random().toString(36).slice(2, 6)}`;
  }
  const organization = {
    id: uid("org"),
    name: String(name || "Enterprise Workspace").trim(),
    slug,
    fraud_threshold: Number(fraudThreshold) || 70,
    created_at: nowIso(),
  };
  organizations.push(organization);
  saveOrganizations(organizations);
  return organization;
}

export function updateOrganizationRecord(updatedOrganization) {
  const organizations = getOrganizations();
  const next = organizations.map((org) => (org.id === updatedOrganization.id ? updatedOrganization : org));
  saveOrganizations(next);
}

export function findOrganizationById(organizationId) {
  return getOrganizations().find((org) => org.id === organizationId) || null;
}

export function getInvites() {
  return readJson(INVITES_KEY, []);
}

export function saveInvites(invites) {
  writeJson(INVITES_KEY, invites || []);
}

export function getOrgUsers(organizationId) {
  return readJson(usersKey(organizationId), []);
}

export function saveOrgUsers(organizationId, users) {
  writeJson(usersKey(organizationId), users || []);
}

export function getOrgTransactions(organizationId) {
  return readJson(transactionsKey(organizationId), []);
}

export function saveOrgTransactions(organizationId, transactions) {
  writeJson(transactionsKey(organizationId), transactions || []);
}

export function getOrgAuditLogs(organizationId) {
  return readJson(auditKey(organizationId), []);
}

export function saveOrgAuditLogs(organizationId, logs) {
  writeJson(auditKey(organizationId), logs || []);
}

export function getOrgComments(organizationId) {
  return readJson(commentsKey(organizationId), []);
}

export function saveOrgComments(organizationId, comments) {
  writeJson(commentsKey(organizationId), comments || []);
}

export function getOrgApiKeys(organizationId) {
  return readJson(apiKeysKey(organizationId), []);
}

export function saveOrgApiKeys(organizationId, apiKeys) {
  writeJson(apiKeysKey(organizationId), apiKeys || []);
}

export function appendAuditLog({ organizationId, userId, actionType, entityType, entityId, details = {} }) {
  const nextLog = {
    log_id: uid("audit"),
    user_id: userId,
    organization_id: organizationId,
    action_type: actionType,
    entity_type: entityType,
    entity_id: entityId,
    timestamp: nowIso(),
    ip_address: "local",
    details,
  };
  const logs = getOrgAuditLogs(organizationId);
  logs.unshift(nextLog);
  saveOrgAuditLogs(organizationId, logs);
  return nextLog;
}

export function findMembershipByEmail(email) {
  const normalized = String(email || "").trim().toLowerCase();
  if (!normalized) return null;
  const organizations = getOrganizations();

  for (const organization of organizations) {
    const users = getOrgUsers(organization.id);
    const user = users.find((item) => String(item.email || "").toLowerCase() === normalized);
    if (user) return { organization, user };
  }
  return null;
}

export function applyFraudThreshold(transaction, threshold) {
  const riskScore = Number(transaction.risk_score || 0);
  return {
    ...transaction,
    risk_score: Number(riskScore.toFixed(2)),
    is_flagged: riskScore >= Number(threshold || 70),
  };
}

export function seedOrgTransactions(organizationId, userId, threshold = 70) {
  const existing = getOrgTransactions(organizationId);
  if (existing.length) return existing;

  const sample = [
    {
      merchant_name: "Metro Foods",
      merchant_category: "Groceries",
      amount: 1240,
      city: "Bengaluru",
      state: "Karnataka",
      country: "India",
      lat: 12.9716,
      lon: 77.5946,
      risk: 18,
    },
    {
      merchant_name: "QuickRide",
      merchant_category: "Transport",
      amount: 420,
      city: "Bengaluru",
      state: "Karnataka",
      country: "India",
      lat: 12.9352,
      lon: 77.6245,
      risk: 28,
    },
    {
      merchant_name: "Unknown Wallet Topup",
      merchant_category: "Wallet",
      amount: 9800,
      city: "Mumbai",
      state: "Maharashtra",
      country: "India",
      lat: 19.076,
      lon: 72.8777,
      risk: 83,
    },
    {
      merchant_name: "Crypto Fast Exchange",
      merchant_category: "Finance",
      amount: 14500,
      city: "Delhi",
      state: "Delhi",
      country: "India",
      lat: 28.6139,
      lon: 77.209,
      risk: 91,
    },
    {
      merchant_name: "City Pharma",
      merchant_category: "Healthcare",
      amount: 870,
      city: "Bengaluru",
      state: "Karnataka",
      country: "India",
      lat: 12.9871,
      lon: 77.593,
      risk: 26,
    },
  ];

  const now = Date.now();
  const seeded = sample.map((item, index) => {
    const date = new Date(now - index * 3600 * 1000);
    const transaction = {
      transaction_id: uid("txn"),
      upi_id: `user${index + 1}@bank`,
      sender_name: "Enterprise User",
      receiver_name: item.merchant_name,
      merchant_name: item.merchant_name,
      merchant_category: item.merchant_category,
      transaction_amount: item.amount,
      currency: "INR",
      transaction_type: "UPI",
      transaction_status: item.risk >= 85 ? "FLAGGED" : "SUCCESS",
      transaction_date: date.toISOString().slice(0, 10),
      transaction_time: date.toTimeString().slice(0, 8),
      geo_latitude: item.lat,
      geo_longitude: item.lon,
      city: item.city,
      state: item.state,
      country: item.country,
      ip_address: `10.0.0.${index + 2}`,
      device_id: `device-${index + 1}`,
      device_type: "mobile",
      notes: "",
      tags: [],
      fraud_signals: item.risk >= 80 ? ["high_velocity", "merchant_anomaly"] : [],
      user_id: userId,
      created_by: userId,
      organization_id: organizationId,
      created_at: date.toISOString(),
      updated_at: date.toISOString(),
      is_frozen: false,
      risk_score: item.risk,
    };
    return applyFraudThreshold(transaction, threshold);
  });

  saveOrgTransactions(organizationId, seeded);
  return seeded;
}
