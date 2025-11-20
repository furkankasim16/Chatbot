# app/domain/services/audit_service.py

from __future__ import annotations

from typing import Any

from app.domain.repositories.audit_repo import add_audit_log, list_recent_audit_logs
from app.domain.schemas.audit import AuditLog


def log_action(user_id: int, action: str, details: dict[str, Any] | None = None) -> None:
    """
    Uygulama içinde kullanacağımız ana logging fonksiyonu.
    """
    add_audit_log(
        user_id=user_id,
        action=action,
        details=details or {},
    )


def get_recent_logs(limit: int = 100) -> list[AuditLog]:
    """
    Admin panel için son log'ları döner.
    """
    return list_recent_audit_logs(limit=limit)
