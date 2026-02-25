# Audit Intelligence Plugin

This plugin adds new website modules for:

- `/audit-advanced`
- `/audit-upload`
- `/risk-intelligence`

## Files

- `index.jsx`: route + nav manifest exports
- `pages/*`: route-level pages
- `components/*`: modular UI cards/panels
- `services/auditApi.js`: backend API integration with local fallback
- `services/uploadPreview.js`: client-side preview parser
- `services/localData.js`: local export and local-storage fallback storage

## Route Registration

Import `auditIntelligenceRoutes` into the app router and map each `path` to `component`.
Import `auditIntelligenceNavItems` into sidebar/nav to expose route links.
