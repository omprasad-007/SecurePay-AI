export const ROLE_KEY = "securepay_role";

export const ROLES = {
  ADMIN: "Admin",
  ANALYST: "Risk Analyst",
  AUDITOR: "Auditor"
};

export function getStoredRole() {
  return localStorage.getItem(ROLE_KEY) || ROLES.ANALYST;
}

export function setStoredRole(role) {
  localStorage.setItem(ROLE_KEY, role);
}

export function canMarkFraud(role) {
  return role === ROLES.ANALYST;
}

export function canOverride(role) {
  return role === ROLES.ADMIN;
}

export function canExport(role) {
  return role === ROLES.AUDITOR || role === ROLES.ADMIN;
}

export function resolveThemeClass(theme) {
  if (theme === "dark") return "theme-dark";
  if (theme === "vibrant") return "theme-vibrant";
  return "theme-light";
}
