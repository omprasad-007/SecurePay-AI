# SecurePay AI Enterprise API

## Run
```bash
cd backend
pip install -r requirements-enterprise.txt
uvicorn main_enterprise:app --host 0.0.0.0 --port 8001 --reload
```

## Auth Flow
1. `POST /auth/login` with Google ID token (or email in secure dev mode).
2. Persist `access_token`, `refresh_token`.
3. Attach `Authorization: Bearer <access_token>` for all protected APIs.
4. Use `POST /auth/refresh` when access token expires.

## cURL Examples

### Login
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "google_id_token": "<FIREBASE_ID_TOKEN>",
    "organization_name": "Acme Finance"
  }'
```

### Create Transaction
```bash
curl -X POST http://localhost:8001/transactions \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "upi_id": "alice@bank",
    "sender_name": "Alice",
    "receiver_name": "Bob",
    "merchant_name": "Acme Retail",
    "merchant_category": "Retail",
    "transaction_amount": 1450.75,
    "currency": "INR",
    "transaction_type": "UPI",
    "transaction_status": "SUCCESS",
    "transaction_date": "2026-02-25",
    "transaction_time": "15:10:00",
    "geo_latitude": 12.9716,
    "geo_longitude": 77.5946,
    "city": "Bengaluru",
    "state": "Karnataka",
    "country": "India",
    "ip_address": "103.22.10.12",
    "device_id": "ios-iphone-15",
    "device_type": "mobile",
    "notes": "Client settlement",
    "tags": ["priority", "upi"]
  }'
```

### Filter + Export Fraud Transactions (CSV)
```bash
curl -L "http://localhost:8001/transactions/export?format=csv&fraud_only=true&date_from=2026-02-01&date_to=2026-02-29" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -o fraud_export.csv
```

### Audit Export (Excel)
```bash
curl -L "http://localhost:8001/audit/export?format=xlsx&action_type=DOWNLOAD" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -o audit_export.xlsx
```
