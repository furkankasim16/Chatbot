from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
import requests
import json
import chromadb
from chromadb.utils import embedding_functions
import re
import uuid
import hashlib

ALLOWED_TOPICS = {"security_policy", "support_flow", "product_basics"}
ALLOWED_LEVELS = {"beginner", "intermediate", "advanced"}

# -----------------------
# Config
# -----------------------
router = APIRouter(prefix="/admin", tags=["admin"])
SECRET_KEY = "furkan-super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE = "data/questions/questions.db"
USERDB = "quiz.db"
OLLAMA_URL = "http://localhost:11434"

# ChromaDB Setup
EMBED_MODEL = "intfloat/multilingual-e5-large"
client = chromadb.PersistentClient(path="chroma_data")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBED_MODEL
)
collection = client.get_or_create_collection(
    name="knowledge_bot",
    embedding_function=sentence_transformer_ef
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def _normalize_topic(topic: str) -> str:
    t = (topic or "").strip().lower().replace(" ", "_")
    if t == "product_basic":
        t = "product_basics"
    return t

def _normalize_level(level: str) -> str:
    l = (level or "").strip().lower()
    aliases = {"basic": "beginner", "mid": "intermediate", "adv": "advanced"}
    return aliases.get(l, l)

def _stable_hash(stem: str, choices: list, topic: str, level: str) -> str:
    payload = json.dumps(
        {"stem": stem.strip(), "choices": [str(c).strip() for c in choices], "topic": topic, "level": level},
        ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _answer_to_index(answer: str, choices: list) -> int:
    """
    Model 'A'/'B'… harfi verdiyse 0-3'e mapler; değilse choices içinde eşleşirse o index; yoksa 0.
    """
    if not choices:
        return 0
    a = (answer or "").strip()
    # Harf ise (A/B/C/D)
    if len(a) == 1 and a.upper() in "ABCD":
        return "ABCD".index(a.upper())
    # "A) ..." formatı gelmişse
    m = re.match(r"^\s*([A-Da-d])\)\s*", a)
    if m:
        return "ABCD".index(m.group(1).upper())
    # Metinle eşle
    for i, ch in enumerate(choices):
        if str(ch).strip().lower() == a.lower():
            return i
        # "A) ..." gibi şıklı choices varsa sadece metin kısmını karşılaştır
        m2 = re.match(r"^\s*[A-Da-d]\)\s*(.+)$", str(ch).strip())
        if m2 and m2.group(1).strip().lower() == a.lower():
            return i
    return 0

def _ensure_unique_hash_index():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_hash ON questions(hash);")
    conn.commit()
    conn.close()

# -----------------------
# Auth helpers
# -----------------------
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    conn = sqlite3.connect(USERDB)
    c = conn.cursor()
    c.execute("SELECT id, username, email, is_admin FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    print("👤 User from DB:", user)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": user[0],
        "username": user[1],
        "email": user[2],
        "is_admin": bool(user[3]),
    }

def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user

# -----------------------
# RAG helper
# -----------------------
def retrieve_context(topic: str, top_k: int = 3, max_chars: int = 3000) -> str:
    try:
        results = collection.query(
            query_texts=[topic],
            n_results=top_k,
            where={"topic": topic},
        )
        if not results["documents"][0]:
            results = collection.query(query_texts=[topic], n_results=top_k)

        chunks = results["documents"][0] if results["documents"] else []
        context = ""
        for chunk in chunks:
            if len(context) + len(chunk) <= max_chars:
                context += chunk + "\n\n"
            else:
                context += chunk[: max_chars - len(context)] + "..."
                break

        print(f"📚 Retrieved {len(chunks)} chunks for topic: {topic}")
        return context.strip()
    except Exception as e:
        print("❌ Error retrieving context:", e)
        return ""

# -----------------------
# Ollama Integration (Fixed)
# -----------------------
def generate_with_ollama_rag(question_type: str, topic: str, level: str, context: str) -> dict:
    """Ollama ile soru üretir (katı JSON formatlı, fallback destekli)."""

    type_map = {
        "mcq": "çoktan seçmeli (4 şık, A-B-C-D formatında)",
        "true_false": "doğru/yanlış",
        "short_answer": "kısa cevap",
        "open_ended": "açık uçlu",
        "scenario": "senaryo tabanlı",
    }

    type_desc = type_map.get(question_type, question_type)

    # Katı formatlı prompt
    prompt = f"""
SEN BİR QUIZ SORUSU ÜRETİCİSİSİN.
AŞAĞIDAKİ BAĞLAMA DAYANARAK SADECE 1 ADET {type_desc.upper()} SORUSU ÜRET.

BAĞLAM:
{context}

KONU: {topic}
ZORLUK: {level}

YANIT TALİMATLARI:
- SADECE GEÇERLİ JSON DÖN.
- JSON DIŞINDA HİÇBİR ŞEY YAZMA.
- JSON KOD BLOĞU, AÇIKLAMA VEYA YAZI EKLEME.
- SADECE "{{" İLE BAŞLA, "}}" İLE BİTİR.
- EĞER GEÇERLİ JSON ÜRETEMEZSEN, SADECE "ERROR_JSON" YAZ.

FORMAT:
{{
  "type": "{question_type}",
  "topic": "{topic}",
  "level": "{level}",
  "stem": "Soru metni",
  "choices": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "answer": "A",
  "answer_index": 0,
  "expected": "Beklenen kısa cevap",
  "rationale": "Kısa açıklama"
}}
"""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "llama3:instruct",  # Alternatif: "llama3.2"
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 800,
                    "format": "json"  # Yeni Ollama sürümlerinde JSON-only kip
                },
            },
            stream=True,
            timeout=None,
        )

        full_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        full_text += chunk["response"]
                except Exception:
                    continue

        print("🟢 Full Ollama response (first 800 chars):")
        print(full_text[:800])

        if not full_text.strip():
            print("⚠️ Ollama boş çıktı üretti.")
            raise ValueError("Empty response from Ollama")

        return parse_ollama_response(full_text, question_type, topic, level)

    except Exception as e:
        print("❌ Ollama error:", str(e))
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")


