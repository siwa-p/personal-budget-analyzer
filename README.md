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

### Authentication

The API now provides JWT-based authentication:

- `POST /api/v1/auth/register` – create a basic user account
- `POST /api/v1/auth/login` – obtain an access token using email + password
- `GET /api/v1/users/me` – fetch the profile of the authenticated user

Include the issued token in the `Authorization: Bearer <token>` header to access protected routes such as `/api/v1/users`.

### Bootstrapping a Superuser

The admin-only routes require an initial superuser. After your containers are running, execute:

```bash
docker-compose run --rm backend python -m app.initial_data
```

The command reads `FIRST_SUPERUSER_*` variables from `backend/.env` (see `backend/.env.example`) and creates the account if it does not already exist.

## Environment Variables

### Backend (.env)
See `backend/.env.example` for all available environment variables.

### Frontend (.env)
See `frontend/.env.example` for all available environment variables.

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

