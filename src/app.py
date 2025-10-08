from fastapi import FastAPI,UploadFile, File , Query
from pydantic import BaseModel
import src.rag as rag 
import src.quiz as quiz
from src.quiz import generate_quiz
import src.question as question
from src.auth import router, init_users_db
from src.admin import router as adminrouter
import json, os, datetime
import traceback, logging, random
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
load_dotenv()



app = FastAPI(title="knowledge-bot", version="0.2.0")

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL'iniz
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication router'ı ekle
app.include_router(router)

app.include_router(adminrouter)

# Uygulama başlatılırken veritabanını oluştur
@app.on_event("startup")
async def startup():
    init_users_db()
    
question.init_db()

logging.basicConfig(level=logging.DEBUG)

class Health(BaseModel):
    status: str = "ok"
    service: str = "knowledge-bot"

@app.get("/health", response_model=Health, tags=["system"])
def health():
    return Health()

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
        return {"status": "error", "detail": str(e)}

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

@app.post("/quiz")
def create_quiz(topic: str, level: str, n: int = 5):
    return generate_quiz(topic, level, n)

@app.post("/questions/generate_random")
async def generate_random_question_endpoint():
    """
    Yeni bir soru üretir (HuggingFace API + RAG context).
    DB'ye kaydeder ve soruyu JSON olarak döner.
    """
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
    qtype: str = Query(..., description="Soru tipi: mcq | truefalse | openended | scenario")
):
    """
    Yeni bir soru üretir (HuggingFace API + RAG context).
    DB'ye kaydeder ve soruyu JSON olarak döner.
    """
    q = question.generate_question_from_context(topic, level, qtype)
    if "error" not in q:
        question.save_question(q)
    return q

@app.get("/questions/random")
async def random_question(
    topic: str = Query(None, description="İsteğe bağlı: sadece bu topic için"),
    level: str = Query(None, description="İsteğe bağlı: sadece bu zorluk için")
):
    """
    DB'den rastgele bir soru getirir.
    """
    q = question.get_random_question(topic=topic, level=level)
    if q:
        return q
    return {"status": "error", "detail": "Veritabanında uygun soru bulunamadı"}    

@app.get("/questions/all")
async def list_questions():
    """
    DB'deki tüm soruları getirir (debug amaçlı).
    """
    return question.get_all_questions()
    
@app.get("/topics")
async def list_topics():
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
    
    
    



