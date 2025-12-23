# app/api/routers/quiz.py

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import on_start_app_db, on_start_questions_db, get_current_user
from app.core.config import settings
from app.core.db import app_cursor
from app.core.paths import APP_DB
from app.domain.repositories.quesitons_repo import get_random, map_level_to_db_difficulty
from app.domain.services.audit_service import log_action
from app.domain.services import llm_service
from app.domain.services.llm_service import LLMModel
from app.domain.schemas.evaluation import EvaluationResponse

router = APIRouter(prefix="/quiz", tags=["quiz"])

OLLAMA_HOST = os.getenv("OLLAMA_HOST", str(settings.OLLAMA_URL) if getattr(settings, "OLLAMA_URL", None) else "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", getattr(settings, "OLLAMA_MODEL", "llama3:instruct"))
DB_PATH = APP_DB


# --------------------------
# Request/Response Models
# --------------------------
class QuizBuildIn(BaseModel):
    topic: str
    level: str = "beginner"
    n: int = 5
    qtype: str = "mcq"
    use_ollama: bool = False


class QuizQuestionOut(BaseModel):
    id: Optional[Union[int, str]] = None
    topic: Optional[str] = None
    level: Optional[str] = None
    type: Optional[str] = None
    qtype: Optional[str] = None
    stem: Optional[str] = None
    question: str
    options: Optional[List[str]] = None
    choices: Optional[List[str]] = None
    answer_index: Optional[int] = None
    answer: Optional[Union[str, bool]] = None
    expected: Optional[str] = None
    expected_points: Optional[List[str]] = None
    rationale: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class QuizBuildOut(BaseModel):
    items: List[QuizQuestionOut]
    shuffle: bool = True


class QuizAttemptStartRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"   # fazladan alanlar 422 üretmesin
    )

    topic: str

    # level <-> difficulty uyumu
    difficulty: str = Field(alias="level")

    # n <-> total_questions uyumu
    total_questions: int = Field(alias="n")

    # client göndermezse server doldursun
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    mode: Optional[str] = None


class QuizStartOut(BaseModel):
    attempt_id: int
    start_time: str


class QuizAttemptEndRequest(BaseModel):
    attempt_id: int
    correct_answers: int
    score: float
    total_duration_ms: Optional[int] = None
    client_end_time: Optional[datetime] = None
    questions_attempted: Optional[str] = None


class OkOut(BaseModel):
    ok: bool = True


class QuestionTimingStartRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    attempt_id: int
    question_id: str
    client_start_time: Optional[datetime] = None



class TimingStartOut(BaseModel):
    timing_id: int
    start_time: str


class QuestionTimingEndRequest(BaseModel):
    timing_id: int
    client_end_time: Optional[datetime] = None


class TimingEndOut(BaseModel):
    success: bool = True
    duration_ms: Optional[int] = None


class EvaluateAnswerIn(BaseModel):
    question: str
    expected: Optional[str] = None
    user_answer: str


class EvaluateAnswerOut(BaseModel):
    is_correct: bool
    score: Optional[float] = None
    feedback: Optional[str] = None
    rubric: Optional[List[dict]] = None


class QuestionResultDetail(BaseModel):
    question_id: str
    stem: str
    user_answer: Union[str, List[str], None]
    correct_answer: Union[str, List[str], None]
    is_correct: bool
    eval_score: Optional[float] = None
    eval_feedback: Optional[str] = None


class QuizAttemptHistoryOut(BaseModel):
    id: int
    quiz_date: str
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    total_questions: int
    correct_answers: int
    score: float
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_duration_ms: Optional[int] = None
    questions: Optional[List[QuestionResultDetail]] = None


# --------------------------
# Helpers
# --------------------------



LLM_EVAL_PROMPT = """
You are a strict exam grader.

You will receive:
- The question
- (Optionally) the expected/ideal answer
- The student's answer

You must return STRICT JSON ONLY, with this schema:

{
  "score": 1-5,
  "is_correct": true or false,
  "feedback": "<short explanation in Turkish>"
}

Scoring rules:
- 5: Completely correct, excellent explanation
- 4: Mostly correct, small issues but acceptable
- 3: Partially correct, important gaps
- 2: Mostly incorrect, a few relevant points
- 1: Completely incorrect or off-topic

If no expected answer is provided, grade based on your own knowledge about the topic.
NO extra text, NO markdown, ONLY JSON.
""".strip()


