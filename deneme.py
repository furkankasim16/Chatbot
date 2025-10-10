import sqlite3, json

DB_PATH = "data/questions/questions.db"

def list_questions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions ORDER BY created_at DESC")
    rows = cur.fetchall()

    print(f"📋 Toplam {len(rows)} soru bulundu\n")
    for r in rows:
        q = dict(r)
        try:
            q["choices"] = json.loads(q.get("choices", "[]"))
        except Exception:
            pass
        print(json.dumps(q, indent=2, ensure_ascii=False))
        print("-" * 80)
    conn.close()

if __name__ == "__main__":
    list_questions()
