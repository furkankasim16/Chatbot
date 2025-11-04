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
        UPDATE quiz_attempts SET end_time=?, correct_answers=?, score=?, total_duration_ms=?, questions_attempted=?
        WHERE id=?
        """, (data["end_time"], data["correct_answers"], data["score"], data["total_duration_ms"], data["questions_attempted"], data["attempt_id"]))

def add_question_timing(data: Dict[str, Any]) -> None:
    with app_cursor() as c:
        c.execute("""
        INSERT INTO question_timings(attempt_id, question_id, start_time, end_time, duration_ms)
        VALUES(?,?,?,?,?)
        """, (data["attempt_id"], data["question_id"], data.get("start_time"), data.get("end_time"), data.get("duration_ms")))

def add_time_event(data: Dict[str, Any]) -> None:
    with app_cursor() as c:
        c.execute("""
        INSERT INTO time_events(attempt_id, event_type, ts, meta_json)
        VALUES(?,?,?,?)
        """, (data["attempt_id"], data["event_type"], data["ts"], data.get("meta_json")))

def user_activity(limit: int = 100) -> List[dict]:
    with app_cursor() as c:
        c.execute("""
        SELECT qa.id, u.username, qa.topic, qa.difficulty, qa.total_questions,
               qa.correct_answers, qa.score, qa.start_time, qa.end_time, qa.total_duration_ms
        FROM quiz_attempts qa JOIN users u ON qa.user_id=u.id
        ORDER BY qa.id DESC LIMIT ?
        """, (limit,))
        rows = c.fetchall()
    out=[]
    for r in rows:
        out.append({
          "attempt_id": r[0], "username": r[1], "topic": r[2], "difficulty": r[3],
          "total_questions": r[4], "correct_answers": r[5], "score": r[6],
          "start_time": r[7], "end_time": r[8], "total_duration_ms": r[9]
        })
    return out