def _uid(current_user: Any) -> int:
    # current_user dict ya da model olabilir
    val = None
    if isinstance(current_user, dict):
        val = current_user.get("id")
    else:
        val = getattr(current_user, "id", None)
    if val is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return int(val)


def _parse_ollama_json(text: str) -> Any:
    t = (text or "").strip()
    m = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", t, flags=re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # çok kaba bir düzeltme: tek tırnak -> çift tırnak
        fixed = re.sub(r"(?<!\\)'", '"', t)
        return json.loads(fixed)


def _normalize_q(q: Any) -> Dict[str, Any]:
    # API servisindeki Question tipine uyumlu normalize
    if isinstance(q, dict):
        y = dict(q)
    elif hasattr(q, "model_dump"):
        y = q.model_dump()
    else:
        y = {k: getattr(q, k, None) for k in ["id", "topic", "level", "qtype", "type", "question", "stem", "options", "choices", "answer", "answer_index", "expected", "expected_points", "rationale", "meta"]}

    # type/qtype uyumu
    if "type" not in y:
        if y.get("question_type"):
            y["type"] = y["question_type"]
        elif y.get("qtype"):
            y["type"] = y["qtype"]

    # stem/question uyumu
    if not y.get("stem") and y.get("question"):
        y["stem"] = y["question"]
    if not y.get("question") and y.get("stem"):
        y["question"] = y["stem"]
    if not y.get("question"):
        y["question"] = "—"

    # options/choices uyumu
    if not y.get("options") and y.get("choices"):
        y["options"] = y["choices"]

    # answer derivation
    options = y.get("options")
    if y.get("answer") is None and isinstance(options, list):
        ans_idx = y.get("answer_index")
        if isinstance(ans_idx, int) and 0 <= ans_idx < len(options):
            y["answer"] = options[ans_idx]

    meta = y.get("meta") or {}
    meta.setdefault("lang", "tr")
    y["meta"] = meta

    return y





