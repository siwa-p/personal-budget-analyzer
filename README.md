# Ledgr

Track spending, set budgets, and reach your savings goals — all in one place.

**[Try it live →](#)** *(link available on request)*

---

## What you can do

**Transactions** — Log income and expenses. Ledgr automatically suggests a category using ML so you spend less time tagging and more time understanding your money.

**Budgets** — Set monthly spending limits per category and see at a glance how much you have left.

**Bills** — Track recurring bills so nothing slips through.

**Goals** — Define savings targets and watch your progress over time.

**Analytics** — Visualize where your money goes with spending breakdowns and monthly trend charts.

**Categories** — 20 built-in categories out of the box. Create your own to match how you actually spend.

**Light & dark mode** — Because your eyes matter.

---

## Getting started

1. Go to the live app (link above)
2. Create an account — you'll get a verification email from AWS Cognito
3. Start adding transactions

That's it.

---

## For tinkerers & developers

### Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript, Vite, Material-UI v6, Recharts |
| Auth | AWS Cognito + Amplify v6 |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16 |
| ML | fastembed (`all-MiniLM-L6-v2`) + scikit-learn |
| Infra | EC2, RDS, S3, CloudFront, ECR |

### Run locally

You'll need a Cognito user pool. Everything else runs in Docker.

```bash
git clone <repo-url>
cd personal-budget-analyzer
cp backend/.env.prod.example backend/.env.prod  # fill in Cognito + DB values
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

### Deploy to AWS

```bash
make deploy          # build + push backend to ECR, restart EC2, build + sync frontend to S3
make deploy-backend  # backend only
make deploy-frontend # frontend only
```

`VITE_*` vars are baked into the bundle at build time — rebuild frontend if they change.

### Project layout

```
frontend/src/
  pages/       # Login, Register, EmailVerification, Dashboard,
               # Transactions, Analytics, Bills, Budgets, Goals, Categories, Profile
  components/  # charts/, layout/
  lib/         # Amplify config

backend/app/
  api/v1/endpoints/  # users, transactions, categories, budgets, bills, goals, analytics
  crud/              # DB layer
  models/            # ORM models
  schemas/           # Pydantic schemas
  services/          # ml_service.py, report_service.py
  db/                # session, init (seeds categories + superuser)
```

### Environment variables

**`backend/.env.prod`**

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | RDS PostgreSQL connection string |
| `BACKEND_CORS_ORIGINS` | JSON array — include your CloudFront domain |
| `COGNITO_USER_POOL_ID` | Cognito user pool ID |
| `COGNITO_APP_CLIENT_ID` | Cognito app client ID |
| `COGNITO_REGION` | Default: `us-east-1` |
| `FIRST_SUPERUSER_EMAIL` | Promoted to superuser on every startup |

**Root `.env.prod`** (used by Makefile)

| Variable | Description |
|----------|-------------|
| `ECR_BASE` | `ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com` |
| `VITE_API_URL` | Backend URL |
| `VITE_COGNITO_USER_POOL_ID` | Baked into frontend bundle |
| `VITE_COGNITO_CLIENT_ID` | Baked into frontend bundle |
| `S3_BUCKET` | Frontend S3 bucket |
| `EC2_HOST` | EC2 public IP |
| `EC2_KEY` | Path to `.pem` SSH key |

### Superuser access

The user matching `FIRST_SUPERUSER_EMAIL` is promoted to superuser on startup. Superusers can manage all user accounts via `GET/POST/PUT/DELETE /api/v1/users/`.

To authenticate in Swagger UI, grab your token from the browser console while logged in:
```js
localStorage.getItem('access_token')
```
Then paste it into the Authorize dialog at `/docs`.

### Common issues

**"There is already a signed in user"** — Stale Amplify session. Refresh the page and try again.

**Can't connect to RDS** — It's in a private VPC. Use the AWS Console RDS Query Editor or SSM port forwarding.

**SSH to EC2 times out** — Your IP changed. Run `curl -4 ifconfig.me` and update the EC2 security group inbound rule.
