from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import Field

from app.models.enums import RoleScope
from app.schemas.common import AppBaseModel


class PermissionResponse(AppBaseModel):
    id: uuid.UUID
    code: str
    module: str
    description: str


class RoleResponse(AppBaseModel):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    name: str
    code: str
    scope: RoleScope
    description: Optional[str] = None
    is_system_role: bool
    permissions: List[str] = []


class CreateRoleRequest(AppBaseModel):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    permission_codes: List[str] = []


class UpdateRoleRequest(AppBaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None
    permission_codes: Optional[List[str]] = None
