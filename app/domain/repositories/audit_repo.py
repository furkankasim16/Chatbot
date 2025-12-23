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
            SELECT a.id, a.user_id, u.username, a.action, a.entity_type, a.entity_id, a.details, a.created_at
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.id DESC
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
            username = row["username"]
            action = row["action"]
            entity_type = row["entity_type"]
            entity_id = row["entity_id"]
            details = row["details"]
            created_at = row["created_at"]
        except (TypeError, KeyError):
            # Tuple fallback (order must match SELECT)
            # id, user_id, username, action, entity_type, entity_id, details, created_at
            id_, user_id, username, action, entity_type, entity_id, details, created_at = row

        items.append(
            AuditLog(
                id=id_,
                user_id=user_id,
                username=username,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                created_at=created_at,
            )
        )

    return items


def get_audit_stats() -> dict:
    """
    Dashboard için özet istatistikler döner:
    1. Günlük aktivite sayısı (son 7 gün)
    2. Aksiyon tiplerine göre dağılım
    """
    stats = {
        "daily_activity": [],
        "action_distribution": []
    }

    with app_cursor() as c:
        # 1. Daily Activity (SQLite specific date function)
        # created_at is ISO string, so substr(created_at, 1, 10) gives YYYY-MM-DD
        daily_rows = c.execute(
            """
            SELECT substr(created_at, 1, 10) as day, count(*) as count
            FROM audit_logs
            GROUP BY day
            ORDER BY day DESC
            LIMIT 7
            """
        ).fetchall()
        
        # Sort chronological (optional, but convenient for charts)
        # fetchall returns list of tuples/rows.
        daily_data = []
        for row in daily_rows:
            # handle row factory
            try:
                day = row["day"]
                cnt = row["count"]
            except (TypeError, KeyError):
                day = row[0]
                cnt = row[1]
            daily_data.append({"date": day, "count": cnt})
        
        # Reverse to show oldest -> newest
        stats["daily_activity"] = list(reversed(daily_data))

        # 2. Action Distribution
        action_rows = c.execute(
            """
            SELECT action, count(*) as count
            FROM audit_logs
            GROUP BY action
            ORDER BY count DESC
            """
        ).fetchall()

        dist_data = []
        for row in action_rows:
            try:
                act = row["action"]
                cnt = row["count"]
            except (TypeError, KeyError):
                act = row[0]
                cnt = row[1]
            dist_data.append({"action": act, "count": cnt})
            
        stats["action_distribution"] = dist_data

    return stats