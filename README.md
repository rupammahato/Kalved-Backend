# Kalved Backend

FastAPI backend for the Kalved healthcare platform.

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- PostgreSQL 14+

## Quick Start

```bash
# Install dependencies
poetry install

# Configure environment
copy .env.example .env
# Edit .env with your database credentials and secrets

# Start Redis (requires Docker Desktop running)
docker-compose up -d redis

# Run migrations
poetry run migrate

# Start server
poetry run runserver
```

API: http://localhost:8000 | Docs: http://localhost:8000/docs


## Docker Services

```bash
docker-compose up -d redis      # Start Redis only (recommended)
docker-compose up -d            # Start all services
docker-compose down             # Stop all services
```

## Development Commands

```bash
poetry run runserver    # Start dev server
poetry run migrate      # Apply migrations
poetry run run-tests    # Run tests
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Redis connection failed | Ensure Docker Desktop is running, then `docker-compose up -d redis` |
| Port 6379 already in use | `docker stop kalved-redis && docker rm kalved-redis` |
| Docker commands fail | Start Docker Desktop and wait for it to initialize |

## License

**Proprietary - All Rights Reserved**

Copyright © 2025 Kalved. All rights reserved.

This software is the confidential and proprietary property of Kalved. Unauthorized copying, distribution, modification, or use of this software is strictly prohibited.
