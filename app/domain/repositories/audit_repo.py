# app/domain/repositories/audit_repo.py

from __future__ import annotations

import json
from typing import Any, Iterable

from app.core.db import app_cursor
from app.domain.schemas.audit import AuditLog


def _ensure_table() -> None:
    """
    audit_logs tablosu yoksa oluşturur.
    app_cursor() bir context manager olduğu için 'with' ile kullanıyoruz.
    """
    with app_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def add_audit_log(user_id: int, action: str, details: dict[str, Any]) -> None:
    """
    Tek bir audit kaydı ekler.
    """
    _ensure_table()
    with app_cursor() as cur:
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, details)
            VALUES (?, ?, ?);
            """,
            (user_id, action, json.dumps(details, ensure_ascii=False)),
        )


def add_audit_logs(logs: Iterable[AuditLog]) -> None:
    """
    Birden fazla log'u tek seferde eklemek için.
    """
    _ensure_table()
    rows = [
        (log.user_id, log.action, json.dumps(log.details, ensure_ascii=False))
        for log in logs
    ]
    with app_cursor() as cur:
        cur.executemany(
            """
            INSERT INTO audit_logs (user_id, action, details)
            VALUES (?, ?, ?);
            """,
            rows,
        )


def list_recent_audit_logs(limit: int = 100) -> list[AuditLog]:
    """
    En son eklenen log'ları getirir.
    """
    _ensure_table()
    with app_cursor() as cur:
        rows = cur.execute(
            """
            SELECT id, user_id, action, details, created_at
            FROM audit_logs
            ORDER BY created_at DESC, id DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()

    result: list[AuditLog] = []
    for r in rows:
        details = {}
        try:
            details = json.loads(r["details"])
        except Exception:
            details = {"raw": r["details"]}

        result.append(
            AuditLog(
                id=r["id"],
                user_id=r["user_id"],
                action=r["action"],
                details=details,
                created_at=r["created_at"],
            )
        )

    return result
