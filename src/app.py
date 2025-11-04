from fastapi import FastAPI, UploadFile, File, Query
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
import jwt
from pydantic import BaseModel
import src.rag as rag
import src.quiz as quiz
from src.quiz import generate_quiz
import src.question as question
import src.admin
from src.auth import router as authrouter, init_users_db
from src.admin import router as adminrouter
from src.evaluate import router as evaluaterouter
import json, os, datetime, traceback, logging, random
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from src import evaluate
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from pathlib import Path
import sqlite3
from typing import Optional


# ------------------------------
# ENVIRONMENT SETUP
# ------------------------------
load_dotenv()

# ------------------------------
# APP INITIALIZATION
# ------------------------------
app = FastAPI(title="knowledge-bot", version="0.2.1")

DB_PATH = str(Path("data/questions/questions.db").resolve())
quiz_path = str(Path("quiz.db").resolve())
# OAuth2 scheme (zaten varsa tekrar eklemeyin)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# JWT ayarları (zaten varsa tekrar eklemeyin)
SECRET_KEY = "furkan-super-secret-key"  # .env'den okumalısınız
ALGORITHM = "HS256"


class QuizStartReq(BaseModel):
    quiz_id: int

class QuizStartRes(BaseModel):
    attempt_id: int
    started_at: str  # ISO

class QuestionStartReq(BaseModel):
    attempt_id: int
    question_id: int
    started_at: Optional[str] = None  # backend default now()

class QuestionEndReq(BaseModel):
    attempt_id: int
    question_id: int
    ended_at: Optional[str] = None
    answer: Optional[str] = None
    correct: Optional[bool] = None
    elapsed_ms: Optional[int] = None  # hesaplayıp yazdırmak kolay olsun

class TimeEventReq(BaseModel):
    attempt_id: int
    event_type: str  # "focus", "blur", "visibility_hidden", "visibility_visible", "idle"
    ts: Optional[str] = None
    meta: Optional[dict] = None

class QuizEndReq(BaseModel):
    attempt_id: int
    ended_at: Optional[str] = None
    total_elapsed_ms: Optional[int] = None


# ✅ CORS SETTINGS (frontend için gerekli)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# ROUTER REGISTRATION
# ------------------------------
app.include_router(authrouter)     # Kullanıcı kayıt & login işlemleri
app.include_router(adminrouter)    # Admin panel API’leri (Ollama + RAG destekli)
app.include_router(evaluaterouter) # Cevap değerlendirme API'si



async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id") or payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        # burada artık numeric beklediğimiz garanti
        return int(user_id)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication")

# ------------------------------
# STARTUP CONFIG
# ------------------------------
@app.on_event("startup")
async def startup():
    """Uygulama başlarken veritabanlarını ve tabloları hazırla."""
    init_users_db()
    question.init_db()
    logging.info("✅ Databases initialized successfully.")

# ------------------------------
# LOGGING
# ------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# ------------------------------
# HEALTH CHECK
# ------------------------------
class Health(BaseModel):
    status: str = "ok"
    service: str = "knowledge-bot"

@app.get("/health", response_model=Health, tags=["system"])
def health():
    return Health()

# ✅ CORS test endpoint'i
@app.options("/__cors_test__")
def cors_test():
    return {"status": "ok"}

# ------------------------------
# FILE INDEXING (RAG)
# ------------------------------
@app.post("/index")
async def index(file: UploadFile = File(...)):
    try:
        raw = await file.read()
        text = rag.extract_text_from_file(file.filename, raw)
        if not text.strip():
            return {"status": "error", "detail": "No text extracted"}
        n_chunks = rag.index_doc(file.filename, text, topic="support_flow")
        return {"status": "indexed", "chunks": n_chunks}
    except Exception as e:
        logging.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}

# ------------------------------
# RAG SEARCH & DELETE
# ------------------------------
@app.get("/search")
async def search(q: str):
    results = rag.search(q)
    return results

@app.delete("/delete/{doc_id}")
async def delete(doc_id: str):
    result = rag.delete_doc(doc_id)
    return result

@app.delete("/delete_all")
async def delete_all():
    return rag.delete_all()

# ------------------------------
# QUIZ GENERATION
# ------------------------------
@app.post("/quiz")
def create_quiz(topic: str, level: str, n: int = 5):
    return generate_quiz(topic, level, n)

# ------------------------------
# QUESTION MANAGEMENT
# ------------------------------
@app.post("/questions/generate_random")
async def generate_random_question_endpoint():
    """Yeni bir rastgele soru üretir (HuggingFace API + RAG context)."""
    topic = random.choice(question.TOPICS)
    level = random.choice(question.LEVELS)
    qtype = random.choice(question.QUESTION_TYPES)
    q = question.generate_question_from_context(topic, level, qtype)
    if "error" not in q:
        question.save_question(q)
    return q

