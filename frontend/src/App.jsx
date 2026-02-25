import React, { useEffect, useMemo, useState } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { auth } from "./utils/firebase";
import Navbar from "./components/Navbar.jsx";
import Sidebar from "./components/Sidebar.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Transactions from "./pages/Transactions.jsx";
import FraudAnalytics from "./pages/FraudAnalytics.jsx";
import About from "./pages/About.jsx";
import FraudHeatmap from "./pages/FraudHeatmap.jsx";
import SimulationLab from "./pages/SimulationLab.jsx";
import ExcelUpload from "./pages/ExcelUpload.jsx";
import RiskInsights from "./pages/RiskInsights.jsx";
import AIAssistant from "./components/AIAssistant.jsx";
import FraudHeatmapIntelligencePage from "./plugins/heatmap-intelligence/pages/FraudHeatmapIntelligencePage.jsx";
import AuditAdvancedPage from "./plugins/audit-intelligence/pages/AuditAdvancedPage.jsx";
import AuditUploadPage from "./plugins/audit-intelligence/pages/AuditUploadPage.jsx";
import RiskIntelligencePage from "./plugins/audit-intelligence/pages/RiskIntelligencePage.jsx";
import EnterpriseApp from "./enterprise/EnterpriseApp.jsx";
import EnterpriseLoginPage from "./enterprise/pages/EnterpriseLoginPage.jsx";
import { getStoredRole, resolveThemeClass, setStoredRole } from "./utils/themeManager";

const ThemeContext = React.createContext();

function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "light");

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("theme-light", "theme-dark", "theme-vibrant");
    root.classList.add(resolveThemeClass(theme));
    localStorage.setItem("theme", theme);
  }, [theme]);

  const value = useMemo(() => ({ theme, setTheme }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => React.useContext(ThemeContext);

function ProtectedRoute({ user, children }) {
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}

function RoleRoute({ role, allow, children }) {
  if (!allow.includes(role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const location = useLocation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState(() => getStoredRole());
  const isEnterprisePath = location.pathname.startsWith("/enterprise");

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });
    return () => unsub();
  }, []);

  const onRoleChange = (nextRole) => {
    setRole(nextRole);
    setStoredRole(nextRole);
  };

  if (loading && !isEnterprisePath) {
    return <div className="min-h-screen flex items-center justify-center text-lg font-semibold">Loading SecurePay AI...</div>;
  }

  return (
    <ThemeProvider>
      <Routes>
        <Route path="/enterprise/login" element={<EnterpriseLoginPage />} />
        <Route path="/enterprise/*" element={<EnterpriseApp />} />
        <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
        <Route path="/signup" element={user ? <Navigate to="/" /> : <Signup />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute user={user}>
              <div className="app-shell">
                <Sidebar />
                <div className="flex flex-col min-h-screen">
                  <Navbar user={user} role={role} onRoleChange={onRoleChange} onLogout={() => signOut(auth)} />
                  <main className="px-6 py-6 lg:px-10 lg:py-8 space-y-6">
                    <Routes>
                      <Route path="/" element={<Dashboard user={user} />} />
                      <Route path="/transactions" element={<Transactions user={user} role={role} />} />
                      <Route path="/analytics" element={<FraudAnalytics user={user} role={role} />} />
                      <Route path="/risk-insights" element={<RiskInsights user={user} />} />
                      <Route path="/risk-intelligence" element={<RiskIntelligencePage />} />
                      <Route path="/heatmap" element={<FraudHeatmap />} />
                      <Route path="/heatmap-intelligence" element={<FraudHeatmapIntelligencePage />} />
                      <Route path="/fraud-heatmap-intelligence" element={<FraudHeatmapIntelligencePage />} />
                      <Route path="/audit-advanced" element={<AuditAdvancedPage />} />
                      <Route path="/audit-upload" element={<AuditUploadPage />} />
                      <Route path="/simulation" element={<SimulationLab />} />
                      <Route path="/excel-upload" element={<ExcelUpload />} />
                      <Route path="/about" element={<About />} />
                      <Route
                        path="/admin-simulation"
                        element={
                          <RoleRoute role={role} allow={["Admin"]}>
                            <SimulationLab />
                          </RoleRoute>
                        }
                      />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </main>
                </div>
                <AIAssistant />
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </ThemeProvider>
  );
}
