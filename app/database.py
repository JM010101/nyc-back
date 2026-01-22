from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings

# Create SQLAlchemy engine with PostGIS support
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database - create all tables and enable PostGIS extension.
    Should be called after Alembic migrations, but useful for testing.
    """
    # Enable PostGIS extension
    with engine.connect() as conn:
        conn.execute(func.select(func.postgis_version()))
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)


@event.listens_for(engine, "connect")
def set_postgis(dbapi_conn, connection_record):
    """Set PostGIS extension on connection."""
    with dbapi_conn.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        dbapi_conn.commit()
