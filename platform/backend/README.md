# Platform Backend

Backend API for the Vision AI Training Platform.

## Features

- ✅ FastAPI async application
- ✅ SQLAlchemy 2.0 async ORM
- ✅ Training job management (CRUD + callbacks)
- ✅ S3-only storage strategy (MinIO for dev)
- ✅ Support for multiple training modes (subprocess, kubernetes)
- ✅ Complete HTTP isolation from Training Services

## Quick Start

### 1. Install Dependencies

```bash
# Install Poetry if you haven't
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run Server

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API Endpoints

### Training Jobs

- `POST /api/v1/training/jobs` - Create training job
- `GET /api/v1/training/jobs` - List training jobs
- `GET /api/v1/training/jobs/{id}` - Get specific job
- `DELETE /api/v1/training/jobs/{id}` - Cancel job

### Callbacks (for Training Services)

- `POST /api/v1/training/jobs/{id}/callback` - Update job status

### Metrics

- `GET /api/v1/training/jobs/{id}/metrics` - Get training metrics

## Development

### Run Tests

```bash
poetry run pytest
```

### Code Quality

```bash
# Format
poetry run black .
poetry run isort .

# Lint
poetry run flake8 .
poetry run mypy .
```

### Database

The backend uses SQLite by default for development. For production, use PostgreSQL:

```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/platform
```

Database tables are created automatically on startup.

## Training Modes

### 1. Subprocess Mode (Development)

Training runs as a subprocess on the same machine:

```env
TRAINING_MODE=subprocess
TRAINER_SUBPROCESS_PATH=../training-services/ultralytics
```

### 2. Kubernetes Mode (Production)

Training runs as Kubernetes Jobs:

```env
TRAINING_MODE=kubernetes
KUBE_NAMESPACE=platform
```

## Architecture

The backend follows these principles:
- **No local file storage** - All datasets/checkpoints use S3 APIs
- **HTTP-only communication** - Training Services are completely isolated
- **Callback pattern** - Training Services report status via HTTP callbacks
- **Database as source of truth** - All state stored in DB

See `../docs/development/IMPLEMENTATION_PLAN.md` for detailed architecture.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | Database connection URL | `sqlite+aiosqlite:///./platform.db` |
| `S3_ENDPOINT` | MinIO/S3 endpoint | `http://localhost:9000` |
| `TRAINING_MODE` | Training execution mode | `subprocess` |
| `BACKEND_BASE_URL` | Backend URL for callbacks | `http://localhost:8000` |

See `.env.example` for complete list.

## License

Copyright © 2025 Vision AI Platform Team
