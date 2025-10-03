# src/question.py
import requests, json, re, os, sqlite3, random
from src.rag import search
from dotenv import load_dotenv
load_dotenv()

DB_PATH = "data/questions.db"

# -------------------
# OpenRouter Config
# -------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

QUESTION_TYPES = ["mcq", "truefalse", "openended", "scenario"]
TOPICS = ["product_basics", "support_flow", "security_policy"]
LEVELS = ["beginner", "intermediate", "advanced"]

# -------------------
# DB INIT
# -------------------
def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        topic TEXT NOT NULL,
        level TEXT NOT NULL,
        stem TEXT NOT NULL,
        choices TEXT,
        answer_index INTEGER,
        rationale TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# -------------------
# DB HELPERS
# -------------------
def save_question(q: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO questions (type, topic, level, stem, choices, answer_index, rationale)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        q.get("type"),
        q.get("topic"),
        q.get("level"),
        q.get("stem"),
        json.dumps(q.get("choices", []), ensure_ascii=False),
        q.get("answer_index"),
        q.get("rationale")
    ))
    conn.commit()
    conn.close()

def get_random_question(topic: str = None, level: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = "SELECT * FROM questions WHERE 1=1"
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
        "created_at": row[8]
    }

# -------------------
# Context & Prompt
# -------------------
def get_context_for_topic(topic: str, n_chunks: int = 3):
    results = search(topic, top_k=n_chunks)
    passages = []
    if "documents" in results:
        for doc_list in results["documents"]:
            passages.extend(doc_list)
    return "\n\n".join(passages) if passages else "İçerik bulunamadı."

def build_prompt(topic, level, qtype, context):
    return f"""
Aşağıdaki pasajlara dayanarak {topic} konusunda {level} seviyesinde bir {qtype} soru üret.

⚠️ Kurallar:
1. ÇIKTIYI SADECE GEÇERLİ JSON OLARAK VER.
2. JSON dışında açıklama, yorum, metin, ```json``` blokları veya ekstra yazılar YASAKTIR.
3. Tüm içerik TÜRKÇE olacak.
4. Sorunun cevabı sadece pasajlardan çıkarılabilir olacak, UYDURMA bilgi ekleme.
5. Şemaya %100 UY:
   - "type": "{qtype}"
   - "topic": "{topic}"
   - "level": "{level}"
   - "stem": "SORU METNİ"
   - "choices": ["A) ...", "B) ...", "C) ...", "D) ..."] (sadece mcq için)
   - "answer_index": 0 (sadece mcq için)
   - "rationale": "Kısa açıklama"

Özel Kurallar:
- 'mcq' için: 1 doğru + 3 mantıklı çeldirici üret.
- 'truefalse' için: sadece "stem" + "rationale" üret. "choices" ve "answer_index" boş bırak.
- 'openended' için: sadece "stem" + "rationale" üret. "choices" ve "answer_index" boş bırak.
- 'scenario' için: "stem" vaka senaryosu, "rationale" açıklama. "choices" ve "answer_index" boş bırak.

ÇIKTI ÖRNEĞİ (mcq için):
{{
  "type": "mcq",
  "topic": "{topic}",
  "level": "{level}",
  "stem": "SORU METNİ",
  "choices": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "answer_index": 2,
  "rationale": "Kısa açıklama"
}}

Pasajlar:
{context}
"""

# -------------------
# Generate Question
# -------------------
def generate_question_from_context(topic: str, level: str, qtype: str, model: str = "mistral"):
    try:
        context = get_context_for_topic(topic, n_chunks=3)
        prompt = build_prompt(topic, level, qtype, context)

        # Ollama çağrısı
        import requests
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_ctx": 4096, "num_predict": 512}
            }
        )

        if res.status_code != 200:
            return {"error": f"Ollama API hatası {res.status_code}", "detail": res.text}

        raw_output = res.json().get("response", "")

        cleaned = raw_output.strip().replace("```json", "").replace("```", "")
        import re, json
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {"error": "JSON bulunamadı", "raw": cleaned}

        q = json.loads(match.group(0))
        q["source_model"] = model
        save_question(q)
        return q

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
