from .db import questions_cursor, app_cursor

def init_questions_db():
    with questions_cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS questions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          hash TEXT UNIQUE,
          type TEXT, topic TEXT, level TEXT,
          stem TEXT, choices TEXT,
          answer_index INTEGER, rationale TEXT,
          source_model TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_hash ON questions(hash)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_questions_level ON questions(level)")

def init_app_db():
    with app_cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          email TEXT UNIQUE NOT NULL,
          hashed_password TEXT NOT NULL,
          is_admin INTEGER DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          quiz_date TEXT NOT NULL,
          topic TEXT NOT NULL,
          difficulty TEXT NOT NULL,
          total_questions INTEGER NOT NULL,
          correct_answers INTEGER DEFAULT 0,
          score REAL DEFAULT 0,
          questions_attempted TEXT,
          start_time TEXT, end_time TEXT, total_duration_ms INTEGER,
          FOREIGN KEY(user_id) REFERENCES users(id)
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS question_timings(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          attempt_id INTEGER NOT NULL,
          question_id TEXT NOT NULL,
          start_time TEXT, end_time TEXT, duration_ms INTEGER
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS time_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          attempt_id INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          ts TEXT NOT NULL,
          meta_json TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          action TEXT NOT NULL,
          details TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")