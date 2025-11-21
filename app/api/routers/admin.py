# app/api/routers/admin.py

from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    on_start_app_db,
    on_start_questions_db,
    get_current_user,
)
from app.domain.services.llm_service import LLMModel, call_model
from app.domain.services.question_service import pick_random_topic_and_level
from app.domain.repositories.quesitons_repo import add_question, get_all_questions
from app.domain.repositories.quiz_repo import user_activity
from app.domain.services.audit_service import log_action, get_recent_logs

from app.domain.schemas.question import Question
from app.domain.schemas.audit import AuditLog


router = APIRouter(prefix="/admin", tags=["admin"])


# --------------------------------------------------------------------
#  SORU ÜRETİMİ (MODEL SEÇİMLİ + LOGGING)
# --------------------------------------------------------------------
@router.post("/generate-question", response_model=Question)
def gen_question(
    topic: str,
    level: str,
    qtype: str = "mcq",
    model: LLMModel = LLMModel.OLLAMA_LOCAL,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Seçilen LLM modeliyle yeni soru üretir, DB'ye kaydeder ve audit log atar.
    """

    # 1) LLM'e çağrı
    raw = call_model(model=model, topic=topic, level=level, qtype=qtype)

    # 2) Question modeli oluştur
    q = Question(
        type=qtype,
        topic=topic,
        level=level,
        stem=raw.get("question"),
        choices=raw.get("options"),
        answer_index=raw.get("answer_index"),
        rationale=raw.get("rationale"),
        source_model=model.value,
    )

    # 3) DB'ye kaydet -> ID dönüyor
    saved_id = add_question(q)
    q.id = saved_id  # response_model için id doldur

    # 4) Audit
    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_QUESTION",
        entity_type="question",
        entity_id=saved_id,
        details={
            "topic": topic,
            "level": level,
            "qtype": qtype,
            "model": model.value,
        },
    )

    return q


# --------------------------------------------------------------------
#  RANDOM SORU ÜRETİMİ (MODEL SEÇİMLİ)
# --------------------------------------------------------------------
@router.post("/generate-random-question", response_model=Question)
def generate_random_question(
    model: LLMModel = LLMModel.OLLAMA_LOCAL,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Rastgele topic/level seçerek soru üretir.
    """

    t, l = pick_random_topic_and_level()

    raw = call_model(model=model, topic=t, level=l, qtype="mcq")

    q = Question(
        type="mcq",
        topic=t,
        level=l,
        stem=raw.get("question"),
        choices=raw.get("options"),
        answer_index=raw.get("answer_index"),
        rationale=raw.get("rationale"),
        source_model=model.value,
    )

    # DB'ye kaydet -> ID dönüyor
    saved_id = add_question(q)
    q.id = saved_id

    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_RANDOM_QUESTION",
        entity_type="question",
        entity_id=saved_id,
        details={
            "topic": t,
            "level": l,
            "qtype": "mcq",
            "model": model.value,
        },
    )

    return q

# --------------------------------------------------------------------
#  SORU LİSTELEME
# --------------------------------------------------------------------
@router.get("/questions", response_model=List[Question])
def list_questions(
    limit: int = 100,
    offset: int = 0,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_QUESTIONS",
        details={"limit": limit, "offset": offset},
    )
    return get_all_questions(limit=limit, offset=offset)


# --------------------------------------------------------------------
#  KULLANICI AKTİVİTESİ — QUIZ PERFORMANSI
# --------------------------------------------------------------------
@router.get("/user-activity")
def get_user_activity(
    limit: int = 100,
    _=Depends(on_start_app_db),
    current_user: dict = Depends(get_current_user),
):
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_USER_ACTIVITY",
        details={"limit": limit},
    )

    return user_activity(limit=limit)


# --------------------------------------------------------------------
#  AUDIT LOG LİSTELEME — TEK VE DOĞRU ENDPOINT
# --------------------------------------------------------------------
@router.get("/audit-logs", response_model=List[AuditLog])
def list_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    _=Depends(on_start_app_db),
    current_user: dict = Depends(get_current_user),
):
    log_action(
        user_id=current_user["id"],
        action="ADMIN_LIST_AUDIT_LOGS",
        details={"limit": limit},
    )

    return get_recent_logs(limit=limit)
