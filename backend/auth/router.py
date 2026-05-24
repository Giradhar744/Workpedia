from fastapi import APIRouter, Depends, Request
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
)
from auth.dependencies import get_current_user
from auth.models import User
from core.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])
# prefix="/auth" → all routes here start with /auth
# tags=["Auth"]  → groups them under "Auth" section in /docs


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return access + refresh tokens.

    - Verifies email + password
    - Enforces brute force protection (locks after 5 failed attempts)
    - Returns user info + JWT tokens on success
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