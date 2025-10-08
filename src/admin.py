"""
FastAPI Admin Endpoints - Backend için admin endpoint'leri

Bu dosya backend'inize eklenecek admin endpoint'lerini içerir.
Mevcut FastAPI uygulamanıza entegre edin.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import sqlite3
import jwt
from datetime import datetime
from passlib.context import CryptContext

router = APIRouter(prefix="/admin", tags=["admin"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# JWT secret key - .env dosyanızdan alın
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"

# Database connection
def get_db():
    conn = sqlite3.connect("data/questions/questions.db")
    conn.row_factory = sqlite3.Row
    return conn

# Verify admin user
async def verify_admin(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if user is admin
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return username
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/generate-random-question")
async def generate_random_question(username: str = Depends(verify_admin)):
    """
    Rastgele bir soru üretir ve veritabanına ekler.
    Ollama kullanarak soru üretimi yapılır.
    """
    # TODO: Ollama ile soru üretimi
    # Bu kısmı mevcut soru üretim fonksiyonunuzla değiştirin
    
    # Örnek soru (gerçek implementasyonda Ollama kullanın)
    question = {
        "id": f"q_{datetime.now().timestamp()}",
        "type": "mcq",
        "topic": "Random Topic",
        "level": "beginner",
        "stem": "This is a randomly generated question?",
        "choices": ["Option A", "Option B", "Option C", "Option D"],
        "answer_index": 0,
        "rationale": "This is the explanation for the correct answer.",
        "source": {
            "doc": "Generated",
            "chunk": 0,
            "topic": "Random"
        }
    }
    
    # Veritabanına ekle
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions (id, type, topic, level, stem, choices, answer_index, rationale, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        question["id"],
        question["type"],
        question["topic"],
        question["level"],
        question["stem"],
        str(question["choices"]),
        question["answer_index"],
        question["rationale"],
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    
    return question

@router.post("/generate-question")
async def generate_question_with_params(
    topic: str,
    level: str = "beginner",
    qtype: str = "mcq",
    username: str = Depends(verify_admin)
):
    """
    Belirtilen parametrelerle soru üretir ve veritabanına ekler.
    """
    # TODO: Ollama ile parametreli soru üretimi
    # Bu kısmı mevcut soru üretim fonksiyonunuzla değiştirin
    
    question = {
        "id": f"q_{datetime.now().timestamp()}",
        "type": qtype,
        "topic": topic,
        "level": level,
        "stem": f"This is a {qtype} question about {topic}?",
        "choices": ["Option A", "Option B", "Option C", "Option D"] if qtype == "mcq" else None,
        "answer_index": 0 if qtype == "mcq" else None,
        "answer": True if qtype == "true_false" else None,
        "expected": "Expected answer" if qtype in ["short_answer", "open_ended"] else None,
        "rationale": "This is the explanation.",
        "source": {
            "doc": "Generated",
            "chunk": 0,
            "topic": topic
        }
    }
    
    # Veritabanına ekle
    conn = get_db()
    cursor = conn.cursor()
    
    if qtype == "mcq":
        cursor.execute("""
            INSERT INTO questions (id, type, topic, level, stem, choices, answer_index, rationale, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question["id"], question["type"], question["topic"], question["level"],
            question["stem"], str(question["choices"]), question["answer_index"],
            question["rationale"], datetime.now().isoformat()
        ))
    elif qtype == "true_false":
        cursor.execute("""
            INSERT INTO questions (id, type, topic, level, stem, answer, rationale, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question["id"], question["type"], question["topic"], question["level"],
            question["stem"], question["answer"], question["rationale"], datetime.now().isoformat()
        ))
    else:
        cursor.execute("""
            INSERT INTO questions (id, type, topic, level, stem, expected, rationale, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question["id"], question["type"], question["topic"], question["level"],
            question["stem"], question["expected"], question["rationale"], datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    return question

@router.delete("/questions/{question_id}")
async def delete_question(question_id: str, username: str = Depends(verify_admin)):
    """
    Belirtilen ID'ye sahip soruyu veritabanından siler.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Question not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Question deleted successfully"}

# Database migration - users tablosuna is_admin kolonu ekleyin
def add_admin_column():
    """
    Mevcut users tablosuna is_admin kolonu ekler.
    Bu fonksiyonu bir kez çalıştırın.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        conn.commit()
        print("is_admin column added successfully")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("is_admin column already exists")
        else:
            raise
    finally:
        conn.close()

# İlk admin kullanıcısı oluşturma
def create_first_admin(username: str):
    """
    Belirtilen kullanıcıyı admin yapar.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    print(f"User {username} is now an admin")

@router.post("/create-first-admin")
async def create_first_admin_endpoint(username: str, email: str, password: str):
    """
    İlk admin kullanıcısını oluşturur.
    Sadece henüz hiç admin yoksa çalışır.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Zaten admin var mı kontrol et
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = 1")
    admin_count = cursor.fetchone()["count"]
    
    if admin_count > 0:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail="An admin user already exists. Use the admin panel to manage users."
        )
    
    # Kullanıcı zaten var mı kontrol et
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
    existing_user = cursor.fetchone()
    
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Şifreyi hashle
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(password)
    
    # Admin kullanıcısı oluştur
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, is_admin, created_at)
        VALUES (?, ?, ?, 1, ?)
    """, (username, email, hashed_password, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return {
        "message": "First admin user created successfully",
        "username": username,
        "email": email
    }
