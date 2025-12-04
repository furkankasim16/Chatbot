# scripts/migrate.py

import sqlite3
import json

from app.core.config import settings

DB_PATH = settings.QUESTIONS_DB_PATH

UNIFIED_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    hash TEXT NOT NULL UNIQUE,

    question_type TEXT NOT NULL,          -- "mcq", "true_false", "short_answer", "open_ended", "scenario"
    topic TEXT,
    subtopic TEXT,
    difficulty TEXT NOT NULL DEFAULT 'medium',
    tags TEXT,                            -- JSON array: ["algo","search"]

    stem TEXT NOT NULL,
    scenario TEXT,                        -- sadece scenario tipinde dolu

    options_json TEXT,                    -- mcq için
    correct_answer_json TEXT,             -- mcq/tf/short/open için

    explanation TEXT,
    max_score REAL NOT NULL DEFAULT 1.0,
    total_score REAL,                     -- scenario için (steps toplamı)

    steps_json TEXT,                      -- scenario için StepQuestion listesi JSON

    source_model TEXT,

    review_status TEXT,
    review_notes TEXT,
    reviewed_by INTEGER,
    reviewed_at TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_table_columns(cur: sqlite3.Cursor, table_name: str) -> list:
    cur.execute(f"PRAGMA table_info({table_name})")
    return [r[1] for r in cur.fetchall()]


def questions_table_exists(cur: sqlite3.Cursor) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='questions'"
    )
    return cur.fetchone() is not None


def ensure_unified_questions_table():
    """
    - Eğer questions tablosu yoksa: unified şemada sıfırdan oluşturur.
    - Eğer eski şemadaysa: eski veriyi yeni unified tabloya migrate eder.
    - Eğer zaten unified ise: hiçbir şey yapmaz.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not questions_table_exists(cur):
        print("[migrate_questions_unified] 'questions' tablosu hiç yok, unified tablo oluşturulacak.")
        cur.executescript(UNIFIED_CREATE_SQL)
        conn.commit()
        conn.close()
        print("[migrate_questions_unified] Yeni 'questions' tablosu (unified) oluşturuldu. İşlem bitti.")
        return

    # Tablo var, kolonlarına bakalım
    cols = get_table_columns(cur, "questions")

    # Zaten unified mı?
    if "question_type" in cols and "options_json" in cols and "correct_answer_json" in cols:
        print("[migrate_questions_unified] 'questions' tablosu zaten unified yapıda. İşlem yapılmadı.")
        conn.close()
        return

    print("[migrate_questions_unified] Eski questions tablosu bulundu, migration başlıyor...")

    # Eski tabloyu rename edelim
    cur.execute("ALTER TABLE questions RENAME TO questions_backup_old")

    # Yeni unified tabloyu oluştur (artık adı 'questions')
    cur.executescript(UNIFIED_CREATE_SQL)

    # Eski veriyi okuyalım
    cur.execute("SELECT * FROM questions_backup_old")
    old_rows = cur.fetchall()
    print(f"[migrate_questions_unified] Eski tablodan {len(old_rows)} satır okundu.")

    insert_sql = """
    INSERT INTO questions (
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
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for row in old_rows:
        d = dict(row)

        # Eski kolon isimlerini tolerant şekilde çekiyoruz
        q_id = d.get("id")
        q_hash = d.get("hash")
        old_type = d.get("type") or "mcq"   # eski sistemde genelde mcq
        topic = d.get("topic")
        level = d.get("level") or d.get("difficulty") or "medium"
        stem = d.get("stem")

        choices_raw = d.get("choices") or d.get("options_json") or "[]"
        answer_index = d.get("answer_index")
        explanation = d.get("rationale") or d.get("explanation")
        source_model = d.get("source_model") or "unknown"
        review_status = d.get("review_status")
        review_notes = d.get("review_notes")
        reviewed_by = d.get("reviewed_by")
        reviewed_at = d.get("reviewed_at")
        created_at = d.get("created_at")

        # Yeni unified mantık:
        question_type = "mcq"  # Eski veriyi komple mcq gibi kabul ediyoruz
        subtopic = None
        difficulty = level
        tags_json = "[]"       # şimdilik tag yok

        # choices JSON'u sağlam mı?
        try:
            options_json = choices_raw
            json.loads(options_json)
        except Exception:
            options_json = "[]"

        if answer_index is None:
            correct_answer_json = json.dumps({"indexes": []}, ensure_ascii=False)
        else:
            correct_answer_json = json.dumps({"indexes": [answer_index]}, ensure_ascii=False)

        scenario = None
        max_score = 1.0
        total_score = None
        steps_json = None

        cur.execute(
            insert_sql,
            (
                q_id,
                q_hash,
                question_type,
                topic,
                subtopic,
                difficulty,
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
                review_status,
                review_notes,
                reviewed_by,
                reviewed_at,
                created_at,
            ),
        )

    conn.commit()
    conn.close()

    print("[migrate_questions_unified] Migration tamamlandı. Eski tablo: questions_backup_old (istersen sonra silebilirsin).")


if __name__ == "__main__":
    ensure_unified_questions_table()
