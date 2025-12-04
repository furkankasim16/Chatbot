# app/api/routes/questions.py

from typing import Any, Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import on_start_questions_db
from app.core.db import questions_cursor
from app.domain.schemas.question import QuestionModel
from app.domain.repositories.quesitons_repo import get_all_questions, get_random, map_level_to_db_difficulty
from app.domain.services.question_generation import generate_question_from_llm

router = APIRouter(prefix="/questions", tags=["questions"])

LEVEL_TO_DIFFICULTY = {
    "beginner": "easy",
    "intermediate": "medium",
    "advanced": "hard",
}

class GenerateQuestionRequest(BaseModel):
    model_name: str
    params: Dict[str, Any]  # question_type, topic, difficulty, vb.


@router.get("/", response_model=List[QuestionModel])
def list_questions(
    limit: int = 100,
    offset: int = 0,
    _=Depends(on_start_questions_db),
):
    return get_all_questions(limit=limit, offset=offset)


@router.get("/random", response_model=QuestionModel)
def random_question(
    topic: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),  # UI'dan gelen: beginner / mixed / vs.
    exclude: Optional[str] = Query(None),     # "1,5,12"
    _=Depends(on_start_questions_db),
):
    exclude_ids = [int(x) for x in exclude.split(",")] if exclude else None

    db_diff = map_level_to_db_difficulty(difficulty)

    q = get_random(
        topic=topic,
        difficulty=db_diff,
        exclude_ids=exclude_ids,
    )

    if not q:
        raise HTTPException(status_code=404, detail="No question found with given filters.")
    return q

@router.get("/topics")
def topics(_=Depends(on_start_questions_db)):
    items = get_all_questions(limit=10_000)
    counts = {}
    for q in items:
        # topic None olabilir, onu da filtreleyelim
        if q.topic:
            counts[q.topic] = counts.get(q.topic, 0) + 1
    return {"topics": counts}


@router.get("/levels")
def list_levels(_=Depends(on_start_questions_db)):
    # Artık kolonumuz "difficulty"
    with questions_cursor() as c:
        rows = c.execute(
            "SELECT DISTINCT difficulty FROM questions ORDER BY difficulty"
        ).fetchall()
    return [r[0] for r in rows if r and r[0]]


@router.post("/generate", response_model=QuestionModel)
async def generate_question(
    req: GenerateQuestionRequest,
    _=Depends(on_start_questions_db),
):
    try:
        return await generate_question_from_llm(
            model_name=req.model_name,
            params=req.params,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
