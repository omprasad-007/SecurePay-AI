const ACCESS_TOKEN_KEY = "enterprise_access_token";
const REFRESH_TOKEN_KEY = "enterprise_refresh_token";
const USER_KEY = "enterprise_user";
const ORG_KEY = "enterprise_org";

export function saveAuthSession(payload) {
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, payload.tokens.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
  localStorage.setItem(ORG_KEY, JSON.stringify(payload.organization));
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getCurrentUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function getCurrentOrganization() {
  const raw = localStorage.getItem(ORG_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearAuthSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(ORG_KEY);
}
