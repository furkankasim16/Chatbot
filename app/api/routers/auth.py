# app/api/routers/auth.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from pydantic import BaseModel

from app.core.config import settings
from app.core.db import app_cursor
from app.core.security import create_access_token, verify_password  # ← tek kaynak
from app.api.deps import get_current_user, on_start_app_db
from app.domain.schemas.auth import UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])

# Swagger "Authorize" düğmesi için
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# ---------- Schemas ----------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool

class UserStats(BaseModel):
    total_quizzes: int
    total_questions: int
    correct_answers: int
    last_quiz_date: Optional[str]  # ISO string veya None
    topic_stats: Dict[str, Dict[str, int]]

# ---------- Auth helpers ----------
def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    with app_cursor() as c:
        row = c.execute(
            "SELECT id, username, hashed_password, is_admin FROM users WHERE username=?",
            (username,),
        ).fetchone()
    if not row:
        return None
    if not verify_password(password, row["hashed_password"]):
        return None
    return {"id": row["id"], "username": row["username"], "is_admin": bool(row["is_admin"])}

@router.get("/me")
def me(current=Depends(get_current_user)):
    return current


# ---------- Routes ----------
@router.post("/login", response_model=TokenResponse, dependencies=[Depends(on_start_app_db)])
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı adı veya şifre hatalı")
    # sub = username (mevcut mimari böyle)
    token = create_access_token({"sub": user["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "is_admin": user["is_admin"],
    }

@router.get("/stats", response_model=UserStats, dependencies=[Depends(on_start_app_db)])
def user_stats(current=Depends(get_current_user)):
    user_id = current["id"]
    with app_cursor() as c:
        # toplam quiz, toplam sorular, toplam doğru, son tarih
        tq = c.execute(
            """
            SELECT
              COUNT(*) AS total_quizzes,
              COALESCE(SUM(total_questions), 0) AS total_questions,
              COALESCE(SUM(correct_answers), 0) AS correct_answers,
              MAX(quiz_date) AS last_quiz_date
            FROM quiz_attempts
            WHERE user_id=?
            """,
            (user_id,),
        ).fetchone() or (0, 0, 0, None)

        # topic bazında doğru/toplam
        rows = c.execute(
            """
            SELECT topic,
                   COALESCE(SUM(correct_answers),0) AS correct,
                   COALESCE(SUM(total_questions),0) AS total
            FROM quiz_attempts
            WHERE user_id=?
            GROUP BY topic
            """,
            (user_id,),
        ).fetchall()

    topic_stats = {r[0]: {"correct": int(r[1]), "total": int(r[2])} for r in rows}

    return {
        "total_quizzes": int(tq[0]),
        "total_questions": int(tq[1]),
        "correct_answers": int(tq[2]),
        "last_quiz_date": tq[3],
        "topic_stats": topic_stats,
    }

@router.post("/register", dependencies=[Depends(on_start_app_db)])
def register(data: "UserCreate"):  # tip import döngüsüne takılmamak için string literal da ok
    try:
        from app.domain.repositories.users_repo import create_user, get_user_by_id
        uid = create_user(data.username, data.email, data.password)
        user = get_user_by_id(uid)
        from app.domain.schemas.auth import UserOut
        return UserOut(**user)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot register: {e}")

@router.post("/submit-result")
def submit_result(current=Depends(get_current_user), payload: Dict[str, Any] | None = None):
    payload = payload or {}
    topic = (payload.get("topic") or "").strip()
    difficulty = (payload.get("difficulty") or "beginner").strip()
    total_questions = int(payload.get("total_questions") or 0)
    correct_answers = int(payload.get("correct_answers") or 0)
    if not topic or total_questions <= 0:
        raise HTTPException(status_code=400, detail="topic ve total_questions zorunludur")

    quiz_date = payload.get("completed_at") or datetime.now(timezone.utc).isoformat()
    questions_attempted = payload.get("questions_attempted") or "[]"
    score = round((correct_answers / total_questions), 4) if total_questions else 0.0

    with app_cursor() as c:
        c.execute(
            """
            INSERT INTO quiz_attempts(
              user_id, quiz_date, topic, difficulty, total_questions,
              correct_answers, score, questions_attempted, start_time, end_time, total_duration_ms
            )
            VALUES (?,?,?,?,?,?,?,?,NULL,?,0)
            """,
            (current["id"], quiz_date, topic, difficulty, total_questions, correct_answers, score, questions_attempted, quiz_date)
        )
    return {"ok": True}



