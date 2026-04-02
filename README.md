# Personal Budget Analyzer

A full-stack budget tracking application with ML-powered expense categorization.

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite + Material-UI
- **Backend**: Python 3.12 + FastAPI + Celery
- **Database**: PostgreSQL 16
- **Cache / Queue**: Redis 7
- **ML**: scikit-learn (TF-IDF + Naive Bayes) with Redis caching
- **OCR**: Donut model for receipt scanning
- **Containerization**: Docker + Docker Compose

## Quick Start (Development)

### Prerequisites

- Docker Desktop installed and running

### Run the application

```bash
git clone <repo-url>
cd personal-budget-analyzer
cp backend/.env.example backend/.env   # fill in required values
docker-compose up --build
```

Services:
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### Stop

```bash
docker-compose down          # stop containers
docker-compose down -v       # stop + delete volumes (database data)
```

## Project Structure

```
personal-budget-analyzer/
├── frontend/                     # React + TypeScript frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── backend/                      # FastAPI backend
│   ├── app/
│   ├── seed_data.sh              # seed 6 months of test transactions
│   └── seed_ml_data.sh           # seed ML training data
├── docker/                       # Dockerfiles + nginx config
│   ├── backend.Dockerfile        # development
│   ├── backend.prod.Dockerfile   # production
│   ├── frontend.Dockerfile       # development
│   ├── frontend.prod.Dockerfile  # production (multi-stage)
│   └── nginx.frontend.conf
├── pyproject.toml                # Python dependencies (uv)
├── uv.lock
├── Makefile                      # ECR build + push commands
├── docker-compose.yml            # development
└── docker-compose.prod.yml       # production
```

## Environment Variables

### Backend
Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT secret (`openssl rand -hex 32`) |
| `FIRST_SUPERUSER_EMAIL` | Initial admin account |
| `FIRST_SUPERUSER_PASSWORD` | Initial admin password |
| `MAIL_PASSWORD` | Resend API key (for password reset emails) |

### Frontend
Copy `frontend/.env.example` to `frontend/.env`:

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend URL (default: `http://localhost:8000`) |

## Authentication

### Register
`POST /api/v1/auth/register`
```json
{
  "username": "john",
  "email": "john@example.com",
  "full_name": "John Doe",
  "password": "strongpassword"
}
```

### Login
`POST /api/v1/auth/login` (form-data)
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=john@example.com&password=strongpassword"
```

Returns `{ "access_token": "<JWT>", "token_type": "bearer" }`. Include in subsequent requests as `Authorization: Bearer <JWT>`.

### Password Reset

Uses Resend SMTP via Celery. Configure `MAIL_PASSWORD` in `backend/.env` with your Resend API key.

> Note: Resend test mode only allows sending to the email that owns the Resend account.

```bash
# Request reset
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'

# Submit new password
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<token-from-email>","new_password":"newpassword"}'
```

## Development

### Logs

```bash
docker-compose logs -f              # all services
docker-compose logs -f backend      # backend only
```

Structured JSON logs also written to `backend/logs/application.log`.

### Database access

```bash
docker-compose exec db psql -U postgres -d budget_analyzer
```

### Seed test data

```bash
cd backend
./seed_data.sh        # 6 months of transactions + budgets
./seed_ml_data.sh     # ~200 varied transactions for ML training
```

## Production Deployment (AWS)

The production stack targets:
- **ECR** — Docker image registry
- **EC2** — Compute (Docker Compose pulling from ECR)
- **S3** — Receipt image storage
- **CloudFront** — CDN distribution

### Build and push images to ECR

Prerequisites: AWS CLI configured (`aws configure`), IAM user with `AmazonEC2ContainerRegistryFullAccess`.

```bash
# One-time: create ECR repositories
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr create-repository --repository-name budget-analyzer/backend --region $AWS_REGION
aws ecr create-repository --repository-name budget-analyzer/frontend --region $AWS_REGION

# Build and push (replace with your EC2 public IP)
make deploy VITE_API_URL=http://YOUR_EC2_PUBLIC_IP:8000
```

> `VITE_API_URL` is baked into the frontend JS bundle at build time — rebuild the frontend image whenever the backend URL changes.

### Production environment

Copy `.env.prod.example` to `.env.prod` and `backend/.env.prod.example` to `backend/.env.prod`, then:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

**Port already in use**: Ensure ports 5173, 8000, 5432, and 6379 are free.

**Database connection errors**: Wait a few seconds on first run for PostgreSQL to initialize.

**Frontend can't reach backend**: Check `VITE_API_URL` in `frontend/.env` matches where the backend is running.
