from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.api.deps import on_start_app_db, on_start_questions_db
from app.domain.services.qustion_service import generate_question
from app.domain.repositories.quiz_repo import user_activity
from app.domain.repositories.quesitons_repo import get_all_questions
from app.domain.schemas.question import Question

router = APIRouter(prefix="/admin")

@router.post("/generate-question", response_model=Question)
def gen_question(
    topic: str, level: str, qtype: str = "mcq",
    _=Depends(on_start_questions_db)
):
    q = generate_question(topic=topic, level=level, qtype=qtype)  # DB'ye kaydeder
    return q

@router.get("/questions", response_model=list[Question])
def list_questions(limit: int = 100, offset: int = 0, _=Depends(on_start_questions_db)):
    return get_all_questions(limit=limit, offset=offset)

@router.get("/user-activity")
def get_user_activity(limit: int = 100, _=Depends(on_start_app_db)):
    return user_activity(limit=limit)
