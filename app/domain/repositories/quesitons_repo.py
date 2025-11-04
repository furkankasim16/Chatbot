import json, random
from typing import List, Optional, Tuple
from pyparsing import Sequence
from app.core.db import questions_cursor
from app.domain.schemas.question import Question

def add_question(q: Question) -> int:
    choices_json = json.dumps(q.choices) if q.choices is not None else None
    with questions_cursor() as c:
        c.execute("""
        INSERT OR IGNORE INTO questions
          (hash, type, topic, level, stem, choices, answer_index, rationale, source_model)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (q.hash, q.type, q.topic, q.level, q.stem, choices_json, q.answer_index, q.rationale, q.source_model))
        return c.lastrowid

def get_all_questions(limit: int = 1000, offset: int = 0) -> List[Question]:
    with questions_cursor() as c:
        c.execute("""SELECT id, hash, type, topic, level, stem, choices, answer_index, rationale, source_model
                     FROM questions ORDER BY id DESC LIMIT ? OFFSET ?""", (limit, offset))
        rows = c.fetchall()
    out: List[Question] = []
    for (id_, h, t, topic, lvl, stem, choices, ai, rat, src) in rows:
        out.append(Question(
            id=id_, hash=h, type=t, topic=topic, level=lvl, stem=stem,
            choices=(json.loads(choices) if choices else None),
            answer_index=ai, rationale=rat, source_model=src
        ))
    return out

def get_random(topic: str, level: str, exclude_ids: Optional[Sequence[int]] = None) -> Optional[dict]:
    sql = "SELECT * FROM questions WHERE topic=? AND level=?"
    params: list = [topic, level]

    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        sql += f" AND id NOT IN ({placeholders})"
        params.extend(list(exclude_ids))

    sql += " ORDER BY RANDOM() LIMIT 1"

    with questions_cursor() as c:
        row = c.execute(sql, tuple(params)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["choices"] = json.loads(d.get("choices") or "[]")
        except Exception:
            d["choices"] = []
        return d
