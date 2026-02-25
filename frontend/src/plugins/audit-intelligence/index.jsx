import AuditAdvancedPage from "./pages/AuditAdvancedPage";
import AuditUploadPage from "./pages/AuditUploadPage";
import RiskIntelligencePage from "./pages/RiskIntelligencePage";

export const auditIntelligenceRoutes = [
  {
    path: "/audit-advanced",
    title: "Audit Advanced",
    component: AuditAdvancedPage,
  },
  {
    path: "/audit-upload",
    title: "Audit Upload",
    component: AuditUploadPage,
  },
  {
    path: "/risk-intelligence",
    title: "Risk Intelligence",
    component: RiskIntelligencePage,
  },
];

export const auditIntelligenceNavItems = auditIntelligenceRoutes.map((route) => ({
  name: route.title,
  path: route.path,
}));

export { AuditAdvancedPage, AuditUploadPage, RiskIntelligencePage };
