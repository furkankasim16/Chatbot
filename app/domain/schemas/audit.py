# app/domain/schemas/audit.py

from typing import Optional
from pydantic import BaseModel


class AuditLog(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    action: str

    # 🔹 yeni eklediğimiz alanlar:
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None

    # DB'de JSON string olarak saklıyoruz
    details: Optional[str] = None

    # SQLite genelde TEXT timestamp döndürüyor (CURRENT_TIMESTAMP)
    created_at: Optional[str] = None