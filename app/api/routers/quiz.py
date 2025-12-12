from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import requests, os, json, re, sqlite3

from app.api.deps import (
    on_start_app_db,
    on_start_questions_db,
    get_current_user,
)
from app.core.db import app_cursor
from app.core.config import settings
from app.core.paths import APP_DB

from app.domain.repositories.quesitons_repo import (
    get_random,
    map_level_to_db_difficulty,
)
from app.domain.repositories.quiz_repo import add_time_event
from app.domain.services.audit_service import log_action

# 🔽 YENİ: normalize & build tek kaynaktan
from app.domain.services.quiz_build_service import (
    normalize_question,
    build_quiz_from_db,
)

router = APIRouter(prefix="/quiz")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:instruct")
DB_PATH = APP_DB

class QuizBuildIn(BaseModel):
    topic: str
    level: str = "beginner"
    n: int = 5
    qtype: str = "mcq"
    use_ollama: bool = False


class QuizBuildOut(BaseModel):
    items: List[Dict[str, Any]]
    shuffle: bool = True

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
- For mcq, always give exactly 4 distinct options
- Do NOT include text outside JSON
""".strip()


def _render_prompt(topic: str, level: str, qtype: str, count: int) -> str:
    return PROMPT_TEMPLATE.format(
        topic=topic,
        level=level,
        qtype=qtype,
        count=count,
    )


def _parse_ollama_json(text: str):
    t = (text or "").strip()
    m = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", t, flags=re.S)
    if m:
        t = m.group(1).strip()
    return json.loads(t)


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
    return data.get("questions", []) if isinstance(data, dict) else []

@router.post("/", response_model=QuizBuildOut)
def build_quiz(data: QuizBuildIn, _=Depends(on_start_questions_db)):

    # 🔹 Ollama ile üretim
    if data.use_ollama:
        raw_items = generate_questions_via_ollama(
            topic=data.topic,
            level=data.level,
            qtype=data.qtype,
            count=data.n,
        )

        items = []
        for q in raw_items:
            q.setdefault("topic", data.topic)
            q.setdefault("level", data.level)
            q.setdefault("qtype", data.qtype)

            meta = q.get("meta") or {}
            meta.setdefault("source", "ollama")
            meta.setdefault("lang", "tr")
            q["meta"] = meta

            items.append(normalize_question(q))

        return {"items": items, "shuffle": True}

    # 🔹 DB'den quiz
    items = build_quiz_from_db(
        topic=data.topic,
        level=data.level,
        n=data.n,
    )

    return {"items": items, "shuffle": True}

class QuizAttemptStartRequest(BaseModel):
    topic: str
    difficulty: str
    total_questions: int
    start_time: datetime
    mode: Optional[str] = None


@router.post("/attempt/start")
def start_quiz_attempt(
    payload: QuizAttemptStartRequest,
    current_user=Depends(get_current_user),
):
    user_id = current_user["id"]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO quiz_attempts (
            user_id, quiz_date, topic, difficulty,
            total_questions, start_time
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            payload.start_time.date().isoformat(),
            payload.topic,
            payload.difficulty,
            payload.total_questions,
            payload.start_time.isoformat(),
        ),
    )

    attempt_id = c.lastrowid
    conn.commit()
    conn.close()

    log_action(
        user_id=user_id,
        action="QUIZ_ATTEMPT_START",
        details=payload.model_dump() | {"attempt_id": attempt_id},
    )

    return {"attempt_id": attempt_id}
