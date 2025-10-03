from fastapi import FastAPI,UploadFile, File , Query
from pydantic import BaseModel
import src.rag as rag 
import src.quiz as quiz
import src.question as question
import json, os, datetime
import traceback, logging, random
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
load_dotenv()



app = FastAPI(title="knowledge-bot", version="0.2.0")

# 🔥 CORS middleware buraya ekleniyor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme için herkese açık
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        n_chunks = rag.index_doc(file.filename, text, topic="product_basics")
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
async def make_quiz(topic: str, level: str = "beginner", n: int = 3):
    try:
        # 🔎 Sadece seçilen topic'e ait chunkları getir
        results = rag.search(topic, top_k=n, where={"topic": topic})

        passages = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        items = []
        for i, p in enumerate(passages):
            q = quiz.generate_mcq(p, topic, level)
            # metadata'dan gerçek topic bilgisi ekle
            if isinstance(q, dict):
                q["source"] = {
                    "doc": metadatas[i].get("doc_id", "unknown"),
                    "chunk": metadatas[i].get("chunk", -1),
                    "topic": metadatas[i].get("topic", topic)
                }
            items.append(q)

        response = {"items": items, "shuffle": True}

        # logla
        quiz.log_quiz(response)

        return response
    except Exception as e:
        import traceback
        logging.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}

@app.post("/questions/generate")
async def generate_question_endpoint(
    topic: str = Query(..., description="Soru konusu (örn: product_basics)"),
    level: str = Query("beginner", description="Zorluk seviyesi"),
    qtype: str = Query("mcq", description="Soru tipi: mcq | truefalse | openended | scenario")
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
    
    
    



