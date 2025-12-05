from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests, os, json
import re
import re as regex
import sqlite3
from typing import Union
from app.api.deps import on_start_app_db, on_start_questions_db, get_current_user
from app.core.db import app_cursor
from app.domain.schemas.quiz import QuizStartIn, QuizEndIn, QuestionTimingIn, TimeEventIn
from app.domain.repositories.quiz_repo import add_time_event, create_attempt, end_attempt, add_question_timing
from app.domain.repositories.quesitons_repo import get_random, map_level_to_db_difficulty
from app.domain.schemas.question import QuestionModel, QuestionType
from app.core.config import settings
from app.core.paths import APP_DB, QUESTIONS_DB
from app.domain.services.audit_service import log_action

LEVEL_TO_DIFFICULTY = {
    "beginner": "easy",
    "intermediate": "medium",
    "advanced": "hard",
}

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:instruct")
DB_PATH = APP_DB

PROMPT_TEMPLATE = """
You are a strict quiz generator. Return STRICT JSON only, no prose.

Schema:
{
  "questions": [
    {
      "topic": "<string>",
      "level": "<beginner|intermediate|advanced>",
      "qtype": "<mcq|truefalse|short>",
      "question": "<string>",
      "options": ["<string>", "<string>", "<string>", "<string>"],
      "answer": "<string>",
      "meta": {"source":"ollama","lang":"tr"}
    }
  ]
}

Constraints:
- Language: Turkish
- topic = {topic}
- level = {level}
- qtype = {qtype}
- count = {count}
- For mcq, always give exactly 4 distinct options and make 'answer' be one of them.
- Do NOT include any text outside JSON. No markdown fences.
Generate now.
""".strip()

# 🔥 LLM tabanlı değerlendirme prompt'u
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

router = APIRouter(prefix="/quiz")

# --------------------------
# Response Models
# --------------------------
class QuizBuildIn(BaseModel):
    topic: str
    level: str = "beginner"
    n: int = 5
    qtype: str = "mcq"
    use_ollama: bool = False


class QuizAttemptStartRequest(BaseModel):
    topic: str
    difficulty: str
    total_questions: int
    start_time: datetime
    mode: Optional[str] = None


class QuizAttemptEndRequest(BaseModel):
    attempt_id: int
    correct_answers: int
    score: float
    total_duration_ms: int
    client_end_time: Optional[datetime] = None
    questions_attempted: Optional[str] = None


class QuizQuestionOut(BaseModel):
    id: Optional[int] = None
    topic: Optional[str] = None
    level: Optional[str] = None
    qtype: Optional[str] = None
    question: str
    options: Optional[List[str]] = None
    answer: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class QuizBuildOut(BaseModel):
    items: List[QuizQuestionOut]
    shuffle: bool = True


class QuizStartOut(BaseModel):
    attempt_id: int
    start_time: str


class TimingStartOut(BaseModel):
    timing_id: int
    start_time: str


class OkOut(BaseModel):
    ok: bool = True


class QuestionTimingStartRequest(BaseModel):
    attempt_id: int
    question_id: str
    client_start_time: Optional[datetime] = None


class QuestionTimingEndRequest(BaseModel):
    timing_id: int
    client_end_time: Optional[datetime] = None


class EvaluateAnswerIn(BaseModel):
    # ⚠️ Frontend ile birebir aynı isimler:
    # body: { question, expected, user_answer }
    question: str
    expected: Optional[str] = None
    user_answer: str


class EvaluateAnswerOut(BaseModel):
    is_correct: bool
    score: Optional[float] = None
    feedback: Optional[str] = None

class QuestionResultDetail(BaseModel):
    question_id: str
    stem: str
    user_answer: Union[str, List[str]]
    correct_answer: Union[str, List[str]]
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
def _render_prompt(topic: str, level: str, qtype: str, count: int) -> str:
    return PROMPT_TEMPLATE.format(topic=topic, level=level, qtype=qtype, count=count)


def _parse_ollama_json(text: str):
    t = (text or "").strip()
    m = regex.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", t, flags=regex.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        fixed = regex.sub(r"(?<!\\)'", '"', t)
        return json.loads(fixed)


def generate_questions_via_ollama(topic: str, level: str, qtype: str, count: int):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": _render_prompt(topic, level, qtype, count),
        "stream": False,
        "options": {"temperature": 0.7},
    }
    r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    data = _parse_ollama_json(r.json().get("response", ""))
    if isinstance(data, dict) and isinstance(data.get("questions"), list):
        return data["questions"]
    if isinstance(data, list):
        return data
    return []


