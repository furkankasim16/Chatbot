from typing import Dict, Any, List
from app.core.db import app_cursor,questions_cursor
from app.domain.schemas.quiz import RecentAttemptOut

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
              qa.start_time,
              qa.end_time,
              qa.total_duration_ms,        -- ⭐ BURADA ARTIK VAR
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
            "start_time": r["start_time"],              # opsiyonel ama faydalı
            "end_time": r["end_time"],                  # opsiyonel
            "total_duration_ms": r["total_duration_ms"],# ⭐ FRONTEND BURAYI KULLANACAK
            "questions_attempted": r["questions_attempted"],
        })
    return out

def usage_stats_by_topic(user_id: int) -> List[Dict[str, Any]]:
    """
    Kullanıcının konu bazlı performansını hesaplar.
    """
    sql = """
    SELECT
        topic,
        COUNT(*) as total_quizzes,
        SUM(total_questions) as total_questions,
        SUM(correct_answers) as total_correct,
        AVG(score) as avg_score
    FROM quiz_attempts
    WHERE user_id = ? AND score IS NOT NULL
    GROUP BY topic
    ORDER BY avg_score DESC
    """
    
    with app_cursor() as c:
        c.execute(sql, (user_id,))
        rows = c.fetchall()
        
    out = []
    for r in rows:
        # SQLite row handling
        t = r["topic"] if isinstance(r, dict) else r[0]
        t_quizzes = r["total_quizzes"] if isinstance(r, dict) else r[1]
        t_questions = r["total_questions"] if isinstance(r, dict) else r[2]
        t_correct = r["total_correct"] if isinstance(r, dict) else r[3]
        avg = r["avg_score"] if isinstance(r, dict) else r[4]
        
        out.append({
            "topic": t,
            "total_quizzes": t_quizzes,
            "total_questions": t_questions,
            "total_correct": t_correct,
            "avg_score": round(avg, 1) if avg else 0
        })
    return out
def get_recent_attempts(limit: int = 5) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 5), 50))

    sql = """
    SELECT
      id,
      user_id,
      quiz_date,
      topic,
      difficulty,
      total_questions,
      correct_answers,
      score,
      total_duration_ms
    FROM quiz_attempts
    ORDER BY
      datetime(quiz_date) DESC,
      id DESC
    LIMIT ?
    """

    with app_cursor() as c:
        c.execute(sql, (limit,))
        rows = c.fetchall()

    # sqlite row_factory dict değilse tuple döner; ikisini de handle edelim
    out: List[Dict[str, Any]] = []
    cols = [
        "id",
        "user_id",
        "quiz_date",
        "topic",
        "difficulty",
        "total_questions",
        "correct_answers",
        "score",
        "total_duration_ms",
    ]

    for r in rows:
        if isinstance(r, dict):
            d = dict(r)
        else:
            d = {cols[i]: r[i] for i in range(len(cols))}

        # UI uyumluluğu için (stats ekranında sık görülen isimler)
        d.setdefault("created_at", d.get("quiz_date"))
        d.setdefault("status", None)
        d.setdefault("quiz_id", d.get("id"))  # quiz_id bekleyen yer varsa kırılmasın

        out.append(d)

    return out