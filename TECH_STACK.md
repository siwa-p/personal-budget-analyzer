# Personal Budget Analyzer - Tech Stack

## Chosen Stack: Option 2 (Python Backend + React Frontend)

### Frontend
- React 18 + TypeScript + Vite
- Material-UI (UI components)
- Redux Toolkit + RTK Query (state management)
- Recharts (data visualization)
- React Hook Form + Zod (validation)

### Backend
- Python 3.12 + FastAPI
- SQLAlchemy ORM + PostgreSQL 16
- Celery + Redis (task queue for async jobs)
- JWT authentication (python-jose)

### ML/AI (Integrated)
- scikit-learn (expense categorization)
- pandas, numpy (data processing)
- Optional: TensorFlow/PyTorch (predictive insights)

### Additional Services
- Plaid API (banking integration)
- Tesseract OCR / Google Cloud Vision API (receipt scanning)
- ReportLab (PDF export)
- Redis (caching + Celery broker)

### DevOps
- Docker + Docker Compose
- PostgreSQL 16 (database)
- Redis 7 (cache + queue)

---

## Project File Structure

```
personal-budget-analyzer/
├── frontend/                       # React application
│   ├── public/
│   │   └── vite.svg
│   ├── src/
│   │   ├── assets/                # Images, fonts, etc.
│   │   ├── components/            # Reusable components
│   │   │   ├── common/           # Buttons, inputs, etc.
│   │   │   ├── transactions/     # Transaction components
│   │   │   ├── dashboard/        # Dashboard widgets
│   │   │   └── charts/           # Chart components
│   │   ├── features/             # Feature-based modules
│   │   │   ├── auth/
│   │   │   ├── transactions/
│   │   │   ├── categories/
│   │   │   ├── bills/
│   │   │   └── goals/
│   │   ├── pages/                # Page components
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   ├── Bills.tsx
│   │   │   └── Goals.tsx
│   │   ├── store/                # Redux store
│   │   │   ├── slices/
│   │   │   ├── api.ts           # RTK Query API
│   │   │   └── store.ts
│   │   ├── hooks/                # Custom hooks
│   │   ├── utils/                # Helper functions
│   │   ├── types/                # TypeScript types
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── .env.example
│   ├── .eslintrc.cjs
│   ├── .gitignore
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── index.html
│
├── backend/                       # FastAPI application
│   ├── app/
│   │   ├── api/                  # API routes
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── users.py
│   │   │   │   │   ├── transactions.py
│   │   │   │   │   ├── categories.py
│   │   │   │   │   ├── bills.py
│   │   │   │   │   ├── goals.py
│   │   │   │   │   └── ml.py
│   │   │   │   └── api.py       # API router
│   │   │   └── deps.py          # Dependencies (auth, db)
│   │   ├── core/                # Core configuration
│   │   │   ├── config.py        # Settings
│   │   │   ├── security.py      # JWT, password hashing
│   │   │   └── celery_app.py    # Celery config
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── transaction.py
│   │   │   ├── category.py
│   │   │   ├── bill.py
│   │   │   └── goal.py
│   │   ├── schemas/             # Pydantic schemas
│   │   │   ├── user.py
│   │   │   ├── transaction.py
│   │   │   ├── category.py
│   │   │   ├── bill.py
│   │   │   └── goal.py
│   │   ├── crud/                # Database operations
│   │   │   ├── user.py
│   │   │   ├── transaction.py
│   │   │   └── ...
│   │   ├── services/            # Business logic
│   │   │   ├── ml_service.py    # ML categorization
│   │   │   ├── plaid_service.py # Banking integration
│   │   │   ├── ocr_service.py   # Receipt scanning
│   │   │   ├── export_service.py # PDF/CSV export
│   │   │   └── analytics.py     # Spending analysis
│   │   ├── tasks/               # Celery tasks
│   │   │   ├── ml_tasks.py
│   │   │   ├── reminder_tasks.py
│   │   │   └── export_tasks.py
│   │   ├── ml/                  # ML models
│   │   │   ├── models/          # Trained models
│   │   │   ├── training.py      # Training scripts
│   │   │   └── categorizer.py   # Categorization logic
│   │   ├── db/                  # Database
│   │   │   ├── base.py          # Base class
│   │   │   ├── session.py       # DB session
│   │   │   └── init_db.py       # DB initialization
│   │   ├── main.py              # FastAPI app entry
│   │   └── __init__.py
│   ├── tests/
│   │   ├── api/
│   │   ├── services/
│   │   └── conftest.py
│   ├── .env.example
│   ├── .gitignore
│   ├── requirements.txt
│   ├── pyproject.toml           # Poetry config (optional)
│   └── README.md
│
├── docker/
│   ├── frontend.Dockerfile
│   ├── backend.Dockerfile
│   └── celery.Dockerfile
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Dependencies & Versions

### Frontend (package.json)

```json
{
  "name": "budget-analyzer-frontend",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "@reduxjs/toolkit": "^2.2.7",
    "react-redux": "^9.1.2",
    "@mui/material": "^6.1.3",
    "@mui/icons-material": "^6.1.3",
    "@emotion/react": "^11.13.3",
    "@emotion/styled": "^11.13.0",
    "recharts": "^2.12.7",
    "react-hook-form": "^7.53.0",
    "zod": "^3.23.8",
    "@hookform/resolvers": "^3.9.0",
    "axios": "^1.7.7",
    "date-fns": "^4.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.2",
    "typescript": "^5.6.2",
    "vite": "^5.4.9",
    "eslint": "^9.12.0",
    "eslint-plugin-react-hooks": "^5.1.0-rc.0",
    "@typescript-eslint/eslint-plugin": "^8.8.0",
    "@typescript-eslint/parser": "^8.8.0"
  }
}
```

### Backend (requirements.txt)

```
# FastAPI
fastapi==0.115.4
uvicorn[standard]==0.32.0
python-multipart==0.0.12

# Database
sqlalchemy==2.0.35
psycopg2-binary==2.9.9

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1

# Validation
pydantic==2.9.2
pydantic-settings==2.6.0
email-validator==2.2.0

# Async Tasks
celery==5.4.0
redis==5.2.0

# ML & Data Processing
scikit-learn==1.5.2
pandas==2.2.3
numpy==2.1.3
joblib==1.4.2

# External APIs
plaid-python==29.0.0
pillow==11.0.0
pytesseract==0.3.13

# Export
reportlab==4.2.5

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2

# CORS
fastapi-cors==0.0.6
```

---

## Basic Setup Instructions

### Prerequisites
- Node.js 20+ and npm/yarn
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (optional but recommended)

---
## Key Configuration Files

### Backend (.env)

```
DATABASE_URL=postgresql://user:password@localhost:5432/budget_analyzer
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox

GOOGLE_CLOUD_VISION_API_KEY=your_key
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

