import React from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import EnterpriseSidebar from "./layout/EnterpriseSidebar";
import { useEnterpriseAuth } from "./hooks/useEnterpriseAuth";
import EnterpriseDashboardPage from "./pages/EnterpriseDashboardPage";
import EnterpriseTransactionsPage from "./pages/EnterpriseTransactionsPage";
import EnterpriseAdminPanelPage from "./pages/EnterpriseAdminPanelPage";
import EnterpriseFraudPage from "./pages/EnterpriseFraudPage";
import EnterpriseAuditPage from "./pages/EnterpriseAuditPage";
import EnterpriseOrganizationPage from "./pages/EnterpriseOrganizationPage";

export default function EnterpriseApp() {
  const { user, role, organization, logout } = useEnterpriseAuth();
  const location = useLocation();
  const navigate = useNavigate();

  if (!user) {
    return <Navigate to="/enterprise/login" replace state={{ from: location }} />;
  }

  const onLogout = () => {
    logout();
    navigate("/enterprise/login", { replace: true });
  };

  return (
    <div className="app-shell">
      <EnterpriseSidebar role={role} user={user} organization={organization} onLogout={onLogout} />
      <main className="px-6 py-6 lg:px-10 lg:py-8 space-y-6">
        <Routes>
          <Route path="dashboard" element={<EnterpriseDashboardPage />} />
          <Route path="transactions" element={<EnterpriseTransactionsPage />} />
          <Route path="fraud" element={<EnterpriseFraudPage />} />
          <Route path="audit" element={<EnterpriseAuditPage />} />
          <Route path="admin" element={<EnterpriseAdminPanelPage />} />
          <Route path="organization" element={<EnterpriseOrganizationPage />} />
          <Route path="*" element={<Navigate to="/enterprise/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
