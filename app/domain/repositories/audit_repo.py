# app/domain/repositories/audit_repo.py

import sqlite3
from typing import List

from app.domain.schemas.audit import AuditLog
from app.core.config import settings
from app.core.db import app_cursor

DB_PATH = settings.APP_DB_PATH  # Örn: "app.db" gibi


def add_audit_log(log: AuditLog) -> AuditLog:
    """
    Tek bir audit log kaydı ekler ve id'sini doldurur.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            log.user_id,
            log.action,
            log.entity_type,
            log.entity_id,
            log.details,
        ),
    )
    conn.commit()
    log.id = cur.lastrowid
    conn.close()
    return log


def get_audit_logs(limit: int = 100) -> List[AuditLog]:
    """
    Son audit log kayıtlarını döner (id DESC).
    """
    items: List[AuditLog] = []

    with app_cursor() as c:
        c.execute(
            """
            SELECT id, user_id, action, entity_type, entity_id, details, created_at
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = c.fetchall()

    for row in rows:
        # row dict-like (sqlite3.Row) veya tuple olabilir
        try:
            id_ = row["id"]
            user_id = row["user_id"]
            action = row["action"]
            entity_type = row["entity_type"]
            entity_id = row["entity_id"]
            details = row["details"]
            created_at = row["created_at"]
        except (TypeError, KeyError):
            id_, user_id, action, entity_type, entity_id, details, created_at = row

        items.append(
            AuditLog(
                id=id_,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                created_at=created_at,
            )
        )

    return items
