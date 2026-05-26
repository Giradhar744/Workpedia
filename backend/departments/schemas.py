from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

from auth.models import UserRole


# ─── Request Schemas (data coming IN) ────────────────────────────────────────

class CreateDepartmentRequest(BaseModel):
    """
    Super admin sends this to create a new department.
    Only name is required — description is optional.
    """
    name: str
    description: Optional[str] = None


class UpdateDepartmentRequest(BaseModel):
    """
    Super admin sends this to update a department.
    Both fields optional — only update what's provided.
    This is a PATCH pattern — partial update.
    """
    name: Optional[str] = None
    description: Optional[str] = None


class AssignUserRequest(BaseModel):
    """
    Super Admin sends this to transfer an existing user to a department.
    Role does NOT change on transfer — stays whatever it was at creation.
    Only Super Admin can transfer users between departments.
    """
    user_id: UUID
    


# ─── Response Schemas (data going OUT) ───────────────────────────────────────

class DepartmentResponse(BaseModel):
    """
    Returned when listing or viewing a department.
    Includes who created it and when.
    """
    id: UUID
    name: str
    description: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentMemberResponse(BaseModel):
    """
    Returned when listing members of a department.
    Shows the user's details + their role + when they were assigned.
    """
    user_id: UUID
    name: str
    email: str
    role: UserRole
    assigned_at: datetime

    model_config = {"from_attributes": True}


class DepartmentDetailResponse(BaseModel):
    """
    Full department view — includes department info + list of members.
    Returned when super admin views a specific department.
    """
    id: UUID
    name: str
    description: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    members: list[DepartmentMemberResponse] = []

    model_config = {"from_attributes": True}