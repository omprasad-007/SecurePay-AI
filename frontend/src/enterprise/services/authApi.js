import { getCurrentOrganization, getCurrentUser, saveAuthSession } from "../auth/sessionStore";
import {
  appendAuditLog,
  createOrganizationRecord,
  findMembershipByEmail,
  findOrganizationById,
  getInvites,
  getOrgUsers,
  saveInvites,
  saveOrgUsers,
  seedOrgTransactions,
} from "./localStore";

function randomToken(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2)}_${Date.now().toString(36)}`;
}

function tokenPair() {
  return {
    access_token: randomToken("enterprise_access"),
    refresh_token: randomToken("enterprise_refresh"),
    token_type: "bearer",
    expires_in_seconds: 30 * 60,
  };
}

function buildUser({ organizationId, email, fullName, role }) {
  const displayName = fullName || email.split("@")[0];
  return {
    id: `usr_${Math.random().toString(36).slice(2, 8)}_${Date.now().toString(36)}`,
    organization_id: organizationId,
    email,
    full_name: displayName,
    role,
    two_factor_enabled: false,
    is_active: true,
    created_at: new Date().toISOString(),
  };
}

export async function loginEnterprise({ email, fullName, organizationName, inviteToken }) {
  const normalizedEmail = String(email || "").trim().toLowerCase();
  if (!normalizedEmail) {
    throw new Error("Email is required");
  }

  const now = new Date();
  const invites = getInvites();
  let organization = null;
  let role = null;

  if (inviteToken) {
    const invite = invites.find((item) => item.invite_token === inviteToken && item.status === "PENDING");
    if (!invite) throw new Error("Invalid invite token");
    if (new Date(invite.expires_at).getTime() < now.getTime()) {
      invite.status = "EXPIRED";
      saveInvites(invites);
      throw new Error("Invite token expired");
    }
    if (String(invite.email || "").toLowerCase() !== normalizedEmail) {
      throw new Error("Invite email mismatch");
    }

    organization = findOrganizationById(invite.organization_id);
    if (!organization) throw new Error("Organization not found for invite");

    role = invite.role;
    invite.status = "ACCEPTED";
    invite.accepted_at = now.toISOString();
    saveInvites(invites);
  } else {
    const existingMembership = findMembershipByEmail(normalizedEmail);
    if (existingMembership) {
      organization = existingMembership.organization;
      role = existingMembership.user.role;
    } else {
      const orgName = String(organizationName || "").trim();
      if (!orgName) {
        throw new Error("Provide organization name for first login or use invite token");
      }
      organization = createOrganizationRecord(orgName, 70);
      role = "ORG_ADMIN";
    }
  }

  const users = getOrgUsers(organization.id);
  let user = users.find((item) => String(item.email || "").toLowerCase() === normalizedEmail);
  if (!user) {
    user = buildUser({
      organizationId: organization.id,
      email: normalizedEmail,
      fullName: String(fullName || "").trim() || null,
      role: role || "VIEWER",
    });
    users.push(user);
  } else if (role && user.role !== role) {
    user.role = role;
  }
  saveOrgUsers(organization.id, users);

  seedOrgTransactions(organization.id, user.id, organization.fraud_threshold);
  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "LOGIN",
    entityType: "AUTH",
    entityId: user.id,
    details: { email: user.email, mode: "local-storage" },
  });

  const response = {
    tokens: tokenPair(),
    user,
    organization,
  };

  saveAuthSession(response);
  return response;
}

export const loginWithGoogle = loginEnterprise;

export async function refreshToken(refreshTokenValue) {
  const currentUser = getCurrentUser();
  const currentOrg = getCurrentOrganization();
  if (!currentUser || !currentOrg) {
    throw new Error("No enterprise session available");
  }

  return {
    access_token: randomToken("enterprise_access"),
    refresh_token: refreshTokenValue || randomToken("enterprise_refresh"),
    token_type: "bearer",
    expires_in_seconds: 30 * 60,
  };
}
