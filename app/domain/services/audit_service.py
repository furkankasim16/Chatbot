# app/domain/services/audit_service.py

import json
from typing import Any, Optional, List
from datetime import datetime, date

from app.domain.schemas.audit import AuditLog
from app.domain.repositories.audit_repo import add_audit_log, get_audit_logs


def _json_default(obj: Any):
    """
    json.dumps içinde datetime vs. geldiğinde nasıl serileştireceğimizi tanımlar.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # Örn. Decimal, UUID vs. gelirse:
    return str(obj)


def log_action(
    *,
    user_id: Optional[int],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[Any] = None,   # 🔧 dict yerine Any yaptık
) -> AuditLog:
    """
    Audit log kaydı oluşturur.
    details JSON string'e çevrilir (datetime vs. için özel default kullanılır).
    """
    detail_str = (
        json.dumps(details, ensure_ascii=False, default=_json_default)
        if details is not None
        else None
    )

    log = AuditLog(
      user_id=user_id,
      action=action,
      entity_type=entity_type,
      entity_id=entity_id,
      details=detail_str,
    )
    return add_audit_log(log)


def get_recent_logs(limit: int = 100) -> List[AuditLog]:
    """
    Son audit log kayıtlarını döner.
    /admin/audit-logs endpoint'i bunu kullanıyor.
    """
    return get_audit_logs(limit=limit)