def _get_id_safe(q: Any) -> Optional[int]:
    val = None
    if isinstance(q, dict):
        val = q.get("id")
    else:
        val = getattr(q, "id", None)
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _normalize_q(q: Any) -> Dict[str, Any]:
    # 1) dict
    if isinstance(q, dict):
        y = dict(q)

        if "type" not in y:
            if "question_type" in y:
                y["type"] = y["question_type"]
            elif "qtype" in y:
                y["type"] = y["qtype"]

        if not y.get("stem") and y.get("question"):
            y["stem"] = y["question"]

        if not y.get("options") and y.get("choices"):
            y["options"] = y["choices"]

        answer = y.get("answer")
        options = y.get("options")
        if answer is None and isinstance(options, list):
            ans_idx = y.get("answer_index")
            if isinstance(ans_idx, int) and 0 <= ans_idx < len(options):
                answer = options[ans_idx]

        if answer is None and isinstance(options, list):
            idxs = y.get("correct_option_indexes")
            if isinstance(idxs, list) and idxs:
                idx = idxs[0]
                if isinstance(idx, int) and 0 <= idx < len(options):
                    answer = options[idx]

        if answer is not None:
            y["answer"] = answer

        meta = y.get("meta") or {}
        meta.setdefault("lang", "tr")
        y["meta"] = meta

        if not y.get("question"):
            y["question"] = y.get("stem") or "—"

        return y

    # 2) Pydantic model
    if hasattr(q, "model_dump"):
        y = q.model_dump()

        if "type" not in y:
            if "question_type" in y:
                y["type"] = y["question_type"]
            elif "qtype" in y:
                y["type"] = y["qtype"]

        if not y.get("stem") and y.get("question"):
            y["stem"] = y["question"]

        if not y.get("options") and y.get("choices"):
            y["options"] = y["choices"]

        options = y.get("options")
        answer = y.get("answer")
        if answer is None and isinstance(options, list):
            ans_idx = y.get("answer_index")
            if isinstance(ans_idx, int) and 0 <= ans_idx < len(options):
                answer = options[ans_idx]

        if answer is None and isinstance(options, list):
            idxs = y.get("correct_option_indexes")
            if isinstance(idxs, list) and idxs:
                idx = idxs[0]
                if isinstance(idx, int) and 0 <= idx < len(options):
                    answer = options[idx]

        if answer is not None:
            y["answer"] = answer

        y.setdefault("meta", {"lang": "tr"})
        if not y.get("question"):
            y["question"] = y.get("stem") or "—"
        return y

    # 3) fallback
    y = {
        "id": getattr(q, "id", None),
        "topic": getattr(q, "topic", None),
        "level": getattr(q, "level", None),
        "type": getattr(q, "type", None) or getattr(q, "question_type", None),
        "stem": getattr(q, "stem", None) or getattr(q, "question", None),
        "options": getattr(q, "options", None) or getattr(q, "choices", None),
        "answer": getattr(q, "answer", None),
        "meta": getattr(q, "meta", None) or {"lang": "tr"},
    }

    options = y.get("options")
    ans_idx = getattr(q, "answer_index", None)
    if y.get("answer") is None and isinstance(ans_idx, int) and isinstance(options, list):
        if 0 <= ans_idx < len(options):
            y["answer"] = options[ans_idx]

    if not y.get("stem"):
        y["stem"] = "—"

    return y


# --------------------------
# Quiz Build
# --------------------------
@router.post("/", response_model=QuizBuildOut)
def build_quiz(data: QuizBuildIn, _=Depends(on_start_questions_db)):

    if data.use_ollama:
        items = generate_questions_via_ollama(
            topic=data.topic,
            level=data.level,
            qtype=data.qtype,
            count=data.n,
        )
        out = []
        for q in items:
            q = dict(q)
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

    for _ in range(data.n):
        q = get_random(
            topic=data.topic,
            difficulty=db_difficulty,
            exclude_ids=exclude,
        )
        if not q:
            break

        qid = getattr(q, "id", None)
        if qid is not None:
            exclude.append(qid)

        items.append(_normalize_q(q))

    return {"items": items, "shuffle": True}


