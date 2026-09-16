from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from app.core.logging import system_logger

# Determine database URL
db_url = settings.DATABASE_URL
if not db_url or "postgres" not in db_url:
    # Use local aiosqlite for zero-config offline/local desktop usage
    db_url = "sqlite+aiosqlite:///./data/yt_automation.db"

# Ensure data directory exists
import os
os.makedirs("./data", exist_ok=True)

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and seed defaults."""
    # Import all models to ensure they are registered with Base.metadata
    from app.models import schema # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    system_logger.info("Database initialized successfully.")
