# app/domain/repositories/question_repo.py

import hashlib
import json
import datetime as dt
from typing import Any, Dict, List, Optional, Sequence

from app.core.db import questions_cursor
from app.domain.schemas.question import (
    QuestionModel,
    QuestionType,
    MCQQuestion,
    QuestionUpdate,
    TrueFalseQuestion,
    ShortAnswerQuestion,
    OpenEndedQuestion,
    ScenarioQuestion,
    StepQuestion,
    ShortAnswerMatchingType,
    DifficultyLevel,
)
import sqlite3


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

                source_model,
                source_context
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                getattr(q, "source_context", None),
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

def _safe_json_load(raw: Optional[str], default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default

def _row_to_question_model(row) -> QuestionModel:
    (
        id_,
        hash_,
        question_type_raw,
        topic,
        subtopic,
        difficulty_raw,
        tags_json,
        stem,
        scenario,
        options_json,
        correct_answer_json,
        explanation,
        max_score,
        total_score,
        steps_json,
        source_model,
        source_context,
        review_status,
        review_notes,
        reviewed_by,
        reviewed_at,
        created_at,
    ) = row

    # --- Ortak alanlar ---

    # question_type
    try:
        qtype = QuestionType(question_type_raw)
    except Exception:
        # Eski/bozuk kayıtlar için default MCQ diyelim
        qtype = QuestionType.MCQ

    # difficulty
    try:
        difficulty = DifficultyLevel(difficulty_raw) if difficulty_raw else DifficultyLevel.MEDIUM
    except Exception:
        difficulty = DifficultyLevel.MEDIUM

    # tags
    try:
        tags = json.loads(tags_json) if tags_json else []
        if not isinstance(tags, list):
            tags = []
    except Exception:
        tags = []

    # options
    try:
        options = json.loads(options_json) if options_json else None
        if options is not None and not isinstance(options, list):
            options = None
    except Exception:
        options = None

    # correct_answer payload
    try:
        ca = json.loads(correct_answer_json) if correct_answer_json else {}
        if not isinstance(ca, dict):
            ca = {}
    except Exception:
        ca = {}

    # steps (sadece scenario için anlamlı)
    try:
        steps_data = json.loads(steps_json) if steps_json else []
        if not isinstance(steps_data, list):
            steps_data = []
    except Exception:
        steps_data = []

    # max_score / total_score default
    max_score_val = float(max_score) if max_score is not None else 1.0
    total_score_val = float(total_score) if total_score is not None else 0.0

    base_kwargs = dict(
        id=id_,
        question_type=qtype,
        topic=topic,
        subtopic=subtopic,
        difficulty=difficulty,
        tags=tags,
        stem=stem,
        explanation=explanation,
        max_score=max_score_val,
        source_model=source_model,
        source_context=source_context,
    )

    # --- Tip bazlı mapping ---

    # 1) MCQ
    if qtype == QuestionType.MCQ:
        mcq_options = options or []
        indexes = ca.get("indexes") or []
        if not isinstance(indexes, list):
            indexes = []
        return MCQQuestion(
            **base_kwargs,
            options=mcq_options,
            correct_option_indexes=indexes,
        )

    # 2) TRUE / FALSE
    if qtype == QuestionType.TRUE_FALSE:
        value = ca.get("value")
        # DB'de bool yerine string gelebilir diye korumalı dönüştür
        if isinstance(value, str):
            value_norm = value.strip().lower()
            if value_norm in ("true", "1", "yes"):
                value = True
            elif value_norm in ("false", "0", "no"):
                value = False
            else:
                value = False
        elif not isinstance(value, bool):
            value = False

        return TrueFalseQuestion(
            **base_kwargs,
            correct_answer=bool(value),
        )

    # 3) SHORT ANSWER
    if qtype == QuestionType.SHORT_ANSWER:
        accepted = ca.get("accepted_answers") or []
        if not isinstance(accepted, list):
            accepted = []

        matching_raw = ca.get("matching_type") or ShortAnswerMatchingType.CASE_INSENSITIVE.value
        try:
            matching = ShortAnswerMatchingType(matching_raw)
        except Exception:
            matching = ShortAnswerMatchingType.CASE_INSENSITIVE

        return ShortAnswerQuestion(
            **base_kwargs,
            accepted_answers=accepted,
            matching_type=matching,
        )

    # 4) OPEN ENDED
    if qtype == QuestionType.OPEN_ENDED:
        rubric = ca.get("rubric")
        return OpenEndedQuestion(
            **base_kwargs,
            rubric=rubric,
        )

    # 5) SCENARIO
    if qtype == QuestionType.SCENARIO:
        step_models: List[StepQuestion] = []

        for s in steps_data:
            if not isinstance(s, dict):
                continue

            step_type_raw = s.get("step_type") or QuestionType.MCQ.value
            try:
                step_qtype = QuestionType(step_type_raw)
            except Exception:
                step_qtype = QuestionType.MCQ

            # matching_type
            mt_raw = s.get("matching_type")
            mt_val: Optional[ShortAnswerMatchingType] = None
            if mt_raw:
                try:
                    mt_val = ShortAnswerMatchingType(mt_raw)
                except Exception:
                    mt_val = None

            step_models.append(
                StepQuestion(
                    step_id=s.get("step_id") or 0,
                    step_type=step_qtype,
                    stem=s.get("stem") or "",
                    max_score=float(s.get("max_score") or 1.0),
                    options=s.get("options"),
                    correct_option_indexes=s.get("correct_option_indexes"),
                    correct_answer_bool=s.get("correct_answer_bool"),
                    accepted_answers=s.get("accepted_answers"),
                    matching_type=mt_val,
                    rubric=s.get("rubric"),
                )
            )

        # total_score boşsa adımlardan hesapla
        if not total_score_val and step_models:
            total_score_val = sum(step.max_score for step in step_models)

        return ScenarioQuestion(
            **base_kwargs,
            scenario=scenario or "",
            steps=step_models,
            total_score=total_score_val,
        )

    # Tanımlanmayan tipler için fallback (MCQ gibi davran)
    return MCQQuestion(
        **base_kwargs,
        options=options or [],
        correct_option_indexes=ca.get("indexes") or [],
    )

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
              source_context,
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
          source_context,
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

def update_question_in_db(
    question_id: int,
    data: QuestionUpdate,
) -> Optional[QuestionModel]:
    """
    Basit metadata + cevap update (topic, question_type, difficulty, stem, options, correct_answer_json, scenario, steps_json).
    Güncel satırı QuestionModel olarak döner.
    """
    fields: list[str] = []
    values: list[object] = []

    # --- Basit alanlar ---
    if data.topic is not None:
        fields.append("topic = ?")
        values.append(data.topic)

    if data.question_type is not None:
        fields.append("question_type = ?")
        qtype_val = (
            data.question_type.value
            if hasattr(data.question_type, "value")
            else data.question_type
        )
        values.append(qtype_val)

    if data.difficulty is not None:
        fields.append("difficulty = ?")
        diff_val = (
            data.difficulty.value
            if hasattr(data.difficulty, "value")
            else data.difficulty
        )
        values.append(diff_val)

    if data.stem is not None:
        fields.append("stem = ?")
        values.append(data.stem)

    # --- SCENARIO metni ---
    if data.scenario is not None:
        fields.append("scenario = ?")
        values.append(data.scenario)

    # --- SCENARIO adımları: steps_json ---
    if data.steps is not None:
        # UI-only alanları (_clientId, _action) çıkart
        cleaned_steps: list[dict] = []
        for s in data.steps:
            # s hem dict hem pydantic objesi olabilir
            if hasattr(s, "model_dump"):
                obj = s.model_dump()
            else:
                obj = dict(s)

            obj.pop("_clientId", None)
            obj.pop("_action", None)
            cleaned_steps.append(obj)

        steps_json = json.dumps(cleaned_steps, ensure_ascii=False)
        fields.append("steps_json = ?")
        values.append(steps_json)

    # --- MCQ: options_json ---
    if data.options is not None:
        fields.append("options_json = ?")
        options_json = json.dumps(data.options, ensure_ascii=False)
        values.append(options_json)

    # --- correct_answer_json: soru tipine göre farklı payload ---
    correct_answer_json_str: Optional[str] = None

    # 1) MCQ -> {"indexes": [...]}
    if data.correct_option_indexes is not None:
        correct_answer_json_str = json.dumps(
            {"indexes": data.correct_option_indexes},
            ensure_ascii=False,
        )

    # 2) TRUE/FALSE -> {"value": true/false}
    elif data.correct_answer_bool is not None:
        correct_answer_json_str = json.dumps(
            {"value": data.correct_answer_bool},
            ensure_ascii=False,
        )

    # 3) SHORT ANSWER -> {"accepted_answers": [...], "matching_type": "..."}
    elif data.accepted_answers is not None or data.matching_type is not None:
        accepted = data.accepted_answers or []
        mtype_raw = data.matching_type or "case_insensitive"
        mtype_val = (
            mtype_raw.value
            if hasattr(mtype_raw, "value")
            else mtype_raw
        )
        correct_answer_json_str = json.dumps(
            {
                "accepted_answers": accepted,
                "matching_type": mtype_val,
            },
            ensure_ascii=False,
        )

    # 4) OPEN ENDED -> {"rubric": "..."}
    elif data.rubric is not None:
        correct_answer_json_str = json.dumps(
            {"rubric": data.rubric},
            ensure_ascii=False,
        )

    if correct_answer_json_str is not None:
        fields.append("correct_answer_json = ?")
        values.append(correct_answer_json_str)

    # Hiç alan yoksa update yapma
    if not fields:
        return None

    values.append(question_id)

    with questions_cursor() as c:
        sql = f"UPDATE questions SET {', '.join(fields)} WHERE id = ?"
        c.execute(sql, values)

        if c.rowcount == 0:
            return None

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
              source_context,
              review_status,
              review_notes,
              reviewed_by,
              reviewed_at,
              created_at
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        )
        row = c.fetchone()

    if not row:
        return None

    return _row_to_question_model(row)
