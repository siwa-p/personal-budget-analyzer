# Personal Budget Analyzer

A full-stack budget tracking application with ML-powered expense categorization, async job processing, and a production AWS deployment.

## Tech Stack

### Frontend
- **React 19** + TypeScript + Vite
- **Material-UI v6** for components and theming (light/dark mode)
- **React Router v6** for client-side routing
- **Recharts** for analytics charts
- **React Hook Form** for form validation

### Backend
- **Python 3.12** + **FastAPI 0.115** + **Uvicorn**
- **SQLAlchemy 2.0** ORM with **PostgreSQL 16**
- **Pydantic v2** for request/response validation
- **Celery 5** + **Redis 7** for async task processing (email sending)
- **python-jose** + **passlib** for JWT auth
- **fastapi-mail** + Resend SMTP for transactional email
- **sentence-transformers** (`all-MiniLM-L6-v2`) + **scikit-learn** for ML categorization
- **ReportLab** + **matplotlib** for PDF/CSV report generation (service implemented, endpoint not yet exposed)

### Infrastructure
- **Docker** + **Docker Compose** (dev and prod configs)
- **AWS ECR** — backend Docker image registry
- **AWS EC2** — runs backend + celery + db + redis via Docker Compose
- **AWS S3** — hosts built frontend static files
- **AWS CloudFront** — CDN in front of S3; proxies `/api/*` to EC2

---

## Quick Start (Development)

### Prerequisites

- Docker Desktop installed and running

### Run the application

```bash
git clone <repo-url>
cd personal-budget-analyzer
cp backend/.env.example backend/.env   # fill in required values (see below)
docker-compose up --build
```

### Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

### Stop

```bash
docker-compose down          # stop containers
docker-compose down -v       # stop + delete volumes (wipes database)
```

### Logs

```bash
docker-compose logs -f              # all services
docker-compose logs -f backend      # backend only
docker-compose logs -f frontend     # frontend only
```

Structured JSON logs are also written to `backend/logs/application.log` (2 MB rotation, 1 backup).

### Database shell

```bash
docker-compose exec db psql -U postgres -d budget_analyzer
```

---

## Project Structure

```
personal-budget-analyzer/
├── frontend/
│   └── src/
│       ├── pages/          # Login, Register, Dashboard, Transactions,
│       │                   # Analytics, Bills, Budgets, Goals, Categories, Profile
│       ├── components/
│       │   ├── charts/     # Recharts-based analytics components
│       │   └── layout/     # Sidebar, layout wrapper
│       ├── contexts/       # ThemeContext (light/dark)
│       └── utils/          # API error helpers
├── backend/
│   └── app/
│       ├── api/v1/endpoints/  # auth, users, categories, transactions,
│       │                      # bills, goals, budgets, analytics
│       ├── core/              # config, JWT security, Celery app
│       ├── crud/              # DB operations per model
│       ├── db/                # SQLAlchemy engine + session
│       ├── models/            # ORM models
│       ├── schemas/           # Pydantic schemas
│       ├── services/          # ml_service.py, report_service.py, email.py
│       └── tasks/             # Celery async tasks
├── docker/
│   ├── backend.Dockerfile        # dev (uvicorn --reload)
│   ├── backend.prod.Dockerfile   # prod
│   ├── frontend.Dockerfile       # dev (Vite dev server)
│   ├── frontend.prod.Dockerfile  # prod (multi-stage build)
│   └── nginx.frontend.conf
├── docker-compose.yml            # development
├── docker-compose.prod.yml       # production (uses ECR image)
├── pyproject.toml                # Python dependencies (uv)
└── uv.lock
```

---

## Environment Variables

### Backend — `backend/.env` (dev) / `backend/.env.prod` (prod)

Copy `backend/.env.example` → `backend/.env` and fill in required values.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `SECRET_KEY` | ✅ | JWT secret — generate: `openssl rand -hex 32` |
| `ALGORITHM` | | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Default: `30` |
| `FIRST_SUPERUSER_EMAIL` | ✅ | Admin account created on first startup |
| `FIRST_SUPERUSER_PASSWORD` | ✅ | Admin password |
| `FIRST_SUPERUSER_USERNAME` | ✅ | Admin username |
| `FRONTEND_URL` | ✅ | Used in password reset email links |
| `MAIL_PASSWORD` | | Resend API key (starts with `re_`) — required for password reset emails |
| `MAIL_FROM` | | Sender email address |
| `PLAID_CLIENT_ID` / `PLAID_SECRET` | | Not yet integrated |
| `GOOGLE_CLOUD_VISION_API_KEY` | | Not yet integrated |

