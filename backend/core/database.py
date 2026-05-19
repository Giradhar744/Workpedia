from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from core.config import settings


# ─── Engine ───────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,        # logs SQL queries in development
    pool_pre_ping=True,         # checks connection health before using it
    pool_size=10,               # max persistent connections
    max_overflow=20,            # extra connections allowed under load
)


# ─── Session Factory ──────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,     # keeps objects accessible after commit
)


# ─── Base Model ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    All SQLAlchemy models inherit from this.
    Usage:
        from core.database import Base

        class User(Base):
            __tablename__ = "users"
            ...
    """
    pass


# ─── Dependency ───────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    Automatically commits on success, rolls back on error, always closes.

    Usage in routers:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
