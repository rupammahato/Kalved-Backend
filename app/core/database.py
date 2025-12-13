from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from app.core.config import settings

if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. Set the DATABASE_URL environment variable or add it to your .env file.\n"
        "Examples:\n"
        "  - For SQLite local dev: DATABASE_URL=sqlite:///./dev.db\n"
        "  - For Postgres:     DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/dbname\n"
    )

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DATABASE_ECHO,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()

# Import models so Base.metadata is populated for migrations/tests
from app.models import user, doctor, patient, admin, clinic, session, audit, document  # noqa: F401,E402

def get_db() -> Session:
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