@app.post("/questions/generate")
async def generate_question_endpoint(
    topic: str = Query(..., description="Soru konusu (örn: product_basics)"),
    level: str = Query(..., description="Zorluk seviyesi"),
    qtype: str = Query(..., description="Soru tipi: mcq | truefalse | openended | scenario"),
):
    """Yeni bir soru üretir (HuggingFace API + RAG context)."""
    q = question.generate_question_from_context(topic, level, qtype)
    if "error" not in q:
        question.save_question(q)
    return q

@app.get("/questions/random")
async def random_question(
    topic: str = Query(None, description="İsteğe bağlı: sadece bu topic için"),
    level: str = Query(None, description="İsteğe bağlı: sadece bu zorluk için"),
    exclude: str = Query(None, description="Virgülle ayrılmış id listesi (örn: 1,2,3)")
):
    """DB'den rastgele bir soru getirir (exclude destekli)."""
    exclude_ids = []
    if exclude:
        try:
            exclude_ids = [int(x) for x in exclude.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="exclude virgülle ayrılmış tamsayılar olmalı")

    q = question.get_random_question(topic=topic, level=level, exclude_ids=exclude_ids)
    if not q:
        return JSONResponse({"detail": "Uygun soru bulunamadı"}, status_code=404, headers={"Cache-Control": "no-store"})

    return JSONResponse(q, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})

@app.get("/questions/all")
async def list_questions():
    """DB'deki tüm soruları getirir (debug amaçlı)."""
    questions = question.get_all_questions()
    return {"count": len(questions), "questions": questions}


# ------------------------------
# TOPICS LIST
# ------------------------------
@app.get("/topics")
async def list_topics():
    """ChromaDB'de kayıtlı topic’leri döner."""
    try:
        data = rag.collection.get()  # tüm chunk’ları al
        topics_count = {}

        for meta in data["metadatas"]:
            if "topic" in meta:
                t = meta["topic"]
                topics_count[t] = topics_count.get(t, 0) + 1

        return {"topics": topics_count}
    except Exception as e:
        logging.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}
if __name__ == "__main__":
    init_users_db()
@app.get("/questions/batch")
async def batch_questions(
    topic: str = Query(..., description="Soru konusu"),
    level: str = Query(..., description="Zorluk seviyesi"),
    count: int = Query(5, description="Kaç soru isteniyor", ge=1, le=20)
):
    """
    Tek istekle birden fazla farklı soru getirir.
    Veritabanında yeterli soru yoksa Ollama ile üretir.
    """
    import sqlite3
    import json
    from pathlib import Path
    
    # Database path (question.py'den alınmış)
    BASE_DIR = Path(__file__).resolve().parent
    DB_PATH = BASE_DIR / "data" / "questions" / "questions.db"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        query = """
            SELECT type, topic, level, stem, choices, answer_index, rationale, source_model 
            FROM questions 
            WHERE topic = ? AND level = ?
            ORDER BY RANDOM()
            LIMIT ?
        """
        
        c.execute(query, (topic, level, count))
        rows = c.fetchall()
        conn.close()
        
        questions = []
        for row in rows:
            questions.append({
                "type": row[0],
                "topic": row[1],
                "level": row[2],
                "stem": row[3],
                "choices": json.loads(row[4]) if row[4] else [],
                "answer_index": row[5],
                "rationale": row[6],
                "source_model": row[7],
            })
        
        # Eğer yeterli soru yoksa, eksik olanları Ollama ile üret
        if len(questions) < count:
            print(f"[BATCH] DB'de {len(questions)} soru bulundu, {count - len(questions)} yeni soru üretiliyor...")
            import random
            from src.question import generate_question_from_context, QUESTION_TYPES
            
            for _ in range(count - len(questions)):
                qtype = random.choice(QUESTION_TYPES)
                new_q = generate_question_from_context(topic, level, qtype)
                if "error" not in new_q:
                    questions.append(new_q)
        
        print(f"[BATCH] {len(questions)} soru döndürülüyor (topic={topic}, level={level})")
        return {"questions": questions, "count": len(questions)}
        
    except Exception as e:
        import traceback
        print(f"[ERROR] batch_questions failed: {e}")
        return {"status": "error", "detail": str(e), "trace": traceback.format_exc()}
    
@app.post("/question/start")
async def start_question(
    attempt_id: int = Query(..., description="Quiz attempt ID"),
    question_id: str = Query(..., description="Question ID"),
    user_id: int = Depends(get_current_user_id)  # <-- JWT'den otomatik çıkar
):
    """Soru zamanlamasını başlatır."""
    from datetime import datetime, timezone
    
    conn = sqlite3.connect(quiz_path)
    c = conn.cursor()
    
    start_time = datetime.now(timezone.utc).isoformat()
    
    c.execute(
        """
        INSERT INTO question_timings 
        (attempt_id, question_id, start_time)
        VALUES (?, ?, ?)
        """,
        (attempt_id, question_id, start_time)
    )
    
    timing_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[TIMING] Question started: timing_id={timing_id}, attempt_id={attempt_id}, question_id={question_id}")
    
    return {"timing_id": timing_id, "start_time": start_time}