# -----------------------
# JSON Parsing (Robust)
# -----------------------
def parse_ollama_response(text: str, q_type: str, topic: str, level: str) -> dict:
    """Ollama yanıtını JSON olarak parse eder, fallback oluşturur."""
    print("📝 Parsing Ollama response...")
    text = text.strip()

    if "ERROR_JSON" in text:
        print("⚠️ Model explicitly returned ERROR_JSON.")
        return {
            "type": q_type,
            "topic": topic,
            "level": level,
            "stem": "Model geçerli JSON üretemedi.",
            "choices": ["A", "B", "C", "D"],
            "answer": "A",
            "answer_index": 0,
            "expected": "",
            "rationale": "Fallback question (ERROR_JSON returned).",
        }

    # JSON gövdesini regex ile ayıkla
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        print("⚠️ No JSON braces found in model output.")
        print("🔴 Raw model output:\n", repr(text[:500]))
        return {
            "type": q_type,
            "topic": topic,
            "level": level,
            "stem": text[:300] or "Model JSON dönmedi.",
            "choices": ["A", "B", "C", "D"],
            "answer": "A",
            "answer_index": 0,
            "expected": "",
            "rationale": "Fallback question (no JSON in response).",
        }

    json_text = match.group(0)
    print("🔍 Extracted JSON snippet:", json_text[:200])

    try:
        data = json.loads(json_text)
        question = {
            "type": data.get("type", q_type),
            "topic": data.get("topic", topic),
            "level": data.get("level", level),
            "stem": data.get("stem", "").strip(),
            "choices": data.get("choices", []),
            "answer": data.get("answer", ""),
            "answer_index": data.get("answer_index", 0),
            "expected": data.get("expected", ""),
            "rationale": data.get("rationale", ""),
        }
        print("✅ Parsed question:", question["stem"][:100])
        return question

    except Exception as e:
        print("❌ JSON parse error:", str(e))
        print("🔴 Raw model output (parse fail):", repr(text[:500]))
        return {
            "type": q_type,
            "topic": topic,
            "level": level,
            "stem": text[:300],
            "choices": [],
            "answer": "",
            "answer_index": 0,
            "expected": "",
            "rationale": f"Failed to parse JSON ({e})",
        }


