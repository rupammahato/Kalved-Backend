from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.config import settings
from app.core.database import Base

from app.models import user, doctor, patient, clinic, session, admin, audit, document  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    if getattr(settings, "DATABASE_URL", None):
        return settings.DATABASE_URL
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url.strip() == "DATABASE_URL":
         raise RuntimeError("DATABASE_URL not found in .env, environment variables, or settings.")

    return ini_url

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = create_engine(
        configuration["sqlalchemy.url"],
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()