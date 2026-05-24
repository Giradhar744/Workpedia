from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from auth.models import User, UserRole
from auth.schemas import UserResponse
from auth.service import decode_token
from core.database import get_db
from core.exceptions import (
    NotAuthenticatedException,
    ForbiddenException,
    AccountSuspendedException
)

# ─── Token Extractor ──────────────────────────────────────────────────────────
# OAuth2PasswordBearer tells FastAPI:
# "look for a Bearer token in the Authorization header"
# It also adds a lock icon to every protected route in /docs UI
# tokenUrl is the login endpoint — used by /docs to show a login form
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ─── Core Dependency ──────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    The most important dependency in the entire project.
    Injected into every protected route.

    Flow:
    1. Extract Bearer token from Authorization header (done by oauth2_scheme)
    2. Decode and validate the JWT
    3. Extract user_id from token payload
    4. Fetch user from DB — ensures user still exists and is active
    5. Check user is not suspended
    6. Return the User object — available in the route as current_user

    Usage in any router:
        @router.get("/something")
        async def my_route(current_user: User = Depends(get_current_user)):
            ...
    """

    # Step 1+2 — decode token (raises InvalidTokenException or TokenExpiredException)
    try:
        payload = decode_token(token, expected_type="access")
    except Exception:
        raise NotAuthenticatedException()

    user_id = payload.get("sub")
    if not user_id:
        raise NotAuthenticatedException()

    # Step 3+4 — fetch user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotAuthenticatedException()

    if not user.is_active:
        raise NotAuthenticatedException()

    # Step 5 — check suspension
    if user.is_suspended:
        raise AccountSuspendedException()

    return user


# ─── Role-Based Access Control ────────────────────────────────────────────────

def require_role(*allowed_roles: UserRole):
    """
    Factory function that creates a role-checking dependency.

    Usage:
        # Only super admins can access this route
        @router.delete("/departments/{id}")
        async def delete_dept(
            current_user: User = Depends(require_role(UserRole.SUPER_ADMIN))
        ):

        # Both super admin and dept admin can access
        @router.post("/documents")
        async def upload_doc(
            current_user: User = Depends(
                require_role(UserRole.SUPER_ADMIN, UserRole.DEPT_ADMIN)
            )
        ):

    Why a factory? Because Depends() needs a callable.
    require_role(UserRole.SUPER_ADMIN) returns a callable that FastAPI can inject.
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException()
        return current_user

    return role_checker


# ─── Convenience Shortcuts ────────────────────────────────────────────────────
# Pre-built dependencies for the 3 role levels
# Import these directly in routers instead of calling require_role() every time

get_current_super_admin = require_role(UserRole.SUPER_ADMIN)

get_current_dept_admin = require_role(
    UserRole.SUPER_ADMIN,   # super admin can do everything dept admin can
    UserRole.DEPT_ADMIN,
)

get_current_employee = require_role(
    UserRole.SUPER_ADMIN,   # higher roles always inherit lower role permissions
    UserRole.DEPT_ADMIN,
    UserRole.EMPLOYEE,
)