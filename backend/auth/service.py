import random
import string
from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from auth.models import User, Session, OTPCode, OTPPurpose
from auth.schemas import (
    LoginRequest, LoginResponse, TokenResponse,
    UserResponse, RefreshTokenRequest, ResetPasswordRequest,
    ForgotPasswordRequest
)
from core.config import settings
from core.exceptions import (
    InvalidCredentialsException,
    AccountLockedException,
    AccountSuspendedException,
    InvalidTokenException,
    TokenExpiredException,
    InvalidOTPException
)

# ─── Password Hashing ─────────────────────────────────────────────────────────
# CryptContext sets up bcrypt as our hashing algorithm
# bcrypt automatically adds a salt and is intentionally slow — good for security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Converts plain text password → bcrypt hash.
    The hash looks like: $2b$12$... (never store plain passwords)
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if plain password matches the stored hash.
    Returns True/False — never raises an exception.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Token Creation ───────────────────────────────────────────────────────

def create_access_token(user_id: UUID, role: str) -> str:
    """
    Creates a short-lived JWT access token (15 minutes by default).

    Payload contains:
    - sub: user ID (subject — standard JWT claim)
    - role: user role — so we don't need a DB call on every request
    - type: "access" — so we can reject refresh tokens used as access tokens
    - exp: expiry timestamp — jose checks this automatically
    """
    expire = datetime.utcnow() + timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """
    Creates a long-lived JWT refresh token (7 days by default).

    Only contains user_id and type — no role.
    Used ONLY to get a new access token, not to access resources.
    """
    expire = datetime.utcnow() + timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    """
    Decodes and validates a JWT token.

    Raises:
    - TokenExpiredException: if token is expired
    - InvalidTokenException: if token is malformed or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        # ensure token type matches what we expect
        # prevents using a refresh token as an access token
        if payload.get("type") != expected_type:
            raise InvalidTokenException()
        return payload
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredException()
        raise InvalidTokenException()


# ─── OTP Generation ───────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """
    Generates a random numeric OTP of given length.
    Default: 6 digits e.g. "482910"
    """
    return "".join(random.choices(string.digits, k=length))


# ─── Auth Service Functions ───────────────────────────────────────────────────

async def login(
    request: LoginRequest,
    db: AsyncSession,
    ip_address: str = None,
    user_agent: str = None,
) -> LoginResponse:
    """
    Full login flow:
    1. Find user by email
    2. Check if account is locked (brute force protection)
    3. Check if account is suspended
    4. Verify password
    5. On wrong password: increment login_attempts, lock if threshold reached
    6. On success: reset login_attempts, create tokens, store session
    """

    # Step 1 — find user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise InvalidCredentialsException()

    # Step 2 — check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        raise AccountLockedException(minutes=remaining)

    # Step 3 — check if account is suspended
    if user.is_suspended:
        raise AccountSuspendedException()

    # Step 4 — verify password
    if not verify_password(request.password, user.hashed_password):
        # wrong password — increment attempts
        user.login_attempts += 1

        # Step 5 — lock account if threshold reached
        if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=settings.ACCOUNT_LOCKOUT_MINUTES
            )
            user.login_attempts = 0      # reset after locking
            await db.commit()
            raise AccountLockedException(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)

        await db.commit()
        raise InvalidCredentialsException()

    # Step 6 — success: reset login attempts
    user.login_attempts = 0
    user.locked_until = None

    # Create tokens
    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    # Store session in DB
    session = Session(
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
    )
    db.add(session)
    await db.commit()
    await db.refresh(user)

    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
        )
    )


async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession,
) -> TokenResponse:
    """
    Issues a new access token using a valid refresh token.

    Flow:
    1. Decode refresh token — raises exception if invalid/expired
    2. Check session exists in DB — if not, token was already used or logged out
    3. Check session hasn't expired
    4. Issue new access token
    """

    # Step 1 — decode refresh token
    payload = decode_token(request.refresh_token, expected_type="refresh")
    user_id = payload.get("sub")

    # Step 2 — check session exists in DB
    result = await db.execute(
        select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.refresh_token == request.refresh_token,
            )
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise InvalidTokenException()

    # Step 3 — check session expiry
    if session.expires_at < datetime.utcnow():
        await db.delete(session)
        await db.commit()
        raise TokenExpiredException()

    # Step 4 — get user and issue new access token
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise InvalidTokenException()

    new_access_token = create_access_token(user.id, user.role.value)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,    # same refresh token
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )


async def logout(refresh_token: str, db: AsyncSession) -> None:
    """
    Invalidates the session by deleting the refresh token from DB.
    After this, the refresh token cannot be used to get new access tokens.
    The access token will expire naturally after 15 minutes.
    """
    result = await db.execute(
        select(Session).where(Session.refresh_token == refresh_token)
    )
    session = result.scalar_one_or_none()

    if session:
        await db.delete(session)
        await db.commit()


async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession,
) -> str:
    """
    Generates and stores an OTP for password reset.

    Returns the OTP code (in production this would be emailed,
    for now we return it directly so you can test via /docs).

    Note: We always return success even if email not found.
    This prevents email enumeration attacks — attacker can't tell
    if an email exists in the system.
    """
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        # silently return — don't reveal if email exists
        return "If this email exists, an OTP has been sent."

    # invalidate any existing unused OTPs for this user
    existing_otps = await db.execute(
        select(OTPCode).where(
            and_(
                OTPCode.user_id == user.id,
                OTPCode.purpose == OTPPurpose.PASSWORD_RESET,
                OTPCode.is_used == False,
            )
        )
    )
    for otp in existing_otps.scalars().all():
        otp.is_used = True

    # generate new OTP
    code = generate_otp()
    otp_record = OTPCode(
        user_id=user.id,
        code=code,
        purpose=OTPPurpose.PASSWORD_RESET,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp_record)
    await db.commit()

    # TODO Phase 9: send email via notifications service
    # For now: return OTP directly for testing
    return code


async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession,
) -> None:
    """
    Verifies OTP and resets password.

    Flow:
    1. Find user by email
    2. Find valid unused OTP for this user
    3. Check OTP matches and hasn't expired
    4. Hash new password and update user
    5. Mark OTP as used
    6. Invalidate all sessions (force re-login everywhere)
    """

    # Step 1 — find user
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise InvalidOTPException()

    # Step 2 & 3 — find and validate OTP
    result = await db.execute(
        select(OTPCode).where(
            and_(
                OTPCode.user_id == user.id,
                OTPCode.code == request.otp,
                OTPCode.purpose == OTPPurpose.PASSWORD_RESET,
                OTPCode.is_used == False,
            )
        )
    )
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        raise InvalidOTPException()

    if otp_record.expires_at < datetime.utcnow():
        otp_record.is_used = True
        await db.commit()
        raise InvalidOTPException()

    # Step 4 — update password
    user.hashed_password = hash_password(request.new_password)
    user.login_attempts = 0
    user.locked_until = None

    # Step 5 — mark OTP as used
    otp_record.is_used = True

    # Step 6 — delete all sessions (force re-login on all devices)
    sessions = await db.execute(
        select(Session).where(Session.user_id == user.id)
    )
    for session in sessions.scalars().all():
        await db.delete(session)

    await db.commit()