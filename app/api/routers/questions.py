from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from app.api.deps import on_start_questions_db
from app.core.db import questions_cursor
from app.domain.schemas.question import Question
from app.domain.repositories.quesitons_repo import get_all_questions, get_random

router = APIRouter(prefix="/questions")

@router.get("/", response_model=List[Question])
def list_questions(limit: int = 100, offset: int = 0, _=Depends(on_start_questions_db)):
    return get_all_questions(limit=limit, offset=offset)

@router.get("/random", response_model=Question)
def random_question(
    topic: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    exclude: Optional[str] = Query(None),   # "1,5,12"
    _=Depends(on_start_questions_db)
):
    exclude_ids = [int(x) for x in exclude.split(",")] if exclude else None
    q = get_random(topic=topic, level=level, exclude_ids=exclude_ids)
    if not q:
        raise HTTPException(status_code=404, detail="No question found with given filters.")
    return q

@router.get("/topics")
def topics(_=Depends(on_start_questions_db)):
    items = get_all_questions(limit=10_000)
    counts = {}
    for q in items:
        counts[q.topic] = counts.get(q.topic, 0) + 1
    return {"topics": counts}

@router.get("/levels")
def list_levels():
    with questions_cursor() as c:
        rows = c.execute("SELECT DISTINCT level FROM questions ORDER BY level").fetchall()
    return [r[0] for r in rows if r and r[0]]