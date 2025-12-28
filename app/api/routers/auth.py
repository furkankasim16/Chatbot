# app/api/routers/auth.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

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
    xp: int = 0
    level: int = 1

class UserStats(BaseModel):
    id: int
    total_quizzes: int
    total_questions: int
    correct_answers: int
    last_quiz_date: Optional[str]
    topic_stats: Dict[str, Dict[str, int]]
    
    # User Profile Data
    xp: int = 0
    level: int = 1

    # ⏱️ Quiz bazlı süreler (ms cinsinden)
    total_quiz_duration_ms: int = 0
    avg_quiz_duration_ms: float = 0.0

    # ⏱️ Soru bazlı süreler
    today_question_count: Optional[int] = 0
    total_questions_timed: int = 0
    total_question_duration_ms: int = 0
    avg_question_duration_ms: float = 0.0
    recommended_study_topics: List[str] = []

# ---------- Auth helpers ----------
import logging
logger = logging.getLogger("app.auth")

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    with app_cursor() as c:
        row = c.execute(
            "SELECT id, username, hashed_password, is_admin, xp, level FROM users WHERE username=?",
            (username,),
        ).fetchone()
    if not row:
        logger.warning(f"Login failed: User '{username}' not found.")
        return None
    if not verify_password(password, row["hashed_password"]):
        logger.warning(f"Login failed: Invalid password for user '{username}'.")
        return None
    
    logger.info(f"User '{username}' logged in successfully.")
    return {
        "id": row["id"], 
        "username": row["username"], 
        "is_admin": bool(row["is_admin"]),
        "xp": row["xp"] or 0,
        "level": row["level"] or 1
    }

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
        "xp": user["xp"],
        "level": user["level"],
    }

@router.get("/stats", response_model=UserStats, dependencies=[Depends(on_start_app_db)])
def user_stats(current=Depends(get_current_user)):
    user_id = current["id"]
    current_xp = current["xp"]
    current_level = current["level"]

    with app_cursor() as c:
        # 1) Toplam quiz, toplam sorular, toplam doğru, son tarih (mevcut mantık)
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

        # 2) topic bazında doğru/toplam (mevcut mantık)
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

        # 3) Quiz bazlı süreler (yalnızca duration'ı olan attempt'ler)
        time_row = c.execute(
            """
            SELECT
              COALESCE(SUM(total_duration_ms), 0) AS total_ms,
              AVG(total_duration_ms) AS avg_ms
            FROM quiz_attempts
            WHERE user_id=?
              AND total_duration_ms IS NOT NULL
              AND total_duration_ms > 0
            """,
            (user_id,),
        ).fetchone() or (0, 0)

        # 4) Soru bazlı süreler (question_timings üzerinden)
        qtime_row = c.execute(
            """
            SELECT
              COUNT(qt.id) AS total_questions_timed,
              COALESCE(SUM(qt.duration_ms), 0) AS total_question_duration_ms,
              AVG(qt.duration_ms) AS avg_question_duration_ms
            FROM question_timings qt
            JOIN quiz_attempts qa ON qa.id = qt.attempt_id
            WHERE qa.user_id = ?
              AND qt.duration_ms IS NOT NULL
            """,
            (user_id,),
        ).fetchone() or (0, 0, 0)

    topic_stats = {r[0]: {"correct": int(r[1]), "total": int(r[2])} for r in rows}

    total_quiz_duration_ms = int(time_row[0] or 0)
    avg_quiz_duration_ms = float(time_row[1] or 0.0)

    total_questions_timed = int(qtime_row[0] or 0)
    total_question_duration_ms = int(qtime_row[1] or 0)
    avg_question_duration_ms = float(qtime_row[2] or 0.0)

    # 💡 RECOMMENDATION ENGINE
    # Başarı oranı %60'ın altındaki konuları "Çalışılması Gerekenler" olarak öner.
    recommendations = []
    for topic_name, stats in topic_stats.items():
        total = stats["total"]
        correct = stats["correct"]
        if total > 0:
            rate = correct / total
            if rate < 0.6:
                recommendations.append(topic_name)
    
    # Hiç veri yoksa veya hepsi iyiyse rastgele bir konu öner (boş kalmasın)
    if not recommendations and not topic_stats:
         recommendations = ["Genel Tekrar (Henüz quiz çözmedin)"]
    elif not recommendations:
         recommendations = ["Tebrikler! Tüm konularda performansın iyi.", "Zorluğu artırmayı dene."]

    return {
        "id": user_id, 
        "xp": current_xp,
        "level": current_level,
        "total_quizzes": int(tq[0]),
        "total_questions": int(tq[1]),
        "correct_answers": int(tq[2]),
        "last_quiz_date": tq[3],
        "topic_stats": topic_stats,

        "total_quiz_duration_ms": total_quiz_duration_ms,
        "avg_quiz_duration_ms": avg_quiz_duration_ms,
        "total_questions_timed": total_questions_timed,
        "total_question_duration_ms": total_question_duration_ms,
        "avg_question_duration_ms": avg_question_duration_ms,
        "recommended_study_topics": recommendations,
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
    
    # --- GAMIFICATION: Award XP ---
    # Hatasiz kul olmaz, ama dogru cevap 10 XP olsun. Quiz bitirme bonusu 20 XP.
    xp_gained = (correct_answers * 10) + 20
    from app.domain.repositories.users_repo import add_xp
    xp_result = add_xp(current["id"], xp_gained)
    
    return {
        "ok": True, 
        "xp_gained": xp_gained, 
        "new_level": xp_result["new_level"],
        "level_up": xp_result["level_up"],
        "total_xp": xp_result["total_xp"]
    }




@router.get("/leaderboard")
def get_leaderboard(limit: int = 10):
    """
    XP'ye gore sirali liderlik tablosu.
    """
    from app.domain.repositories.users_repo import get_top_users
    return get_top_users(limit)

UserStats.model_rebuild()
