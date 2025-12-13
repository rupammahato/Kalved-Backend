# Kalved Backend (Auth API)

Scaffold for authentication API using FastAPI, SQLAlchemy, JWT, and Google OAuth.

Structure includes placeholders for models, schemas, routers, services, middleware and tests.

This README lists common commands to start, configure, and test the application locally.

1) Using Poetry (recommended)

- Create the virtual environment and install dependencies:

```bash
poetry install
```

- Activate the virtual environment (Windows cmd):

```bash
poetry shell
```

- Run the development server:

```bash
poetry run uvicorn app.main:app --reload
```

- Run tests:

```bash
poetry run pytest -q
```

2) Using the bundled venv (if `.venv` exists)

- Install dependencies into the in-project virtualenv (Windows):

```bash
.venv\Scripts\pip.exe install -r requirements.txt
```

- Start the server using the venv Python:

```bash
.venv\Scripts\uvicorn.exe app.main:app --reload
```

3) Using pip / global venv

- Create a virtual environment and install requirements:

```bash
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
```

4) Docker (compose)

- Build and run using Docker Compose:

```bash
docker-compose up --build
```

5) Environment variables

- Copy the example `.env` and update secret values:

```bash
copy .env.example .env
# Then edit .env and set SECRET_KEY, DATABASE_URL, SMTP credentials, etc.
```

- To generate a secure `SECRET_KEY` (Python):

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

6) Database migrations (Alembic)

- Create a new revision (autogenerate if models are importable):

```bash
alembic revision --autogenerate -m "describe change"
```

- Apply migrations:

```bash
alembic upgrade head
```

7) Quick checks

- Verify the app package imports (useful after dependency changes):

```bash
poetry run python -c "import app; print('app import OK')"
```

8) Common troubleshooting

- If you see "DATABASE_URL is not configured", set `DATABASE_URL` in `.env` or environment.
- If `requests` is missing for Google auth, install it:

```bash
poetry add requests
# or
.venv\Scripts\pip.exe install requests
```

9) Development helpers (Poetry scripts)

- The project includes convenience scripts in `pyproject.toml`:

```bash
poetry run runserver   # shorthand for app.cli:runserver
poetry run run-tests   # shorthand for app.cli:run_tests
poetry run migrate     # shorthand for app.cli:run_migrations
poetry run init-env    # shorthand for app.cli:init_env
```
