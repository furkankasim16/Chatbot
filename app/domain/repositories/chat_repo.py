# app/domain/repositories/chat_repo.py

import sqlite3
from typing import List, Optional
from uuid import uuid4

from app.core.config import settings
from app.core.db import app_cursor
from app.domain.schemas.chat import ChatMessage, ChatMessageRole, ChatMode


DB_PATH = settings.APP_DB_PATH


def create_chat_session(
    user_id: Optional[int],
    mode: ChatMode,
    topic: Optional[str],
    level: Optional[str],
    language: str = "tr",
) -> str:
    """
    Yeni bir chat session oluşturur ve session_id (uuid) döner.
    """
    session_id = str(uuid4())
    with app_cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_sessions (id, user_id, mode, topic, level, language, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (session_id, user_id, mode.value, topic, level, language),
        )
    return session_id


def touch_chat_session(session_id: str) -> None:
    """
    updated_at alanını günceller (bir mesaj geldiğinde çağırabiliriz).
    """
    with app_cursor() as cur:
        cur.execute(
            """
            UPDATE chat_sessions
            SET updated_at = datetime('now')
            WHERE id = ?
            """,
            (session_id,),
        )


def add_chat_message(
    session_id: str,
    role: ChatMessageRole,
    content: str,
) -> None:
    """
    Session'a mesaj ekler.
    """
    with app_cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role.value, content),
        )


def get_session_messages(
    session_id: str,
    limit: int = 20,
) -> List[ChatMessage]:
    """
    Verilen session için son N mesajı (eski → yeni) döner.
    """
    with app_cursor() as cur:
        cur.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = cur.fetchall()

    # DESC aldık, tersten çevirelim ki eski → yeni olsun
    rows.reverse()

    out: List[ChatMessage] = []
    for role_str, content in rows:
        out.append(
            ChatMessage(
                role=ChatMessageRole(role_str),
                content=content,
            )
        )
    return out
