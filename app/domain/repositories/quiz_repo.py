from typing import Dict, Any, List
from app.core.db import app_cursor

def create_attempt(data: Dict[str, Any]) -> int:
    with app_cursor() as c:
        c.execute("""
        INSERT INTO quiz_attempts(user_id, quiz_date, topic, difficulty, total_questions, start_time)
        VALUES(?, date('now'), ?, ?, ?, ?)
        """, (data["user_id"], data["topic"], data["difficulty"], data["total_questions"], data["start_time"]))
        return c.lastrowid

def end_attempt(data: Dict[str, Any]) -> None:
    with app_cursor() as c:
        c.execute("""
        UPDATE quiz_attempts
        SET end_time=?, correct_answers=?, score=?, total_duration_ms=?, questions_attempted=?
        WHERE id=?
        """, (
            data["end_time"],
            data["correct_answers"],
            data["score"],
            data["total_duration_ms"],
            data["questions_attempted"],
            data["attempt_id"],
        ))

def add_question_timing(data: Dict[str, Any]) -> None:
    with app_cursor() as c:
        c.execute("""
        INSERT INTO question_timings(attempt_id, question_id, start_time, end_time, duration_ms)
        VALUES(?,?,?,?,?)
        """, (
            data["attempt_id"],
            data["question_id"],
            data.get("start_time"),
            data.get("end_time"),
            data.get("duration_ms"),
        ))

def add_time_event(data: Dict[str, Any]) -> None:
    with app_cursor() as c:
        c.execute("""
        INSERT INTO time_events(attempt_id, event_type, ts, meta_json)
        VALUES(?,?,?,?)
        """, (
            data["attempt_id"],
            data["event_type"],
            data["ts"],
            data.get("meta_json"),
        ))

def user_activity(limit: int = 100) -> List[dict]:
    with app_cursor() as c:
        c.execute("""
            SELECT
              qa.id,
              u.username,
              qa.quiz_date,
              qa.topic,
              qa.difficulty,
              qa.total_questions,
              qa.correct_answers,
              qa.score,
              qa.questions_attempted
            FROM quiz_attempts qa
            JOIN users u ON u.id = qa.user_id
            ORDER BY qa.id DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()

    out: List[dict] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "username": r["username"],
            "quiz_date": r["quiz_date"],
            "topic": r["topic"],
            "difficulty": r["difficulty"],
            "total_questions": r["total_questions"],
            "correct_answers": r["correct_answers"],
            "score": r["score"],
            "questions_attempted": r["questions_attempted"],
        })
    return out