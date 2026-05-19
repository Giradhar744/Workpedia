import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make sure 'backend/' is on the Python path ──────────────────────────────
# This lets us do: from core.config import settings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load app settings (reads from backend/.env) ──────────────────────────────
from core.config import settings

# ── Import Base so Alembic knows about all tables ────────────────────────────
from core.database import Base

# ── Import ALL models so Base.metadata is populated ─────────────────────────
# If you skip any model file here, Alembic won't see those tables
# and won't generate migrations for them
import auth.models
import departments.models
import ingestion.models
import audit.models
import rag.models

# ── Alembic config object ────────────────────────────────────────────────────
config = context.config

# ── Logging setup ────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Point Alembic to our models ──────────────────────────────────────────────
target_metadata = Base.metadata

# ── Override sqlalchemy.url with value from .env ─────────────────────────────
# Alembic runs synchronously, so we swap asyncpg → psycopg2 for migrations only
# Your FastAPI app still uses asyncpg at runtime — this only affects alembic commands
sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2").replace("%", "%%")
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """
    Offline mode: generate SQL script without connecting to DB.
    Useful for reviewing what SQL will be run before applying it.
    Run with: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Online mode: connect to DB and apply migrations directly.
    This is what runs when you do: alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()