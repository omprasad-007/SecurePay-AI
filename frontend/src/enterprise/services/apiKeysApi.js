import { appendAuditLog, getOrgApiKeys, getSessionContext, nowIso, saveOrgApiKeys } from "./localStore";

function randomToken(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}_${Date.now().toString(36)}`;
}

export function createApiKey(name) {
  const { organization, user } = getSessionContext();
  const label = String(name || "").trim() || "default";
  const rawKey = `sp_${randomToken("key")}`;
  const entry = {
    id: randomToken("api"),
    name: label,
    key_prefix: rawKey.slice(0, 12),
    key_last4: rawKey.slice(-4),
    is_active: true,
    created_at: nowIso(),
    masked_key: `${rawKey.slice(0, 8)}...${rawKey.slice(-4)}`,
  };

  const keys = getOrgApiKeys(organization.id);
  keys.unshift(entry);
  saveOrgApiKeys(organization.id, keys);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "CREATE",
    entityType: "API_KEY",
    entityId: entry.id,
  });

  return { ...entry, raw_key: rawKey };
}

export function listApiKeys() {
  const { organization } = getSessionContext();
  return getOrgApiKeys(organization.id);
}

export function revokeApiKey(keyId) {
  const { organization, user } = getSessionContext();
  const keys = getOrgApiKeys(organization.id);
  const next = keys.map((entry) =>
    entry.id === keyId ? { ...entry, is_active: false, revoked_at: nowIso() } : entry
  );
  saveOrgApiKeys(organization.id, next);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "DELETE",
    entityType: "API_KEY",
    entityId: keyId,
  });

  return { status: "revoked" };
}
