"""
FastAPI Authentication Backend
Bu dosyayı backend projenize ekleyin ve gerekli bağımlılıkları yükleyin:
pip install fastapi python-jose[cryptography] passlib[bcrypt] python-multipart
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
import sqlite3

# Güvenlik ayarları
SECRET_KEY = "your-secret-key-change-this-in-production"  # ÖNEMLİ: Production'da değiştirin!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 gün

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/auth", tags=["authentication"])

# Database helper
def get_db():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

# Database initialization
def init_users_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            completed_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

# Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

class QuizResult(BaseModel):
    topic: str
    difficulty: str
    total_questions: int
    correct_answers: int
    completed_at: str

class UserStats(BaseModel):
    total_quizzes: int
    total_questions: int
    correct_answers: int
    last_quiz_date: Optional[str]
    topic_stats: dict

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(username: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

# Endpoints
@router.post("/register", response_model=Token)
async def register(user: UserRegister):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (user.username, user.email))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Kullanıcı adı veya e-posta zaten kullanılıyor")
    
    # Create user
    hashed_password = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
        (user.username, user.email, hashed_password)
    )
    conn.commit()
    conn.close()
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "username": user["username"]}

@router.post("/submit-result")
async def submit_result(result: QuizResult, current_user = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO quiz_results (user_id, topic, difficulty, total_questions, correct_answers, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (current_user["id"], result.topic, result.difficulty, result.total_questions, 
          result.correct_answers, result.completed_at))
    
    conn.commit()
    conn.close()
    
    return {"message": "Sonuç kaydedildi"}

@router.get("/stats", response_model=UserStats)
async def get_stats(current_user = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    # Total stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_quizzes,
            SUM(total_questions) as total_questions,
            SUM(correct_answers) as correct_answers,
            MAX(completed_at) as last_quiz_date
        FROM quiz_results
        WHERE user_id = ?
    """, (current_user["id"],))
    
    stats = cursor.fetchone()
    
    # Topic stats
    cursor.execute("""
        SELECT 
            topic,
            SUM(correct_answers) as correct,
            SUM(total_questions) as total
        FROM quiz_results
        WHERE user_id = ?
        GROUP BY topic
    """, (current_user["id"],))
    
    topic_stats = {}
    for row in cursor.fetchall():
        topic_stats[row["topic"]] = {
            "correct": row["correct"],
            "total": row["total"]
        }
    
    conn.close()
    
    return {
        "total_quizzes": stats["total_quizzes"] or 0,
        "total_questions": stats["total_questions"] or 0,
        "correct_answers": stats["correct_answers"] or 0,
        "last_quiz_date": stats["last_quiz_date"],
        "topic_stats": topic_stats
    }