@app.post("/question/end")
async def end_question(
    timing_id: int = Query(..., description="Question timing ID"),
    user_id: int = Depends(get_current_user_id)  # <-- JWT'den otomatik çıkar
):
    """Soru zamanlamasını sonlandırır."""
    from datetime import datetime, timezone
    
    conn = sqlite3.connect(quiz_path)
    c = conn.cursor()
    
    end_time = datetime.now(timezone.utc).isoformat()
    
    # Start time'ı al
    c.execute("SELECT start_time FROM question_timings WHERE id = ?", (timing_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Question timing not found")
    
    start_time_str = row[0]
    start_time = datetime.fromisoformat(start_time_str)
    end_time_dt = datetime.fromisoformat(end_time)
    
    # Süreyi hesapla (milliseconds)
    duration_ms = int((end_time_dt - start_time).total_seconds() * 1000)
    
    # Timing'i güncelle
    c.execute(
        """
        UPDATE question_timings 
        SET end_time = ?, duration_ms = ?
        WHERE id = ?
        """,
        (end_time, duration_ms, timing_id)
    )
    
    conn.commit()
    conn.close()
    
    print(f"[TIMING] Question ended: timing_id={timing_id}, duration={duration_ms}ms")
    
    return {"timing_id": timing_id, "duration_ms": duration_ms}

@app.post("/quiz/start")
async def start_quiz(
    topic: str = Query(..., description="Quiz topic"),
    difficulty: str = Query(..., description="Quiz difficulty"),
    user_id: int = Depends(get_current_user_id)  # <-- JWT'den otomatik çıkar
):
    """Quiz başlatır ve attempt_id döner."""
    from datetime import datetime, timezone
    
    conn = sqlite3.connect(quiz_path)
    c = conn.cursor()
    
    start_time = datetime.now(timezone.utc).isoformat()
    
    c.execute(
        """
        INSERT INTO quiz_attempts 
        (user_id, quiz_date, topic, difficulty, total_questions, correct_answers, score, questions_attempted, start_time)
        VALUES (?, ?, ?, ?, 0, 0, 0.0, '[]', ?)
        """,
        (user_id, start_time, topic, difficulty, start_time)
    )
    
    attempt_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[TIMING] Quiz started: attempt_id={attempt_id}, user_id={user_id}, topic={topic}, difficulty={difficulty}")
    
    return {"attempt_id": attempt_id, "start_time": start_time}


@app.post("/quiz/end")
async def end_quiz(
    attempt_id: int = Query(..., description="Quiz attempt ID"),
    user_id: int = Depends(get_current_user_id)  # <-- JWT'den otomatik çıkar
):
    """Quiz'i sonlandırır ve toplam süreyi hesaplar."""
    from datetime import datetime, timezone
    
    conn = sqlite3.connect(quiz_path)
    c = conn.cursor()
    
    end_time = datetime.now(timezone.utc).isoformat()
    
    # Start time'ı al
    c.execute("SELECT start_time FROM quiz_attempts WHERE id = ?", (attempt_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    
    start_time_str = row[0]
    start_time = datetime.fromisoformat(start_time_str)
    end_time_dt = datetime.fromisoformat(end_time)
    
    # Toplam süreyi hesapla (milliseconds)
    total_duration_ms = int((end_time_dt - start_time).total_seconds() * 1000)
    
    # Quiz'i güncelle
    c.execute(
        """
        UPDATE quiz_attempts 
        SET end_time = ?, total_duration_ms = ?
        WHERE id = ?
        """,
        (end_time, total_duration_ms, attempt_id)
    )
    
    conn.commit()
    conn.close()
    
    print(f"[TIMING] Quiz ended: attempt_id={attempt_id}, duration={total_duration_ms}ms")
    
    return {"attempt_id": attempt_id, "total_duration_ms": total_duration_ms}

@app.post("/time/event")
async def log_time_event(
    req: TimeEventReq,
    user_id: int = Depends(get_current_user_id)
):
    from datetime import datetime, timezone
    conn = sqlite3.connect(quiz_path)
    c = conn.cursor()
    ts = req.ts or datetime.now(timezone.utc).isoformat()
    c.execute("""
        INSERT INTO time_events (attempt_id, event_type, ts, meta_json)
        VALUES (?, ?, ?, ?)
    """, (req.attempt_id, req.event_type, ts, json.dumps(req.meta or {})))
    conn.commit()
    conn.close()
    print(f"[TIME EVENT] attempt={req.attempt_id}, event={req.event_type}")
    return {"ok": True}
    