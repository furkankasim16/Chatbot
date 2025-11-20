# app/domain/schemas/audit.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    id: Optional[int] = None
    user_id: int
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
