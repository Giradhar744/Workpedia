from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import departments.service as dept_service
from departments.schemas import (
    CreateDepartmentRequest,
    UpdateDepartmentRequest,
    AssignUserRequest,
    DepartmentResponse,
    DepartmentDetailResponse,
    DepartmentMemberResponse,
)
from auth.dependencies import get_current_super_admin, get_current_dept_admin
from auth.models import User, UserRole
from core.exceptions import ForbiddenException
from auth.schemas import MessageResponse
from core.database import get_db

router = APIRouter(prefix="/departments", tags=["Departments"])
# prefix="/departments" → all routes start with /departments
# tags=["Departments"]  → groups them in /docs


# ─── Create Department ────────────────────────────────────────────────────────

@router.post("", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: CreateDepartmentRequest,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new department.
    Only super admin can create departments.
    Returns 409 if department name already exists.
    """
    return await dept_service.create_department(
        request=body,
        current_user=current_user,
        db=db,
    )


# ─── Get All Departments ──────────────────────────────────────────────────────

@router.get("", response_model=list[DepartmentResponse])
async def get_all_departments(
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all departments in the system.
    Ordered alphabetically by name.
    Only super admin can see all departments.
    """
    return await dept_service.get_all_departments(db=db)


# ─── Get Department By ID ─────────────────────────────────────────────────────

@router.get("/{department_id}", response_model=DepartmentDetailResponse)
async def get_department(
    department_id: UUID,
    current_user: User = Depends(get_current_dept_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full details of a department including all its members.
    - Super Admin → can view any department
    - Dept Admin → can only view their own department
    Returns 404 if department not found.
    Returns 403 if dept admin tries to view another department.
    """
    # dept admin can only view their own department
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.department_id != department_id:
            raise ForbiddenException(
                "You can only view your own department."
            )
    return await dept_service.get_department_by_id(
        department_id=department_id,
        db=db,
    )


# ─── Update Department ────────────────────────────────────────────────────────

@router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID,
    body: UpdateDepartmentRequest,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update a department (name and/or description).
    Only sends what changed — unset fields are ignored.
    Returns 404 if department not found.
    Returns 409 if new name already taken.
    """
    return await dept_service.update_department(
        department_id=department_id,
        request=body,
        db=db,
    )


# ─── Delete Department ────────────────────────────────────────────────────────

@router.delete("/{department_id}", response_model=MessageResponse)
async def delete_department(
    department_id: UUID,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a department.
    Returns 400 if department still has members.
    Remove all members first, then delete.
    """
    await dept_service.delete_department(
        department_id=department_id,
        db=db,
    )
    return MessageResponse(message="Department deleted successfully.")


# ─── Assign User to Department ────────────────────────────────────────────────

@router.post("/{department_id}/users", response_model=DepartmentMemberResponse, status_code=201)
async def assign_user(
    department_id: UUID,
    body: AssignUserRequest,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Transfer an existing user to a department.
    Super Admin only.

    - Role does NOT change on transfer
    - If user already in another dept, removed from old dept first
    - Cannot transfer Super Admin to a department
    """
    
    return await dept_service.assign_user(
        department_id=department_id,
        request=body,
        current_user=current_user,
        db=db,
    )


# ─── Get Department Members ───────────────────────────────────────────────────

@router.get("/{department_id}/users", response_model=list[DepartmentMemberResponse])
async def get_department_members(
    department_id: UUID,
    current_user: User = Depends(get_current_dept_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List all members of a department.
    - Super Admin → can view any department's members
    - Dept Admin → can only view their own department's members
    Shows name, email, role and when they were assigned.
    """
    # dept admin can only view their own department
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.department_id != department_id:
            raise ForbiddenException(
                "You can only view your own department."
            )
    return await dept_service.get_department_members(
        department_id=department_id,
        db=db,
    )


# ─── Remove User from Department ──────────────────────────────────────────────

@router.delete("/{department_id}/users/{user_id}", response_model=MessageResponse)
async def remove_user(
    department_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_dept_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a user from a department.
    Also resets their role back to EMPLOYEE.
    Returns 404 if department or membership not found.
    """
    await dept_service.remove_user(
        department_id=department_id,
        user_id=user_id,
        current_user=current_user,
        db=db,
    )
    return MessageResponse(message="User removed from department successfully.")