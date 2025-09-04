# IPRE Debate Agents - Backend

A FastAPI-based backend for simulating agent-based debates with configurable AI personas.

## Quick Start

### Option 1: Full Docker Setup (Recommended)
```bash
# Start everything (database + API + admin UI)
docker compose up --build

# Seed the database (in another terminal, while containers are running)
python -m app.database.cli seed
```

**What happens:**
- Database starts with empty tables
- API container runs migrations automatically (`alembic upgrade head`)
- You manually run seeding to add initial agent templates
- API available at `http://localhost:8000`, admin UI at `http://localhost:8080`

### Option 2: Local Development
```bash
# Start only the database
docker compose up db -d

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database with initial data
python -m app.database.cli fresh

# Start server
uvicorn app.main:app --reload
```

## Database Management

All database operations use the CLI:

```bash
python -m app.database.cli fresh          # Reset + seed (good for development)
python -m app.database.cli seed           # Add initial data only
python -m app.database.cli migrate        # Run migrations
python -m app.database.cli reset          # Drop and recreate tables
python -m app.database.cli status         # Check migration status
```

**With Docker:** You can run CLI commands from your host (they'll connect to the Docker database), or run them inside the container:
```bash
# From host (requires local Python setup)
python -m app.database.cli seed

# Or from inside the API container
docker compose exec api python -m app.database.cli seed
```

## Development

### Environment
- **Database**: PostgreSQL (Docker)
- **Python**: 3.8+ with SQLModel/FastAPI
- **Migrations**: Alembic

### Project Structure
```
app/
├── api/                # API routes and schemas
├── classes/            # Domain logic (agents, simulation)  
├── database/           # Database utilities and seeds
│   ├── cli.py         # Database management commands
│   └── seeds/         # Organized seed data
├── models.py          # SQLModel database models
├── main.py           # FastAPI application
└── services/         # Application services
```

For API documentation, visit `/docs` when the server is running.