# SecurePay AI Enterprise Upgrade Blueprint

## 1) Architecture Overview

### Frontend
- Stack: React (Vite), responsive layout, role-based sidebar, dark/light theme compatibility.
- Module path: `frontend/src/enterprise/`
- Security:
  - Access token in memory/local storage (scaffold), refresh token rotation support.
  - API client auto-refreshes on `401`.
  - Role/permission gates before sensitive UI actions.

### Backend
- Stack: FastAPI + SQLAlchemy + PostgreSQL.
- Entry point: `backend/main_enterprise.py`
- Multi-tenant enforcement:
  - Every business record includes `organization_id`.
  - Every privileged query filters by `organization_id` unless caller is `SUPER_ADMIN`.
- Security:
  - JWT access + refresh tokens.
  - BCrypt password hashing utilities available.
  - RBAC dependency guard.
  - Request rate limiting middleware.
  - CORS restricted to configured frontend origin.
  - Audit logging on create/edit/delete/download.

### Database
- SQL schema file: `backend/enterprise/sql/schema.sql`
- ORM models: `backend/enterprise/models.py`
- Core entities:
  - `organizations`
  - `users`
  - `organization_invites`
  - `transactions`
  - `transaction_comments`
  - `audit_logs`
  - `api_keys`

## 2) Role Model and Permissions

### Roles
- `SUPER_ADMIN`
- `ORG_ADMIN`
- `ANALYST`
- `VIEWER`

### Permission Matrix
- `SUPER_ADMIN`
  - Cross-org visibility
  - Full exports
  - User/org management
- `ORG_ADMIN`
  - Org-scoped user management
  - Create/update/delete transactions
  - Audit access + export
  - Invite members
- `ANALYST`
  - Create/update transactions
  - Fraud analytics access
  - Transaction export
- `VIEWER`
  - Read-only access
  - No mutation/delete

## 3) API Endpoints (Implemented)

### Auth
- `POST /auth/login`
- `POST /auth/refresh`

### Transactions
- `POST /transactions`
- `GET /transactions`
- `PUT /transactions/{id}`
- `DELETE /transactions/{id}`
- `GET /transactions/export`
- `GET /transactions/{id}/report` (PDF)
- `POST /transactions/{id}/comments`
- `GET /transactions/{id}/comments`

### Audit
- `GET /audit`
- `GET /audit/export`

### Users
- `POST /users/invite`
- `GET /users`
- `DELETE /users/{id}`

### Organization
- `POST /organization`
- `GET /organization`
- `PATCH /organization` (fraud threshold)

### Integrations
- `POST /integrations/api-keys`
- `GET /integrations/api-keys`
- `DELETE /integrations/api-keys/{id}`

## 4) Transaction Model Compliance

Customizable fields are supported in `TransactionCreate` and persisted in `transactions`:
- `transaction_id` (UUID generated)
- `upi_id`
- `sender_name`
- `receiver_name`
- `merchant_name`
- `merchant_category`
- `transaction_amount`
- `currency`
- `transaction_type`
- `transaction_status`
- `transaction_date`
- `transaction_time`
- `geo_latitude`
- `geo_longitude`
- `city`
- `state`
- `country`
- `ip_address`
- `device_id`
- `device_type`
- `risk_score` (ML-driven at write/update)
- `is_flagged`
- `notes`
- `created_by`
- `organization_id`

Additional enterprise controls:
- `is_frozen`
- `tags`
- `fraud_signals`
- comments (`transaction_comments`)

## 5) Multi-Tenant Isolation Rules

1. All write operations set `organization_id` from authenticated principal (except super-admin scoped operations).
2. All reads apply tenant guard:
   - non-super-admin: `WHERE organization_id = principal.organization_id`
   - super-admin: optional explicit org filter.
3. Cross-organization update/delete attempts return `403`.
4. Audit records carry `organization_id` and `user_id` for traceability.

## 6) Fraud and Risk Features (Implemented)

Service: `backend/enterprise/services/fraud.py`

- ML-based risk scoring wrapper using existing pipeline.
- Repeated merchant risk signal.
- Velocity spike detection.
- Geo-distance anomaly signal.
- Device anomaly signal.
- Graph risk signal.

Organization-level threshold control:
- `PATCH /organization` updates `fraud_threshold`.

## 7) Export and Audit System

Export service: `backend/enterprise/services/exporter.py`

Formats:
- CSV
- Excel (`.xlsx`)
- PDF

Scopes:
- Filtered transaction export
- Fraud-only transaction export
- Date/user/action-filtered audit export
- Individual transaction PDF report

Every export writes an audit event: `action_type = DOWNLOAD`.

## 8) Frontend Enterprise Module

Path: `frontend/src/enterprise/`

### Structure
- `api/httpClient.js` secure API client with token refresh
- `auth/sessionStore.js` auth session storage
- `rbac/permissions.js` role/permission matrix
- `layout/EnterpriseSidebar.jsx` role-based navigation
- `hooks/useEnterpriseAuth.js` session hook
- `services/` endpoint wrappers (`authApi`, `transactionsApi`, `auditApi`, `usersApi`, `organizationApi`, `apiKeysApi`)
- `pages/` enterprise page scaffolds
- `types/transactionSchema.js` transaction contract reference

## 9) Production Deployment Instructions

### Backend
1. Create PostgreSQL database.
2. Install enterprise dependencies:
   - `pip install -r backend/requirements-enterprise.txt`
3. Configure environment:
   - `ENTERPRISE_DATABASE_URL`
   - `ENTERPRISE_JWT_SECRET`
   - `ENTERPRISE_FRONTEND_ORIGIN`
   - Firebase variables (if using Google token verification)
4. Start API:
   - `uvicorn main_enterprise:app --host 0.0.0.0 --port 8001 --reload`

### Frontend
1. Configure enterprise API URL:
   - `VITE_ENTERPRISE_API_URL=http://localhost:8001`
2. Run Vite app:
   - `npm install`
   - `npm run dev`

### Production hardening checklist
- Put backend behind HTTPS reverse proxy.
- Use managed PostgreSQL and rotate secrets.
- Enable strict JWT secret management.
- Enable SIEM ingestion for audit logs.
- Add Redis-backed distributed rate limiter.
- Add background workers for email invite delivery and alert notifications.

## 10) Recommended Next Additions (Aligned to your request)
- Suspicious velocity tracking dashboards (streaming).
- Geo-distance anomaly alerting via webhook/email.
- Merchant risk watchlist with org-level controls.
- Admin override with immutable override audit chain.
- Organization-level dynamic threshold policies by transaction type.
