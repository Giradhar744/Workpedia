from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.schemas import HealthCheckResponse


# ─── App Factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,       # hide docs in production
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # ── Middleware ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else [],      # lock down in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────
    # Routers will be registered here as each phase is built:
    #
    # from auth.router import router as auth_router
    # from departments.router import router as dept_router
    # from ingestion.router import router as ingestion_router
    # from rag.router import router as rag_router
    # from audit.router import router as audit_router
    # from analytics.router import router as analytics_router
    #
    # app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
    # app.include_router(dept_router, prefix="/api/v1/departments", tags=["Departments"])
    # app.include_router(ingestion_router, prefix="/api/v1/documents", tags=["Ingestion"])
    # app.include_router(rag_router, prefix="/api/v1/query", tags=["RAG"])
    # app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit"])
    # app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])

    # ── Health Check ──────────────────────────────────────────
    @app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
    async def health_check():
        return HealthCheckResponse(
            status="ok",
            app=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
        )

    return app


# ─── App Instance ─────────────────────────────────────────────────────────────

app = create_app()
