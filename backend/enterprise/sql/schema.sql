-- SecurePay AI Enterprise Schema (PostgreSQL)
-- Multi-tenant isolation by organization_id

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  slug VARCHAR(180) UNIQUE NOT NULL,
  fraud_threshold DOUBLE PRECISION NOT NULL DEFAULT 70,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  email VARCHAR(320) UNIQUE NOT NULL,
  full_name VARCHAR(180),
  role VARCHAR(20) NOT NULL,
  oauth_provider VARCHAR(50),
  password_hash VARCHAR(255),
  two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization_invites (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  email VARCHAR(320) NOT NULL,
  role VARCHAR(20) NOT NULL,
  invited_by_user_id UUID NOT NULL REFERENCES users(id),
  token VARCHAR(72) UNIQUE NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  accepted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  user_id UUID NOT NULL REFERENCES users(id),
  created_by UUID NOT NULL REFERENCES users(id),
  upi_id VARCHAR(180) NOT NULL,
  sender_name VARCHAR(180),
  receiver_name VARCHAR(180),
  merchant_name VARCHAR(180) NOT NULL,
  merchant_category VARCHAR(180),
  transaction_amount DOUBLE PRECISION NOT NULL,
  currency VARCHAR(10) NOT NULL,
  transaction_type VARCHAR(20) NOT NULL,
  transaction_status VARCHAR(20) NOT NULL,
  transaction_date DATE NOT NULL,
  transaction_time TIME NOT NULL,
  geo_latitude DOUBLE PRECISION,
  geo_longitude DOUBLE PRECISION,
  city VARCHAR(100),
  state VARCHAR(100),
  country VARCHAR(100),
  ip_address VARCHAR(64),
  device_id VARCHAR(180),
  device_type VARCHAR(100),
  risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  is_flagged BOOLEAN NOT NULL DEFAULT FALSE,
  is_frozen BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT,
  tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  fraud_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_comments (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  transaction_id UUID NOT NULL REFERENCES transactions(id),
  user_id UUID NOT NULL REFERENCES users(id),
  comment TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY,
  organization_id UUID REFERENCES organizations(id),
  user_id UUID NOT NULL REFERENCES users(id),
  action_type VARCHAR(60) NOT NULL,
  entity_type VARCHAR(60) NOT NULL,
  entity_id VARCHAR(80) NOT NULL,
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  ip_address VARCHAR(64),
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  created_by UUID NOT NULL REFERENCES users(id),
  name VARCHAR(120) NOT NULL,
  key_hash VARCHAR(255) UNIQUE NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_org ON users(organization_id);
CREATE INDEX IF NOT EXISTS ix_transactions_org ON transactions(organization_id);
CREATE INDEX IF NOT EXISTS ix_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_transactions_org_user ON transactions(organization_id, user_id);
CREATE INDEX IF NOT EXISTS ix_transactions_org_risk ON transactions(organization_id, risk_score);
CREATE INDEX IF NOT EXISTS ix_audit_org ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS ix_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_org_user ON audit_logs(organization_id, user_id);
