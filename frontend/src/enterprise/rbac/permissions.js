export const ROLES = {
  SUPER_ADMIN: "SUPER_ADMIN",
  ORG_ADMIN: "ORG_ADMIN",
  ANALYST: "ANALYST",
  VIEWER: "VIEWER"
};

export const PERMISSIONS = {
  VIEW_ALL_ORGS: [ROLES.SUPER_ADMIN],
  MANAGE_ORG_USERS: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN],
  CREATE_TRANSACTION: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN, ROLES.ANALYST],
  EDIT_TRANSACTION: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN, ROLES.ANALYST],
  DELETE_TRANSACTION: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN],
  EXPORT_TRANSACTIONS: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN, ROLES.ANALYST],
  VIEW_AUDIT: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN],
  EXPORT_AUDIT: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN],
  VIEW_ANALYTICS: [ROLES.SUPER_ADMIN, ROLES.ORG_ADMIN, ROLES.ANALYST, ROLES.VIEWER]
};

export function can(role, permission) {
  return (PERMISSIONS[permission] || []).includes(role);
}

export function menuByRole(role) {
  const allItems = [
    { id: "dashboard", label: "Dashboard", path: "/enterprise/dashboard", permission: "VIEW_ANALYTICS" },
    { id: "transactions", label: "Transactions", path: "/enterprise/transactions", permission: "VIEW_ANALYTICS" },
    { id: "fraud", label: "Fraud Analytics", path: "/enterprise/fraud", permission: "VIEW_ANALYTICS" },
    { id: "audit", label: "Audit Logs", path: "/enterprise/audit", permission: "VIEW_AUDIT" },
    { id: "admin", label: "Admin Panel", path: "/enterprise/admin", permission: "MANAGE_ORG_USERS" },
    { id: "org", label: "Organization", path: "/enterprise/organization", permission: "MANAGE_ORG_USERS" }
  ];

  return allItems.filter((item) => can(role, item.permission));
}
