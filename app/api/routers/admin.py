# app/api/routers/admin.py

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    on_start_app_db,
    on_start_questions_db,
    get_current_user,  # <- eğer sende farklıysa buna göre düzelt
)
from app.domain.services.question_service import generate_question
from app.domain.repositories.quiz_repo import user_activity
from app.domain.repositories.quesitons_repo import get_all_questions
from app.domain.schemas.question import Question
from app.domain.schemas.audit import AuditLog
from app.domain.services.audit_service import log_action, get_recent_logs
from app.domain.schemas.audit import AuditLog

router = APIRouter(prefix="/admin", tags=["admin"])


# --------------------------------------------------------------------
#  SORU ÜRETİMİ (LOGGING İLE)
# --------------------------------------------------------------------
@router.post("/generate-question", response_model=Question)
def gen_question(
    topic: str,
    level: str,
    qtype: str = "mcq",
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    LLM ile yeni soru üretir, DB'ye kaydeder ve audit log atar.
    """
    q = generate_question(topic=topic, level=level, qtype=qtype)

    # Audit log
    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_QUESTION",
        details={
            "topic": topic,
            "level": level,
            "qtype": qtype,
            "question_id": getattr(q, "id", None),
            "source_model": getattr(q, "source_model", None),
        },
    )

    return q


# --------------------------------------------------------------------
#  SORU LİSTELEME
# --------------------------------------------------------------------
@router.get("/questions", response_model=list[Question])
def list_questions(
    limit: int = 100,
    offset: int = 0,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    # İstersen burayı da loglayabilirsin, örneğin:
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_QUESTIONS",
        details={"limit": limit, "offset": offset},
    )
    return get_all_questions(limit=limit, offset=offset)


# --------------------------------------------------------------------
#  KULLANICI AKTİVİTESİ
# --------------------------------------------------------------------
@router.get("/user-activity")
def get_user_activity(
    limit: int = 100,
    _=Depends(on_start_app_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Kullanıcıların quiz aktivitelerini getirir.
    Admin panelindeki tablo bu veriyi kullanır.
    """
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_USER_ACTIVITY",
        details={"limit": limit},
    )
    return user_activity(limit=limit)


# --------------------------------------------------------------------
#  AUDIT LOG LİSTELEME (ADMIN PANEL İÇİN)
# --------------------------------------------------------------------
@router.get("/audit-logs", response_model=list[AuditLog])
def list_audit_logs(
    limit: int = 100,
    _=Depends(on_start_app_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Son audit log kayıtlarını döner.
    """
    # Yetki kontrolü istiyorsan burada rol bakabilirsin.
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_AUDIT_LOGS",
        details={"limit": limit},
    )
    return get_recent_logs(limit=limit)

@router.get("/audit-logs", response_model=list[AuditLog])
def list_audit_logs(
    limit: int = 100,
    _=Depends(on_start_app_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Admin paneli için audit log kayıtlarını listeler.
    """
    # Audit log da loglanabilir :)
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_AUDIT_LOGS",
        details={"limit": limit},
    )

    return get_recent_logs(limit=limit)