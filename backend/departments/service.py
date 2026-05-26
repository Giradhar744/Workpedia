# business logic related to department
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from departments.models import Department, UserDepartment
from departments.schemas import (
    CreateDepartmentRequest,
    UpdateDepartmentRequest,
    AssignUserRequest,
    DepartmentResponse,
    DepartmentDetailResponse,
    DepartmentMemberResponse,
)
from auth.models import User, UserRole
from core.exceptions import (
    DepartmentNotFoundException,
    CannotDeleteDepartmentWithUsersException,
    AlreadyExistsException,
    NotFoundException,
    ForbiddenException,
)


# ─── Create Department ────────────────────────────────────────────────────────

async def create_department(
    request: CreateDepartmentRequest,
    current_user: User,
    db: AsyncSession,
) -> DepartmentResponse:
    """
    Creates a new department.

    Flow:
    1. Check no department with same name exists
    2. Create department, set created_by to current super admin
    3. Return the new department
    """

    # Step 1 — check for duplicate name
    result = await db.execute(
        select(Department).where(Department.name == request.name)
    )
    if result.scalar_one_or_none():
        raise AlreadyExistsException("Department")

    # Step 2 — create department
    department = Department(
        name=request.name,
        description=request.description,
        created_by=current_user.id,
    )
    db.add(department)
    await db.commit()
    await db.refresh(department)

    return DepartmentResponse.model_validate(department)


# ─── Get All Departments ──────────────────────────────────────────────────────

async def get_all_departments(
    db: AsyncSession,
) -> list[DepartmentResponse]:
    """
    Returns all departments in the system.
    Only super admin can see all departments.
    """
    result = await db.execute(
        select(Department).order_by(Department.name)
    )
    departments = result.scalars().all()
    return [DepartmentResponse.model_validate(d) for d in departments]


# ─── Get Department By ID ─────────────────────────────────────────────────────

