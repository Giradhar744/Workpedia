from fastapi import HTTPException, status


# ─── Auth Exceptions ──────────────────────────────────────────────────────────

class InvalidCredentialsException(HTTPException):
    """Wrong email or password."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(HTTPException):
    """JWT access or refresh token has expired."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenException(HTTPException):
    """JWT token is malformed or invalid."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AccountLockedException(HTTPException):
    """Account locked after too many failed login attempts."""
    def __init__(self, minutes: int = 30):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to too many failed attempts. "
                   f"Try again in {minutes} minutes.",
        )


class AccountSuspendedException(HTTPException):
    """Account suspended by an admin."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Contact your administrator.",
        )


class InvalidOTPException(HTTPException):
    """OTP is wrong or expired."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please request a new one.",
        )


# ─── Authorization Exceptions ─────────────────────────────────────────────────

class ForbiddenException(HTTPException):
    """User does not have permission to perform this action."""
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )


class NotAuthenticatedException(HTTPException):
    """User is not authenticated."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Resource Exceptions ──────────────────────────────────────────────────────

class NotFoundException(HTTPException):
    """Requested resource does not exist."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found.",
        )


class AlreadyExistsException(HTTPException):
    """Resource already exists (duplicate)."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} already exists.",
        )


# ─── Department Exceptions ────────────────────────────────────────────────────

class DepartmentNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )


class UserNotInDepartmentException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this department.",
        )


class CannotDeleteDepartmentWithUsersException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete department that still has active users.",
        )


# ─── Document / Ingestion Exceptions ─────────────────────────────────────────

class UnsupportedFileTypeException(HTTPException):
    """File type is not supported for ingestion."""
    def __init__(self, file_type: str):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file_type}' is not supported. "
                   f"Supported types: PDF, DOCX, PPTX, XLSX, MD, TXT, Python, JS, TS.",
        )


class FileTooLargeException(HTTPException):
    """Uploaded file exceeds the size limit."""
    def __init__(self, max_mb: int = 50):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the maximum allowed size of {max_mb}MB.",
        )


class DocumentNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )


class IngestionJobNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion job not found.",
        )


class DocumentAlreadyExistsException(HTTPException):
    """Duplicate document uploaded to same department."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A document with this name already exists in this department.",
        )


# ─── RAG / Query Exceptions ───────────────────────────────────────────────────

class QueryTooLongException(HTTPException):
    """User query exceeds the token limit."""
    def __init__(self, max_tokens: int = 500):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query is too long. Maximum allowed length is {max_tokens} tokens.",
        )


class VectorStoreException(HTTPException):
    """Qdrant operation failed."""
    def __init__(self, message: str = "Vector store operation failed."):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        )


class LLMException(HTTPException):
    """LLM API call failed."""
    def __init__(self, message: str = "AI service is temporarily unavailable."):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        )


# ─── Storage Exceptions ───────────────────────────────────────────────────────

class StorageUploadException(HTTPException):
    """File upload to Cloudinary failed."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage service is temporarily unavailable. Please try again.",
        )


# ─── Validation Exceptions ────────────────────────────────────────────────────

class ValidationException(HTTPException):
    """Generic input validation error."""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        )