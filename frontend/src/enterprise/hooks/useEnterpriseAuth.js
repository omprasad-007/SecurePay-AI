import { useMemo } from "react";
import { clearAuthSession, getCurrentOrganization, getCurrentUser } from "../auth/sessionStore";

export function useEnterpriseAuth() {
  const user = getCurrentUser();
  const organization = getCurrentOrganization();

  const role = user?.role || "VIEWER";

  const identity = useMemo(
    () => ({
      user,
      organization,
      role,
      logout: () => clearAuthSession()
    }),
    [user, organization, role]
  );

  return identity;
}
