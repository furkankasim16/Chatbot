from fastapi import FastAPI, UploadFile, File, Query
from pydantic import BaseModel
import src.rag as rag
import src.quiz as quiz
from src.quiz import generate_quiz
import src.question as question
import src.admin
from src.auth import router as authrouter, init_users_db
from src.admin import router as adminrouter
import json, os, datetime, traceback, logging, random
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------
# ENVIRONMENT SETUP
# ------------------------------
load_dotenv()

# ------------------------------
# APP INITIALIZATION
# ------------------------------
app = FastAPI(title="knowledge-bot", version="0.2.1")

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
):
    """DB'den rastgele bir soru getirir."""
    q = question.get_random_question(topic=topic, level=level)
    if q:
        return q
    return {"status": "error", "detail": "Veritabanında uygun soru bulunamadı"}

@app.get("/questions/all")
async def list_questions():
    """DB'deki tüm soruları getirir (debug amaçlı)."""
    return question.get_all_questions()

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
