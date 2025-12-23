import sys
import os
import sqlite3
from passlib.context import CryptContext

sys.path.append(os.getcwd())
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_admin():
    db_path = settings.APP_DB_PATH
    print(f"Opening DB: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    username = "admin"
    password = "admin123"
    email = "admin@chatbot.com"
    hashed = get_password_hash(password)
    
    try:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing = cursor.fetchone()
        if existing:
            print(f"User '{username}' already exists. Updating password...")
            cursor.execute("""
                UPDATE users 
                SET hashed_password = ?, is_admin = 1 
                WHERE username = ?
            """, (hashed, username))
            conn.commit()
            print(f"User '{username}' password updated successfully.")
        else:
            cursor.execute("""
                INSERT INTO users (username, email, hashed_password, is_admin)
                VALUES (?, ?, ?, 1)
            """, (username, email, hashed))
            conn.commit()
            print(f"User '{username}' created successfully.")
    except Exception as e:
        print(f"Error seeding user: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_admin()
