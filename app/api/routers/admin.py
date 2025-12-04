# app/api/routers/admin.py

from __future__ import annotations

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app.api.deps import (
    on_start_app_db,
    on_start_questions_db,
    get_current_user,
)
from app.domain.repositories.llm_run_repo import get_llm_stats_summary
from app.domain.schemas.llm_run import LLMStatsSummary
from app.domain.services.llm_service import LLMModel
from app.domain.services.question_service import (
    pick_random_topic_and_level,
    generate_question,  # bizim facade (async → generate_question_from_llm)
)
from app.domain.repositories.quesitons_repo import (
    get_all_questions,
    update_question_review,
    delete_question,
)
from app.domain.repositories.quiz_repo import user_activity
from app.domain.services.audit_service import log_action, get_recent_logs
from app.domain.schemas.question import QuestionModel
from app.domain.schemas.audit import AuditLog

router = APIRouter(prefix="/admin", tags=["admin"])


class ReviewQuestionRequest(BaseModel):
    status: str  # "approved" | "rejected"
    notes: str | None = None


def _map_level_to_difficulty(level: str) -> str:
    """
    Eski admin UI 'beginner/intermediate/advanced' kullanıyorsa,
    bunları unified difficulty ('easy/medium/hard') ile eşliyoruz.
    Zaten doğru geliyorsa olduğu gibi döner.
    """
    level = (level or "").lower()
    mapping = {
        "beginner": "easy",
        "intermediate": "medium",
        "advanced": "hard",
    }
    return mapping.get(level, level or "medium")


# --------------------------------------------------------------------
#  SORU ÜRETİMİ (MODEL SEÇİMLİ + LOGGING)
# --------------------------------------------------------------------
@router.post("/generate-question", response_model=QuestionModel)
async def gen_question(
    topic: str,
    level: str,
    qtype: str = "mcq",  # "mcq", "true_false", "short_answer", "open_ended", "scenario"
    model: LLMModel = LLMModel.OLLAMA_LOCAL,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Seçilen LLM modeliyle yeni soru üretir, DB'ye kaydeder ve audit log atar.
    Yeni unified QuestionModel yapısını ve generate_question pipeline'ını kullanır.
    """

    difficulty = _map_level_to_difficulty(level)

    params: Dict[str, Any] = {
        "question_type": qtype,
        "topic": topic,
        "difficulty": difficulty,
    }

    # Yeni pipeline: LLM → JSON → QuestionModel → DB
    q: QuestionModel = await generate_question(
        model_name=model.value,  # LLMModel enum → string
        params=params,
    )

    if getattr(q, "id", None) is None:
        # Normalde generate_question_from_llm içerisinde id set ediliyor
        raise HTTPException(status_code=500, detail="Question ID not set after generation")

    # Audit
    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_QUESTION",
        entity_type="question",
        entity_id=q.id,
        details={
            "topic": topic,
            "level": level,
            "difficulty": difficulty,
            "qtype": qtype,
            "model": model.value,
        },
    )

    return q


# --------------------------------------------------------------------
#  RANDOM SORU ÜRETİMİ (MODEL SEÇİMLİ)
# --------------------------------------------------------------------
@router.post("/generate-random-question", response_model=QuestionModel)
async def generate_random_question(
    model: LLMModel = LLMModel.OLLAMA_LOCAL,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Rastgele topic/level seçerek soru üretir.
    Yeni unified QuestionModel + generate_question pipeline kullanır.
    """

    topic, level = pick_random_topic_and_level()
    difficulty = _map_level_to_difficulty(level)

    params: Dict[str, Any] = {
        "question_type": "mcq",  # random üretimi şimdilik mcq ile sınırlandırıyoruz
        "topic": topic,
        "difficulty": difficulty,
    }

    q: QuestionModel = await generate_question(
        model_name=model.value,
        params=params,
    )

    if getattr(q, "id", None) is None:
        raise HTTPException(status_code=500, detail="Question ID not set after generation")

    log_action(
        user_id=current_user["id"],
        action="ADMIN_GENERATE_RANDOM_QUESTION",
        entity_type="question",
        entity_id=q.id,
        details={
            "topic": topic,
            "level": level,
            "difficulty": difficulty,
            "qtype": "mcq",
            "model": model.value,
        },
    )

    return q


# --------------------------------------------------------------------
#  SORU LİSTELEME
# --------------------------------------------------------------------
@router.get("/questions", response_model=List[QuestionModel])
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


@router.get("/llm-stats/summary", response_model=List[LLMStatsSummary])
def llm_stats_summary() -> List[LLMStatsSummary]:
    """
    LLM model bazlı performans özeti:
    - total_calls
    - avg/min/max latency
    - avg input/output tokens
    """
    stats = get_llm_stats_summary()
    return [LLMStatsSummary(**row) for row in stats]


@router.post("/questions/{question_id}/review")
def review_question(
    question_id: int,
    body: ReviewQuestionRequest,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Geçersiz status")

    # DB güncelle
    update_question_review(
        question_id=question_id,
        status=body.status,
        notes=body.notes,
        reviewer_id=current_user["id"],
    )

    # Audit log
    log_action(
        user_id=current_user["id"],
        action="ADMIN_REVIEW_QUESTION",
        entity_type="question",
        entity_id=question_id,
        details={
            "status": body.status,
            "notes": body.notes,
        },
    )

    return {"ok": True}


@router.delete("/questions/{question_id}", status_code=204)
def delete_question_endpoint(
    question_id: int,
    _=Depends(on_start_questions_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Admin: ID'ye göre soruyu siler (reddetme butonu).
    Soru yoksa 404 döner.
    """
    deleted = delete_question(question_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")

    log_action(
        user_id=current_user["id"],
        action="ADMIN_DELETE_QUESTION",
        entity_type="question",
        entity_id=question_id,
        details={},
    )

    # 204 No Content
    return Response(status_code=204)
