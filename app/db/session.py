"""Database session management with async SQLAlchemy."""

from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

logger = structlog.get_logger(__name__)

# Create async engine
# Use NullPool for serverless deployments (Azure Container Apps)
engine = create_async_engine(
    str(settings.database_url),
    echo=settings.db_echo,
    pool_size=settings.db_pool_size if not settings.is_production else 0,
    max_overflow=settings.db_max_overflow if not settings.is_production else 0,
    poolclass=NullPool if settings.is_production else None,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection on startup."""
    logger.info("Initializing database connection", database_url=str(settings.database_url).split("@")[-1])

    # Test connection
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)

    logger.info("Database connection established")


async def close_db() -> None:
    """Close database connection on shutdown."""
    logger.info("Closing database connection")
    await engine.dispose()
    logger.info("Database connection closed")
