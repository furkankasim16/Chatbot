# app/api/v1/admin_quiz.py

from __future__ import annotations

import json
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.core.db import app_cursor
from pydantic import BaseModel

router = APIRouter(prefix="/admin/quiz", tags=["admin-quiz"])


# ---------------------------------------------------------
# ADMIN CHECK (dict tabanlı user için düzenlendi)
# ---------------------------------------------------------
def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Kullanıcı dict döndüğü için User modeli yerine dict ile admin kontrolü yapıyoruz.
    """
    is_admin = False

    if isinstance(current_user, dict):
        is_admin = bool(current_user.get("is_admin"))
    else:
        # Eğer ileride User modeli eklenirse yine çalışsın
        is_admin = getattr(current_user, "is_admin", False)

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return current_user


# ---------------------------------------------------------
# RESPONSE MODELS
# ---------------------------------------------------------
class AdminQuestionAttemptOut(BaseModel):
    question_id: str
    stem: str
    user_answer: Any | None = None
    correct_answer: Any | None = None
    is_correct: bool
    eval_score: Optional[float] = None
    eval_feedback: Optional[str] = None


class AdminQuizAttemptOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    total_questions: int
    correct_answers: Optional[int] = None
    score: Optional[float] = None
    quiz_date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_duration_ms: Optional[int] = None


class AdminQuizAttemptDetailOut(AdminQuizAttemptOut):
    questions: List[AdminQuestionAttemptOut] = []


# ---------------------------------------------------------
# LIST ATTEMPTS
# ---------------------------------------------------------
@router.get("/attempts", response_model=List[AdminQuizAttemptOut])
def list_quiz_attempts(
    _: Dict[str, Any] = Depends(require_admin),
    user_id: Optional[int] = Query(None),
    topic: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """
    Admin → quiz attempt listesi
    """
    sql = """
        SELECT
          qa.id,
          qa.user_id,
          u.username,
          qa.topic,
          qa.difficulty,
          qa.total_questions,
          qa.correct_answers,
          qa.score,
          qa.quiz_date,
          qa.start_time,
          qa.end_time,
          qa.total_duration_ms
        FROM quiz_attempts qa
        LEFT JOIN users u ON u.id = qa.user_id
        WHERE 1=1
    """
    params: list[Any] = []

    if user_id is not None:
        sql += " AND qa.user_id = ?"
        params.append(user_id)

    if topic:
        sql += " AND qa.topic = ?"
        params.append(topic)

    sql += " ORDER BY qa.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with app_cursor() as c:
        rows = c.execute(sql, params).fetchall()

    out: List[AdminQuizAttemptOut] = []
    for r in rows:
        out.append(
            AdminQuizAttemptOut(
                id=r["id"],
                user_id=r["user_id"],
                username=r["username"],
                topic=r["topic"],
                difficulty=r["difficulty"],
                total_questions=r["total_questions"],
                correct_answers=r["correct_answers"],
                score=r["score"],
                quiz_date=r["quiz_date"],
                start_time=r["start_time"],
                end_time=r["end_time"],
                total_duration_ms=r["total_duration_ms"],
            )
        )

    return out


# ---------------------------------------------------------
# SINGLE ATTEMPT DETAIL
# ---------------------------------------------------------
@router.get("/attempts/{attempt_id}", response_model=AdminQuizAttemptDetailOut)
def get_quiz_attempt_detail(
    attempt_id: int,
    _: Dict[str, Any] = Depends(require_admin),
):
    """
    Admin → Tek quiz attempt detay + soru bazlı sonuçlar
    """
    with app_cursor() as c:
        row = c.execute(
            """
            SELECT
              qa.*,
              u.username
            FROM quiz_attempts qa
            LEFT JOIN users u ON u.id = qa.user_id
            WHERE qa.id = ?
            """,
            (attempt_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    questions: list[AdminQuestionAttemptOut] = []
    raw = row["questions_attempted"]

    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for item in parsed:
                    questions.append(
                        AdminQuestionAttemptOut(
                            question_id=str(item.get("question_id", "")),
                            stem=item.get("stem") or "",
                            user_answer=item.get("user_answer"),
                            correct_answer=item.get("correct_answer"),
                            is_correct=bool(item.get("is_correct")),
                            eval_score=item.get("eval_score"),
                            eval_feedback=item.get("eval_feedback"),
                        )
                    )
        except Exception:
            questions = []

    return AdminQuizAttemptDetailOut(
        id=row["id"],
        user_id=row["user_id"],
        username=row["username"],
        topic=row["topic"],
        difficulty=row["difficulty"],
        total_questions=row["total_questions"],
        correct_answers=row["correct_answers"],
        score=row["score"],
        quiz_date=row["quiz_date"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        total_duration_ms=row["total_duration_ms"],
        questions=questions,
    )
