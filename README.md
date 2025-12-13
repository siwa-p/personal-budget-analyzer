# Personal Budget Analyzer

A full-stack budget tracking application with React frontend, FastAPI backend, and PostgreSQL database.

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite + Material-UI
- **Backend**: Python 3.12 + FastAPI
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed on your system

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