def _normalize_answer(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[.,!?;:]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _word_overlap_score(a: str, b: str) -> float:
    a_norm = _normalize_answer(a)
    b_norm = _normalize_answer(b)
    if not a_norm or not b_norm:
        return 0.0
    a_words = set(a_norm.split())
    b_words = set(b_norm.split())
    if not a_words or not b_words:
        return 0.0
    overlap = len(a_words & b_words)
    union = len(a_words | b_words)
    return overlap / union


# --------------------------
# Quiz Build
# --------------------------
@router.post("/", response_model=QuizBuildOut)
async def build_quiz(data: QuizBuildIn, _=Depends(on_start_questions_db)):
    if data.use_ollama:
        # Async batch generation
        items = await llm_service.generate_batch(
            topic=data.topic,
            level=data.level,
            n=data.n,
            qtype=data.qtype,
            model=LLMModel.OLLAMA_LOCAL
        )
        
        out: List[dict] = []
        for q in items:
            q = dict(q)
            # generate_batch zaten meta vs ekliyor ama garanti olsun
            q.setdefault("topic", data.topic)
            q.setdefault("level", data.level)
            q.setdefault("qtype", data.qtype)
            meta = q.get("meta") or {}
            meta.setdefault("source", "ollama")
            meta.setdefault("lang", "tr")
            q["meta"] = meta
            out.append(_normalize_q(q))
        return {"items": out, "shuffle": True}

    exclude: List[int] = []
    items: List[dict] = []
    db_difficulty = map_level_to_db_difficulty(data.level)

    for _i in range(int(data.n)):
        q = get_random(topic=data.topic, difficulty=db_difficulty, exclude_ids=exclude)
        if not q:
            break
        qid = getattr(q, "id", None)
        if qid is not None:
            try:
                exclude.append(int(qid))
            except Exception:
                pass
        items.append(_normalize_q(q))

    return {"items": items, "shuffle": True}


# --------------------------
# Quiz Attempt (start/end)
# --------------------------
@router.post("/attempt/start", response_model=QuizStartOut)
def start_quiz_attempt(payload: QuizAttemptStartRequest, current_user=Depends(get_current_user)):
    user_id = _uid(current_user)

    quiz_date = payload.start_time.date().isoformat()
    start_time_str = payload.start_time.isoformat()

    with app_cursor() as c:
        c.execute(
            """
            INSERT INTO quiz_attempts (
              user_id,
              quiz_date,
              topic,
              difficulty,
              total_questions,
              start_time
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                quiz_date,
                payload.topic,
                payload.difficulty,
                payload.total_questions,
                start_time_str,
            ),
        )
        attempt_id = int(c.lastrowid)

    log_action(
        user_id=user_id,
        action="QUIZ_ATTEMPT_START",
        details={
            "attempt_id": attempt_id,
            "topic": payload.topic,
            "difficulty": payload.difficulty,
            "total_questions": payload.total_questions,
            "start_time": start_time_str,
            "mode": payload.mode,
        },
    )

    return QuizStartOut(attempt_id=attempt_id, start_time=start_time_str)


@router.post("/attempt/end", response_model=OkOut, dependencies=[Depends(on_start_app_db)])
def end_quiz_attempt(payload: QuizAttemptEndRequest, current_user=Depends(get_current_user)):
    user_id = _uid(current_user)

    server_end_time = datetime.now(timezone.utc)
    end_dt = payload.client_end_time or server_end_time
    end_time_str = end_dt.isoformat()

    with app_cursor() as c:
        row = c.execute(
            "SELECT id FROM quiz_attempts WHERE id=? AND user_id=?",
            (payload.attempt_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Quiz attempt not found")

        c.execute(
            """
            UPDATE quiz_attempts
            SET
              end_time = ?,
              total_duration_ms = COALESCE(?, total_duration_ms),
              correct_answers = ?,
              score = ?,
              questions_attempted = COALESCE(?, questions_attempted)
            WHERE id = ? AND user_id = ?
            """,
            (
                end_time_str,
                payload.total_duration_ms,
                payload.correct_answers,
                payload.score,
                payload.questions_attempted,
                payload.attempt_id,
                user_id,
            ),
        )

    log_action(
        user_id=user_id,
        action="QUIZ_ATTEMPT_END",
        details={
            "attempt_id": payload.attempt_id,
            "end_time": end_time_str,
            "correct_answers": payload.correct_answers,
            "score": payload.score,
            "total_duration_ms": payload.total_duration_ms,
            "questions_attempted": payload.questions_attempted,
        },
    )

    return {"ok": True}


# --------------------------
# Question Timing
# --------------------------
@router.post("/question/start", response_model=TimingStartOut)
def start_question_timing(payload: QuestionTimingStartRequest, current_user=Depends(get_current_user)):
    user_id = _uid(current_user)

    start_dt = payload.client_start_time or datetime.now(timezone.utc)
    start_time_str = start_dt.isoformat()

    with app_cursor() as c:
        c.execute(
            """
            INSERT INTO question_timings (attempt_id, question_id, start_time)
            VALUES (?, ?, ?)
            """,
            (payload.attempt_id, payload.question_id, start_time_str),
        )
        timing_id = int(c.lastrowid)

    log_action(
        user_id=user_id,
        action="QUIZ_QUESTION_TIMING_START",
        details={
            "timing_id": timing_id,
            "attempt_id": payload.attempt_id,
            "question_id": payload.question_id,
            "start_time": start_time_str,
        },
    )

    return TimingStartOut(timing_id=timing_id, start_time=start_time_str)


@router.post("/question/end", response_model=TimingEndOut)
def end_question_timing(payload: QuestionTimingEndRequest, current_user=Depends(get_current_user)):
    user_id = _uid(current_user)

    with app_cursor() as c:
        row = c.execute(
            "SELECT start_time FROM question_timings WHERE id = ?",
            (payload.timing_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Timing not found")

        start_time_str = row["start_time"] if isinstance(row, dict) else row[0]

        end_dt = payload.client_end_time or datetime.now(timezone.utc)
        end_time_str = end_dt.isoformat()

        duration_ms: Optional[int] = None
        try:
            start_dt = datetime.fromisoformat(start_time_str)
            duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
        except Exception:
            duration_ms = None

        c.execute(
            """
            UPDATE question_timings
            SET end_time = ?, duration_ms = ?
            WHERE id = ?
            """,
            (end_time_str, duration_ms, payload.timing_id),
        )

    log_action(
        user_id=user_id,
        action="QUIZ_QUESTION_TIMING_END",
        details={
            "timing_id": payload.timing_id,
            "end_time": end_time_str,
            "duration_ms": duration_ms,
        },
    )

    return TimingEndOut(success=True, duration_ms=duration_ms)


# --------------------------
# Evaluate Answer (open-ended / scenario)
# --------------------------
@router.post("/evaluate-answer", response_model=EvaluateAnswerOut)
async def evaluate_answer_endpoint(payload: EvaluateAnswerIn, current_user=Depends(get_current_user)):
    _ = _uid(current_user)  # sadece auth doğrulaması

    expected = payload.expected or ""
    user_answer = payload.user_answer or ""

    try:
        # Rubric-based evaluation via LLM Service
        result: EvaluationResponse = await llm_service.evaluate_answer_with_rubric(
            question=payload.question,
            expected_answer=expected or "",
            user_answer=user_answer,
            model=LLMModel.OLLAMA_LOCAL
        )

        # Log action
        log_action(
            user_id=_uid(current_user),
            action="QUIZ_EVALUATE_ANSWER",
            details={
                "question": payload.question,
                "score": result.score,
                "is_correct": result.is_correct
            }
        )

        return EvaluateAnswerOut(
            score=result.score,
            is_correct=result.is_correct,
            feedback=result.feedback,
            rubric=[r.model_dump() for r in result.rubric]
        )

    except Exception as e:
        # Fallback to simple similarity if LLM fails
        sim = _word_overlap_score(expected, user_answer) if expected else 0.0
        # ... validation logic ...
        score = 0
        if sim >= 0.8: score = 90
        elif sim >= 0.6: score = 75
        elif sim >= 0.4: score = 50
        elif sim >= 0.2: score = 25
        else: score = 10

        is_correct = score >= 70
        feedback = f"[Fallback] Benzerlik skoru: {sim:.2f}"
        return EvaluateAnswerOut(score=float(score), is_correct=is_correct, feedback=feedback, rubric=[])


# --------------------------
# Recent Attempts (current user)
# --------------------------
@router.get("/attempts/recent", response_model=List[QuizAttemptHistoryOut])
def get_recent_attempts(limit: int = 10, current_user=Depends(get_current_user)):
    user_id = _uid(current_user)
    limit = max(1, min(int(limit or 10), 50))

    with app_cursor() as c:
        rows = c.execute(
            """
            SELECT
              id,
              quiz_date,
              topic,
              difficulty,
              total_questions,
              correct_answers,
              score,
              start_time,
              end_time,
              total_duration_ms,
              questions_attempted
            FROM quiz_attempts
            WHERE user_id = ?
            ORDER BY start_time DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    out: List[QuizAttemptHistoryOut] = []

    for row in rows:
        # row dict olabilir (row_factory) ya da tuple olabilir
        if isinstance(row, dict):
            attempt_id = row["id"]
            quiz_date = row["quiz_date"]
            topic = row["topic"]
            difficulty = row["difficulty"]
            total_questions = row["total_questions"]
            correct_answers = row["correct_answers"]
            score = row["score"]
            start_time = row["start_time"]
            end_time = row["end_time"]
            total_duration_ms = row["total_duration_ms"]
            questions_json = row["questions_attempted"]
        else:
            (
                attempt_id,
                quiz_date,
                topic,
                difficulty,
                total_questions,
                correct_answers,
                score,
                start_time,
                end_time,
                total_duration_ms,
                questions_json,
            ) = row

        questions: Optional[List[QuestionResultDetail]] = None
        if questions_json:
            try:
                raw = json.loads(questions_json)
                if isinstance(raw, list):
                    parsed: List[QuestionResultDetail] = []
                    for item in raw:
                        if isinstance(item, dict):
                            try:
                                parsed.append(QuestionResultDetail(**item))
                            except Exception:
                                continue
                    questions = parsed
            except Exception:
                questions = None

        out.append(
            QuizAttemptHistoryOut(
                id=int(attempt_id),
                quiz_date=str(quiz_date),
                topic=topic,
                difficulty=difficulty,
                total_questions=int(total_questions or 0),
                correct_answers=int(correct_answers or 0),
                score=float(score or 0),
                start_time=start_time,
                end_time=end_time,
                total_duration_ms=total_duration_ms,
                questions=questions,
            )
        )

    return out