# --------------------------
# Quiz Attempt (start/end)
# --------------------------
@router.post("/attempt/start")
def start_quiz_attempt(
    payload: QuizAttemptStartRequest,
    current_user=Depends(get_current_user),
):
    quiz_date = payload.start_time.date().isoformat()
    start_time_str = payload.start_time.isoformat()

    user_id = getattr(current_user, "id", current_user.get("id"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

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

    attempt_id = c.lastrowid
    conn.commit()
    conn.close()

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

    return {"attempt_id": attempt_id}


@router.post("/attempt/end", dependencies=[Depends(on_start_app_db)])
def end_quiz_attempt(payload: QuizAttemptEndRequest, current=Depends(get_current_user)):
    user_id = current["id"]

    server_end_time = datetime.now(timezone.utc).isoformat()
    end_time = payload.client_end_time or server_end_time

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
                end_time,
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
            "end_time": end_time,
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
@router.post("/question/start")
def start_question_timing(
    payload: QuestionTimingStartRequest,
    current_user=Depends(get_current_user),
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    start_dt = payload.client_start_time or datetime.utcnow()
    start_time_str = start_dt.isoformat()

    c.execute(
        """
        INSERT INTO question_timings (attempt_id, question_id, start_time)
        VALUES (?, ?, ?)
        """,
        (
            payload.attempt_id,
            payload.question_id,
            start_time_str,
        ),
    )

    timing_id = c.lastrowid
    conn.commit()
    conn.close()

    user_id = getattr(current_user, "id", current_user.get("id"))
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

    return {"timing_id": timing_id}


@router.post("/question/end")
def end_question_timing(
    payload: QuestionTimingEndRequest,
    current_user=Depends(get_current_user),
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    row = c.execute(
        "SELECT start_time FROM question_timings WHERE id = ?",
        (payload.timing_id,),
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Timing not found")

    start_time_str = row[0]

    end_dt = payload.client_end_time or datetime.utcnow()
    end_time_str = end_dt.isoformat()

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
        (
            end_time_str,
            duration_ms,
            payload.timing_id,
        ),
    )

    conn.commit()
    conn.close()

    user_id = getattr(current_user, "id", current_user.get("id"))
    log_action(
        user_id=user_id,
        action="QUIZ_QUESTION_TIMING_END",
        details={
            "timing_id": payload.timing_id,
            "end_time": end_time_str,
            "duration_ms": duration_ms,
        },
    )

    return {"success": True}


# --------------------------
# Genel Zaman Olayları
# --------------------------
@router.post("/time/event", response_model=OkOut)
def time_event(data: TimeEventIn, _=Depends(on_start_app_db)):
    add_time_event(data.model_dump())
    return {"ok": True}


# --------------------------
# Evaluate Answer (open-ended / scenario)
# --------------------------
def _normalize_answer(text: str) -> str:
    """
    Cevapları kıyaslamadan önce normalize et:
    - lowercase
    - baş/son boşlukları sil
    - noktalama işaretlerini kaldır
    - çoklu boşlukları tek boşluğa indir
    """
    text = text.lower().strip()
    text = re.sub(r"[.,!?;:]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _word_overlap_score(a: str, b: str) -> float:
    """
    İki cümle arasındaki kelime kesişimini oran olarak döndür (0.0–1.0).
    """
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


@router.post("/evaluate-answer", response_model=EvaluateAnswerOut)
def evaluate_answer_endpoint(
    payload: EvaluateAnswerIn,
    current_user=Depends(get_current_user),
):
    """
    Açık uçlu / senaryo soruları için LLM tabanlı değerlendirme.
    Hata olursa kelime benzerliği fallback'ine düşer.

    Frontend'den gelen body:
    {
      "question": "...",
      "expected": "...",       # optional
      "user_answer": "..."
    }
    """
    expected = payload.expected or ""
    user_answer = payload.user_answer or ""

    # 1) Önce LLM ile değerlendirmeyi dene
    try:
        prompt = f"""{LLM_EVAL_PROMPT}

QUESTION:
{payload.question}

EXPECTED (optional):
{expected or "N/A"}

STUDENT_ANSWER:
{user_answer}
"""

        r = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0},
            },
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json().get("response", "") or ""
        data = _parse_ollama_json(raw)

        score = float(data.get("score", 3))
        is_correct = bool(data.get("is_correct", score >= 4))
        feedback = data.get("feedback") or "LLM değerlendirmesi tamamlandı."

        return EvaluateAnswerOut(
            score=score,
            is_correct=is_correct,
            feedback=feedback,
        )

    except Exception as e:
        # 2) Hata olursa eski kelime-benzerliği fallback'ine dön
        sim = _word_overlap_score(expected, user_answer) if expected else 0.0

        if sim >= 0.8:
            score = 5
        elif sim >= 0.6:
            score = 4
        elif sim >= 0.4:
            score = 3
        elif sim >= 0.2:
            score = 2
        else:
            score = 1

        is_correct = score >= 4

        feedback_parts: list[str] = []
        feedback_parts.append(f"[Fallback] Similarity score: {sim:.2f}")
        if is_correct:
            feedback_parts.append("Your answer is close enough to the expected answer.")
        else:
            feedback_parts.append("Your answer differs significantly from the expected answer.")

        feedback = " ".join(feedback_parts)

        return EvaluateAnswerOut(
            score=score,
            is_correct=is_correct,
            feedback=feedback,
        )


@router.get("/attempts/recent", response_model=List[QuizAttemptHistoryOut])
def get_recent_attempts(
    limit: int = 10,
    current_user=Depends(get_current_user),
):
    """
    Aktif kullanıcının son N quiz denemesini döner.
    questions_attempted kolonundaki JSON'u parse edip
    QuestionResultDetail listesine çevirir.
    """
    user_id = getattr(current_user, "id", current_user.get("id"))

    rows: list[tuple] = []
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
            ORDER BY start_time DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    attempts: List[QuizAttemptHistoryOut] = []

    for row in rows:
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
                                # Bozuk item’ı atla
                                continue
                    questions = parsed
            except Exception:
                questions = None

        attempts.append(
            QuizAttemptHistoryOut(
                id=attempt_id,
                quiz_date=quiz_date,
                topic=topic,
                difficulty=difficulty,
                total_questions=total_questions or 0,
                correct_answers=correct_answers or 0,
                score=float(score or 0),
                start_time=start_time,
                end_time=end_time,
                total_duration_ms=total_duration_ms, 
                questions=questions,
            )
        )

    return attempts