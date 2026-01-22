# Backend API Documentation

## Setup

See main [README.md](../README.md) for full setup instructions.

## Running the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## Data Import

See main README for data import instructions.

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api/test_properties.py

# Run with coverage
pytest --cov=app --cov-report=html
```

## API Endpoints

See main README for API documentation, or visit `/docs` when the server is running.