async def get_department_by_id(
    department_id: UUID,
    db: AsyncSession,
) -> DepartmentDetailResponse:
    """
    Returns full department detail including all members.

    Flow:
    1. Fetch department — raise 404 if not found
    2. Fetch all UserDepartment records for this dept
    3. For each member, fetch their User record
    4. Build and return DepartmentDetailResponse
    """

    # Step 1 — fetch department
    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise DepartmentNotFoundException()

    # Step 2 — fetch memberships
    memberships_result = await db.execute(
        select(UserDepartment).where(
            UserDepartment.department_id == department_id
        )
    )
    memberships = memberships_result.scalars().all()

    # Step 3 — build member list
    members = []
    for membership in memberships:
        user_result = await db.execute(
            select(User).where(User.id == membership.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            members.append(DepartmentMemberResponse(
                user_id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                assigned_at=membership.assigned_at,
            ))

    return DepartmentDetailResponse(
        id=department.id,
        name=department.name,
        description=department.description,
        created_by=department.created_by,
        created_at=department.created_at,
        updated_at=department.updated_at,
        members=members,
    )


# ─── Update Department ────────────────────────────────────────────────────────

async def update_department(
    department_id: UUID,
    request: UpdateDepartmentRequest,
    db: AsyncSession,
) -> DepartmentResponse:
    """
    Partially updates a department (PATCH pattern).
    Only updates fields that are provided in the request.

    Flow:
    1. Fetch department — raise 404 if not found
    2. Check new name doesn't conflict with another dept
    3. Apply only the provided fields
    4. Commit and return updated department
    """

    # Step 1 — fetch department
    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise DepartmentNotFoundException()

    # Step 2 — check name conflict (only if name is being changed)
    if request.name and request.name != department.name:
        existing = await db.execute(
            select(Department).where(Department.name == request.name)
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsException("Department")

    # Step 3 — apply only provided fields
    if request.name is not None:
        department.name = request.name
    if request.description is not None:
        department.description = request.description

    department.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(department)

    return DepartmentResponse.model_validate(department)


# ─── Delete Department ────────────────────────────────────────────────────────

async def delete_department(
    department_id: UUID,
    db: AsyncSession,
) -> None:
    """
    Deletes a department.

    Business rule: cannot delete a department that still has members.
    Super admin must remove all users first, then delete.

    Why this rule?
    Prevents accidental deletion of active departments.
    Forces intentional cleanup before deletion.
    """

    # Fetch department
    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = result.scalar_one_or_none()
    if not department:
        raise DepartmentNotFoundException()

    # Check for existing members
    members_result = await db.execute(
        select(UserDepartment).where(
            UserDepartment.department_id == department_id
        )
    )
    members = members_result.scalars().all()
    if members:
        raise CannotDeleteDepartmentWithUsersException()

    await db.delete(department)
    await db.commit()


# ─── Assign User to Department ────────────────────────────────────────────────

async def assign_user(
    department_id: UUID,
    request: AssignUserRequest,
    current_user: User,
    db: AsyncSession,
) -> DepartmentMemberResponse:
    """
    Transfers an existing user to a department.
    Only Super Admin can transfer users between departments.

    Rules:
    - Super Admin can transfer anyone to any department
    - Role does NOT change on transfer
    - If user already belongs to another department,
      they are removed from old dept first
    - Cannot transfer Super Admin to a department

    Flow:
    1. Verify department exists
    2. Fetch user being transferred
    3. Block Super Admin transfer
    4. Check if user already in this department
    5. Remove from old department if exists
    6. Add to new department
    7. Update department_id on User
    """

    # Step 1 — verify department exists
    dept_result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = dept_result.scalar_one_or_none()
    if not department:
        raise DepartmentNotFoundException()

    # Step 2 — fetch user being transferred
    user_result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User")

    # Step 3 — block Super Admin transfer
    if user.role == UserRole.SUPER_ADMIN:
        raise ForbiddenException(
            "Cannot assign Super Admin to a department."
        )

    # Step 4 — check if user already in this department
    existing_result = await db.execute(
        select(UserDepartment).where(
            and_(
                UserDepartment.user_id == request.user_id,
                UserDepartment.department_id == department_id,
            )
        )
    )
    if existing_result.scalar_one_or_none():
        raise AlreadyExistsException("User already in this department")

    # Step 5 — remove from old department if exists
    old_membership_result = await db.execute(
        select(UserDepartment).where(
            UserDepartment.user_id == request.user_id
        )
    )
    old_membership = old_membership_result.scalar_one_or_none()
    if old_membership:
        await db.delete(old_membership)

    # Step 6 — add to new department
    new_membership = UserDepartment(
        user_id=request.user_id,
        department_id=department_id,
        assigned_by=current_user.id,
        assigned_at=datetime.utcnow(),
    )
    db.add(new_membership)

    # Step 7 — update department_id on User
    user.department_id = department_id

    await db.commit()
    await db.refresh(user)

    return DepartmentMemberResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        assigned_at=new_membership.assigned_at,
    )


# ─── Get Department Members ───────────────────────────────────────────────────

async def get_department_members(
    department_id: UUID,
    db: AsyncSession,
) -> list[DepartmentMemberResponse]:
    """
    Returns all members of a specific department.
    """

    # Verify department exists
    dept_result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    if not dept_result.scalar_one_or_none():
        raise DepartmentNotFoundException()

    # Fetch memberships
    memberships_result = await db.execute(
        select(UserDepartment).where(
            UserDepartment.department_id == department_id
        )
    )
    memberships = memberships_result.scalars().all()

    members = []
    for membership in memberships:
        user_result = await db.execute(
            select(User).where(User.id == membership.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            members.append(DepartmentMemberResponse(
                user_id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                assigned_at=membership.assigned_at,
            ))

    return members


# ─── Remove User from Department ──────────────────────────────────────────────

async def remove_user(
    department_id: UUID,
    user_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> None:
    """
    Removes a user from a department.

    Rules:
    - Super Admin can remove anyone from any department
    - Dept Admin can only remove employees from their own department
    - Nobody can remove a Super Admin from a department

    Also clears department_id on the User record after removal.
    """

    # Verify department exists
    dept_result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    if not dept_result.scalar_one_or_none():
        raise DepartmentNotFoundException()

    # Find membership
    membership_result = await db.execute(
        select(UserDepartment).where(
            and_(
                UserDepartment.user_id == user_id,
                UserDepartment.department_id == department_id,
            )
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        raise NotFoundException("User in this department")

    # Fetch user being removed
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User")

    # Role checks for dept admin
    if current_user.role == UserRole.DEPT_ADMIN:
        # dept admin cannot remove super admin or another dept admin
        if user.role != UserRole.EMPLOYEE:
            raise ForbiddenException(
                "Dept Admin can only remove Employees."
            )
        # dept admin can only remove from their own department
        if current_user.department_id != department_id:
            raise ForbiddenException(
                "You can only manage your own department."
            )

    # Nobody can remove super admin from a department
    if user.role == UserRole.SUPER_ADMIN:
        raise ForbiddenException(
            "Cannot remove Super Admin from a department."
        )

    # Clear user department and reset role to employee
    user.role = UserRole.EMPLOYEE
    user.department_id = None

    await db.delete(membership)
    await db.commit()