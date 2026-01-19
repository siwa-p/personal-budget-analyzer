# Personal Budget Analyzer

A full-stack budget tracking application with React frontend, FastAPI backend, and PostgreSQL database.

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite + Material-UI
- **Backend**: Python 3.12 + FastAPI
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Containerization**: Docker + Docker Compose

## First-Time Setup (For Junior Developers)

If you're new to Docker or setting up your development environment for the first time, follow these steps:

### 1. Install Docker Desktop

**Download and Install:**
- **macOS**: Download from [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
- **Windows**: Download from [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
- **Linux**: Follow instructions at [Docker Engine for Linux](https://docs.docker.com/engine/install/)

**After Installation:**
1. Open Docker Desktop application
2. Wait for it to fully start (you'll see a green "running" status)
3. Docker Desktop includes Docker Compose, so you'll have everything you need

### 2. Verify Installation

Open your terminal and run:
```bash
docker --version
docker-compose --version
```

You should see version numbers for both commands.

### 3. Clone the Repository

```bash
git clone git@github.com:Code-Campfire/smores-syntax.git
cd smores-syntax
```

### 4. Need Help?

- **Ask Claude Code**: If you run into issues during setup, ask Claude (claude.ai/code) to help troubleshoot. Claude can help with Docker installation, configuration, and common errors.

- **Stuck or Running Older Hardware?**: If you're completely stuck or running on an older computer that can't handle Docker Desktop, reach out to your **team lead or admins** for assistance. They can help with alternative setup options or hardware upgrades.

## Quick Start

### Prerequisites

- Docker Desktop installed and running on your system (see "First-Time Setup" above if you haven't installed it yet)

### Running the Application

1. **Clone the repository** (if not already done)

2. **Start all services with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

   This will start:
   - Frontend on http://localhost:5173
   - Backend API on http://localhost:8000
   - PostgreSQL database on localhost:5432
   - Redis on localhost:6379

3. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API docs: http://localhost:8000/docs
   - Backend health check: http://localhost:8000/health

### Stopping the Application

```bash
docker-compose down
```

To also remove volumes (database data):
```bash
docker-compose down -v
```

## Project Structure

```
personal-budget-analyzer/
├── frontend/               # React + TypeScript frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── backend/                # FastAPI backend
│   ├── app/
│   ├── requirements.txt
│   └── .env.example
├── docker/                 # Docker configuration
│   ├── frontend.Dockerfile
│   └── backend.Dockerfile
└── docker-compose.yml      # Docker Compose orchestration
```

## Development

### Frontend Development

The frontend runs with hot-reload enabled. Any changes to files in `frontend/src/` will automatically refresh the browser.

### Backend Development

The backend runs with uvicorn's reload feature. Any changes to Python files will automatically restart the server.

### Database Access

To access the PostgreSQL database directly:
```bash
docker-compose exec db psql -U postgres -d budget_analyzer
```

### View Logs

View logs for all services:
```bash
docker-compose logs -f
```

View logs for a specific service:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### User Authentication

The backend exposes a simple JWT-based login flow that the frontend (or external clients) can call:

1. **Create the initial superuser** – required to access admin-only endpoints. After the stack is running execute:
   ```bash
   docker-compose run --rm backend python -m app.initial_data
   ```
   This command reads the `FIRST_SUPERUSER_*` variables from `backend/.env` (see `backend/.env.example`) and creates the account if it does not already exist.

2. **Register a regular user** – submit `POST /api/v1/auth/register` with the JSON payload:
   ```json
   {
     "username": "luis",
     "email": "luis@example.com",
     "full_name": "Luis Estigarribia",
     "password": "strong-password"
   }
   ```
   The endpoint enforces unique `email`/`username` combinations and will always store new accounts as active, non‑superusers.

3. **Obtain a token** – call `POST /api/v1/auth/login` with form-data (`application/x-www-form-urlencoded`). Example `curl`:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=luis@example.com&password=strong-password"
   ```
   The response contains:
   ```json
   {
     "access_token": "<JWT>",
     "token_type": "bearer"
   }
   ```

4. **Use the token** – include `Authorization: Bearer <JWT>` in subsequent requests. Useful endpoints:
   - `GET /api/v1/users/me` – returns the profile tied to the current token.
   - `GET /api/v1/users` and `POST /api/v1/users` – admin-only operations that require the superuser token.

### Password Reset (Resend + Celery)

Forgot password is supported via email verification. The flow uses a password reset token stored in the database and a Celery worker to send emails through Resend SMTP.

Important for local testing: Resend test mode only allows sending to the email address that owns the Resend account. Each teammate must use their own Resend account and API key, and test using their own email address. This is expected for development; production configuration will be handled later.

1. **Configure env vars** in your local `.env` (root of repo):
   ```bash
   MAIL_FROM=onboarding@resend.dev
   MAIL_FROM_NAME=Smore Budget
   MAIL_USERNAME=resend
   MAIL_PASSWORD=re_XXXXXXXXXXXX  # This is the Resend API KEY, you need to copy it from your Resend account
   ```
   Also set `FRONTEND_URL` and `PASSWORD_RESET_PATH` if your frontend differs from defaults.

2. **Start the stack**, including the Celery worker:
   ```bash
   docker compose up --build
   ```

3. **Request a reset**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
     -H "Content-Type: application/json" \
     -d "{\"email\":\"your-own-resend-email@example.com\"}"
   ```
   Example (must be the email tied to your Resend account):
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
     -H "Content-Type: application/json" \
     -d "{\"email\":\"you@your-resend-email.com\"}"
   ```
   **The API always returns a success message, even if the email is not registered.**

4. **Reset password** using the token from the email:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/reset-password \
     -H "Content-Type: application/json" \
     -d "{\"token\":\"<token-from-email>\",\"new_password\":\"new-strong-password\"}"
   ```

## Environment Variables

### Backend (.env)
See `backend/.env.example` for all available environment variables.

### Frontend (.env)
See `frontend/.env.example` for all available environment variables.

## Testing the Frontend (Register, Login, Profile Update)

Once the application is running (see Quick Start above), test the authentication features:

### 1. Register a New User
- Navigate to http://localhost:5173/register
- Fill in the form:
  - First Name: `John`
  - Last Name: `Doe`
  - Email: `john.doe@example.com`
  - Password: `password123` (min 8 chars)
- Click **Register**
- ✅ You should see a success message and be redirected to the update profile page

### 2. Login
- Navigate to http://localhost:5173/login
- Enter credentials:
  - Email: `john.doe@example.com`
  - Password: `password123`
- Click **Sign In**
- ✅ You should be redirected to the update profile page

### 3. Update Profile
- On the profile page (http://localhost:5173/profile)
- Modify any field (e.g., Full Name or Theme)
- Click **Save changes**
- ✅ Changes should be saved and theme should update immediately

### 4. Test Theme Persistence
- Change theme to **Dark** and save
- Logout and login again
- ✅ Dark theme should be automatically applied

## Next Steps

This is a basic skeleton setup. To add features:

1. Add database models in `backend/app/models/`
2. Create API endpoints in `backend/app/api/v1/endpoints/`
3. Build UI components in `frontend/src/components/`
4. Add pages in `frontend/src/pages/`
5. Set up Redux store in `frontend/src/store/`

## Troubleshooting

**Port already in use**: If you see port binding errors, make sure ports 5173, 8000, 5432, and 6379 are not being used by other applications.

**Database connection errors**: Wait a few seconds for the database to fully initialize on first run.

**Frontend can't connect to backend**: Make sure the `VITE_API_URL` environment variable is set correctly.

