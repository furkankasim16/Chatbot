import sqlite3

conn = sqlite3.connect("quiz.db")
c = conn.cursor()

c.execute("ALTER TABLE users RENAME TO users_old")

c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# Eski verileri aktar
c.execute("""
INSERT INTO users (username, email, hashed_password, is_admin)
SELECT username, email, password_hash, is_admin FROM users_old
""")

conn.commit()
conn.close()

print("✅ users tablosu güncellendi (password_hash → hashed_password)")
