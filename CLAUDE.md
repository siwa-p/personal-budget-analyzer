# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal Budget Analyzer is a full-stack budget tracking application with ML-powered expense categorization. The application is designed to integrate with external services (Plaid for banking, OCR for receipts) and includes async job processing capabilities.

## Constraints and Rules

### Database Migrations
- You MAY create migration files if requested by the user (e.g., Alembic migrations)
- You MUST NEVER run migrations or directly modify database data
- Migration execution should always be left to the user

### Git Operations
- Git operations (commit, push, pull, rebase, etc.) are DESTRUCTIVE operations
- You MUST NEVER run git commands unless the user has EXPLICITLY requested them
- When in doubt, ask the user before performing any git operation

## Architecture

### Docker-First Development
This project runs entirely in Docker with hot-reload enabled for both frontend and backend. All services are orchestrated via `docker-compose.yml`:

- **Frontend** (port 5173): React + Vite with live reload
- **Backend** (port 8000): FastAPI with uvicorn auto-reload
- **Database** (port 5432): PostgreSQL 16
- **Cache/Queue** (port 6379): Redis 7 (used for caching and Celery broker)

The backend and frontend volumes are mounted for development, so code changes reflect immediately without rebuilding containers.

### Backend Architecture (FastAPI)

The backend follows a layered architecture:

1. **`app/core/`** - Application configuration and cross-cutting concerns
   - `config.py`: Centralized settings using `pydantic-settings` (loads from `.env` or environment variables)
   - Future: `security.py` for JWT/auth, `celery_app.py` for async tasks

2. **`app/db/`** - Database setup and session management
   - `base.py`: SQLAlchemy declarative base
   - `session.py`: Database engine and session factory with `get_db()` dependency
   - Tables are auto-created on startup via `Base.metadata.create_all(bind=engine)` in `main.py`

3. **`app/models/`** - SQLAlchemy ORM models (to be created)
   - Domain entities: `user.py`, `transaction.py`, `category.py`, `bill.py`, `goal.py`

4. **`app/schemas/`** - Pydantic schemas for validation (to be created)
   - Request/response models matching the ORM models

5. **`app/crud/`** - Database operations (to be created)
   - CRUD functions that accept `db: Session` and return ORM models

6. **`app/api/v1/endpoints/`** - API route handlers (to be created)
   - RESTful endpoints for each resource
   - Use dependency injection: `db: Session = Depends(get_db)`

7. **`app/services/`** - Business logic layer (to be created)
   - `ml_service.py`: scikit-learn expense categorization
   - `plaid_service.py`: Banking data integration
   - `ocr_service.py`: Receipt scanning (Tesseract/Google Vision)
   - `export_service.py`: PDF/CSV generation
   - `analytics.py`: Spending insights

8. **`app/tasks/`** - Celery async tasks (to be created)
   - Background jobs for ML training, reminders, exports

### Frontend Architecture (React + TypeScript)

The frontend uses a feature-based organization (to be implemented):

1. **`src/components/`** - Reusable UI components
   - `common/`: Generic components (buttons, inputs, modals)
   - Domain-specific: `transactions/`, `dashboard/`, `charts/`

2. **`src/features/`** - Feature modules with co-located logic
   - Each feature contains components, hooks, types, utils
   - Examples: `auth/`, `transactions/`, `categories/`, `bills/`, `goals/`

3. **`src/pages/`** - Route-level page components
   - Top-level views: `Login.tsx`, `Dashboard.tsx`, `Transactions.tsx`, etc.

4. **`src/store/`** - Redux Toolkit state management
   - `slices/`: Feature-based state slices
   - `api.ts`: RTK Query API setup for backend communication

5. **`src/hooks/`** - Custom React hooks

6. **`src/utils/`** - Shared utilities

7. **`src/types/`** - TypeScript type definitions

The frontend communicates with the backend via `VITE_API_URL` environment variable.

### Configuration Philosophy

- **Backend**: Settings are centralized in `app/core/config.py` using Pydantic's `BaseSettings`
  - Environment variables override defaults
  - All services (DB, Redis, external APIs) configured here
  - CORS origins defined for frontend access

- **Frontend**: Environment variables prefixed with `VITE_` are exposed to client
  - `VITE_API_URL`: Backend API base URL

## Development Commands

### Starting the Application
```bash
docker-compose up --build    # Build and start all services
docker-compose up            # Start existing containers
docker-compose up -d         # Start in detached mode
```

### Stopping the Application
```bash
docker-compose down          # Stop and remove containers
docker-compose down -v       # Also remove volumes (database data)
```

### Viewing Logs
```bash
docker-compose logs -f                # All services
docker-compose logs -f backend        # Backend only
docker-compose logs -f frontend       # Frontend only
docker-compose logs -f db             # Database only
```

### Database Access
```bash
docker-compose exec db psql -U postgres -d budget_analyzer
```

### Backend Shell (for debugging)
```bash
docker-compose exec backend /bin/bash
```

### Frontend Shell (for npm commands)
```bash
docker-compose exec frontend /bin/sh
```

## Service Endpoints

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Adding New Features

### Backend: Adding an API Endpoint

1. Create SQLAlchemy model in `app/models/`
2. Create Pydantic schemas in `app/schemas/`
3. Create CRUD functions in `app/crud/`
4. Create endpoint in `app/api/v1/endpoints/`
5. Register router in `app/api/v1/api.py`
6. Include router in `app/main.py`

Example pattern:
```python
# In endpoint file
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter()

@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    # Use db session for queries
    pass
```

### Frontend: Adding a Feature

1. Create feature directory in `src/features/<feature-name>/`
2. Add components, hooks, and types within feature
3. Create Redux slice if state management needed
4. Add API endpoints to RTK Query in `src/store/api.ts`
5. Create page component in `src/pages/` if new route
6. Update router configuration

## Important Notes

- **Database migrations**: Currently uses `Base.metadata.create_all()` on startup. For production, migrate to Alembic for proper schema migrations.
- **Authentication**: JWT setup is planned but not yet implemented. Add in `app/core/security.py` and `app/api/deps.py`.
- **Celery**: Redis is configured as broker, but Celery worker container not yet set up. Add `docker/celery.Dockerfile` when implementing async tasks.
- **Hot reload**: Both frontend and backend have hot-reload enabled. Backend uses uvicorn's `--reload`, frontend uses Vite's HMR.
- **Volume mounts**: Frontend node_modules are in an anonymous volume to prevent host conflicts.
- **Health checks**: Database and Redis have health checks; backend waits for them before starting.

## Planned Integrations

- **Plaid API**: Banking connection (credentials in `app/core/config.py`)
- **OCR**: Receipt scanning via Tesseract or Google Cloud Vision
- **ML**: Expense categorization using scikit-learn
- **Celery**: Background jobs for ML training, reminders, data exports
- **ReportLab**: PDF export functionality
