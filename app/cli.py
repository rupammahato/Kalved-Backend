"""Small CLI helpers wired to Poetry scripts for developer convenience.

Usage (from project root):
  poetry run runserver --host 0.0.0.0 --port 8000 --no-reload
  poetry run run-tests
  poetry run migrate        # defaults to `alembic upgrade head`
  poetry run init-env       # copies .env.example -> .env if missing
"""
from __future__ import annotations

import sys
import shutil
import subprocess
from pathlib import Path
from typing import List


def _args() -> List[str]:
    return sys.argv[1:]


def runserver() -> None:
    """Run Uvicorn programmatically. Accepts simple flags:

    --host=<host>  (default 127.0.0.1)
    --port=<port>  (default 8000)
    --no-reload    (disable auto-reload)
    --reload       (enable auto-reload)
    """
    try:
        import uvicorn
    except Exception:
        print("uvicorn is not installed in the environment. Run `poetry add uvicorn[standard]`.")
        raise

    host = "127.0.0.1"
    port = 8000
    reload = True

    for a in _args():
        if a.startswith("--host="):
            host = a.split("=", 1)[1]
        elif a.startswith("--port="):
            try:
                port = int(a.split("=", 1)[1])
            except Exception:
                pass
        elif a == "--no-reload":
            reload = False
        elif a == "--reload":
            reload = True

    print(f"Starting uvicorn on {host}:{port} (reload={reload})")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


def run_tests() -> None:
    """Run pytest with any forwarded args."""
    args = _args()
    cmd = ["pytest"] + args
    subprocess.run(cmd, check=True)


def run_migrations() -> None:
    """Run alembic. If no args provided, runs `alembic upgrade head`."""
    args = _args()
    if args:
        cmd = ["alembic"] + args
    else:
        cmd = ["alembic", "upgrade", "head"]
    subprocess.run(cmd, check=True)


def init_env() -> None:
    """Copy `.env.example` to `.env` if `.env` is missing."""
    root = Path(__file__).resolve().parents[1]
    src = root / ".env.example"
    dst = root / ".env"
    if dst.exists():
        print(f".env already exists at {dst}")
        return
    if not src.exists():
        print(f".env.example not found at {src}")
        return
    shutil.copy(src, dst)
    print(f"Created .env from .env.example at {dst}")


if __name__ == "__main__":
    # Allow running the helpers directly: python -m app.cli runserver
    if len(sys.argv) <= 1:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    sys.argv.pop(1)
    if cmd == "runserver":
        runserver()
    elif cmd in ("run-tests", "tests", "test"):
        run_tests()
    elif cmd in ("migrate", "alembic"):
        run_migrations()
    elif cmd in ("init-env", "initenv"):
        init_env()
    else:
        print(f"Unknown command: {cmd}")
