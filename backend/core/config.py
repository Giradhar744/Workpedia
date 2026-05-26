from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    All environment variables for the WorkPedia platform.
    Values are loaded from the .env file automatically.
    Never hardcode secrets — always use these settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── App ──────────────────────────────────────────────────
    APP_NAME: str = "WorkPedia"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"          # development | production

    # ─── PostgreSQL ───────────────────────────────────────────
    # Render gives you this full connection string
    # Example: postgresql+asyncpg://user:pass@host:5432/dbname
    DATABASE_URL: str

    # ─── Redis ───────────────────────────────────────────────
    # Render gives you this connection string
    # Example: redis://default:password@host:6379
    REDIS_URL: str

    # ─── JWT Auth ─────────────────────────────────────────────
    JWT_SECRET: str                           # long random string, keep secret
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15       # access token expires in 15 min
    JWT_REFRESH_EXPIRE_DAYS: int = 7          # refresh token expires in 7 days

    # ─── OTP ─────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10              # OTP valid for 10 minutes

    # ─── Rate Limiting ────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 5              # lock account after 5 failed logins
    ACCOUNT_LOCKOUT_MINUTES: int = 30        # locked for 30 minutes

    # ─── Qdrant Cloud ─────────────────────────────────────────
    # From cloud.qdrant.io — free 1GB cluster
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "workpedia_docs"

    # ─── Cloudinary ───────────────────────────────────────────
    # From cloudinary.com — free tier
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # ─── AI — Anthropic Claude ────────────────────────────────
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-5"
    CLAUDE_MAX_TOKENS: int = 2048

    # ─── AI — OpenAI Embeddings ───────────────────────────────
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536           # dimension for text-embedding-3-small

    # ─── RAG Settings ─────────────────────────────────────────
    CHUNK_SIZE_TOKENS: int = 512              # target chunk size
    CHUNK_OVERLAP_TOKENS: int = 64           # overlap between chunks (~10-20%)
    RAG_TOP_K: int = 10                      # retrieve top 10 chunks from Qdrant
    RAG_RERANK_TOP_N: int = 5               # after rerank keep top 5
    RAG_MIN_SCORE: float = 0.5              # minimum similarity score threshold
                                             # below this → "No relevant info found"

    # ─── Email ────────────────────────────────────────────────
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # ─── Super Admin (used by seed script only) ───────────────
    SUPER_ADMIN_EMAIL: str
    SUPER_ADMIN_PASSWORD: str
    SUPER_ADMIN_NAME: str = "Super Admin"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    Use this everywhere:
        from core.config import get_settings
        settings = get_settings()
    """
    return Settings()


# Single instance — import this directly for convenience
settings = get_settings()