import sqlite3
from contextlib import contextmanager
from app.core.paths import ensure_dirs
from app.core.config import settings

def _open_sqlite(db_path: str | bytes):
    ensure_dirs()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # sağlam bağlantı varsayılanları
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def get_questions_conn():
    return _open_sqlite(settings.QUESTIONS_DB_PATH)

def get_app_conn():
    return _open_sqlite(settings.APP_DB_PATH)

@contextmanager
def questions_cursor():
    conn = get_questions_conn()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()

@contextmanager
def app_cursor():
    conn = get_app_conn()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()