from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


class AppBaseModel(BaseModel):
    """Base Pydantic model with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class SuccessResponse(AppBaseModel, Generic[DataT]):
    """Standard success response envelope."""
    success: bool = True
    data: DataT
    message: str = "Operation successful"


class ErrorDetail(AppBaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(AppBaseModel):
    """Standard error response envelope."""
    success: bool = False
    error: Dict[str, Any]

    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
    ) -> "ErrorResponse":
        return cls(
            error={
                "code": code,
                "message": message,
                "details": [d.model_dump() for d in (details or [])],
            }
        )


class PaginationMeta(AppBaseModel):
    total: int
    page: int
    size: int
    pages: int


class PaginatedResponse(AppBaseModel, Generic[DataT]):
    """Standard paginated response envelope."""
    success: bool = True
    data: List[DataT]
    pagination: PaginationMeta


class PaginationParams(AppBaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size
