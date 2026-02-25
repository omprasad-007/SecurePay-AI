import {
  appendAuditLog,
  applyFraudThreshold,
  createOrganizationRecord,
  getOrgTransactions,
  getSessionContext,
  saveOrgTransactions,
  updateOrganizationRecord,
} from "./localStore";

export function createOrganization(payload = {}) {
  const name = String(payload.name || "").trim();
  if (!name) throw new Error("Organization name is required");
  return createOrganizationRecord(name, Number(payload.fraud_threshold) || 70);
}

export function getOrganization() {
  const { organization } = getSessionContext();
  return organization;
}

export function updateFraudThreshold(fraudThreshold) {
  const { organization, user } = getSessionContext();
  const nextThreshold = Math.max(0, Math.min(100, Number(fraudThreshold)));

  const updatedOrg = { ...organization, fraud_threshold: nextThreshold };
  updateOrganizationRecord(updatedOrg);

  const transactions = getOrgTransactions(organization.id);
  const recalculated = transactions.map((item) => applyFraudThreshold(item, nextThreshold));
  saveOrgTransactions(organization.id, recalculated);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "UPDATE",
    entityType: "ORGANIZATION",
    entityId: organization.id,
    details: { fraud_threshold: nextThreshold },
  });

  return updatedOrg;
}
