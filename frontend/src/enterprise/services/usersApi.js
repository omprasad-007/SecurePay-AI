import {
  appendAuditLog,
  getInvites,
  getOrgUsers,
  getSessionContext,
  nowIso,
  saveInvites,
  saveOrgUsers,
} from "./localStore";

function randomToken(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export function inviteUser(payload = {}) {
  const { organization, user } = getSessionContext();
  const email = String(payload.email || "").trim().toLowerCase();
  const role = String(payload.role || "").trim().toUpperCase();

  if (!email) throw new Error("Email is required");
  if (!role || role === "SUPER_ADMIN") throw new Error("Invalid invite role");

  const invites = getInvites();
  const invite = {
    invite_id: randomToken("inv"),
    email,
    role,
    organization_id: organization.id,
    invite_token: randomToken("invite"),
    status: "PENDING",
    expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: nowIso(),
  };
  invites.unshift(invite);
  saveInvites(invites);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "INVITE",
    entityType: "USER",
    entityId: invite.invite_id,
    details: { email, role },
  });

  return invite;
}

export function getUsers(params = {}) {
  const { organization } = getSessionContext();
  let users = getOrgUsers(organization.id);

  if (params.email) {
    const target = String(params.email).trim().toLowerCase();
    users = users.filter((item) => String(item.email || "").toLowerCase().includes(target));
  }
  if (params.role) {
    const targetRole = String(params.role).toUpperCase();
    users = users.filter((item) => String(item.role || "").toUpperCase() === targetRole);
  }

  return users;
}

export function deleteUser(userId) {
  const { organization, user } = getSessionContext();
  if (user.id === userId) throw new Error("Cannot delete active user");

  const users = getOrgUsers(organization.id);
  const next = users.filter((item) => item.id !== userId);
  if (next.length === users.length) throw new Error("User not found");

  saveOrgUsers(organization.id, next);
  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "DELETE",
    entityType: "USER",
    entityId: userId,
  });

  return { status: "deleted" };
}