### Frontend — `frontend/.env` (dev)

Copy `frontend/.env.example` → `frontend/.env`.

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend URL (default: `http://localhost:8000`) |

> In production, `VITE_API_URL` is baked into the JS bundle at build time. Rebuild and redeploy the frontend whenever it changes.

### Production root — `.env.prod`

Copy `.env.prod.example` → `.env.prod`. Used by `docker-compose.prod.yml` and the `Makefile`.

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database credentials |
| `ECR_BASE` | `ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com` |
| `VITE_API_URL` | CloudFront domain (e.g. `https://abc123.cloudfront.net`) |
| `S3_BUCKET` | S3 bucket name for frontend static files |
| `EC2_HOST` | EC2 public IP |
| `EC2_KEY` | Path to `.pem` SSH key file |

---

## API Overview

All endpoints are prefixed with `/api/v1`. Full interactive docs at `/docs`.

| Router | Prefix | Description |
|--------|--------|-------------|
| Auth | `/auth` | Register, login (JWT), forgot/reset password |
| Users | `/users` | Profile management, theme preference |
| Transactions | `/transactions` | Full CRUD, date/category/type filters, ML categorization |
| Categories | `/categories` | Hierarchical categories, 20 system defaults seeded on init |
| Budgets | `/budgets` | Budget tracking with progress |
| Bills | `/bills` | Recurring bill management |
| Goals | `/goals` | Savings goals with progress tracking |
| Analytics | `/analytics` | Category distribution, monthly spending trends |

---

## Authentication

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"john","email":"john@example.com","full_name":"John Doe","password":"strongpassword"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=john@example.com&password=strongpassword"
# Returns: {"access_token": "<JWT>", "token_type": "bearer"}
```

Include the token in subsequent requests:
```
Authorization: Bearer <JWT>
```

### Password Reset

Requires `MAIL_PASSWORD` (Resend API key) configured. Reset emails are sent via Celery async task.

```bash
# Request reset email
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'

# Submit new password
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<token-from-email>","new_password":"newpassword"}'
```

> Resend test mode only allows sending to the account owner's email address.

---

## ML Categorization

Transactions are automatically categorized using a two-layer system:

- **Model**: `sentence-transformers/all-MiniLM-L6-v2` generates embeddings; scikit-learn classifies against user categories
- **L1 cache**: In-memory (process lifetime)
- **L2 cache**: Redis (24h TTL)
- **Feedback loop**: User corrections are stored with 3× weighting and used to retrain the model

The HuggingFace model is cached in a Docker named volume (`hf_cache`) so it persists across container restarts.

---

## Production Deployment (AWS)

### Architecture

```
CloudFront → S3 (React static files)
           → EC2 :8000 /api/* (FastAPI via Docker Compose)
                    └── ECR (backend image)
                    └── PostgreSQL + Redis + Celery (same EC2)
```

### Prerequisites

- AWS CLI configured with an IAM user that has ECR, S3, and EC2 permissions
- A `Makefile` (not tracked in git — configure from `.env.prod.example` instructions)
- EC2 instance running with Docker installed and IAM role granting ECR pull access

### Environment setup

Fill in `.env.prod` (root) and `backend/.env.prod` from their respective `.example` files.

### Deploy

```bash
# Full deploy: build + push backend to ECR, SSH into EC2 to pull + restart,
# build frontend static files, upload to S3
make deploy

# Individual targets
make build-backend       # build backend Docker image
make push                # push backend image to ECR
make deploy-backend      # push + SSH into EC2 to pull and restart
make build-frontend      # build React static files
make deploy-frontend     # sync frontend/dist to S3
```

---

## Troubleshooting

**Port already in use**: Ensure ports 5173, 8000, 5432, and 6379 are free before starting.

**Database connection errors on first run**: PostgreSQL takes a few seconds to initialize. The backend has a health check dependency — it will retry automatically.

**Frontend can't reach backend**: Check `VITE_API_URL` in `frontend/.env` matches where the backend is running. In production, this is baked into the bundle at build time.

**ML model slow on first request**: The sentence-transformers model (~400–500 MB) loads into memory on first use. Subsequent requests are fast. On EC2 t3.micro (1 GB RAM), monitor memory — upgrade to t3.small if containers OOM-kill.

**SSH to EC2 times out**: Your home IP may have changed. Run `curl -4 ifconfig.me` and update the EC2 security group SSH inbound rule.
