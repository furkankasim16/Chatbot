from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pytest import Session
import requests,os,json
import re as regex
from app.api.deps import on_start_app_db, on_start_questions_db
from app.core.db import app_cursor
from app.domain.schemas.quiz import QuizStartIn, QuizEndIn, QuestionTimingIn, TimeEventIn
from app.domain.repositories.quiz_repo import add_time_event, create_attempt, end_attempt, add_question_timing
from app.domain.repositories.quesitons_repo import get_random
from app.domain.schemas.question import Question
from app.core.config import settings
from app.api.deps import get_current_user
import sqlite3
from src.auth import get_db  
from app.core.paths import APP_DB, QUESTIONS_DB
from app.domain.services.audit_service import log_action


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:instruct")  # qwen2.5:7b da olur
DB_PATH = APP_DB
PROMPT_TEMPLATE = """
You are a strict quiz generator. Return STRICT JSON only, no prose.

Schema:
{{
  "questions": [
    {{
      "topic": "<string>",
      "level": "<beginner|intermediate|advanced>",
      "qtype": "<mcq|truefalse|short>",
      "question": "<string>",
      "options": ["<string>", "<string>", "<string>", "<string>"],
      "answer": "<string>",
      "meta": {{"source":"ollama","lang":"tr"}}
    }}
  ]
}}

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

router = APIRouter(prefix="/quiz")

# --------------------------
# Response Models
# --------------------------
class QuizBuildIn(BaseModel):
    topic: str
    level: str = "beginner"
    n: int = 5
    qtype: str = "mcq"              # varsa kullan
    use_ollama: bool = False        # << eklendi

class QuizAttemptStartRequest(BaseModel):
    topic: str
    difficulty: str
    total_questions: int
    start_time: datetime
    mode: str | None = None

class QuizAttemptEndRequest(BaseModel):
    attempt_id: int
    correct_answers: int
    score: float
    total_duration_ms: int
    client_end_time: datetime | None = None 
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
    client_start_time: datetime | None = None  # opsiyonel

class QuestionTimingEndRequest(BaseModel):
    timing_id: int
    client_end_time: datetime | None = None    # opsiyonel


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
        fixed = regex.sub(r"(?<!\\)'", '"', t)  # tek tırnakları düzelt
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
    """
    Question objesi (Pydantic/ORM) veya dict olabilir.
    Güvenli şekilde id'yi int olarak döndür.
    """
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
    """
    Çıkışı dict'e normalize et (UI için stabil şema).
    DB kayıtları: stem, choices, answer_index, type
    LLM kayıtları: question, options, answer, qtype
    """
    # 1) dict ise doğrudan kopyasını al
    if isinstance(q, dict):
        y = dict(q)  # kopya

        # type -> qtype
        if "qtype" not in y and "type" in y:
            y["qtype"] = y.pop("type")

        # stem -> question
        if not y.get("question") and y.get("stem"):
            y["question"] = y["stem"]

        # choices -> options
        if not y.get("options") and y.get("choices"):
            y["options"] = y["choices"]

        # answer_index -> answer (metin)
        if not y.get("answer"):
            ans_idx = y.get("answer_index")
            opts = y.get("options")
            if isinstance(ans_idx, int) and isinstance(opts, list) and 0 <= ans_idx < len(opts):
                y["answer"] = opts[ans_idx]

        # meta güvenliği
        meta = y.get("meta") or {}
        meta.setdefault("lang", "tr")
        y["meta"] = meta

        # minimum garanti: question boş kalmasın (response_model zorunlu)
        if not y.get("question"):
            y["question"] = "—"

        return y

    # 2) Pydantic ise
    if hasattr(q, "model_dump"):
        y = q.model_dump()
        # type -> qtype gibi küçük eşitlemeler
        if "qtype" not in y and "type" in y:
            y["qtype"] = y.pop("type")
        if not y.get("question") and y.get("stem"):
            y["question"] = y["stem"]
        if not y.get("options") and y.get("choices"):
            y["options"] = y["choices"]
        if not y.get("answer"):
            ans_idx = y.get("answer_index")
            opts = y.get("options")
            if isinstance(ans_idx, int) and isinstance(opts, list) and 0 <= ans_idx < len(opts):
                y["answer"] = opts[ans_idx]
        y.setdefault("meta", {"lang": "tr"})
        if not y.get("question"):
            y["question"] = "—"
        return y

    # 3) ORM/başka tip ise alanları elde etmeye çalış
    y = {
        "id": getattr(q, "id", None),
        "topic": getattr(q, "topic", None),
        "level": getattr(q, "level", None),
        "qtype": getattr(q, "qtype", None) or getattr(q, "type", None),
        "question": getattr(q, "question", None) or getattr(q, "stem", None),
        "options": getattr(q, "options", None) or getattr(q, "choices", None),
        "answer": getattr(q, "answer", None),
        "meta": getattr(q, "meta", None) or {"lang": "tr"},
    }
    # answer_index -> answer
    ans_idx = getattr(q, "answer_index", None)
    if y.get("answer") is None and isinstance(ans_idx, int) and isinstance(y.get("options"), list):
        if 0 <= ans_idx < len(y["options"]):
            y["answer"] = y["options"][ans_idx]
    if not y.get("question"):
        y["question"] = "—"
    return y


# --------------------------
# Quiz Build (Soru seti)
# --------------------------

@router.post("/", response_model=QuizBuildOut)
def build_quiz(data: QuizBuildIn, _=Depends(on_start_questions_db)):
    if data.use_ollama:
        items = generate_questions_via_ollama(
            topic=data.topic, level=data.level, qtype=data.qtype, count=data.n
        )
        normalized = []
        for q in items:
            q = dict(q)
            q.setdefault("topic", data.topic)
            q.setdefault("level", data.level)
            q.setdefault("qtype", data.qtype)
            meta = q.get("meta") or {}
            meta.setdefault("source", "ollama")
            meta.setdefault("lang", "tr")
            q["meta"] = meta
            normalized.append(_normalize_q(q))  # senin mevcut normalize fonksiyonun
        return {"items": normalized, "shuffle": True}

    # mevcut DB yolu (aynı kalsın)
    items: List[Dict[str, Any]] = []
    exclude: List[int] = []
    for _i in range(data.n):
        q = get_random(topic=data.topic, level=data.level, exclude_ids=exclude)
        if not q: break
        qid = _get_id_safe(q)
        if qid is not None:
            exclude.append(qid)
        items.append(_normalize_q(q))
    return {"items": items, "shuffle": True}

    # aksi halde ESKİ DB YOLU (mevcut kodun aynen kalsın)
    items: List[Dict[str, Any]] = []
    exclude: List[int] = []
    for _i in range(data.n):
        q = get_random(topic=data.topic, level=data.level, exclude_ids=exclude)
        if not q:
            break
        qid = _get_id_safe(q)
        if qid is not None:
            exclude.append(qid)
        items.append(_normalize_q(q))
    return {"items": items, "shuffle": True}

# --------------------------
# Quiz Attempt (başlangıç/bitiş)
# --------------------------
@router.post("/attempt/start")
def start_quiz_attempt(
    payload: QuizAttemptStartRequest,
    current_user = Depends(get_current_user),
):
    quiz_date = payload.start_time.date().isoformat()
    start_time_str = payload.start_time.isoformat()

    user_id = getattr(current_user, "id", current_user["id"])

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

    # 🔹 Audit log
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

    # 🔹 Audit log
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
# Question Timing (başlangıç/bitiş)
# --------------------------
@router.post("/question/start")
def start_question_timing(
    payload: QuestionTimingStartRequest,
    current_user = Depends(get_current_user),
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

    # 🔹 Audit log
    user_id = getattr(current_user, "id", current_user["id"])
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
    current_user = Depends(get_current_user),
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

    # 🔹 Audit log
    user_id = getattr(current_user, "id", current_user["id"])
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
