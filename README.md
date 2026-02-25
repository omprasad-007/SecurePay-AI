# SecurePay AI – Intelligent UPI Fraud Detection & Behavioral Monitoring System

## Problem Statement
UPI/digital payment systems need real-time, explainable fraud detection that can identify anomalous behavior, risky users, and suspicious network patterns without relying on heavy databases.

## About Us
SecurePay AI is a final-year, placement-ready fintech project that demonstrates how modern ML, graph analytics, and cybersecurity controls can protect real-time UPI transactions. The goal is to provide explainable risk insights for analysts and decision-makers while keeping the system lightweight and deployable.

## Architecture Overview
- React + Tailwind frontend (dashboard, charts, graph view, AI assistant)
- FastAPI backend (anomaly detection + supervised ML + graph intelligence)
- Firebase Authentication for user login
- Local Storage for transaction simulation

## Enterprise Architecture Upgrade
Frontend
-> API Gateway (FastAPI)
-> Fraud Pipeline (existing anomaly + supervised + graph)
-> Adaptive Risk Layer (dynamic thresholds + device/context)
-> Decision Engine (LOW/MEDIUM/HIGH/CRITICAL with action mapping)
-> Explainability Module (risk drivers + pattern detection)

## AI Flow
1. Extract behavioral features (velocity, device change, geo shift, beneficiary novelty)
2. Anomaly detection (Isolation Forest)
3. Supervised classification (XGBoost/RandomForest)
4. Graph analysis (NetworkX)
5. Weighted fusion score with risk banding

## Tech Stack
Frontend: React (Vite), TailwindCSS, Framer Motion, Recharts/Chart.js, Firebase Auth
Backend: FastAPI, Scikit-learn, XGBoost, IsolationForest, NetworkX, Uvicorn

## Folder Structure
```
securepay-ai/
├── frontend/
├── backend/
└── README.md
```

## Setup

### 1) Backend
```
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
set ALLOW_INSECURE_DEV=true
uvicorn main:app --reload --port 8000
```

### 2) Frontend
```
cd frontend
npm install
npm run dev
```

