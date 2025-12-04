# app/domain/repositories/question_repo.py

import hashlib
import json
import datetime as dt
from typing import List, Optional, Sequence

from app.core.db import questions_cursor
from app.domain.schemas.question import (
    QuestionModel,
    QuestionType,
    MCQQuestion,
    TrueFalseQuestion,
    ShortAnswerQuestion,
    OpenEndedQuestion,
    ScenarioQuestion,
    StepQuestion,
    ShortAnswerMatchingType,
    DifficultyLevel,
)


def _compute_question_hash(q: QuestionModel) -> str:
    """
    Aynı sorunun tekrar eklenmesini engellemek için
    soru içeriğinden deterministic bir hash üretir.
    """
    base = {
        "question_type": q.question_type.value,
        "topic": q.topic,
        "subtopic": q.subtopic,
        "difficulty": q.difficulty.value if isinstance(q.difficulty, DifficultyLevel) else q.difficulty,
        "stem": q.stem,
        "tags": sorted(q.tags or []),
    }

    if isinstance(q, MCQQuestion):
        base["options"] = q.options
        base["correct_option_indexes"] = sorted(q.correct_option_indexes)

    elif isinstance(q, TrueFalseQuestion):
        base["correct_answer"] = q.correct_answer

    elif isinstance(q, ShortAnswerQuestion):
        base["accepted_answers"] = sorted(q.accepted_answers or [])
        base["matching_type"] = (
            q.matching_type.value
            if isinstance(q.matching_type, ShortAnswerMatchingType)
            else q.matching_type
        )

    elif isinstance(q, OpenEndedQuestion):
        base["rubric"] = q.rubric

    elif isinstance(q, ScenarioQuestion):
        base["scenario"] = q.scenario
        steps_payload = []
        for s in q.steps:
            steps_payload.append(
                {
                    "step_id": s.step_id,
                    "step_type": s.step_type.value if isinstance(s.step_type, QuestionType) else s.step_type,
                    "stem": s.stem,
                    "max_score": s.max_score,
                    "options": s.options,
                    "correct_option_indexes": s.correct_option_indexes,
                    "correct_answer_bool": s.correct_answer_bool,
                    "accepted_answers": s.accepted_answers,
                    "matching_type": (
                        s.matching_type.value
                        if isinstance(s.matching_type, ShortAnswerMatchingType)
                        else s.matching_type
                    ) if s.matching_type else None,
                    "rubric": s.rubric,
                }
            )
        base["steps"] = steps_payload
        base["total_score"] = q.total_score

    as_str = json.dumps(base, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(as_str.encode("utf-8")).hexdigest()


def add_question(q: QuestionModel) -> int:
    """
    Yeni soruyu DB'ye ekler.

    - Hash'i burada hesaplıyoruz.
    - source_model None ise "unknown" kaydediyoruz.
    - UNIQUE hash sayesinde aynı soru tekrar gelirse
      INSERT OR IGNORE devreye girer, mevcut id'yi geri döneriz.
    """
    q_hash = _compute_question_hash(q)

    tags_json = json.dumps(q.tags or [], ensure_ascii=False)

    options_json = None
    correct_answer_json = None
    steps_json = None
    total_score = None
    scenario = None

    if isinstance(q, MCQQuestion):
        options_json = json.dumps(q.options, ensure_ascii=False)
        correct_answer_json = json.dumps(
            {"indexes": q.correct_option_indexes},
            ensure_ascii=False,
        )

    elif isinstance(q, TrueFalseQuestion):
        correct_answer_json = json.dumps(
            {"value": q.correct_answer},
            ensure_ascii=False,
        )

    elif isinstance(q, ShortAnswerQuestion):
        correct_answer_json = json.dumps(
            {
                "accepted_answers": q.accepted_answers,
                "matching_type": q.matching_type.value
                if isinstance(q.matching_type, ShortAnswerMatchingType)
                else q.matching_type,
            },
            ensure_ascii=False,
        )

    elif isinstance(q, OpenEndedQuestion):
        correct_answer_json = json.dumps(
            {"rubric": q.rubric},
            ensure_ascii=False,
        )

    elif isinstance(q, ScenarioQuestion):
        scenario = q.scenario
        steps_json = json.dumps(
            [s.model_dump() for s in q.steps],
            ensure_ascii=False,
        )
        total_score = q.total_score

    difficulty_value = (
        q.difficulty.value
        if isinstance(q.difficulty, DifficultyLevel)
        else q.difficulty
    )

    with questions_cursor() as c:
        c.execute(
            """
            INSERT OR IGNORE INTO questions
            (
                hash,
                question_type,
                topic,
                subtopic,
                difficulty,
                tags,
                stem,
                scenario,
                options_json,
                correct_answer_json,
                explanation,
                max_score,
                total_score,
                steps_json,
                source_model
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                q_hash,
                q.question_type.value,
                q.topic,
                q.subtopic,
                difficulty_value,
                tags_json,
                q.stem,
                scenario,
                options_json,
                correct_answer_json,
                q.explanation,
                q.max_score,
                total_score,
                steps_json,
                getattr(q, "source_model", None) or "unknown",
            ),
        )


        if c.lastrowid:
            return c.lastrowid

        # Aynı hash varsa mevcut id'yi bul
        c.execute("SELECT id FROM questions WHERE hash = ?", (q_hash,))
        row = c.fetchone()
        if not row:
            raise RuntimeError("Question insert failed and existing row not found")

        return row[0]


def _row_dict(row) -> dict:
    """
    sqlite3.Row / dict / tuple her ne geliyorsa
    düzgün bir dict'e çevirmek için yardımcı.
    """
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except TypeError:
        # Tuple ise, SELECT sırasına göre map etmemiz gerek
        raise RuntimeError("Row is not dict-like; please adjust SELECT / row_factory.")


def _row_to_question_model(row) -> QuestionModel:
    """
    DB satırını uygun QuestionModel tipine çevirir.
    """
    d = _row_dict(row)

    question_type = QuestionType(d["question_type"])
    difficulty = DifficultyLevel(d["difficulty"])

    tags = json.loads(d["tags"]) if d.get("tags") else []
    options = json.loads(d["options_json"]) if d.get("options_json") else None
    correct_raw = json.loads(d["correct_answer_json"]) if d.get("correct_answer_json") else None
    steps_raw = json.loads(d["steps_json"]) if d.get("steps_json") else None

    common_kwargs = {
        "id": d["id"],
        "question_type": question_type,
        "topic": d.get("topic"),
        "subtopic": d.get("subtopic"),
        "difficulty": difficulty,
        "tags": tags,
        "stem": d["stem"],
        "explanation": d.get("explanation"),
        "max_score": d.get("max_score", 1.0),
    }

    if question_type == QuestionType.MCQ:
        return MCQQuestion(
            **common_kwargs,
            options=options or [],
            correct_option_indexes=(correct_raw or {}).get("indexes", []),
        )

    if question_type == QuestionType.TRUE_FALSE:
        return TrueFalseQuestion(
            **common_kwargs,
            correct_answer=(correct_raw or {}).get("value", False),
        )

    if question_type == QuestionType.SHORT_ANSWER:
        accepted_answers = (correct_raw or {}).get("accepted_answers", [])
        matching_type_raw = (correct_raw or {}).get("matching_type", "case_insensitive")
        matching_type = ShortAnswerMatchingType(matching_type_raw)
        return ShortAnswerQuestion(
            **common_kwargs,
            accepted_answers=accepted_answers,
            matching_type=matching_type,
        )

    if question_type == QuestionType.OPEN_ENDED:
        rubric = (correct_raw or {}).get("rubric")
        return OpenEndedQuestion(
            **common_kwargs,
            rubric=rubric,
        )

    if question_type == QuestionType.SCENARIO:
        steps: List[StepQuestion] = []
        for s in steps_raw or []:
            step_type = QuestionType(s["step_type"])
            matching_type = (
                ShortAnswerMatchingType(s["matching_type"])
                if s.get("matching_type")
                else None
            )
            steps.append(
                StepQuestion(
                    step_id=s["step_id"],
                    step_type=step_type,
                    stem=s["stem"],
                    max_score=s.get("max_score", 1.0),
                    options=s.get("options"),
                    correct_option_indexes=s.get("correct_option_indexes"),
                    correct_answer_bool=s.get("correct_answer_bool"),
                    accepted_answers=s.get("accepted_answers"),
                    matching_type=matching_type,
                    rubric=s.get("rubric"),
                )
            )

        return ScenarioQuestion(
            **common_kwargs,
            scenario=d.get("scenario") or "",
            steps=steps,
            total_score=d.get("total_score") or 0.0,
        )

    raise ValueError(f"Unsupported question_type: {question_type}")


def get_all_questions(limit: int = 100, offset: int = 0) -> List[QuestionModel]:
    with questions_cursor() as c:
        c.execute(
            """
            SELECT
              id,
              hash,
              question_type,
              topic,
              subtopic,
              difficulty,
              tags,
              stem,
              scenario,
              options_json,
              correct_answer_json,
              explanation,
              max_score,
              total_score,
              steps_json,
              source_model,
              review_status,
              review_notes,
              reviewed_by,
              reviewed_at,
              created_at
            FROM questions
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = c.fetchall()

    out: List[QuestionModel] = []
    for row in rows:
        out.append(_row_to_question_model(row))

    return out


def get_random(
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    exclude_ids: Optional[Sequence[int]] = None,
) -> Optional[QuestionModel]:
    """
    Rastgele soru getirir.

    - topic None ise topic filtresi uygulanmaz.
    - difficulty:
        * None / "any" / "mixed" => difficulty filtresi uygulanmaz
        * "easy" / "medium" / "hard" gibi değerler => direkt filtre
    """
    sql = """
        SELECT
          id,
          hash,
          question_type,
          topic,
          subtopic,
          difficulty,
          tags,
          stem,
          scenario,
          options_json,
          correct_answer_json,
          explanation,
          max_score,
          total_score,
          steps_json,
          source_model,
          review_status,
          review_notes,
          reviewed_by,
          reviewed_at,
          created_at
        FROM questions
        WHERE 1=1
    """

    params: List = []

    if topic:
        sql += " AND topic = ?"
        params.append(topic)

    # difficulty None, "any" veya "mixed" ise filtreleme yapma
    if difficulty and difficulty.lower() not in ("any", "mixed"):
        sql += " AND difficulty = ?"
        params.append(difficulty)

    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        sql += f" AND id NOT IN ({placeholders})"
        params.extend(list(exclude_ids))

    sql += " ORDER BY RANDOM() LIMIT 1"

    with questions_cursor() as c:
        row = c.execute(sql, tuple(params)).fetchone()
        if not row:
            return None

        return _row_to_question_model(row)


def update_question_review(
    question_id: int,
    status: str,
    notes: Optional[str],
    reviewer_id: int,
) -> None:
    if status not in ("approved", "rejected", "pending"):
        raise ValueError("Geçersiz review_status")

    now = dt.datetime.utcnow().isoformat()

    with questions_cursor() as c:
        c.execute(
            """
            UPDATE questions
            SET review_status = ?,
                review_notes = ?,
                reviewed_by = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (status, notes, reviewer_id, now, question_id),
        )


def delete_question(question_id: int) -> bool:
    """
    Id'ye göre soruyu kalıcı olarak siler.
    Herhangi bir satır silindiyse True, yoksa False döner.
    """
    with questions_cursor() as c:
        c.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        return c.rowcount > 0
def map_level_to_db_difficulty(level: Optional[str]) -> Optional[str]:
    """
    UI'dan gelen level değerini (beginner / intermediate / advanced / mixed ...)
    DB'deki difficulty kolonuna çevirir.

    None veya tanınmayan bir değer dönerse => difficulty filtresi uygulanmaz.
    """
    if not level:
        return None

    lv = level.lower()

    if lv in ("mixed", "any"):
        # tüm zorluklardan karışık
        return None

    if lv in ("beginner", "easy"):
        return "easy"

    if lv in ("intermediate", "medium"):
        return "medium"

    if lv in ("advanced", "hard"):
        return "hard"

    # bilinmeyen değer: filtreleme yapmayalım
    return None