# -----------------------
# Endpoints
# -----------------------
@router.post("/generate-random-question", tags=["admin"])
async def generate_random_question_rag(current_user: dict = Depends(get_current_admin_user)):
    import random
    types = ["mcq", "true_false", "short_answer"]
    topics = ["product_basics", "design_thinking", "user_research", "prototyping"]
    levels = ["beginner", "intermediate", "advanced"]

    q_type = random.choice(types)
    topic = random.choice(topics)
    level = random.choice(levels)

    context = retrieve_context(topic)
    if not context:
        raise HTTPException(status_code=404, detail=f"No documents found for topic '{topic}'.")

    question_data = generate_with_ollama_rag(q_type, topic, level, context)

    conn = sqlite3.connect(USERDB)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO questions (type, topic, level, stem, choices, answer, answer_index, expected, rationale)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            question_data["type"],
            question_data["topic"],
            question_data["level"],
            question_data["stem"],
            json.dumps(question_data["choices"], ensure_ascii=False),
            question_data["answer"],
            question_data["answer_index"],
            question_data.get("expected", ""),
            question_data.get("rationale", ""),
        ),
    )
    conn.commit()
    qid = c.lastrowid
    conn.close()
    print(f"💾 Question saved to DB with ID: {qid}")

    return {"status": "success", "question": {"id": qid, **question_data}}

@router.delete("/questions/{qid}", tags=["admin"])
async def delete_question(qid: int, current_user: dict = Depends(get_current_admin_user)):
    """Veritabanından bir soruyu siler."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id FROM questions WHERE id = ?", (qid,))
    row = c.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Question with id={qid} not found.")

    c.execute("DELETE FROM questions WHERE id = ?", (qid,))
    conn.commit()
    conn.close()

    print(f"🗑️ Question deleted with ID: {qid}")
    return {"status": "deleted", "id": qid}

@router.get("/user-activity")
async def get_user_activity(current_user: dict = Depends(get_current_admin_user)):
    """Admin panelinde: tüm kullanıcıların quiz aktivitelerini döner."""
    conn = sqlite3.connect(USERDB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            qa.id AS attempt_id,
            u.username AS username,
            qa.user_id,
            qa.quiz_date,
            qa.topic,
            qa.difficulty,
            qa.total_questions,
            qa.correct_answers,
            qa.score,
            qa.questions_attempted
        FROM quiz_attempts qa
        JOIN users u ON qa.user_id = u.id
        ORDER BY qa.quiz_date DESC
    """)
    
    rows = c.fetchall()
    conn.close()
    
    # Tüm sonuçları JSON olarak döndür
    results = []
    for row in rows:
        results.append({
            "id": row["attempt_id"],
            "user_id": row["user_id"],
            "username": row["username"],
            "quiz_date": row["quiz_date"],
            "topic": row["topic"],
            "difficulty": row["difficulty"],
            "total_questions": row["total_questions"],
            "correct_answers": row["correct_answers"],
            "score": row["score"],
            "questions_attempted": json.loads(row["questions_attempted"]) if row["questions_attempted"] else []
        })
    
    return results


def init_quiz_attempts_table():
    """Quiz attempts tablosunu oluşturur."""
    conn = sqlite3.connect(USERDB)
    conn.execute("PRAGMA foreign_keys = ON;")  # ✅ foreign key desteği
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quiz_date TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            score REAL NOT NULL,
            questions_attempted TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ quiz_attempts table created/verified")

@router.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında gerekli tabloları oluştur."""
    init_quiz_attempts_table()

# -----------------------
# 🔹 Generate Question by Topic-Level-Type
# -----------------------
@router.post("/generate-question", tags=["admin"])
async def generate_question_endpoint(
    topic: str,
    level: str,
    qtype: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Admin panelinden belirli konu, seviye ve türde soru üretir.
    """
    print(f"⚙️ Generating question: topic={topic}, level={level}, qtype={qtype}")

    context = retrieve_context(topic)
    if not context:
        raise HTTPException(status_code=404, detail=f"No context found for topic '{topic}'.")

    # Ollama'dan soru oluştur
    question_data = generate_with_ollama_rag(qtype, topic, level, context)

    # Veritabanına kaydet
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO questions (type, topic, level, stem, choices, answer, answer_index, expected, rationale)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            question_data["type"],
            question_data["topic"],
            question_data["level"],
            question_data["stem"],
            json.dumps(question_data["choices"], ensure_ascii=False),
            question_data.get("answer", ""),
            question_data.get("answer_index", 0),
            question_data.get("expected", ""),
            question_data.get("rationale", ""),
        ),
    )
    conn.commit()
    qid = c.lastrowid
    conn.close()

    print(f"💾 New question saved with ID {qid}")

    return {
        "status": "success",
        "question": {"id": qid, **question_data}
    }

