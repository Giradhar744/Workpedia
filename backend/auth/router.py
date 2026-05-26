from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

import auth.service as auth_service
from auth.schemas import (
    LoginRequest,
    LoginResponse,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserResponse,
    MessageResponse,
    CreateUserBySuperAdminRequest,
    CreateUserByDeptAdminRequest,
    ChangeUserRoleRequest
)
from auth.dependencies import get_current_user, get_current_dept_admin, get_current_super_admin
from uuid import UUID
from auth.models import User
from core.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])
# prefix="/auth" → all routes here start with /auth
# tags=["Auth"]  → groups them under "Auth" section in /docs


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Login endpoint — works with Swagger Authorize button.
    Enter email in username field.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    body = LoginRequest(email=form_data.username, password=form_data.password)
    result = await auth_service.login(
        request=body,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    # Swagger needs access_token at root level to auto-authorize
    # We return full LoginResponse but also inject root level token
    return {
        "user": result.user,
        "tokens": result.tokens,
        "access_token": result.tokens.access_token,
        "token_type": "bearer"
    }

# ─── Login (JSON) — for frontend/mobile clients ───────────────────────────────

@router.post("/login/json", response_model=LoginResponse)
async def login_json(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    JSON login endpoint — used by React frontend in production.
    Accepts: {"email": "...", "password": "..."}

    /auth/login      → Swagger /docs (form data)
    /auth/login/json → Frontend (JSON body)
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await auth_service.login(
        request=body,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# ─── Refresh Token ────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.

    Called automatically by the frontend when the access token expires.
    No user interaction needed — happens silently in the background.
    """
    return await auth_service.refresh_access_token(request=body, db=db)


# ─── Logout ───────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Invalidate the session by deleting the refresh token.

    After logout:
    - Refresh token is deleted from DB → cannot get new access tokens
    - Access token expires naturally in 15 minutes
    """
    await auth_service.logout(refresh_token=body.refresh_token, db=db)
    return MessageResponse(message="Logged out successfully.")


# ─── Forgot Password ──────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a password reset OTP to the user's email.

    Always returns success — even if email doesn't exist.
    This prevents email enumeration attacks.

    NOTE: OTP is returned in the response for now (testing only).
    Phase 9 will replace this with actual email delivery.
    """
    otp = await auth_service.forgot_password(request=body, db=db)

    # TODO Phase 9: remove otp from response — send via email instead
    return MessageResponse(
        message=f"If this email exists, an OTP has been sent. [DEV MODE: {otp}]"
    )


# ─── Reset Password ───────────────────────────────────────────────────────────

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify OTP and set a new password.

    On success:
    - Password is updated
    - All active sessions are invalidated (forced re-login everywhere)
    - OTP is marked as used (cannot be reused)
    """
    await auth_service.reset_password(request=body, db=db)
    return MessageResponse(message="Password reset successfully. Please log in again.")


# ─── Get Current User ─────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the currently authenticated user's profile.

    Called by the frontend on app load to:
    - Check if the user is still logged in
    - Get user role (to decide which dashboard to show)
    - Get user name/email to display in UI

    This route is protected — requires a valid access token.
    No DB call needed here — get_current_user already fetched the user.
    """
    return UserResponse.model_validate(current_user)


# ─── User Management ──────────────────────────────────────────────────────────

# ─── User Management — Super Admin ───────────────────────────────────────────

@router.post("/users/admin", response_model=UserResponse, status_code=201)
async def create_user_by_super_admin(
    body: CreateUserBySuperAdminRequest,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Super Admin creates a dept_admin or employee.
    Must pass role and department_id explicitly.

    Cannot create another super_admin via API.
    """
    return await auth_service.create_user_by_super_admin(
        request=body,
        current_user=current_user,
        db=db,
    )


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_dept_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List users based on role:
    - Super Admin → sees all users in the system
    - Dept Admin → sees only employees in their own department
    """
    return await auth_service.get_all_users(
        current_user=current_user,
        db=db,
    )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(get_current_dept_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate a user account.
    - Super Admin → can deactivate dept_admin or employee
    - Dept Admin → can only deactivate their own dept employees
    """
    await auth_service.deactivate_user(
        user_id=user_id,
        current_user=current_user,
        db=db,
    )
    return MessageResponse(message="User deactivated successfully.")


# ─── User Management — Dept Admin ────────────────────────────────────────────

@router.post("/users/employee", response_model=UserResponse, status_code=201)
async def create_user_by_dept_admin(
    body: CreateUserByDeptAdminRequest,
    current_user: User = Depends(get_current_dept_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Dept Admin creates an employee in their own department.
    Role is automatically EMPLOYEE — no need to pass it.
    Department is automatically their own — no need to pass it.
    """
    return await auth_service.create_user_by_dept_admin(
        request=body,
        current_user=current_user,
        db=db,
    )


# ─── Role Management — Super Admin only ──────────────────────────────────────

@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: UUID,
    body: ChangeUserRoleRequest,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Super Admin changes a user's role.
    Cannot change role to super_admin.
    Cannot change super_admin's role.
    Cannot change your own role.

    Example use cases:
    - Promote employee to dept_admin
    - Demote dept_admin back to employee
    """
    return await auth_service.change_user_role(
        user_id=user_id,
        request=body,
        current_user=current_user,
        db=db,
    )