"""Common/shared schemas for pagination and responses."""
from pydantic import BaseModel
from typing import Any, Optional


class Pagination(BaseModel):
    total: int
    page: int
    size: int


class SuccessResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
