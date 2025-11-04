# question.py
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import os

# Tekil DB yolu
DB_PATH = str(Path("data/questions/questions.db").resolve())

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hash TEXT UNIQUE,
        type TEXT,
        topic TEXT,
        level TEXT,
        stem TEXT,
        choices TEXT,
        answer_index INTEGER,
        rationale TEXT,
        source_model TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def _row_to_question(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "hash": row["hash"],
        "type": row["type"],
        "topic": row["topic"],
        "level": row["level"],
        "stem": row["stem"],
        "choices": json.loads(row["choices"]) if row["choices"] else [],
        "answer_index": row["answer_index"],
        "rationale": row["rationale"],
        "source_model": row["source_model"],
        "created_at": row["created_at"],
    }

def ensure_schema():
    """DB yoksa tabloyu oluşturur ve temel indeksleri ekler."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
      id INTEGER PRIMARY KEY,
      hash TEXT,
      type TEXT,
      topic TEXT,
      level TEXT,
      stem TEXT,
      choices TEXT,
      answer_index INTEGER,
      rationale TEXT,
      source_model TEXT,
      created_at TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_questions_level ON questions(level);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_hash ON questions(hash);")
    conn.commit()
    conn.close()

def get_all_questions(topic: Optional[str] = None,
                      level: Optional[str] = None,
                      limit: Optional[int] = None,
                      offset: int = 0) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    where = []
    params = []

    if topic:
        where.append("LOWER(topic) LIKE ?")
        params.append(f"%{topic.lower()}%")
    if level:
        where.append("LOWER(level) = ?")
        params.append(level.lower())

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit_sql = f" LIMIT {int(limit)} OFFSET {int(offset)}" if limit else ""

    cur.execute(f"""
        SELECT id, hash, type, topic, level, stem, choices, answer_index, rationale, source_model, created_at
        FROM questions
        {where_sql}
        ORDER BY created_at DESC, id DESC
        {limit_sql}
    """, params)

    rows = cur.fetchall()
    conn.close()
    return [_row_to_question(r) for r in rows]

def get_random_question(topic: Optional[str] = None,
                        level: Optional[str] = None,
                        exclude_ids: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
    """SQLite üzerinde gerçekten rastgele bir soru döndürür (ORDER BY RANDOM())."""
    exclude_ids = exclude_ids or []
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    where = []
    params = []

    if topic:
        where.append("LOWER(topic) LIKE ?")
        params.append(f"%{topic.lower()}%")
    if level:
        where.append("LOWER(level) = ?")
        params.append(level.lower())
    if exclude_ids:
        placeholders = ",".join("?" for _ in exclude_ids)
        where.append(f"id NOT IN ({placeholders})")
        params.extend(exclude_ids)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    cur.execute(f"""
        SELECT id, hash, type, topic, level, stem, choices, answer_index, rationale, source_model, created_at
        FROM questions
        {where_sql}
        ORDER BY RANDOM()
        LIMIT 1
    """, params)

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return _row_to_question(row)