### 3) Environment Variables
Create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
```

Firebase config is currently embedded in `frontend/src/utils/firebase.js` for quick demo setup. Replace the values with your own project config if needed.

Backend env (optional Firebase verification):
```
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email
ALLOW_INSECURE_DEV=true
RATE_LIMIT_PER_MIN=60
FRONTEND_ORIGIN=http://localhost:5173
ENABLE_AUDIT_PLUGIN=false
ENABLE_HEATMAP_INTELLIGENCE=false
AUDIT_PLUGIN_DB_URL=sqlite:///./audit_plugin.db
HEATMAP_PLUGIN_DB_URL=sqlite:///./audit_plugin.db
```

## How To Use
1. Start backend with `uvicorn main:app --reload --port 8000`.
2. Start frontend with `npm run dev` in `frontend`.
3. Sign up or login using Firebase Auth.
4. Open `Transactions` to simulate a new transfer and get a fraud score.
5. Download the demo CSV from Transactions for training or reporting.
6. Open `Fraud Analytics` to view graph risk, anomaly summaries, and controls.
7. Open `/enterprise/login` for multi-tenant enterprise mode (local storage; no enterprise DB/JWT setup needed).

## Product Tour
1. Dashboard: View total transactions, fraud rate, and live risk trends.
2. Transactions: Simulate UPI transfers and receive real-time scores.
3. Fraud Analytics: Inspect graph clusters and risk breakdowns.
4. AI Assistant: Ask “Why flagged?” or “How to reduce fraud?” for explanations.
5. About: Read the platform mission and core modules.

## API Endpoints
- `POST /predict` - returns anomaly score, supervised probability, graph risk, final score
- `POST /analytics/graph` - returns graph nodes/edges with risk summary
- `POST /feedback` - stores analyst/admin fraud feedback in `backend/feedback.json`
- `POST /reports/export` - exports CSV, summary PDF, or metrics (auditor/admin)
- `POST /upload-excel` - ingests base64 CSV/XLSX, cleans, scores, and returns processed transactions + insights
- `POST /upload-excel/report` - generates markdown documentation from upload insights
- `GET /health` - backend status + optional plugin mount status
- `GET /api/audit/*` - advanced audit plugin APIs (when `ENABLE_AUDIT_PLUGIN=true`)
- `GET /api/heatmap/*` - heatmap intelligence APIs (when `ENABLE_HEATMAP_INTELLIGENCE=true`)

## Dataset & Training
Generate synthetic transactions:
```
cd backend
python scripts/generate_synthetic.py --rows 3000 --output data/synthetic_upi.csv
```

Train and export the supervised model:
```
cd backend
python scripts/train_model.py --input data/synthetic_upi.csv --output fraud_model.pkl
```

If `fraud_model.pkl` exists, the backend will automatically load it for supervised scoring.

## Diagrams (Viva Ready)
PDFs are stored in `docs/`:
- `docs/securepay-architecture.pdf`
- `docs/ai-flowchart.pdf`

To regenerate:
```
python docs/generate_diagrams.py
```

## Dataset Options
- Synthetic UPI transaction generator (frontend local storage)
- Kaggle Credit Card Fraud Dataset for training experiments

## Results
- Final score is computed as:
  - `(amount_deviation_risk * 0.30)`
  - `+ (location_anomaly_risk * 0.20)`
  - `+ (velocity_risk * 0.15)`
  - `+ (merchant_novelty_risk * 0.15)`
  - `+ (time_based_risk * 0.05)`
  - `+ (account_risk * 0.10)`
  - `+ (graph_network_risk * 0.05)`
- Risk levels: Low (0–30), Medium (31–60), High (61–80), Critical (81–100)

## Cybersecurity Controls
- API rate limiting
- JWT/Firebase token verification
- Input sanitization and validation
- Fraud attempt logging

## Deployment
Frontend: Vercel / Netlify
Backend: Render / Railway
Firebase: Authentication only

## Future Scope
- Real-time streaming (Kafka)
- Graph neural networks
- Device fingerprinting API integration
- RBI-grade audit trails

## Enterprise Additions Implemented
- Adaptive risk engine wrapper (`backend/models/adaptive_risk.py`) without changing core pipeline.
- Decision engine categories and actions (`backend/models/decision_engine.py`).
- Pattern detection (`backend/models/pattern_detector.py`) attached to prediction response.
- Feedback learning loop (`POST /feedback`, `backend/retrain.py`).
- Device fingerprint utility (`frontend/src/utils/deviceFingerprint.js`).
- Fraud heatmap page (`frontend/src/pages/FraudHeatmap.jsx`).
- Simulation lab page (`frontend/src/pages/SimulationLab.jsx`) isolated from real store.
- Explainable breakdown panel (`frontend/src/components/RiskBreakdownPanel.jsx`).
- Fraud pattern library (`frontend/src/components/PatternLibrary.jsx`).
- Role-based controls (Admin, Risk Analyst, Auditor) via frontend role gate + backend header validation.
- Export compliance reports (`backend/generate_report.py`, `/reports/export`).
- Professional Vibrant Mode in 3-mode theme toggle.

## Excel Intelligence Flow
Excel Upload -> Validation -> Cleaning -> Fraud Pipeline -> Adaptive Risk -> Decision Engine -> Pattern Detector -> Analytics Summary -> LocalStorage Injection -> Dashboard Update

Frontend Excel module:
- Route: `/excel-upload`
- Components: `ExcelSummaryPanel`, `DatasetInsights`
- Utility: `src/utils/fileParser.js`

Backend Excel module:
- `backend/utils/excel_ingestion.py`
- `backend/utils/data_cleaner.py`
- `backend/utils/documentation_generator.py`
- `backend/routes/excel_upload.py`

## Screenshots
Add screenshots after running the app locally.

## Enterprise Upgrade (Multi-Tenant)
- Frontend enterprise module (active local-storage mode): `frontend/src/enterprise/`
- Enterprise backend blueprint (optional): `backend/main_enterprise.py`
- Enterprise schema/docs (optional reference): `backend/enterprise/sql/schema.sql`, `docs/enterprise-production-upgrade.md`
