# app_package/database.py
"""
Asynchronous database configuration for TrueTag using SQLAlchemy & PostgreSQL.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Ensure async driver
db_url = str(settings.DATABASE_URL)
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Async engine
engine = create_async_engine(
    db_url,
    echo=settings.DB_ECHO,  # Use a setting for echo
    future=True
)

# Session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Base ORM class
Base = declarative_base()

# Dependency for routes
async def get_db() -> AsyncSession:
    """
    Yields an async database session for use in API routes.
    """
    async with AsyncSessionLocal() as session:
        yield session