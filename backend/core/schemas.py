from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List
from datetime import datetime

# Generic type for paginated responses
T = TypeVar("T")


# ─── Base Response ────────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    """
    Standard success response for actions that don't return data.
    Example: delete document, suspend user, assign dept admin.
    """
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """
    Standard error response shape returned by all exception handlers.
    """
    success: bool = False
    detail: str


# ─── Paginated Response ───────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Wraps any list response with pagination metadata.

    Usage:
        return PaginatedResponse(
            items=users,
            total=100,
            page=1,
            page_size=20
        )
    """
    items: List[T]
    total: int                  # total number of records in DB
    page: int                   # current page number (1-indexed)
    page_size: int              # number of items per page
    total_pages: int            # total number of pages

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        """Helper to calculate total_pages automatically."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


# ─── Pagination Query Params ──────────────────────────────────────────────────

class PaginationParams(BaseModel):
    """
    Standard pagination query parameters.
    Use as a dependency in routers:
        params: PaginationParams = Depends()
    """
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """SQLAlchemy offset for the current page."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


# ─── Timestamp Mixin ──────────────────────────────────────────────────────────

class TimestampSchema(BaseModel):
    """
    Adds created_at and updated_at to any response schema.
    Inherit from this for all DB-backed response schemas.
    """
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Health Check ─────────────────────────────────────────────────────────────

class HealthCheckResponse(BaseModel):
    """Response for GET /health endpoint."""
    status: str = "ok"
    app: str
    version: str
    environment: str