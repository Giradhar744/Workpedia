from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID

from auth.models import UserRole


# ─── Request Schemas (data coming IN) ────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    What the frontend sends when user clicks 'Login'.
    Email + password. That's it.
    """
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """
    User enters their email to receive an OTP.
    """
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """
    User enters the OTP they received + their new password.
    """
    email: EmailStr
    otp: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        Enforce minimum password strength at schema level.
        This runs before the request even reaches the service.
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        return v


class RefreshTokenRequest(BaseModel):
    """
    Frontend sends the refresh token to get a new access token.
    Sent when the access token expires (every 15 minutes).
    """
    refresh_token: str


class LogoutRequest(BaseModel):
    """
    Frontend sends the refresh token to invalidate the session.
    """
    refresh_token: str


# ─── Response Schemas (data going OUT) ───────────────────────────────────────

class TokenResponse(BaseModel):
    """
    Returned after successful login.
    - access_token: short-lived (15 min) — used in Authorization header
    - refresh_token: long-lived (7 days) — used to get new access tokens
    - token_type: always "bearer" — tells client how to send the token
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int             # seconds until access token expires (e.g. 900 = 15 min)


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool
    is_suspended: bool
    department_id: Optional[UUID] = None    # None for super admin
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """
    Full response after successful login.
    Combines user info + tokens in one response.
    access_token and token_type at root level for Swagger compatibility.
    """
    user: UserResponse
    tokens: TokenResponse
    access_token: str = ""
    token_type: str = "bearer"

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """
    Simple message response for actions that don't return data.
    Example: logout, forgot-password email sent.
    """
    message: str

class CreateUserBySuperAdminRequest(BaseModel):
    """
    Used by Super Admin ONLY to create dept_admin or employee.
    Super Admin explicitly passes role and department_id.
    """
    name: str
    email: EmailStr
    password: str
    role: UserRole          # dept_admin or employee (not super_admin)
    department_id: UUID     # which department to assign them to

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        return v


class CreateUserByDeptAdminRequest(BaseModel):
    """
    Used by Dept Admin ONLY to create employees.
    Role is automatically EMPLOYEE — no choice needed.
    Department is automatically their own — no choice needed.
    """
    name: str
    email: EmailStr
    password: str           # dept admin sets initial password

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        return v

class ChangeUserRoleRequest(BaseModel):
    """
    Super Admin sends this to change a user's role.
    Cannot change role to super_admin via API.
    Cannot change super_admin's role via API.

    Example: promote employee to dept_admin
    or demote dept_admin back to employee.
    """
    role: UserRole