# migrate_audit_logs.py

import sqlite3

DB_PATH = "app/storage/db/app.db"  # settings.APP_DB_PATH neyse onu yaz

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Zaten varsa hata almasın diye try/except
for sql in [
    "ALTER TABLE audit_logs ADD COLUMN entity_type TEXT;",
    "ALTER TABLE audit_logs ADD COLUMN entity_id INTEGER;",
]:
    try:
        cur.execute(sql)
    except Exception as e:
        print("Skip / already exists:", sql, "->", e)

conn.commit()
conn.close()
print("Migration OK")
