# src/question.py
import os, re, json, sqlite3, random, hashlib, requests
from dotenv import load_dotenv
from src.rag import search

load_dotenv()

DB_PATH = "data/questions/questions.db"

# -----------------------
# Ollama Config
# -----------------------
OLLAMA_MODEL = "llama3:instruct"
OLLAMA_URL = "http://localhost:11434/api/generate"

QUESTION_TYPES = ["mcq", "truefalse", "openended", "scenario"]
TOPICS = ["product_basics", "support_flow", "security_policy"]
LEVELS = ["beginner", "intermediate", "advanced"]

# -----------------------
# Database Setup
# -----------------------
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hash TEXT UNIQUE,
        type TEXT,
        topic TEXT,
        level TEXT,
        stem TEXT,
        choices TEXT,
        answer_index INTEGER,
        rationale TEXT,
        source_model TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# -----------------------
# Helpers
# -----------------------
def question_hash(q: dict) -> str:
    raw = json.dumps({
        "type": q.get("type"),
        "topic": q.get("topic"),
        "level": q.get("level"),
        "stem": q.get("stem")
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def save_question(q: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    qhash = question_hash(q)
    try:
        c.execute("""
        INSERT INTO questions (hash, type, topic, level, stem, choices, answer_index, rationale, source_model)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            qhash,
            q.get("type"),
            q.get("topic"),
            q.get("level"),
            q.get("stem"),
            json.dumps(q.get("choices", []), ensure_ascii=False),
            q.get("answer_index"),
            q.get("rationale"),
            q.get("source_model", "ollama")
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"⚠️  Duplicate skipped: {q.get('stem')[:50]}")
    finally:
        conn.close()

def get_random_question(topic: str = None, level: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = "SELECT id, type, topic, level, stem, choices, answer_index, rationale, source_model, created_at FROM questions WHERE 1=1"
    params = []
    if topic:
        query += " AND topic=?"
        params.append(topic)
    if level:
        query += " AND level=?"
        params.append(level)
    query += " ORDER BY RANDOM() LIMIT 1"
    c.execute(query, params)
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "type": row[1],
        "topic": row[2],
        "level": row[3],
        "stem": row[4],
        "choices": json.loads(row[5]) if row[5] else [],
        "answer_index": row[6],
        "rationale": row[7],
        "source_model": row[8],
        "created_at": row[9],
    }

def get_all_questions(limit: int = 100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM questions ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "type": r[2],
            "topic": r[3],
            "level": r[4],
            "stem": r[5],
            "choices": json.loads(r[6]) if r[6] else [],
            "answer_index": r[7],
            "rationale": r[8],
            "source_model": r[9],
            "created_at": r[10]
        } for r in rows
    ]

# -----------------------
# Context & Prompt
# -----------------------

def get_context_for_topic(topic: str, n_chunks: int = 3):
    """Belirli topic'e göre filtrelenmiş RAG context getirir."""
    try:
        results = search(topic, top_k=n_chunks, filters={"topic": topic})
    except TypeError:
        # Eğer search() filters parametresi almıyorsa fallback
        results = search(topic, top_k=n_chunks)

    passages = []
    if "documents" in results:
        for doc_list in results["documents"]:
            passages.extend(doc_list)

    if not passages:
        return f"{topic} hakkında genel bilgi: temel kavramları öğretici biçimde açıkla."
    return "\n\n".join(passages)


def get_prompt_by_topic(topic: str, context: str, level: str, qtype: str):
    """Etiket bazlı akıllı prompt seçimi."""
    base_header = "Sen QuizBot adında bir yapay zekâ asistanısın.\n"

    if topic == "product_basics":
        return f"""{base_header}
Görevin: Rotamen ve Avansas sistemlerinin ürün işleyişi, Lucy/Lecy planlama, zone yönetimi ve mobil operasyon modülleri hakkında quiz soruları üretmek.
Belgelerde planlama algoritmaları, araç sıralama, xDock/Subzone yönetimi, teslimat ve raporlama süreçleri anlatılmaktadır.

Aşağıdaki metne dayanarak {level} seviyesinde, {qtype} formatında, teknik terimler içeren 3-5 soru oluştur:
- Belgede geçen terimleri (Lucy, Lecy, Subzone, Takas, Gün Sonu vb.) kullan.
- Her sorunun A, B, C şıkları olsun, açıklamalı doğru cevabı yaz.

Metin:
{context}
"""

    elif topic == "support_flow":
        return f"""{base_header}
Görevin: müşteri destek, teslimat sonrası süreçler ve saha operasyonları hakkında quiz soruları üretmek.
Belgelerde Lucy planlama, Rotamen–SAP entegrasyonu, müşteri SMS bildirimleri, adres öğrenme ve teslimat izleme konuları geçmektedir.

Aşağıdaki bilgilere dayanarak {level} seviyesinde {qtype} tipi sorular üret:
- Operasyon adımlarını, kullanıcı davranışlarını ve iletişim kurallarını sorgulasın.
- Her soru Türkçe, kısa, açıklamalı ve özgün olsun.

Metin:
{context}
"""

    elif topic == "security_policy":
        return f"""{base_header}
Görevin: ONUSS Şirket Prensipleri dokümanına dayanarak etik, gizlilik, bilgi güvenliği ve sosyal medya politikalarıyla ilgili quiz soruları üretmek.
Belgelerde bütünlük, çıkar çatışması, veri gizliliği, sosyal medya, iş etiği ve gizli bilgi paylaşımı gibi konular anlatılmaktadır.

Aşağıdaki metne dayanarak {level} seviyesinde {qtype} tipi sorular üret:
- Gizlilik, etik, veri güvenliği ve davranış kurallarını ölçsün.
- Şıklar açık, doğru cevap açıklamalı olmalı.

Metin:
{context}
"""

    else:
        return f"{base_header}\nKonu belirtilmemiş. Genel bilgi soruları oluştur.\n\n{context}"

# -----------------------
# Question Generation
# -----------------------
def generate_question_from_context(topic: str, level: str, qtype: str):
    try:
        context = get_context_for_topic(topic)
        prompt = get_prompt_by_topic(topic, context, level, qtype)

        res = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 4096, "num_predict": 512}
            }
        )

        if res.status_code != 200:
            return {"error": f"Ollama API hatası {res.status_code}", "detail": res.text}

        output = res.json().get("response", "")
        cleaned = output.strip().replace("```json", "").replace("```", "")
        matches = re.findall(r"\{[\s\S]*?\}", cleaned)
        if not matches:
            return {"error": "JSON bulunamadı", "raw": cleaned}

        for block in sorted(matches, key=len, reverse=True):
            try:
                q = json.loads(block)
                break
            except json.JSONDecodeError:
                continue
        else:
            return {"error": "Geçerli JSON parse edilemedi", "raw": cleaned}

        if q.get("type") == "mcq" and (not q.get("choices") or q.get("answer_index") is None):
            return {"error": "Eksik seçenek veya cevap", "raw": q}
        if not q.get("stem"):
            return {"error": "Soru metni eksik"}

        q["source_model"] = OLLAMA_MODEL
        save_question(q)
        return q

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
